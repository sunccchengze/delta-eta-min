"""S12′：每档独立目录跑 SU2，并落一份 run_meta.json 给 E4 报告当数据源。

用法:
    python tools/run_levels.py L1 L2 L3
    python tools/run_levels.py --cfg cases/naca0012_2nd.cfg L2 L3     # S16′ 二阶
    python tools/run_levels.py --dry-run L1                            # 只装配目录，不跑求解器

干的事：
  1) 复制 cfg 到 runs/{L}/config.cfg，把 MESH_FILENAME 指到 mesh/mesh_{L}.su2
  2) 跑之前先做三件事：SU2 可执行文件找得到、网格文件在、marker 名与 cfg 对得上
  3) 记录 wall time / 退出码 / SU2 版本横幅 → runs/{L}/run_meta.json
  4) 重跑 runs/RUNS.md 台账表（档位 / 单元数 / 步数 / 残差降幅 / 核时）

不生成任何"结论"。收敛与否由 src/convergence.py + 你自己判读。
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
LEVELS = ("L1", "L2", "L3")


def find_su2() -> str | None:
    return shutil.which("SU2_CFD") or shutil.which("SU2_CFD.exe")


def su2_version(su2: str) -> str:
    try:
        out = subprocess.run([su2, "--version"], capture_output=True, text=True,
                             timeout=60, check=False)
        txt = (out.stdout or "") + (out.stderr or "")
    except Exception as exc:                                   # pragma: no cover
        return f"读取失败：{exc}"
    m = re.search(r"v?(\d+\.\d+(?:\.\d+)?)", txt)
    return m.group(1) if m else txt.strip().splitlines()[0][:80] if txt.strip() else "无输出"


def markers_in_cfg(cfg_text: str) -> set[str]:
    """抓 MARKER_EULER / MARKER_FAR / MARKER_DIRIKLET… 里的标记名，与 .su2 的 MARKER_TAG 比对。"""
    names: set[str] = set()
    for key in ("MARKER_EULER", "MARKER_FAR", "MARKER_DIRIKLET", "MARKER_NEUMANN",
                "MARKER_SYM", "MARKER_MONITORING", "SURFACE_FORCE_COEFF"):
        for line in cfg_text.splitlines():
            if line.strip().upper().startswith(key):
                names |= set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", line.split("=", 1)[1]))
    return names - {"NO", "YES", "CUSTOM"}


def prepare(level: str, cfg_path: Path) -> tuple[Path, str]:
    d = ROOT / "runs" / level
    d.mkdir(parents=True, exist_ok=True)
    cfg = cfg_path.read_text(encoding="utf-8")
    mesh_rel = f"../../mesh/mesh_{level}.su2"
    if re.search(r"^\s*MESH_FILENAME\s*=", cfg, re.M):
        cfg = re.sub(r"(^\s*MESH_FILENAME\s*=\s*)\S+", rf"\g<1>{mesh_rel}", cfg, flags=re.M)
    else:
        cfg = f"MESH_FILENAME= {mesh_rel}\n" + cfg
    (d / "config.cfg").write_text(cfg, encoding="utf-8")

    mesh_file = ROOT / "mesh" / f"mesh_{level}.su2"
    if not mesh_file.exists():
        sys.exit(f"[{level}] 缺 {mesh_file.relative_to(ROOT)}；先跑 tools/make_grids*.py（S10′）")

    from tools.su2mesh import parse_su2            # 本地导入：dry-run 时也想跑这个检查
    want = markers_in_cfg(cfg)
    have = set(parse_su2(mesh_file).markers)
    missing = {m for m in want if m not in have}
    if missing:
        sys.exit(f"[{level}] cfg 引用了网格里没有的 marker：{sorted(missing)}；"
                 f"网格里有 {sorted(have)}。改 .geo 的 Physical Curve 名字或改 cfg。")
    return d, mesh_rel


def write_runs_md() -> Path:
    rows = ["| 档位 | 单元数 | SU2 | cfg | 步数 | wall (s) | 退出码 | history.csv | 时间戳 |",
            "|---|---|---|---|---|---|---|---|---|"]
    for lv in LEVELS:
        meta_p = ROOT / "runs" / lv / "run_meta.json"
        if not meta_p.exists():
            continue
        meta = json.loads(meta_p.read_text(encoding="utf-8"))
        hist = ROOT / "runs" / lv / "history.csv"
        rows.append(
            f"| {lv} | {meta.get('n_cells', '—')} | {meta.get('su2_version', '—')} | "
            f"{meta.get('cfg', '—')} | {meta.get('iters_requested', '—')} | "
            f"{meta.get('wall_s', '—')} | {meta.get('returncode', '—')} | "
            f"{'✅' if hist.exists() else '—'} | {meta.get('started_utc', '—')} |")
    body = ("# runs 台账（S12′/S16′ 自动汇总）\n\n"
            "> 数字全部来自 `runs/*/run_meta.json` 与 `mesh/mesh_manifest.json`，**不手填**。\n"
            "> 收敛达标与否不在此表 —— 那是 `src/convergence.py` + 你判读的事。\n\n"
            + "\n".join(rows) + "\n")
    out = ROOT / "runs" / "RUNS.md"
    out.write_text(body, encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="S12′ 三档批量跑")
    ap.add_argument("levels", nargs="*", default=list(LEVELS), choices=LEVELS)
    ap.add_argument("--cfg", default="cases/naca0012.cfg")
    ap.add_argument("--dry-run", action="store_true", help="只装配+校验，不调用求解器")
    args = ap.parse_args(argv)
    levels = args.levels or list(LEVELS)
    cfg_path = (ROOT / args.cfg) if not Path(args.cfg).is_absolute() else Path(args.cfg)
    if not cfg_path.exists():
        sys.exit(f"找不到 cfg：{cfg_path}")

    su2 = None if args.dry_run else find_su2()
    if not su2 and not args.dry_run:
        sys.exit("找不到 SU2_CFD：先完成 S08（装 SU2 并进 PATH）。"
                 "临时验证脚手架可用 --dry-run；但 E4 必须你本机真跑，"
                 "沙箱里没有求解器也不许拿别处的数当自己的结论。")

    for level in levels:
        d, mesh_rel = prepare(level, cfg_path)
        meta = {"level": level, "cfg": str(cfg_path.relative_to(ROOT)),
                "mesh": mesh_rel, "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        man = ROOT / "mesh" / "mesh_manifest.json"
        if man.exists():
            meta["n_cells"] = json.loads(man.read_text(encoding="utf-8")).get(level, {}).get("n_cells")
        text = cfg_path.read_text(encoding="utf-8")
        m = re.search(r"^\s*ITER\s*=\s*(\d+)", text, re.M)
        meta["iters_requested"] = int(m.group(1)) if m else None

        if args.dry_run:
            meta.update({"returncode": None, "note": "dry-run：已装配目录并校验 marker"})
            (d / "run_meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False),
                                            encoding="utf-8")
            print(f"[{level}] dry-run OK → {d.relative_to(ROOT)}/config.cfg")
            continue

        meta["su2_version"] = su2_version(su2)
        print(f"[{level}] SU2 {meta['su2_version']} 运行中 → {d.relative_to(ROOT)}")
        t0 = time.time()
        with open(d / "su2.log", "w", encoding="utf-8") as log:
            rc = subprocess.run([su2, "config.cfg"], cwd=d, stdout=log,
                               stderr=subprocess.STDOUT, check=False).returncode
        meta["wall_s"] = round(time.time() - t0, 1)
        meta["returncode"] = rc
        tail = (d / "su2.log").read_text(encoding="utf-8", errors="replace")[-4000:]
        if re.search(r"[Dd]ivergen|Failed|failed to", tail):
            meta["warning"] = "日志含 divergence/failed 字样，见 su2.log"
            print(f"[{level}] ⚠️ {meta['warning']}；卡壳预案：CFL_NUMBER 4.0 → 1.0")
        (d / "run_meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False),
                                        encoding="utf-8")
        print(f"[{level}] 退出码 {rc}，wall {meta['wall_s']}s，收敛史 {d/'history.csv'}")

    print(f"台账 -> {write_runs_md().relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
