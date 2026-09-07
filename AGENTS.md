# 本仓铁律（对任何 AI 会话与人类协作者生效）

> 本仓不是"多一个 AI 产物"，而是**反 slop 的能力建设仓**。规则违反一次，仓里的 git log 就失去证据价值。

## 1. 手写区不可代写
`src/` 下三个核心模块**必须承泽本人逐行手写**，AI 只可审查、不可代写、不可"顺手补全"：

| 模块 | 步骤 | 规格 | 验收 |
|---|---|---|---|
| `src/convergence.py` | S13′ | `docs/SPEC-01-convergence.md` | `pytest tests/test_convergence.py` 绿 |
| `src/gci.py` | S14′ | `docs/SPEC-02-gci.md` | `pytest tests/test_gci.py` 绿 |
| `src/significance.py` | S15′ | `docs/SPEC-03-significance.md` | `pytest tests/test_significance.py` 绿 |

规格文档给的是**公式、契约和判据**，不给实现代码——这是刻意的。想抄，代码在你自己的跟做手册里，抄之前先问自己：这次推导我记住了吗。

## 2. 署名 = 事实（科研诚实红线）
- 谁写的代码就署谁的名。承泽手写的 `src/` 提交，本来就不该有 AI co-author——**因为确实没有 AI 写它**，这条同时是证据链和诚实线。
- AI 起草的脚手架（`tools/` `tests/` `docs/` `README`）**保留** `Co-authored-by: arena-agent` 署名，不摘。
- 🩸 红线：不得为了制造"手写证据链"而摘掉 AI -authored 提交的 co-author。被发现的代价是整个证据链（乃至白皮书里"证据等级"这套自设标准）作废。
- 对应监督协议触发线②：`src/` 出现代写痕迹 = 立即提醒。

## 3. AI 允许的范围
`tests/` 夹具与测试、`tools/` 脚本、文档装配、图表美化、LEDGER/报告排版。这些"只要有"的东西一律 AI 提速 + **人工核每个数字**。

## 4. 数值纪律
- 铁律④：引用任何数字前先自己复现，不许照抄。`docs/SOURCES.md` 每行必须可回溯到出处页码才可打 ✅。
- **复算完成前，README 与 docs 不展示任何 CFD 数值。** 空着的表比填了猜测的表强。
- 每个 E 级标注沿用白皮书口径：本仓目标是 **E4（自己生成的网格 + 自己跑到的收敛）**；AI 代跑不计 E 级，沙箱没有求解器也不假装跑过。

## 5. 流程纪律
- 每完成一个可交付单元立刻 `commit` + `push`，绝不攒提交。
- 每步 ≤3 小时；超了 = 步骤设计错误，当场拆两步。卡壳 45 分钟 = 写 `BLOCKERS.md` 然后跳步。
- 收尾必 commit + 填 `LEDGER.md`。
- 遇到权限/网络/环境问题直接说，不绕过去假装完成。
