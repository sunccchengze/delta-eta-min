# BLOCKERS · 卡壳台账（卡壳 45 分钟就写这里，然后跳步）

> 规则来自顺序单：45 分钟 = 上限；写下来 = 把坑变成证据，不是变成失败。
> 每条格式：**症状 / 复现 / 已试 / 绕行 / 待验证**。

## #1 `import gmsh` → `OSError: libGLU.so.1`（本沙箱实测，2026-09-07）
- 症状：`pip install gmsh` 成功，`import gmsh` 直接崩在 `CDLL(libpath)`。
- 复现：`python -c "import gmsh; gmsh.initialize()"`，Debian 精简镜像 + venv，无 GUI 库。
- 已试：`sudo apt-get install libglu1-mesa`（本沙箱 apt 源不可达 → 失败）。
- 绕行（已落进本仓）：`tools/make_grids_numpy.py` —— 纯 numpy 结构化 O-grid，判据与路径 A 相同，
  且额外保证三档**嵌套**；`.geo` 路径留着，装好 GUI 依赖后随时可切回。
- 待验证：你本机若 `import gmsh` 正常，就用路径 A（与手册一致），并把本条标 ✅。

## #2 沙箱没有 SU2，且 GitHub release 资产域名 TLS 被断
- 症状：`curl https://github.com/su2code/SU2/releases/download/...` →
  `OpenSSL SSL_connect: SSL_ERROR_SYSCALL in connection to release-assets.githubusercontent.com:443`
  （与《BRANCH-SAFETY.md》通用坑 #5「沙盒出口白名单」同类；302 本身是通的，断在资产域名）。
- 后果（诚实声明）：**本会话没有运行过任何求解器。** 因此：
  1. `cases/*.cfg` 的键名相对手册做了 3 处规范化（见 cfg 头部 `%NOTE`），**未经真实 SU2 验证**；
  2. S08/S12′/S16′ 的判据一个都没打勾 —— 不由 AI 代打；
  3. 仓里没有任何 CFD 数值，图与 `delta_min.json` 只能由你本机真跑后生成。
- 你首跑要做的事：`SU2_CFD runs/L1/config.cfg` 跑 20 步，看有没有
  `invalid or unknown key` 警告；有就把行号和正确键名记回本文件，再 commit。

## #3 待补（S13′–S15′ 手写过程中产生）
- ☐ 例：平台期尾部取 25% 时，若 CFG 的 `CONV_RESIDUAL_MINVAL` 提前触发停算，样本数可能 <min_tail。
  → 处理：`plateau_stats` 的 `min_tail=50` 兜底，但样本 <50 时报告要标注"平台期样本不足"。

## #4 🩸 抓到上游文档的错误：GCI 自检用例的数值不自洽（2026-09-07，本仓 QA 实测）
- 出处：`跟做手册-逐行版.md` S14′ 的 `tests/test_gci.py`，写作
  `gci(1.0625, 1.25, 1.5, r=2)` 并注明 `φ = 1 + h²`。
- 事实：φ(h)=1+h² 在 h=1 时是 **2.0**，不是 1.5。按手册的三元组实测（本会话跑过，非推算）：
  **p_obs=0.4150、φ_ex=0.5000、GCI_fine=66.18%**；改成 `(1.0625, 1.25, 2.0)` 后
  **p_obs=2.0000、φ_ex=1.0000、GCI_fine=7.35%**（解析真值 p=2、φ=1）。
  也就是说：**照手册写出的实现会在它自己的自检用例上红；写对了的实现也会红**。
  这是"判据本身错了"的那一类坑，比代码 bug 贵得多。
- 本仓处理：改成解析解自洽的 `(1.0625, 1.25, 2.0)` → p=2、φ_ex=1 精确复原；
  并在 `tests/test_gci.py::test_second_order_recovery` 的 docstring 里留了这条来龙去脉。
- 你要做的：把这个结论**回写上游**（手册或白皮书对应页），并在 S26 对表时算一条打脸链路：
  预测"文档可用" → 实验"自检用例不自洽" → 结论"引用数字前自己复现（铁律④）不是口号"。

## #5 push 被拒 ≠ 通道已关：先读错误类型（2026-09-07 实测，PR #1 合并之后）
- 症状：合并 PR #1 后执行 `git push --force-with-lease origin <会话分支>` →
  `! [rejected] ... (stale info)`。**这不是**《BRANCH-SAFETY.md》铁律 2 说的"通道已关"。
- 真因：Arena 沙箱的 clone 是**单分支** refspec（`+refs/heads/main:refs/remotes/origin/main`），
  本地根本没有会话分支的 remote-tracking 引用 → `--force-with-lease` 拿不到期望值，只能报 stale info。
- 解药（已验证有效）：显式给 lease 期望值 ——
  `git push --force-with-lease=refs/heads/<分支>:<远端sha> origin HEAD:refs/heads/<分支>`。
- 本次实测副产品：**REST 合并（merge_method=rebase）之后 push 仍可用**，
  即"合并 PR 立刻关闭本会话远程通道"在这一次没有复现。
  ⚠️ 但**不要把这条当免死金牌**：铁律 1（每步 commit+push）保护的是"未推送的提交永久丢失"，
  那是不可逆损失；通道是否关闭只是可用性问题。一条样本也不足以推翻旧教训，照旧先推再做。

## #6 matplotlib 默认字体无 CJK（本仓 QA 实测）
- 症状：`UserWarning: Glyph 65289 (FULLWIDTH RIGHT PARENTHESIS) missing from font(s) DejaVu Sans`
  → 图里的中文/全角符号渲成方块。
- 已处理：`tools/plot_results.py` 图内文字改全 ASCII（论文图本来也该如此）。
- 若确需中文图：装字体后 `plt.rcParams["font.sans-serif"]=[...]`，并把字体名写进 E4 报告的复现段
  （否则换机器复现不出来 = 口径丢失）。

