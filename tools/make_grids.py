"""S10′ 路径 A：gmsh + `mesh/naca0012.geo`，一个模板出三档网格。

用法: python tools/make_grids.py [--only L1] [--geo mesh/naca0012.geo]

与路径 B（tools/make_grids_numpy.py）互斥使用：一次 S10′ 只挑一条路，三档同源。
生成后接着跑 `python tools/check_mesh.py`（离线拓扑体检，不依赖求解器）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LEVELS = {"L1": 0.012, "L2": 0.006, "L3": 0.003}   # 特征长度 lc（弦长=1）；细化比 r=2
NEEDED_MARKERS = {"Airfoil", "Farfield"}            # 必须与 cfg 的 MARKER_* 逐字一致
NODES_PER_TYPE = {2: 3, 3: 4, 8: 6, 9: 8}           # gmsh 单元类型 → 节点数（三角形/四边形）


def import_gmsh():
    try:
        import gmsh
    except OSError as exc:                  # 典型故障：libGLU.so.1 缺失（见 BLOCKERS.md #1）
        sys.exit(
            f"gmsh 导入失败：{exc}\n"
            "  方案 1（Linux）  sudo apt-get install -y libglu1-mesa\n"
            "  方案 2（conda）  conda install -c conda-forge gmsh\n"
            "  方案 3（换路）    python tools/make_grids_numpy.py   ← 零 GUI 依赖，同一判据\n"
        )
    return gmsh


def count_2d_cells(gmsh, dim: int = 2) -> int:
    """按类型统计 2D 单元数（三角形 3 节点、四边形 4 节点，别拿节点数瞎除）。"""
    tags, _nodes, types = gmsh.model.mesh.getElements(dim)
    return sum(len(t) // NODES_PER_TYPE.get(int(tp), 3) for t, tp in zip(tags, types))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="gmsh 三档网格（手册 S10′ 原路径）")
    ap.add_argument("--only", choices=sorted(LEVELS))
    ap.add_argument("--geo", default=str(ROOT / "mesh" / "naca0012.geo"))
    args = ap.parse_args(argv)

    gmsh = import_gmsh()
    geo = Path(args.geo)
    if not geo.exists():
        sys.exit(f"找不到模板 {geo}；先按手册 S10′ 把手敲区补全")
    tpl = geo.read_text(encoding="utf-8")
    if "LC_TOKEN" not in tpl:
        sys.exit(f"{geo.name} 缺 LC_TOKEN 占位符，无法注入 lc（检查模板第 2 行）")

    mesh_dir = ROOT / "mesh"
    mesh_dir.mkdir(parents=True, exist_ok=True)
    reports: dict[str, dict] = {}
    prev_cells = None
    for name, lc in LEVELS.items():
        if args.only and name != args.only:
            continue
        tmp = mesh_dir / f"_{name}.geo"
        tmp.write_text(tpl.replace("LC_TOKEN", repr(lc)), encoding="utf-8")
        gmsh.initialize()
        gmsh.option.setNumber("General.Terminal", 1)
        gmsh.open(str(tmp))
        gmsh.model.mesh.generate(2)
        n2d = count_2d_cells(gmsh)
        out = mesh_dir / f"mesh_{name}.su2"
        gmsh.write(str(out))
        marks = sorted({gmsh.model.getPhysicalName(d, t)
                        for d, t in gmsh.model.getPhysicalGroups(1)})
        rep = {"level": name, "lc": lc, "markers": marks, "n_cells": int(n2d),
               "file": out.name, "size_bytes": out.stat().st_size,
               "path": "gmsh"}
        if prev_cells:
            rep["r_vs_previous"] = round((n2d / prev_cells) ** 0.5, 3)
        prev_cells = n2d
        reports[name] = rep
        print(f"[{name}] lc={lc} 单元数={n2d} markers={marks} -> {out.name}")
        if NEEDED_MARKERS - set(marks):
            print(f"   ⚠️ markers={marks}，与 cfg 的 MARKER_EULER/MARKER_FAR 不一致 → 改 .geo 末尾三行")
        if n2d < 200:
            print(f"   ⚠️ 单元数异常偏小（{n2d}），lc 可能没注入成功")
        gmsh.finalize()
        tmp.unlink(missing_ok=True)

    out = mesh_dir / "mesh_manifest.json"
    out.write_text(json.dumps(reports, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"清单 -> {out.relative_to(ROOT)}")
    print("接着：python tools/check_mesh.py    然后：python tools/run_levels.py L1 L2 L3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
