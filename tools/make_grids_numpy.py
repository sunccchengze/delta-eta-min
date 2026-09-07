"""S10′ 路径 B：纯 numpy 结构化 O-grid（除 numpy 外零依赖）。

为什么要有这个文件
------------------
本沙箱实测：`pip install gmsh` 后 `import gmsh` 直接
`OSError: libGLU.so.1` —— 干净 Linux / 精简 Windows 上 GUI 依赖缺失是**真实故障**
（见 BLOCKERS.md #1）。GCI 只要求三档拓扑一致 + 细化比 ≥1.3，不挑网格是谁生成的，
所以路径 B 与 `tools/make_grids.py`（gmsh 路径）互为卡壳预案。

口径纪律
--------
* 三档必须来自**同一条路径**。L1 用 gmsh、L3 用 numpy 会让 p_obs 失去意义。
* 法向用**与 nr 无关的连续映射** s(η)=(e^{κη}−1)/(e^{κ}−1)·D 均匀取样，于是：
  - 三档是**嵌套网格**（L1 节点集 ⊂ L2 ⊂ L3，`tests/test_mesh_tools.py` 逐点验证）；
  - `h_eq = sqrt(A/N)` 严格减半 ⇒ GCI 的细化比 **r=2 是精确成立的**（两向同步翻倍）；
  - 首层厚度比是 0.47–0.48 而非 0.5：指数聚层映射在 η→0 处非线性（e^{κ/nr}−1 不是 1/nr 的
    线性函数）。**这是实测值，别在报告里写"严格减半"**；要写就写 h_eq 口径减半、
    近壁间距实测比 ~0.47，并把 manifest 里的数一并交出。
  （反面教训：本文件初版用"固定拉伸比 + 每档解 Δ_0"，首层厚度变成 0.142/0.018/0.0004，
  细化比在法向完全不成立，GCI 直接失真。）
* 与 .geo 路径的两处已知差异（不是 bug，是口径）：
  1) 远场：本文件是法向等距外推的"圆角翼型"封闭外边界；.geo 是 20c×20c 方框。
  2) 尾缘：本文件用闭合尾缘系数 −0.1015；手册 .geo 用 −0.1036（开口尾缘）。

用法
----
    python tools/make_grids_numpy.py                # 出 L1/L2/L3 + manifest
    python tools/make_grids_numpy.py --only L1      # 单档
    python tools/make_grids_numpy.py --check        # 只跑拓扑/质量体检，不写文件
    python tools/make_grids_numpy.py --preview      # 另存 mesh/preview_{L}.png
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]

# ── 算例与档位定义（配置区 = 原 S06「档位定义」，不单开模块）─────────────────
CHORD = 1.0
THICKNESS = 0.12
TE_COEFF = -0.1036          # 闭合尾缘：0.2969-0.1260-0.3516+0.2843-0.1036 = 0 ⇒ y_t(1)=0
                            # （易错点：换成 -0.1015 会在 x=1 留下 0.126% 弦长的假厚度）
FARFIELD_DIST = 10.0        # 远场法向外推距离（单位 = 弦长）
KAPPA = 6.0                 # 法向聚层强度：越大越贴壁；首层 ≈ D·κ/(e^κ−1)/nr
LEVELS = {                  # nb = 周向节点数，nr = 法向层数；两向同步翻倍
    "L1": {"nb": 96, "nr": 24},
    "L2": {"nb": 192, "nr": 48},
    "L3": {"nb": 384, "nr": 96},
}
AIRFOIL_MARKER = "Airfoil"
FARFIELD_MARKER = "Farfield"


def naca0012_thickness(x: np.ndarray) -> np.ndarray:
    """半厚度分布 y_t(x)（x 已在上游按余弦分布加密）。"""
    x = np.clip(np.asarray(x, float), 0.0, 1.0)
    return 5.0 * THICKNESS * (
        0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x**2 + 0.2843 * x**3 + TE_COEFF * x**4
    )


def thickness_slope(x: np.ndarray) -> np.ndarray:
    """dy_t/dx。x=0 处 → ∞（前缘圆头），用 clip 兜住并让法向退化成 (−1,0)。"""
    x = np.clip(np.asarray(x, float), 1e-12, 1.0)
    hp = 5.0 * THICKNESS * (0.2969 / (2 * np.sqrt(x)) - 0.1260 - 2 * 0.3516 * x
                            + 3 * 0.2843 * x**2 + 4 * TE_COEFF * x**3)
    return np.clip(hp, -1e6, 1e6)


def surface_nodes(nb: int) -> np.ndarray:
    """逆时针排布的 nb 个物面点（CCW 序：上表面 TE→LE，下表面 LE→TE），无重复点。

    取样只依赖 `beta = linspace(0, pi, nb//2 + 1)` ⇒ nb 翻倍时旧点精确落在新点上，
    这是嵌套性的**第一个**前提（第二个是法向必须与 nb 无关，见 surface_normals）。
    """
    if nb % 2:
        raise ValueError(f"nb 必须是偶数（上/下对称取样），收到 {nb}")
    n = nb // 2 + 1
    beta = np.linspace(0.0, math.pi, n)          # 余弦分布：前后缘自动加密
    x = 0.5 * (1.0 - np.cos(beta))
    y = naca0012_thickness(x)
    upper = np.column_stack([x, y])
    lower = np.column_stack([x[::-1], -y[::-1]])[1:-1]   # 掐掉与 upper 重合的两端
    return orient_ccw(np.vstack([upper, lower]))


def _x_and_side(pts: np.ndarray, tol: float = 1e-12) -> tuple[np.ndarray, np.ndarray]:
    """从 CCW 多边形点列反解 (x, σ)：σ=+1 上表面、−1 下表面、NaN = 角点（y≈0）。"""
    y = pts[:, 1]
    sigma = np.where(y > tol, 1.0, np.where(y < -tol, -1.0, np.nan))
    return pts[:, 0], sigma


def surface_normals(pts: np.ndarray) -> np.ndarray:
    """**解析**外法向：n = normalize((−y_t'(x), σ))，σ=±1 为上/下表面。

    不用多边形中心差分，因为那会让法向随 nb 变化 —— 三档节点就不再重合（嵌套性破），
    本仓实测踩过：中心差分版本下 L1 有 96/2400 个点不在 L2 上（tests 抓出来的）。
    前缘/尾缘两个角点取上下法向的角平分线，免得在 TE 留一个张开的楔。
    """
    x, sigma = _x_and_side(pts)
    hp = thickness_slope(x)
    n = np.column_stack([-hp, sigma])
    corner = ~np.isfinite(sigma)                 # y==0：LE 与 TE 两个角点
    if corner.any():
        n_up = np.column_stack([-hp[corner], np.ones(corner.sum())])
        n_dn = np.column_stack([-hp[corner], -np.ones(corner.sum())])
        n[corner] = n_up + n_dn
    norm = np.linalg.norm(n, axis=1, keepdims=True)
    return n / np.where(norm == 0, 1.0, norm)


def orient_ccw(pts: np.ndarray) -> np.ndarray:
    """多边形有向面积为负则反转（保证 k 推进方向 = 逆时针 = 外法向约定成立）。"""
    x, y = pts[:, 0], pts[:, 1]
    area2 = float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))
    return pts if area2 > 0 else pts[::-1]


def radial_offsets(nr: int, dist: float = FARFIELD_DIST, kappa: float = KAPPA) -> np.ndarray:
    """s_j = dist·(e^{κ j/nr}−1)/(e^{κ}−1)：只依赖 η=j/nr 的连续映射 ⇒ 三档嵌套。"""
    eta = np.arange(nr + 1) / nr
    return dist * (np.exp(kappa * eta) - 1.0) / (math.exp(kappa) - 1.0)


def build_mesh(nb: int, nr: int):
    """返回 (nodes, quads, airfoil_edges, farfield_edges)；quads 已按 CCW 定向。"""
    pts = surface_nodes(nb)
    nrm = surface_normals(pts)
    s = radial_offsets(nr)
    nodes = (pts[None, :, :] + s[:, None, None] * nrm[None, :, :]).reshape((nr + 1) * nb, 2)

    k = np.arange(nb)
    kn = (k + 1) % nb
    j = np.arange(nr)[:, None]
    n00 = k[None, :] + nb * j
    n10 = kn[None, :] + nb * j
    n01 = k[None, :] + nb * (j + 1)
    n11 = kn[None, :] + nb * (j + 1)
    quads = np.stack([n00, n01, n11, n10], axis=-1).reshape(-1, 4)
    quads = np.where((signed_area(quads, nodes) < 0)[:, None], quads[:, ::-1], quads)

    return nodes, quads, np.stack([k, kn], axis=1), np.stack([k + nb * nr, kn + nb * nr], axis=1)


def signed_area(quads: np.ndarray, nodes: np.ndarray) -> np.ndarray:
    """鞋带公式有向面积：≤0 = 单元翻转/退化（拓扑体检的第一道关）。"""
    p = nodes[quads]
    x, y = p[:, :, 0], p[:, :, 1]
    return 0.5 * np.sum(x * np.roll(y, -1, axis=1) - np.roll(x, -1, axis=1) * y, axis=1)


def inspect(nodes: np.ndarray, quads: np.ndarray, nb: int, nr: int) -> dict:
    """拓扑与质量体检。判据全过才允许进 S12′。"""
    area = signed_area(quads, nodes)
    edges: dict[tuple[int, int], int] = {}
    for q in quads:
        for a, b in zip(q, np.roll(q, -1)):
            key = (int(min(a, b)), int(max(a, b)))
            edges[key] = edges.get(key, 0) + 1
    counts = np.fromiter(edges.values(), int)
    p = nodes[quads]
    elen = np.linalg.norm(p - np.roll(p, -1, axis=1), axis=2)
    return {
        "n_nodes": int(nodes.shape[0]),
        "n_cells": int(quads.shape[0]),
        "domain_area": float(area.sum()),
        "h_eq": math.sqrt(float(area.sum()) / quads.shape[0]),   # 2D 名义网格尺寸（GCI 口径）
        "first_layer_thickness": float(np.linalg.norm(nodes[nb] - nodes[0])),
        "cells_negative_area": int(np.sum(area <= 0)),
        "cells_degenerate": int(np.sum(np.abs(area) < 1e-14)),
        "edges_nonmanifold": int(np.sum(counts > 2)),
        "edges_boundary": int(np.sum(counts == 1)),
        "expected_boundary_edges": 2 * nb,
        "min_edge_len": float(elen.min()),
        "worst_cell_shape": round(float(np.max(elen.min(axis=1) / elen.max(axis=1))), 4),  # 1=理想
    }


def write_su2(path: Path, nodes, quads, surf, far) -> None:
    """SU2 native mesh（MeshVersion=2, NDIME=2）；marker 单元 id 从 NELEM 起续编。"""
    lines = ["MeshVersion= 2", "NDIME= 2", f"NELEM= {len(quads)}", ""]
    for i, q in enumerate(quads):
        lines.append(f"3005 {i} {q[0]} {q[1]} {q[2]} {q[3]} 0")
    lines += ["", f"POIN= {len(nodes)}"]
    for i, (x, y) in enumerate(nodes):
        lines.append(f"{i} {x:.15e} {y:.15e}")
    lines += ["", "MARKERS=", "NMARK= 2"]
    for tag, elems, mid in ((AIRFOIL_MARKER, surf, 0), (FARFIELD_MARKER, far, 1)):
        lines += [f"MARKER_TAG= {tag}", f"MARKER_ELEMS= {len(elems)}"]
        for offset, (n0, n1) in enumerate(elems):
            lines.append(f"3001 {len(quads) + offset} {int(n0)} {int(n1)} {mid}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def make_level(name: str, out_dir: Path = ROOT / "mesh") -> dict:
    nb, nr = LEVELS[name]["nb"], LEVELS[name]["nr"]
    nodes, quads, surf, far = build_mesh(nb, nr)
    rep = inspect(nodes, quads, nb, nr)
    bad = [k for k in ("cells_negative_area", "cells_degenerate", "edges_nonmanifold") if rep[k]]
    if bad or rep["edges_boundary"] != rep["expected_boundary_edges"]:
        raise RuntimeError(f"[{name}] 拓扑检查未过：{ {k: rep[k] for k in bad} }")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"mesh_{name}.su2"
    write_su2(out, nodes, quads, surf, far)
    rep.update({"level": name, "nb": nb, "nr": nr, "file": out.name,
                "size_bytes": out.stat().st_size})
    return rep


def preview(name: str, out_dir: Path = ROOT / "mesh") -> str | None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:                                     # pragma: no cover
        print(f"[{name}] 跳过预览：matplotlib 不可用（{exc}）")
        return None
    nb, nr = LEVELS[name]["nb"], LEVELS[name]["nr"]
    nodes, quads, _, _ = build_mesh(nb, nr)
    fig, ax = plt.subplots(figsize=(4.0, 2.6), dpi=200)
    for q in quads[:: max(1, len(quads) // 4000)]:      # 太密就抽样画，够肉眼判读即可
        poly = nodes[np.append(q, q[0])]
        ax.plot(poly[:, 0], poly[:, 1], lw=0.15, color="0.35")
    ax.plot(*surface_nodes(nb).T, "r-", lw=1.0)
    ax.set_xlim(-0.3, 1.6); ax.set_ylim(-0.5, 0.5)
    ax.set_aspect("equal"); ax.axis("off")
    fig.tight_layout()
    png = out_dir / f"preview_{name}.png"
    fig.savefig(png, bbox_inches="tight"); plt.close(fig)
    return str(png)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="S10′ 三档结构化网格（纯 numpy 路径）")
    ap.add_argument("--only", choices=sorted(LEVELS), help="只生成指定档位")
    ap.add_argument("--check", action="store_true", help="只做拓扑体检，不写文件")
    ap.add_argument("--preview", action="store_true", help="另存 mesh/preview_{L}.png")
    args = ap.parse_args(argv)

    names = [args.only] if args.only else list(LEVELS)
    reports: dict[str, dict] = {}
    prev = None
    for name in names:
        nb, nr = LEVELS[name]["nb"], LEVELS[name]["nr"]
        if args.check:
            rep = inspect(*build_mesh(nb, nr)[:2], nb, nr)
            rep.update({"level": name, "nb": nb, "nr": nr})
        else:
            rep = make_level(name)
        if prev:
            # 细化比 r = h_prev/h_cur；2D 结构化下 = sqrt(N_cur/N_prev)，两向翻倍 ⇒ 恰为 2
            rep["r_vs_previous"] = round(math.sqrt(rep["n_cells"] / prev), 4)
            rep["first_layer_ratio"] = round(rep["first_layer_thickness"] / prev_first, 4)
        prev, prev_first = rep["n_cells"], rep["first_layer_thickness"]
        reports[name] = rep
        ok = not (rep["cells_negative_area"] or rep["cells_degenerate"] or rep["edges_nonmanifold"])
        print(f"[{name}] nb={nb} nr={nr} 单元={rep['n_cells']} h_eq={rep['h_eq']:.4e} "
              f"r={rep.get('r_vs_previous', '—')} 首层={rep['first_layer_thickness']:.3e}"
              f"(比 {rep.get('first_layer_ratio', '—')}) 形状={rep['worst_cell_shape']} "
              f"→ {'OK' if ok else 'FAIL'}")
        if args.preview and not args.check:
            p = preview(name)
            if p:
                print(f"        预览 -> {p}")

    if not args.check:
        out = ROOT / "mesh" / "mesh_manifest.json"
        out.write_text(json.dumps(reports, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"清单 -> {out.relative_to(ROOT)}（E4 报告的三档网格表以此为准，勿手填）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
