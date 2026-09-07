"""S10′ 判据自检：python tools/check_mesh.py [mesh/*.su2 ...]

不带参数时，自动检查 mesh/ 下的 mesh_L{1,2,3}.su2（两条生成路径通用）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.su2mesh import parse_su2, passes, quality_report  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="离线 SU2 网格体检（不依赖求解器）")
    ap.add_argument("files", nargs="*", help="待检查的 .su2；省略则查 mesh/mesh_L*.su2")
    ap.add_argument("--json", action="store_true", help="同时写 mesh/mesh_quality.json")
    args = ap.parse_args(argv)

    files = [Path(f) for f in args.files] or sorted((ROOT / "mesh").glob("mesh_L*.su2"))
    if not files:
        sys.exit("没有 .su2 可查。先跑 python tools/make_grids.py 或 make_grids_numpy.py")

    out = {}
    ok_all = True
    for f in files:
        if not f.exists():
            print(f"[{f.name}] 文件不存在 → FAIL")
            ok_all = False
            continue
        rep = quality_report(parse_su2(f))
        out[f.name] = rep
        marks = ",".join(sorted(rep["markers"]))
        ok = passes(rep)
        ok_all &= ok
        print(f"[{f.name}] v{rep['version']} 节点={rep['n_nodes']} 单元={rep['n_cells']} "
              f"markers=[{marks}] 翻转={rep['flipped_or_zero_area_cells']} "
              f"非流形边={rep['edges_nonmanifold']} 孤儿点={rep['orphan_nodes']} "
              f"最小单元面积={rep['min_abs_cell_area']} → {'OK' if ok else 'FAIL'}")
        if not ok:
            print("   卡壳预案：gmsh 报 CurvesList → 老版本改 EdgesList；"
                  "markers 缺失 → 检查 .geo 末尾三行 Physical Curve 的引号拼写")
    if args.json:
        (ROOT / "mesh" / "mesh_quality.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
        print("→ mesh/mesh_quality.json")
    print("\n判据：翻转=0 非流形=0 孤儿=0 且两个 marker 都在 ⇒ S10′ 的"
          "拓扑检查过关（SU2 启动 100 步需本机验证）")
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
