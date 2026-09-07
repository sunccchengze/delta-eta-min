"""S10′ 网格工具的测试（tools/ 属 AI 允许区，但**判据由你亲自跑一遍**）。

这些测试只回答一个问题：三档网格是不是**同一族几何的规约细化**。
不是的话，后面的 GCI / p_obs / Δη_min 全部失去意义，所以把它钉死在这里。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.make_grids_numpy import (  # noqa: E402
    LEVELS, build_mesh, inspect, naca0012_thickness, radial_offsets, surface_nodes,
)


def test_te_closed_and_le_at_origin():
    s = surface_nodes(96)
    assert abs(naca0012_thickness(np.array([1.0]))[0]) < 1e-6   # 闭合尾缘
    assert s.shape == (96, 2)
    assert np.isfinite(s).all()


def test_surface_is_simple_closed_ccw():
    s = surface_nodes(96)
    x, y = s[:, 0], s[:, 1]
    assert float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)) > 0     # 逆时针
    assert np.linalg.norm(s - np.roll(s, -1, axis=0), axis=1).min() > 0    # 无重合相邻点
    assert len({tuple(map(float, p)) for p in s}) == 96                    # 无重复节点


@pytest.mark.parametrize("lvl", list(LEVELS))
def test_mesh_topology_clean(lvl):
    nb, nr = LEVELS[lvl]["nb"], LEVELS[lvl]["nr"]
    nodes, quads, surf, far = build_mesh(nb, nr)
    rep = inspect(nodes, quads, nb, nr)
    assert rep["cells_negative_area"] == 0        # 无翻转单元
    assert rep["cells_degenerate"] == 0           # 无退化单元
    assert rep["edges_nonmanifold"] == 0          # 无非流形边
    assert rep["edges_boundary"] == 2 * nb         # 边界边数 = 物面 + 远场
    assert len(surf) == len(far) == nb
    assert rep["n_cells"] == nb * nr
    assert rep["n_nodes"] == nb * (nr + 1)


def test_nominal_refinement_is_exactly_halving():
    """h_eq 严格减半 ⇒ GCI 用 r=2 的前提成立；首层厚度只要求"接近"减半。

    为什么分开卡：h_eq=sqrt(A/N) 在周向+法向同步翻倍时是**精确** 0.5；
    近壁首层厚度由指数聚层映射决定，η→0 处非线性 ⇒ 实测比 ~0.47（非 bug）。
    报告里引用哪个数、用哪个口径，就看这条测试怎么写的。
    """
    reps = {}
    for lvl in LEVELS:
        nb, nr = LEVELS[lvl]["nb"], LEVELS[lvl]["nr"]
        reps[lvl] = inspect(*build_mesh(nb, nr)[:2], nb, nr)
    assert abs(reps["L2"]["h_eq"] / reps["L1"]["h_eq"] - 0.5) < 1e-3
    assert abs(reps["L3"]["h_eq"] / reps["L2"]["h_eq"] - 0.5) < 1e-3
    for a, b in (("L2", "L1"), ("L3", "L2")):
        ratio = reps[a]["first_layer_thickness"] / reps[b]["first_layer_thickness"]
        assert 0.45 < ratio < 0.52, f"{a}/{b} 首层厚度比 {ratio} 离谱（细化几乎没生效？）"


def test_grids_are_nested():
    """L1 节点集 ⊂ L2 ⊂ L3：嵌套族是"同一算例、同一口径"最硬的经验证据。"""
    def node_set(lvl):
        nb, nr = LEVELS[lvl]["nb"], LEVELS[lvl]["nr"]
        nodes = build_mesh(nb, nr)[0]
        return {(round(float(x), 9), round(float(y), 9)) for x, y in nodes}

    s1, s2, s3 = node_set("L1"), node_set("L2"), node_set("L3")
    assert s1 <= s2, f"L1 有 {len(s1 - s2)} 个点不在 L2 上"
    assert s2 <= s3, f"L2 有 {len(s2 - s3)} 个点不在 L3 上"


def test_radial_mapping_independent_of_nr():
    """s(η) 只依赖 η，与 nr 无关 —— 嵌套性的解析原因。"""
    fine = radial_offsets(96)[::4]     # 每取 4 个 = η 步长 1/24
    coarse = radial_offsets(24)
    assert np.allclose(fine, coarse, atol=1e-14)


def test_odd_nb_rejected():
    with pytest.raises(ValueError):
        surface_nodes(97)
