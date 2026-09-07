# runs/ · 求解器输出目录（每档一个子目录）

```
runs/L1/config.cfg      # tools/run_levels.py 生成（MESH_FILENAME 已改写）
runs/L1/su2.log         #  stdout/stderr 合并，判 divergence 用
runs/L1/history.csv     #  S13′ 解析器的输入（判据文件）
runs/L1/run_meta.json   #  单元数/SU2 版本/wall time/退出码 → RUNS.md 与 E4 报告的数据源
runs/RUNS.md            #  自动汇总台账（勿手填）
```

- 本目录整体在 `.gitignore` 里（SU2 产物大且可重跑；参照 S02 的"公开仓减重"教训，
  一开始就别让 100MB 的 restart 文件进树）。
- 想留证：把 `history.csv` + `run_meta.json` 两个小文件单独 `git add -f`，
  这样 60 天后别人能复算你的图，而不必你重跑。**这才是 E4 的可审计形态。**
- `RUNS_solution.dat` / `*.vr` / `mesh_L3_*.vtu` 之类永不提交。
