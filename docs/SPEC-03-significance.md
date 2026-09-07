# SPEC-03 · `src/significance.py`（S15′ Δη_min 检验）— 手写区规格 ★全计划心脏

> 实现由你手写。验收 = `pytest tests/test_significance.py` 绿。预算 2.5h。
> 这个模块把白皮书 6.2① 那句话变成可执行判据：**宣称增益 > Δη_min 才有资格被叫"成果"。**

## 定义（写进报告的话就照这段写）

对某个观测量 φ（效率 η、力系数 CD 均可，**必须是同一口径的绝对量**）：

```
Δη_min = max( u_grid , u_iter )

u_grid = GCI_fine% / 100 · |φ_fine|        # 网格不确定度（绝对量）—— 来自 gci()
u_iter = bootstrap CI 半宽 of mean         # 迭代平台期统计不确定度
```

- 取 **max**，不相加：两者量纲同为绝对值，相加会把"一个来源已经足够大"的情形虚报成更悲观的结论；
  若要合成（平方和开根），那是另一种口径，**必须在 docstring 与报告里同时改**，不许两处不一致。
- v1 只有 bootstrap 一种统计口径（顺序单 v2 的单口径原则）；t 检验留 Phase 2。

## 必须导出的三个函数

### `bootstrap_ci(samples, B=10000, alpha=0.05, seed=42) -> tuple[float, float, float]`
- 统计量：均值。重采样必须**有放回**、长度为 n。
- 分位数用 `[alpha/2, 1−alpha/2]`（percentile 法即可，但要写明用了哪种 quantile —— numpy 默认 `linear`）。
- 返回 `(lo, hi, (hi−lo)/2)`；同 seed 必须逐位可复现（测试会打这条，报告数字要能回溯）。
- `B` 与 `seed` 是显式参数：报告里要写"B=10000, seed=42"，别人才能重跑出一样的数。

### `delta_min(plateau_samples_fine, phi_fine, phi_med, phi_coarse, r=2.0, B=10000) -> dict`
返回键（`tools/plot_results.py` 与 `docs/delta_min.json` 依赖）：
```
{boot_half, gci_abs, dmin, p_obs, phi_ex}
```
`dmin = max(boot_half, gci_abs)`；`p_obs`/`phi_ex` 从 `gci()` 透传，别自己再算一遍。

### `is_significant(claimed_delta, dmin) -> tuple[bool, dict]`
- 判据：`abs(claimed_delta) − dmin > 0`，**严格不等号**（恰好等于 → 判"不可分辨"，宁可保守）。
- 返回 `dict(margin=..., verdict="显著"|"不可分辨", direction="上升"|"下降"|"零")`。
  `direction` 按 `claimed_delta` 的**符号**给，别按绝对值 —— 效率掉 2% 被报成"显著上升"是最难看的错误。

## 测试会在这里咬你（都是有意设计的）
| 测试 | 它在防什么错误 |
|---|---|
| `test_bootstrap_covers_truth` | 忘乘 2、把 std 当半宽、分位数取错尾 |
| `test_bootstrap_is_reproducible_and_wider_with_fewer_samples` | 没有 seed 参数（报告不可复现）；CI 不随 n 变化（重采样写错） |
| `test_delta_min_takes_max_of_two_sources` / `..._dominated_by_iteration_noise` | 两个不确定度的合成方式含糊；把网格细到没意义却忘看平台噪声 |
| `test_boundary_is_strict_and_signed_claims_work` | `>=` 与 `>` 的边界；负增益的方向丢失 |
| `test_end_to_end_synthetic_recovers_known_truth` | 框架本身判反（把噪声当成果 / 把真增益判死） |

## 一个必须自己回答的问题（写进 S24′ 的"局限"节）
`u_iter` 来自**单次运行**的平台期样本，它量化的是"迭代噪声"，不是"随机初值/超参的 run-to-run 离散度"。
白皮书里 A1（多次独立运行离散度）是另一件事——**别把这两者混为一个数**，
混了就等于给"未经显著性检验的增益"发了通行证。
