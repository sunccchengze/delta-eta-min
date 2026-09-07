"""S13′ 验收测试（AI 写的夹具，模块本体你手写）。

跑法：pytest tests/test_convergence.py -q
红 = src/convergence.py 还没写；绿 = 规格达成，可以进 S14′。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load():
    try:
        from src.convergence import summary, plateau_stats  # noqa: F401
    except ImportError as exc:
        pytest.fail(f"src/convergence.py 尚未手写完成（S13′）；规格 docs/SPEC-01-convergence.md（{exc}）")
    return summary, plateau_stats


def _fake_history(tmp_path, cd_drift=1e-5, n=200):
    """造一份 SU2 风格的 history.csv（真日志到手后请再跑一遍 test_real_log_shape）。"""
    rng = np.random.default_rng(0)
    rows = {"Iteration": np.arange(n),
            "rms[Rho]": 1e-1 * 10 ** (-np.arange(n) / 20),
            "DCD": 0.0227 + cd_drift * rng.standard_normal(n),
            "DCL": 0.35 + 0.1 * np.exp(-np.arange(n) / 30)}
    p = tmp_path / "history.csv"
    pd.DataFrame(rows).to_csv(p, index=False)
    return p


def test_summary(tmp_path):
    summary, _ = _load()
    s = summary(_fake_history(tmp_path))
    assert s["iters"] == 199
    assert s["orders_drop"] > 9                 # 假残差降了 ~10 个量级
    assert abs(s["CD_mean"] - 0.0227) < 1e-4
    assert set(["CD_plateau", "CL_plateau"]) <= set(s)


def test_plateau_rel_std_small(tmp_path):
    summary, _ = _load()
    s = summary(_fake_history(tmp_path))
    assert s["CD_plateau"]["rel_std"] < 0.01
    assert s["CD_plateau"]["n"] >= 50           # tail 至少 min_tail 个样本


def test_column_alias_accepted(tmp_path):
    """SU2 各版本列名不一致（Iteration/ITER/Inner_Iter，DCD/CD）——别名必须都吃。"""
    summary, _ = _load()
    n = 120
    alt = {"Inner_Iter": np.arange(n),
           "rms[Density]": 1e-2 * 10 ** (-np.arange(n) / 15),
           "CD": 0.021 + 1e-6 * np.sin(np.arange(n)),
           "CL": 0.34 + 1e-6 * np.cos(np.arange(n))}
    p = tmp_path / "history_alt.csv"
    pd.DataFrame(alt).to_csv(p, index=False)
    s = summary(p)
    assert s["iters"] == n - 1
    assert np.isfinite(s["CD_mean"])


def test_missing_column_raises_keyerror_with_hint(tmp_path):
    summary, _ = _load()
    p = tmp_path / "bad.csv"
    pd.DataFrame({"Iteration": [0, 1], "rms[Rho]": [1e-2, 1e-3]}).to_csv(p, index=False)
    with pytest.raises(KeyError) as ei:
        summary(p)
    assert "CD" in str(ei.value) or "实际列" in str(ei.value)   # 报错要说人话


def test_plateau_stats_tail_size():
    _, plateau_stats = _load()
    x = list(range(1000))
    st = plateau_stats(x)
    assert st["n"] == 250                       # 默认末段 25%
    assert st["mean"] == pytest.approx(874.5)
    st2 = plateau_stats(x, tail_frac=0.5, min_tail=2000)
    assert st2["n"] == 2000                     # min_tail 生效


def test_constant_series_rel_std_zero():
    _, plateau_stats = _load()
    st = plateau_stats([2.0] * 80)
    assert st["rel_std"] == 0.0
    assert st["std"] == pytest.approx(0.0, abs=1e-12)


def test_real_log_shape(tmp_path):
    """真跑之后取消 skip：用 runs/L1/history.csv 复核解析器吃得到真日志。"""
    real = ROOT / "runs" / "L1" / "history.csv"
    if not real.exists():
        pytest.skip("S12′ 未跑；本机真跑完把这行 skip 删掉再复核一次（铁律④：不照抄）")
    summary, _ = _load()
    s = summary(real)
    assert s["iters"] > 0
    assert np.isfinite(s["CD_mean"])
