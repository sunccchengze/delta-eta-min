# mesh/ · S10′ 三档网格

| 文件 | 来源 | 说明 |
|---|---|---|
| `naca0012.geo` | 手册路径 A | 含 🔒 手敲区（型线数学），`LC_TOKEN` 由 `tools/make_grids.py` 注入 |
| `make_grids.py` / `make_grids_numpy.py` | tools/ | 两条互斥路径，**三档必须同源** |
| `mesh_{L1,L2,L3}.su2` | 生成物（已 gitignore） | 187KB / 747KB / 3.1MB，别提交 |
| `mesh_manifest.json` | 生成物 | 单元数 / h_eq / 首层厚度 / 细化比 —— E4 报告的网格表以此为准 |

## 档位（口径）

| 档位 | 路径 A `lc` | 路径 B `nb × nr` | 名义 h | 相对上一档 r |
|---|---|---|---|---|
| L1 | 0.012 | 96 × 24 | 0.012 | — |
| L2 | 0.006 | 192 × 48 | 0.006 | 2 |
| L3 | 0.003 | 384 × 96 | 0.003 | 2 |

## 两路径的已知差异（不是 bug，是口径；报告里要写清用了哪条）

1. **远场形状**：A 用 20c×20c 方框；B 用物面法向等距外推 10c 的封闭外边界。
   远场尺寸会直接影响 Euler 的 CD（反射波/边界距离效应）→ 换路径 = 换算例，不能混档。
2. **尾缘**：A 用 −0.1036（开口尾缘，TE 有微小厚度）；B 用 −0.1015（闭合尾缘）。
3. **网格族性质**：B 是**嵌套**族（L1 节点 ⊂ L2 ⊂ L3，`tests/test_mesh_tools.py` 逐点验证），
   法向由与 `nr` 无关的连续映射 `s(η)=(e^{κη}−1)/(e^{κ}−1)·D` 给出 ⇒ `h_eq` 精确减半（r=2 成立），
   首层厚度实测比 0.47–0.48（指数聚层的非线性，报告里如实写）；
   A 由 gmsh 尺寸场生成，非严格嵌套 —— 用 A 时 `p_obs` 偏离 1/2 更多是**正常现象**，
   不要为了好看去挑网格，把 `p_obs` 如实写进报告。

## 判据（S10′）
```
python tools/check_mesh.py            # 翻转=0、非流形=0、孤儿点=0、两个 marker 都在
python tools/run_levels.py --dry-run L1 L2 L3   # marker 名与 cfg 逐字一致
SU2_CFD ...  # 本机：三档各能启动 ≥100 步（沙箱无求解器，这条只能你自己打勾）
```

## 卡壳预案（按顺序试，别硬磕）
1. L3 太慢 → `lc` 改 0.004（r≈1.5 仍达标 ≥1.3），并同步改 `tools/plot_results.py::H_NOMINAL`。
2. gmsh 报 `CurvesList` 无效 → 老版本改回 `EdgesList`。
3. markers 缺失 → 检查 `.geo` 末尾三行 `Physical Curve("...")` 的引号与拼写。
4. `import gmsh` OSError（libGLU）→ 直接走路径 B；或 `conda install -c conda-forge gmsh`。
