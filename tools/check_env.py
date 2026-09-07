"""开工体检：python tools/check_env.py

S05/S08 的判据自检。只报事实，不替你装东西。
"""
from __future__ import annotations

import importlib
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def line(name, ok, detail=""):
    print(f"  [{'✅' if ok else '❌'}] {name}{('  —  ' + detail) if detail else ''}")
    return ok


def main() -> int:
    print(f"delta-eta-min 环境体检 · {platform.system()} {platform.release()} · "
          f"python {platform.python_version()} ({sys.executable})")
    ok = True

    print("\n1) Python 环境")
    in_venv = sys.prefix != sys.base_prefix or os.environ.get("CONDA_PREFIX")
    ok &= line("在独立环境里（conda t1 / venv）", bool(in_venv),
               str(os.environ.get("CONDA_PREFIX") or sys.prefix) if in_venv
               else "先用 conda activate t1；别装进系统 Python")
    ok &= line("版本 ≥ 3.10", sys.version_info >= (3, 10), platform.python_version())

    print("\n2) 依赖")
    for mod, why in (("numpy", "GCI/bootstrap 全部依赖"), ("pandas", "history.csv 解析"),
                     ("pytest", "手写模块的验收判据"), ("matplotlib", "S17′ 出图")):
        try:
            m = importlib.import_module(mod)
            ok &= line(mod, True, getattr(m, "__version__", "?"))
        except Exception as exc:
            ok &= line(mod, False, f"{type(exc).__name__}: {exc}")
    try:
        importlib.import_module("gmsh")
        ok &= line("gmsh（S10′ 路径 A）", True, "可用；路径 B 不需要它")
    except Exception as exc:
        print(f"  [⚠️] gmsh 不可用：{type(exc).__name__}: {exc}")
        print("        → 用 python tools/make_grids_numpy.py（同一判据，零 GUI 依赖），或按 "
              "BLOCKERS.md #1 修 libGLU")

    print("\n3) 求解器（S08）")
    su2 = shutil.which("SU2_CFD") or shutil.which("SU2_CFD.exe")
    if su2:
        try:
            out = subprocess.run([su2, "--version"], capture_output=True, text=True,
                                timeout=60, check=False)
            banner = ((out.stdout or "") + (out.stderr or "")).strip().splitlines()
            ver = next((l for l in banner if "SU2" in l), banner[0] if banner else "")
            ok &= line("SU2_CFD --help/--version 出横幅", True, f"{su2} · {ver[:70]}")
        except Exception as exc:
            ok &= line("SU2_CFD 可执行", False, f"{type(exc).__name__}: {exc}")
    else:
        print("  [⚠️] PATH 里找不到 SU2_CFD → S08 未完成（判据：终端能打出 v8.5.0 横幅）")
        print("        临时可用绝对路径；E4 必须本机真跑，不接受借用别人的收敛史")

    print("\n4) 仓库状态")
    for rel, need in (("mesh/naca0012.geo", "S10′ 手敲区待补"),
                      ("cases/naca0012.cfg", "已就位"),
                      ("src/gci.py", "S14′ 待手写"),
                      ("src/significance.py", "S15′ 待手写"),
                      ("LEDGER.md", "已就位")):
        p = ROOT / rel
        print(f"  [{'有' if p.exists() else '无'}] {rel}  （{need}）")
    for lv in ("L1", "L2", "L3"):
        h = ROOT / "runs" / lv / "history.csv"
        print(f"  [{'有' if h.exists() else '无'}] runs/{lv}/history.csv")

    print("\n下一步（顺序不许跳）：pytest -q → make_grids* → run_levels --dry-run → 本机真跑")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
