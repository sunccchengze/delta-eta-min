"""SU2 native mesh（MeshVersion=2）的最小读写器 + 离线质量体检。

存在的理由：S10′ 的判据里"拓扑检查（负体积/非流形）"必须在**开跑之前**能被验证，
而本仓不假设每台机器都装了 SU2。这里读的是**落盘的 .su2 文件本身**（= SU2 将看到的东西），
所以 gmsh 路径和 numpy 路径用同一把尺子量。

支持单元：LINE(3001) / TRIANGLE(3003) / QUAD(3005)。够用，不做通用性（范围纪律）。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

N_VERTS = {3001: 2, 3003: 3, 3005: 4}


@dataclass
class Su2Mesh:
    nodes: np.ndarray = field(default_factory=lambda: np.empty((0, 2)))
    cells: dict[int, np.ndarray] = field(default_factory=dict)   # vtype -> (n, k) 索引
    markers: dict[str, np.ndarray] = field(default_factory=dict)  # tag -> (n, 3) [vtype, n0, n1]
    ndime: int = 2
    version: int = 2

    @property
    def n_cells(self) -> int:
        return sum(len(v) for v in self.cells.values())


def parse_su2(path: str | Path) -> Su2Mesh:
    lines = [ln.strip() for ln in Path(path).read_text(encoding="utf-8").splitlines()]
    lines = [ln for ln in lines if ln and not ln.startswith("%")]
    m = Su2Mesh()
    cells: dict[int, list] = {}
    marker_elems: list[tuple[int, int, int, int]] = []   # (vtype, n0, n1, markid)
    pending_tag, pending_left = None, -1
    i = 0
    while i < len(lines):
        head, _, rest = lines[i].partition("=")
        key, rest = head.strip().upper(), rest.strip()
        try:
            if key == "NDIME":
                m.ndime = int(rest)
            elif key == "MESHVERSION":
                m.version = int(float(rest))
            elif key == "NELEM":
                for _ in range(int(rest)):
                    i += 1
                    t = lines[i].split()
                    vtype, idx, tail = int(t[0]), int(t[1]), t[2:]
                    nv = N_VERTS.get(vtype)
                    if nv is None:                       # 未知单元类型：不猜，直接停
                        raise NotImplementedError(f"不支持的单元类型 {vtype}（第 {i+1} 行）")
                    cells.setdefault(vtype, []).append([int(x) for x in tail[:nv]])
            elif key == "POIN":
                n = int(rest)
                arr = np.zeros((n, 2))
                for _ in range(n):
                    i += 1
                    t = lines[i].split()
                    arr[int(t[0])] = [float(t[1]), float(t[2])]
                m.nodes = arr
            elif key == "MARKER_TAG":
                pending_tag, pending_left = rest, -1
            elif key == "MARKER_ELEMS":
                pending_left = int(rest)
            elif key in ("NMARK", "MARKERS"):
                pass
            elif key == "":
                pass
            else:
                # marker 单元数据行：<vtype> <id> <n0> <n1> <markid>
                t = lines[i].split()
                if len(t) >= 5 and t[0].isdigit() and pending_left != 0:
                    vtype, n0, n1 = int(t[0]), int(t[2]), int(t[3])
                    marker_elems.append((vtype, n0, n1, pending_tag))
                    if pending_left > 0:
                        pending_left -= 1
        except ValueError as exc:
            raise ValueError(f"{path} 第 {i+1} 行解析失败：{lines[i]!r}") from exc
        i += 1

    m.cells = {k: np.asarray(v, dtype=int) for k, v in cells.items()}
    by_tag: dict[str, list] = {}
    for vtype, n0, n1, tag in marker_elems:
        by_tag.setdefault(tag, []).append([vtype, n0, n1])
    m.markers = {k: np.asarray(v, dtype=int) for k, v in by_tag.items()}
    return m


def quality_report(mesh: Su2Mesh) -> dict:
    """有向面积（2D 的"负体积"等价物）、非流形边、marker 一致性。"""
    area_min = math.inf
    flipped = 0
    edges: dict[tuple[int, int], int] = {}
    for vtype, arr in mesh.cells.items():
        p = mesh.nodes[arr]
        if vtype in (3003, 3005):
            a = 0.5 * np.sum(p[:, :, 0] * np.roll(p[:, :, 1], -1, axis=1)
                             - np.roll(p[:, :, 0], -1, axis=1) * p[:, :, 1], axis=1)
            flipped += int(np.sum(a <= 0))
            area_min = min(area_min, float(np.abs(a).min()))
        k = N_VERTS[vtype]
        for q in arr:
            for j in range(k):
                n0, n1 = int(q[j]), int(q[(j + 1) % k])
                key = (min(n0, n1), max(n0, n1))
                if k > 2:                                   # 只数体积单元的边
                    edges[key] = edges.get(key, 0) + 1
    counts = np.fromiter(edges.values(), int) if edges else np.array([0])
    n_used = {int(x) for a in mesh.cells.values() for x in a.ravel()}
    n_used |= {int(x) for arr in mesh.markers.values() for x in arr[:, 1:].ravel()}
    return {
        "ndime": mesh.ndime,
        "version": mesh.version,
        "n_nodes": int(len(mesh.nodes)),
        "n_nodes_referenced": len(n_used),
        "orphan_nodes": int(len(mesh.nodes) - len(n_used)),
        "n_cells": mesh.n_cells,
        "cells_by_type": {str(k): int(len(v)) for k, v in mesh.cells.items()},
        "flipped_or_zero_area_cells": flipped,
        "min_abs_cell_area": None if area_min is math.inf else float(area_min),
        "edges_nonmanifold": int(np.sum(counts > 2)),
        "markers": {t: {"elems": int(len(a)),
                        "types": sorted({int(x) for x in a[:, 0]}),
                        "bad_index": int(np.sum((a[:, 1] >= len(mesh.nodes))
                                               | (a[:, 2] >= len(mesh.nodes))))}
                    for t, a in mesh.markers.items()},
    }


def passes(rep: dict) -> bool:
    return (rep["flipped_or_zero_area_cells"] == 0
            and rep["edges_nonmanifold"] == 0
            and rep["orphan_nodes"] == 0
            and all(v["bad_index"] == 0 for v in rep["markers"].values())
            and len(rep["markers"]) >= 2)
