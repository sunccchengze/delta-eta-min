# delta-eta-min · T1 收益显著性检验框架（Δη_min）

> 一句话：**未经显著性检验的效率增益，不能被称为成果。**
> 本仓把这句话变成三个能跑、能测、能复现的函数：`convergence` → `gci` → `significance`。
> 出处：行动计划 §2.1（选题 T1）+ 白皮书 6.2① / 6.3。

## 当前状态

`S05` 前置骨架已就位（目录 + 工具 + 测试 + 规格），**仓内不含任何 CFD 数值结论**。
所有数值必须由 S12′–S16′ 在你本机真跑之后填入；`src/` 三个核心模块**故意是空的**。

```
$ python -m pytest -q
....FFF
FAILED tests/test_smoke.py::test_gci_import      ← 占位红 = 进度条，手写完成即绿
FAILED tests/test_gci.py ...                      ← 同上（src/gci.py 尚不存在）
```

红测试不是 bug，是打卡器：`pytest` 全绿 = 手写证据链（S13′+S14′+S15′）成型。

## 分工（详见 [AGENTS.md](AGENTS.md)）

| 区域 | 谁写 | 说明 |
|---|---|---|
| `src/convergence.py` `src/gci.py` `src/significance.py` | 🔒 **你**逐行手写 | AI 只审查；规格 `docs/SPEC-0*.md` |
| `mesh/naca0012.geo` 型线区 | 🔒 手敲区（文件内已标注） | S10′，抄前先看懂 |
| `tools/` `tests/` 夹具 `docs/` 装配 | 🤖 AI 起草 + 你核数 | 已交付 |
| `runs/**` 求解器输出 | ⏳ 你本机真跑 | 沙箱无求解器，AI 不代跑、不代跑出的数不标 E 级 |

## 30 秒上手（你的环境 = Windows PowerShell 5.1 + conda `t1`）

```powershell
conda activate t1
cd delta-eta-min
python tools/check_env.py        # 环境与依赖体检（先跑这个）
python -m pytest -q              # 期望：mesh 工具绿，src 相关红（占位进度条）
python tools/make_grids.py       # S10′ 路径 A：gmsh 出三档网格
python tools/make_grids_numpy.py # S10′ 路径 B：无 gmsh 依赖的纯 numpy 结构化 O-grid
python tools/run_levels.py L1 L2 L3   # S12′（需要 SU2 在 PATH 里）
```

PowerShell 5.1 没有 `&&`，多命令用 `;` 或分行。

## 数据流（每步的产物就是下一步的输入）

```
mesh/naca0012.geo ─┐
                   ├→ mesh/mesh_{L1,L2,L3}.su2 + mesh_manifest.json
tools/make_grids*  ┘         │
cases/naca0012.cfg ──→ tools/run_levels.py ──→ runs/{L}/history.csv + run_meta.json
                                                       │
                       S13′ src/convergence.py  ←──────┘   →  统一摘要 JSON
                       S14′ src/gci.py        （Richardson + GCI）
                       S15′ src/significance.py（bootstrap → Δη_min + 判据）
                                                       │
                              tools/plot_results.py ←──┘  → docs/fig1_gci.png / fig2_deltamin.png / delta_min.json
```

## 三档网格（口径先钉死，避免"数字口径答不上来"）

| 档位 | 特征长度 h | 细化比 r | 2D 结构化网格数 | 收敛口径 |
|---|---|---|---|---|
| L1 粗 | 0.012 | — | 由 `mesh_manifest.json` 填 | 一阶 ROE，隐式，CFL 4 |
| L2 中 | 0.006 | 2 | 同上 | 同上 |
| L3 细 | 0.003 | 2 | 同上 | 同上 |

> 表里的"网格数"必须由 `mesh_manifest.json` 的实际输出填入，不手填估计值。GCI 要求三档**同一算例、同一格式、同一收敛判据**，否则 `p_obs` 无意义。

## 已知前置风险（本沙箱实测，已写进 [BLOCKERS.md](BLOCKERS.md)）

1. pip 的 `gmsh` 在缺 `libGLU.so.1` 的机器上 `import gmsh` 直接 OSError → 提供路径 B（纯 numpy 网格生成，无 gmsh 依赖）。
2. 沙箱到 `release-assets.githubusercontent.com` TLS 被断 → **本会话没有 SU2，仓里任何 cfg 都未经真实求解器验证**，你首跑时按 `BLOCKERS.md` 的清单核对键名。

## 边界（这个框架不声称解决什么）

- 只处理**等比三档 + 单一观测量**的网格不确定度；非单调序列直接拒绝出数（`gci` 抛 `ValueError`），不做"看着像就报"。
- Δη_min 是"可分辨下限"，不是"显著性检验"的全部；v1 只有 bootstrap 一种口径，t 检验留 Phase 2。
- Euler/无粘 + 教程级算例（M=0.8, α=1.25°）只用于**方法论闭环**，不用于对叶轮机械下任何结论。

*台账见 [LEDGER.md](LEDGER.md)；60 天检查点 2026-11-06（S26 对表，未完成项不许擦除）。*
