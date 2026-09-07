"""S15′ 验收测试：Δη_min 与判据函数（★全计划心脏）。

核心可检验性：用**已知真值差**的合成数据，看判据函数的接受/拒绝是否正确。
"接受/拒绝"错了，后面所有回判表都是空中楼阁。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _api():
    try:
        from src.significance import bootstrap_ci, delta_min, is_significant
    except ImportError as exc:
        pytest.fail(f"src/significance.py 尚未手写完成（S15′）；规格 docs/SPEC-03-significance.md（{exc}）")
    return bootstrap_ci, delta_min, is_significant


def test_bootstrap_covers_truth():
    bootstrap_ci, _, _ = _api()
    x = np.random.default_rng(1).normal(0.5, 0.01, 400)
    lo, hi, half = bootstrap_ci(x)
    assert lo < 0.5 < hi
    assert 0 < half < 0.01


def test_bootstrap_is_reproducible_and_wider_with_fewer_samples():
    bootstrap_ci, _, _ = _api()
    x = np.random.default_rng(3).normal(0.0, 1.0, 300)
    a = bootstrap_ci(x, seed=7)
    b = bootstrap_ci(x, seed=7)
    c = bootstrap_ci(x[:30], seed=7)              # 样本少 10 倍 → CI 明显更宽
    assert a == b, "同 seed 必须逐位可复现（不然报告数字无法回溯）"
    assert c[2] > 2 * a[2]


def test_delta_min_takes_max_of_two_sources():
    _, delta_min, _ = _api()
    x = np.random.default_rng(2).normal(1.25, 1e-4, 300)     # 迭代噪声极小
    d = delta_min(x, phi_fine=1.25, phi_med=1.5, phi_coarse=2.0, r=2)
    assert d["dmin"] == pytest.approx(max(d["boot_half"], d["gci_abs"]), rel=1e-12)
    assert d["dmin"] >= d["boot_half"] and d["dmin"] >= d["gci_abs"]
    assert {"p_obs", "phi_ex"} <= set(d)


def test_delta_min_dominated_by_iteration_noise():
    """平台期噪声很大时 dmin 必须由 boot_half 决定（网格再细也白搭）。

    三档用"干净的一阶序列"（e32 = 2·e21 ⇒ p_obs=1），这样 gci_abs 是个小确定值；
    不要图省事把 φ 写成近似相等——那会让 p_obs→0、GCI 发散（见 test_gci 里的同类守卫）。
    """
    _, delta_min, _ = _api()
    noisy = np.random.default_rng(5).normal(1.25, 0.05, 200)
    d = delta_min(noisy, phi_fine=1.25, phi_med=1.2501, phi_coarse=1.2503, r=2)
    assert d["p_obs"] == pytest.approx(1.0, rel=1e-9)
    assert d["boot_half"] > d["gci_abs"]
    assert d["dmin"] == pytest.approx(d["boot_half"], rel=1e-9)



def test_verdicts():
    _, _, is_significant = _api()
    ok, v1 = is_significant(0.10, 0.01)
    no, v2 = is_significant(0.005, 0.01)
    assert ok and v1["verdict"] == "显著"
    assert not no and v2["verdict"] == "不可分辨"


def test_boundary_is_strict_and_signed_claims_work():
    """恰好等于 dmin ⇒ 不可分辨（宁可保守）；负增益用绝对值口径判幅度、用原值报方向。"""
    _, _, is_significant = _api()
    edge, v = is_significant(0.01, 0.01)
    assert edge is False, "等于判据线不算显著（严格不等式）"
    neg, vn = is_significant(-0.10, 0.01)
    assert neg and vn.get("direction", "下降") == "下降", "负增益也要能判，且方向要说出来"


def test_end_to_end_synthetic_recovers_known_truth():
    """真值差已知 → 判据应拒绝小于 dmin 的宣称、接受远大于 dmin 的宣称。

    这是 T1 方法学的"冒烟 + 自检"：如果这条不过，框架本身就是错的。
    """
    _, delta_min, is_significant = _api()
    rng = np.random.default_rng(11)
    fine_plateau = rng.normal(0.0, 2e-4, 400)            # 细档平台期噪声（CD 量级）
    d = delta_min(fine_plateau, phi_fine=0.0230, phi_med=0.0236, phi_coarse=0.0250, r=2)
    tiny, vt = is_significant(0.3 * d["dmin"], d["dmin"])
    big, vb = is_significant(50 * d["dmin"], d["dmin"])
    assert not tiny, f"把噪声当成果了：Δ=0.3·dmin 却判显著（{vt}）"
    assert big, f"真增益被判不可分辨，框架过保守：{vb}"
    assert d["dmin"] > 0
