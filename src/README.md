# `src/` 是手写区（这里没有代码，是故意的）

| 文件 | 步骤 | 规格 | 验收 |
|---|---|---|---|
| `convergence.py` | S13′ | `docs/SPEC-01-convergence.md` | `pytest tests/test_convergence.py` |
| `gci.py` | S14′ | `docs/SPEC-02-gci.md` | `pytest tests/test_gci.py` |
| `significance.py` | S15′ | `docs/SPEC-03-significance.md` | `pytest tests/test_significance.py` |

三条约定：
1. 规格文档只给**公式、契约、判据**，不给实现。想抄，代码在你自己的跟做手册里——抄之前先答 SPEC 末尾的自检三问。
2. 本目录的 commit 由你本人署名。因为代码是你写的，所以没有 AI co-author；**这就是证据链**，不需要额外操作。
3. AI 在这里只做一件事：你写完让它找茬（审查）。它递过来的补丁，除非你逐行看懂并改写，否则不合并。

目标体量：三个模块合计 ≥300 行、带类型注记、可被 `tools/plot_results.py` 直接调用。
