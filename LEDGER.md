# LEDGER · delta-eta-min（本仓台账，随做随填）

> 上游总台账在 `Vicious-competitor-scz/执行顺序单-每步3小时.md`；这里只跟本仓相关步骤。
> 规则：**收尾必 commit + 填本表**。状态用 ☐ / 🔶 / ✅ / ⏸（跳步须在 BLOCKERS.md 有对应行）。
> 判据不达标不许打 ✅ —— 这张表是 60 天对表（S26）的唯一底账，擦除等于自欺。

| 步骤 | 名称 | 预算 | AI | 状态 | commit | 完成日 | 判据（原样抄自顺序单/手册） |
|---|---|---|---|---|---|---|---|
| S05 | 建仓 + 骨架 + 冒烟 | 0.5h | 🤖 | ✅ 已闭环：骨架已合入 main（PR #1） | main: 9626e43 + c48c28f（PR #1 rebase 合并，线性无 merge commit） | 09-07 | `pytest` 跑通；src 相关红=进度条（正常） |
| S07 | T1 证据源锁定 | 0.5h | 🤖 | ☐ | | | `docs/SOURCES.md` 每行可回溯页码才打 ✅ |
| S08 | 本地装 SU2 + 冒烟 | 1h | — | ☐ | | | `SU2_CFD --version` 打出 v8.5.0 横幅 |
| S10′ | 一个脚本出三档网格 🔒 | 1.5h | 部分 | ☐ | | | 三档生成成功 + `tools/check_mesh.py` 全 OK + SU2 各跑 100 步 |
| S12′ | 三档一阶批量跑 | 1h+挂机 | ⏳ | ☐ | | | 三个 `runs/L*/history.csv` 存在，日志尾无 divergence |
| S13′ | 收敛史解析器 🔒手写 | 2h | — | ☐ | | | `pytest tests/test_convergence.py` 绿；真日志复核过 |
| S14′ | GCI 模块 🔒手写 | 2h | — | ☐ | | | `pytest tests/test_gci.py` 绿（两个解析解精确复原） |
| S15′ | Δη_min 检验 🔒手写 | 2.5h | — | ☐ | | | `pytest` 全绿；`git log -1` 无 co-author（因为你真的手写完了） |
| S16′ | 细档二阶深收敛 ⏳ | 0.5h+整夜 | — | ☐ | | | 残差降 ≥4 量级 → 打 🏁 = 第一个个人 E4 |
| S17′ | 两张图 | 1h | 🤖 | ☐ | | | `docs/fig1_gci.png` `fig2_deltamin.png` + `delta_min.json` 数字一致 |
| S22′ | E4 报告 | 1h | 🤖 | ☐ | | | `docs/E4_REPORT.md` 每数字可回溯 |
| S23′ | 线上站挂 E4 | 0.75h | 🤖 | ☐ | | | 部署绿（在 turbine 平台仓做，不在本仓） |
| S24′ | T1 报告 v1 | 1.5h | 🤖 | ☐ | | | 先手写 5 行骨架 → 装配 → 自检三问可答 |
| S25 | 师兄评审一轮 | 1h | — | ☐ | | | `docs/review_r1.md` 3 条狠批逐条落实或反驳 |
| S26 | 60 天对表 🔒 | 1h | — | ☐ | | | `docs/AUDIT-1106.md`（2026-11-06），未完成项不擦除 |

## 🏁 里程碑
- ☐ **第一个个人 E4**（S16′ 达成日 = ______）。在此之前本仓不发布任何数值结论。

## S05 收尾实测记录（2026-09-07，沙箱内可验证的部分；口径全部可复现）
```
$ python -m pytest                     → 27 failed, 12 passed, 1 skipped
  · 12 passed  = 网格生成/拓扑体检/工具类（tools + tests/test_mesh_tools.py + test_smoke 的非手写区条目）
  · 27 failed  = src/ 三个手写模块的验收测试（模块不存在 → 有意红，进度条）
  · 1 skipped  = test_real_log_shape，等 S12′ 真日志（不许用假日志冒充实测）
$ python tools/make_grids_numpy.py     → L1/L2/L3 = 2304/9216/36864 单元，h_eq 精确减半，首层比 0.469/0.484
$ python tools/check_mesh.py           → 三份 .su2 全 OK（翻转/非流形/孤儿点 = 0，markers=[Airfoil,Farfield]）
$ python tools/run_levels.py --dry-run L1 L2 L3 → 装配 + cfg↔mesh marker 交叉校验通过
（以上仅证明"脚手架可用 + 判据自洽"，不构成任何 CFD 结论；判据可达性另用仓外参考实现验证为 40 passed 后删除）
```
未打勾项（沙箱物理限制，见 BLOCKERS #2）：`SU2_CFD` 冒烟、三档各 100 步、任何收敛数值 —— 全归你本机。


## 手写证据链自查（S26 要对这三行负责）
```bash
git log --oneline -- src/ | wc -l          # 手写提交数（目标：60 天 ≥20 个手写 commit 全仓）
git log --format='%an' -- src/ | sort -u   # 只应出现承泽；出现 agent = 代写，按 AGENTS.md §2 处理
git log --grep='Co-authored-by' --oneline -- src/   # 应为空
```

## 周工时账（每周 4–5h 手写+复算；≥3h 必须无 AI 会话）
| 周 | 手写 h | 复算/挂机 h | 白板次数 | 真人反馈 | 本周唯一交付 |
|---|---|---|---|---|---|
| W1 09-07→09-13 | | | | | S05 收尾 + S08 + S10′ |
| W2 09-14→09-20 | | | | | S12′ + S13′ |
| W3 09-21→09-27 | | | | | S14′ + S15′（9 月底判据：仓建立、1 档跑通、手写 ≥300 行带测试） |
| W4 09-28→10-04 | | | | | S16′ 整夜 + S17′ |
