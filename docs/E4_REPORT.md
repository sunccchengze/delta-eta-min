# E4 收敛报告：NACA0012 Euler 跨声速（M=0.8, α=1.25°）· 骨架

> 状态：**未开跑，全文无数值**。数值只能来自 S12′/S16′ 在你本机的真跑。
> 装配方式（🤖 允许 AI 填表）：AI 从 `runs/*/run_meta.json`、`mesh/mesh_manifest.json`、
> `docs/delta_min.json` 抽数填进本骨架，你逐格核对可回溯性后署名。
> 证据等级：**E4 = 自己生成的网格 + 自己跑到的收敛**。达不到就写 E3，别借级别。

## 1 设置
| 项 | 值 | 出处 |
|---|---|---|
| 求解器 | SU2 ________（`run_meta.json.su2_version`） | `runs/*/run_meta.json` |
| 算例 | NACA0012, Euler 2D, M=0.8, α=1.25° | `cases/naca0012.cfg` |
| 网格路径 | A（gmsh）/ B（numpy 结构化，勾选） | `mesh/mesh_manifest.json.path` |
| 格式 | 一阶 ROE 隐式 CFL=4 / 二阶 MUSCL+VenkataKishnan CFL=1.5 | 两份 cfg |
| 收敛判据 | `CONV_FIELD=RMS_DENSITY`，`CONV_RESIDUAL_MINVAL=-10`，`ITER=1000/3000` | cfg |
| 远场 | ________（方框 20c×20c 或 法向外推 10c，按实际路径写） | `mesh/naca0012.geo` |

## 2 三档网格表
| 档位 | nb×nr 或 lc | 单元数 | h_eq | 首层厚度 | r vs 上一档 |
|---|---|---|---|---|---|
| L1 | | | | | — |
| L2 | | | | | |
| L3 | | | | | |

拓扑检查：`tools/check_mesh.py` 输出粘贴处 →
```
（待填：翻转/非流形/孤儿点全 0）
```

## 3 收敛史
| 档位 | 步数 | 残差降幅（量级） | 平台期 CD 均值 | 平台期相对标准差 |
|---|---|---|---|---|
门槛：**≥4 个量级**才叫收敛（B4）。未达标档位在此标注，不得省略。

## 4 GCI 与 Δη_min
| 口径 | p_obs | φ_ex | GCI_fine% | GCI_med% | Δη_min（绝对量） |
|---|---|---|---|---|---|
| 一阶 | | | | | |
| 二阶 | | | | | |

`p_obs` 与理论阶（一阶≈1 / 二阶≈2）的对照解读见 `docs/SPEC-02-gci.md` 表；
**偏离时如实写**，不要挑网格凑一个好看的 p。

## 5 局限（这段必须自己写，AI 不许替你承认局限）
- ☐ Euler 无粘：不含边界层与尾迹耗散，CD 绝对值不可与 RANS 对标；
- ☐ 等比三档 + 2D 单一观测量：p_obs 是三点的斜率，不是渐近阶的证明；
- ☐ 远场尺寸/形状对 Euler CD 的影响未单独量化（可选：L3 换 D=20 复算一档做敏感度）；
- ☐ 单一 α、单马赫：不构成任何"方法有效"的普适结论；
- ☐ 其他：______

## 6 图
`docs/fig1_gci.png` · `docs/fig2_deltamin.png`（由 `tools/plot_results.py` 生成，勿手画）

---
*附：本报告与 `runs/` 一起构成 60 天检查点第 3 项证据（S26 对表）。*
