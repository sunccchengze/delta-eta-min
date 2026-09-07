"""S05 冒烟 + 手写进度条。

`test_import` 必须绿；后面三条在对应模块手写完成前**故意是红的**——
它们是打卡器，不是 bug（判据见 AGENTS.md §1）。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_import():
    import src  # noqa: F401


@pytest.mark.parametrize("mod,attr,step", [
    ("src.convergence", "summary", "S13′"),
    ("src.gci", "gci", "S14′"),
    ("src.significance", "delta_min", "S15′"),
])
def test_handwritten_modules_exist(mod, attr, step):
    import importlib
    try:
        m = importlib.import_module(mod)
    except ImportError:
        pytest.fail(f"{mod} 尚未手写完成（{step}）。规格：docs/SPEC-0*.md，"
                    f"验收：pytest tests/test_{mod.split('.')[-1]}.py")
    assert hasattr(m, attr), f"{mod} 缺 {attr}()（见 SPEC 的函数签名契约）"


def test_mesh_generator_runs_offline(tmp_path):
    """路径 B 的小档冒烟：不依赖 gmsh，也不依赖求解器。"""
    sys.path.insert(0, str(ROOT))
    from tools.make_grids_numpy import build_mesh, inspect

    nodes, quads, surf, far = build_mesh(16, 6)
    rep = inspect(nodes, quads, 16, 6)
    assert rep["cells_negative_area"] == 0
    assert rep["n_cells"] == 16 * 6
    assert len(surf) == len(far) == 16


def test_ledger_exists_and_has_open_items():
    led = ROOT / "LEDGER.md"
    assert led.exists(), "LEDGER.md 是收尾必填项，别丢"
    assert "☐" in led.read_text(encoding="utf-8"), "台账全绿了就去做 S26 对表，不用再看这条"
