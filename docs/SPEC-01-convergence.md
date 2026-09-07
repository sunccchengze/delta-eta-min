# SPEC-01 · `src/convergence.py`（S13′ 收敛史解析器）— 手写区规格

> 这是**规格**，不是代码。实现由你逐行手写（AGENTS.md §1）。
> 验收 = `pytest tests/test_convergence.py` 绿 + 真日志跑通（`test_real_log_shape` 解除 skip）。
> 预算 2h；卡壳 45 分钟 → 写 `BLOCKERS.md` 跳步。

## 范围纪律
只支持 SU2 的 `history.csv`（`HISTORY_OUTPUT= (ITER, RMS_RES, AERO_COEFF)` + `OUTPUT_FORMAT= CSV`）。
不做通用性：不解析 `.csv` 之外的格式、不支持多时间步、不做并行日志拼接。

## 必须导出的三个名字

### `load_history(path) -> tuple[DataFrame, str, str, str, str]`
读 CSV，列名两端空白和引号都要剥掉；返回 `(df, iter_col, rms_col, cd_col, cl_col)`。
列名走**别名匹配**（大小写不敏感，按下表顺序取第一个命中的）：

| 逻辑列 | 可接受别名（按优先级） |
|---|---|
| 迭代号 | `Iteration`, `ITER`, `Inner_Iter`, `Outer_Iter` |
| 残差 | `rms[Rho]`, `rms[Density]`, `Residual[rho]`, 任何 `rms[` 前缀 |
| 阻力系数 | `DCD`, `CD` |
| 升力系数 | `DCL`, `CL` |

找不到必需列 → 抛 `KeyError`，消息里必须带上**实际列名清单**（报错说人话是判据之一）。

### `orders_dropped(rms) -> float`
`log10(rms[0]) − log10(min(rms))`，即残差降了几个量级。E4 的硬门槛是 **≥4**。

### `plateau_stats(values, tail_frac=0.25, min_tail=50) -> dict`
取有限值序列的最后 `max(min_tail, int(n·tail_frac))` 个样本，返回
`{n, mean, std, rel_std, samples}`。约定：
- `std` = 样本标准差（`ddof=1`）
- `rel_std = std/|mean|`；`mean == 0` 时给 `inf`
- 常数序列 → `std = 0`、`rel_std = 0`（除零要挡住，测试会打这里）
- `samples` 原样保留：`significance.py` 要靠它做 bootstrap，**不要在这一步做平滑/去趋势**

### `summary(path) -> dict`
组合上面三个，返回**恰好**包含这些键（`docs/*.json` 与 `tools/plot_results.py` 依赖键名）：

```
{file, iters, orders_drop, CD_mean, CL_mean, CD_plateau, CL_plateau, rms_final, marker_cols}
```
- `iters` = 迭代列最后一个值（不是行数——测试用 `iters == n-1` 卡住这条）
- `CD_mean` / `CL_mean` 取平台期均值（与 `*_plateau["mean"]` 同值，为方便报告而并列）
- `rms_final` = 残差列最后 10 个的均值（报告里"残差终点"用）
- `marker_cols` = 实际匹配到的列名，写进 JSON 供审计（口径可追溯）

## 输出契约
`summary()` 必须能 `json.dumps`（纯 Python 类型；`samples` 用 `.tolist()` 转成 list，别留 numpy 标量）。

## 三个自检问题（写完答一遍，答不上就重来）
1. 平台期为什么取末段 25% 而不是最后 50 个点？两者何时不等价？
2. `orders_drop` 用 `min(rms)` 而不是 `rms[-1]`，会掩盖什么现象？（提示：震荡后段反弹）
3. 如果 SU2 在 `CONV_STARTITER` 之前写了几行全 0 残差，你的 `orders_dropped` 会给出什么？
