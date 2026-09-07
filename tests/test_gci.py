"""S14′ 验收测试：GCI（Richardson 外推 + Roache/Celik 2008 口径）。

设计原则：用**解析解自检**——构造已知阶数的 φ(h)，看模块能否复原 p 和真值。
这是唯一不需要外部 CFD 结论就能证明"公式写对了"的办法。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _gci():
    try:
        from src.gci import gci  # noqa: WPS433
    except ImportError as exc:
        pytest.fail(f"src/gci.py 尚未手写完成（S14′）；规格 docs/SPEC-02-gci.md（{exc}）")
    return gci


def test_first_order_recovery():
    """φ(h) = 1 + C·h，C=1，h = 1/0.5/0.25（r=2）→ 真值 1、p=1。"""
    gci = _gci()
    res = gci(1.25, 1.5, 2.0, r=2)
    assert abs(res.p_obs - 1.0) < 1e-9
    assert abs(res.phi_ex - 1.0) < 1e-9
    assert res.gci_fine_pct > 0


def test_second_order_recovery():
    """φ(h) = 1 + C·h²，C=1，h = 1/0.5/0.25 → (2.0, 1.25, 1.0625)，真值 1、p=2。

    ⚠️ 跟做手册 S14′ 此处写作 `gci(1.0625, 1.25, 1.5)` 并注明 "φ = 1 + h^2"——**那是错的**：
    h=1 时 1+h²=2.0 而不是 1.5。用 1.5 会得到 p_obs=0.415，一个**正确**的实现反而会红。
    本仓按解析解重算并改正（2026-09-07 QA 实测，见 BLOCKERS.md #4）。
    """
    gci = _gci()
    res = gci(1.0625, 1.25, 2.0, r=2)            # φ = 1 + h²
    assert abs(res.p_obs - 2.0) < 1e-9
    assert abs(res.phi_ex - 1.0) < 1e-9


def test_zero_observed_order_rejected():
    """e32 ≈ e21 ⇒ p_obs ≈ 0 ⇒ r^p−1 ≈ 0 ⇒ GCI 炸成天文数字或 ZeroDivisionError。

    三档看不出收敛趋势时正确行为是**拒出并说人话**，不是给一个 1e18 的"不确定度"。
    """
    gci = _gci()
    with pytest.raises(ValueError) as ei:
        gci(1.25, 1.250001, 1.250002, r=2)
    assert "阶" in str(ei.value) or "p_obs" in str(ei.value) or "收敛" in str(ei.value)


def test_amplitude_of_gci_formula():
    """GCI_21 = Fs·|e21/φ2|/(r^p−1)。手算一遍：e21=−0.25, φ2=1.25, p=1, r=2, Fs=1.25。"""
    gci = _gci()
    res = gci(1.25, 1.5, 2.0, r=2, Fs=1.25)
    expected = 1.25 * abs((1.5 - 1.25) / 1.25) / (2 ** 1 - 1) * 100
    assert res.gci_fine_pct == pytest.approx(expected, rel=1e-9)


def test_oscillatory_rejected():
    gci = _gci()
    with pytest.raises(ValueError) as ei:
        gci(1.0, 1.1, 1.05, r=2)                 # 非单调 → 拒出，不猜
    assert "单调" in str(ei.value) or "渐近" in str(ei.value)


def test_zero_diff_rejected():
    """两档一模一样 = 网格没起作用或输出被截断，不许出 0% GCI 冒充收敛。"""
    gci = _gci()
    with pytest.raises(ValueError):
        gci(1.0, 1.0, 1.2, r=2)


@pytest.mark.parametrize("bad_r", [1.0, 0.5, -2.0])
def test_refinement_ratio_guard(bad_r):
    gci = _gci()
    with pytest.raises(ValueError):
        gci(1.25, 1.5, 2.0, r=bad_r)


def test_decreasing_sequence_direction():
    """φ 单调递减（CD 常如此）与递增必须对称处理，不能只在一个方向上工作。"""
    gci = _gci()
    up = gci(1.25, 1.5, 2.0, r=2)
    dn = gci(-1.25, -1.5, -2.0, r=2)
    assert abs(up.p_obs - dn.p_obs) < 1e-9
    assert abs(abs(up.phi_ex) - abs(dn.phi_ex)) < 1e-9


def test_result_fields_present():
    gci = _gci()
    res = gci(1.0625, 1.25, 1.5, r=2)
    for field in ("p_obs", "phi_ex", "gci_fine_pct", "gci_med_pct", "e21", "e32"):
        assert hasattr(res, field), f"缺字段 {field}（SPEC-02 的数据类契约）"
