"""S17′：两张图 + `docs/delta_min.json`。

用法: python tools/plot_results.py            # 需要 S12′ 真跑 + S13′/S14′/S15′ 手写完成
前置：src/ 三个手写模块已绿，否则本脚本会明确告诉你缺哪一步（它不猜数据）。

图 1 = 三档 φ(h) 收敛曲线 + Richardson 外推点 + Δη_min 带
图 2 = "宣称增益 vs Δη_min"判据带（T1 报告的核心论据雏形）

⚠️ 图内文字故意全用 ASCII：默认 DejaVu Sans 没有 CJK 字形，写中文会渲成豆腐块
   （本仓 QA 实测报 `Glyph 65289 missing from font`）。要在图里用中文，
   先 `plt.rcParams["font.sans-serif"] = ["Source Han Sans SC"]` 之类的**已安装**字体，
   并且换机器要重新确认字体存在——别把字体问题留到投稿那天。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

LEVELS = ("L1", "L2", "L3")
H_NOMINAL = {"L1": 0.012, "L2": 0.006, "L3": 0.003}      # 与 cases/*.cfg、make_grids 一致
OBSERVABLE = "CD"                                          # v1 单一观测量（口径写死）


def _need(mod: str, step: str):
    import importlib
    try:
        return importlib.import_module(mod)
    except ImportError:
        sys.exit(f"缺 {mod}（{step} 未完成）。顺序：S13′ → S14′ → S15′，"
                 f"验收 pytest tests/test_{mod.rsplit('.', 1)[-1]}.py")


def main() -> int:
    conv = _need("src.convergence", "S13′")
    sig = _need("src.significance", "S15′")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    runs = {}
    for lv in LEVELS:
        p = ROOT / "runs" / lv / "history.csv"
        if not p.exists():
            sys.exit(f"缺 {p.relative_to(ROOT)}：先跑 python tools/run_levels.py {' '.join(LEVELS)}"
                     f"（S12′，必须本机真跑；E4 不接受借用别人的收敛史）")
        runs[lv] = conv.summary(p)

    phi = {lv: runs[lv][f"{OBSERVABLE}_mean"] for lv in LEVELS}
    for lv in LEVELS:
        if runs[lv]["orders_drop"] < 4:
            print(f"⚠️ [{lv}] 残差只降 {runs[lv]['orders_drop']:.2f} 个量级（<4）："
                  f"平台期均值不代表收敛值，图先出、结论先压（LEDGER 标 ⚠️）")

    plateau = runs["L3"][f"{OBSERVABLE}_plateau"]["samples"]
    try:
        d = sig.delta_min(plateau, phi["L3"], phi["L2"], phi["L1"])
    except ValueError as exc:                    # 非单调：不硬造结论，把拒因写进台账
        (ROOT / "docs").mkdir(exist_ok=True)
        (ROOT / "docs" / "delta_min.json").write_text(
            json.dumps({"status": "rejected", "reason": str(exc), "phi": phi},
                       indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"❌ GCI 拒绝出数：{exc}\n   → 已写 docs/delta_min.json（status=rejected）。"
              f"这就是结果，不是失败：把这条写进 E4 报告的'局限'。")
        return 1

    out = ROOT / "docs"
    out.mkdir(exist_ok=True)
    payload = {"observable": OBSERVABLE, "phi": phi,
               "h": {lv: H_NOMINAL[lv] for lv in LEVELS},
               "orders_drop": {lv: runs[lv]["orders_drop"] for lv in LEVELS},
               "plateau_rel_std": {lv: runs[lv][f"{OBSERVABLE}_plateau"]["rel_std"] for lv in LEVELS},
               **d}
    (out / "delta_min.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                                        encoding="utf-8")

    plt.rcParams.update({"font.size": 9, "axes.linewidth": 0.6})

    # ── fig1：φ vs h + 外推点 + Δη_min 带 ─────────────────────────────────
    fig, ax = plt.subplots(figsize=(4.2, 3.2), dpi=300)
    hs = [H_NOMINAL[lv] for lv in LEVELS]
    vs = [phi[lv] for lv in LEVELS]
    ax.plot(hs, vs, "o-", ms=4, lw=0.8, label=f"{OBSERVABLE}(h)")   # 图内文字一律 ASCII
    ax.errorbar([H_NOMINAL["L3"]], [phi["L3"]], yerr=d["dmin"], fmt="none",
                ecolor="0.35", elinewidth=0.8, capsize=3, label="Δη_min")
    ax.axhline(d["phi_ex"], lw=0.8, ls="--", label=f"Richardson φ_ex={d['phi_ex']:.5f}")
    ax.axhspan(d["phi_ex"] - d["dmin"], d["phi_ex"] + d["dmin"], alpha=0.12,
               label=f"Δη_min={d['dmin']:.2e} (p={d['p_obs']:.2f})")
    ax.set_xscale("log"); ax.set_xlabel("mesh size h (log)"); ax.set_ylabel(OBSERVABLE)
    ax.legend(frameon=False, fontsize=7)
    fig.tight_layout(); fig.savefig(out / "fig1_gci.png", bbox_inches="tight"); plt.close(fig)

    # ── fig2：宣称增益 vs 判据带 ──────────────────────────────────────────
    claims = [("L1→L3 网格差", abs(phi["L1"] - phi["L3"])),
              ("L2→L3 网格差", abs(phi["L2"] - phi["L3"]))]
    y = np.arange(len(claims))
    fig, ax = plt.subplots(figsize=(4.2, 3.2), dpi=300)
    ax.barh(y, [c[1] for c in claims], height=0.45, lw=0)
    ax.axvline(d["dmin"], color="crimson", lw=1.0)
    ax.text(d["dmin"], len(claims) - 0.35, "  dmin : left of line = indistinguishable",
            color="crimson", fontsize=8)
    ax.set_yticks(y, [c[0] for c in claims]); ax.set_xlabel(f"|Δ {OBSERVABLE}|")
    fig.tight_layout(); fig.savefig(out / "fig2_deltamin.png", bbox_inches="tight"); plt.close(fig)

    print(f"figs -> {out/'fig1_gci.png'} , {out/'fig2_deltamin.png'}")
    print(f"dmin = {d['dmin']:.3e}  (boot_half={d['boot_half']:.3e}, gci_abs={d['gci_abs']:.3e})")
    print("铁律④：图上每个数字都要能在 docs/delta_min.json 与 runs/*/history.csv 回溯，"
          "画图不等于结论，你核过才算。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
