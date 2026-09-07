// NACA0012 · 2D Euler 网格 · lc 由 tools/make_grids.py 注入（LC_TOKEN）
// ─────────────────────────────────────────────────────────────────────────
// 🔒 手敲区：下面 1–25 行（型线数学）请逐行手打，不要复制。
//    抄之前先回答自己：为什么 x 用余弦分布？为什么半厚度是 5t·(...)？
//    最后一项系数 −0.1036 与 −0.1015 的差别是什么（开口 vs 闭合尾缘）？
//    答不上来就说明这块还没长在你身上。
// ─────────────────────────────────────────────────────────────────────────
lc = LC_TOKEN;                       // 特征长度（弦长=1）；L1=0.012 L2=0.006 L3=0.003

// ── 翼型型线：闭合 NACA 方程 + 余弦分布（每边 N 点）──
N = 60;
For i In {1 : N}
  x = 0.5*(1 - Cos(Pi*i/N));         // 余弦加密：前后缘自然变密
  y = 0.6*(0.2969*Sqrt(x) - 0.126*x - 0.3516*x^2 + 0.2843*x^3 - 0.1036*x^4);
  pu[i] = newp; Point(pu[i]) = { x,  y, 0, lc};
  pl[i] = newp; Point(pl[i]) = { x, -y, 0, lc};
EndFor
pLE = newp; Point(pLE) = {0, 0, 0, lc};
pTE = newp; Point(pTE) = {1, 0, 0, lc};

upp[] = {pLE};
For i In {1 : N} upp[] += pu[i]; EndFor
upp[] += pTE;                         // 上表面 LE→TE
low[] = {pTE};
For i In {1 : N} low[] += pl[N+1-i]; EndFor
low[] += pLE;                         // 下表面 TE→LE（闭环）

Spline(1) = upp[];
Spline(2) = low[];
Curve Loop(1) = {1, 2};               // 翼型 = 洞

// ── 以下非手敲区（工具口径，改了一处三档都受影响，改前先看 mesh/README.md）──
D = 10;
p1 = newp; Point(p1) = {-D, -D, 0, 10*lc};
p2 = newp; Point(p2) = { D, -D, 0, 10*lc};
p3 = newp; Point(p3) = { D,  D, 0, 10*lc};
p4 = newp; Point(p4) = {-D,  D, 0, 10*lc};
Line(3) = {p1, p2}; Line(4) = {p2, p3}; Line(5) = {p3, p4}; Line(6) = {p4, p1};
Curve Loop(2) = {3, 4, 5, 6};

Plane Surface(1) = {2, 1};            // 外环 − 内洞 = 计算域

// ── 尺寸场：近翼型 lc，随距离线性放大（控总量）──
Field[1] = Distance;  Field[1].CurvesList = {1, 2}; Field[1].NNodesByEdge = 100;
Field[2] = MathEval;  Field[2].F = Sprintf("%g + 0.1*F1", lc);
Field[3] = Min;       Field[3].FieldsList = {2};
Background Field = 3;

// ── 物理组：名字必须与 cases/naca0012.cfg 的 MARKER_* 逐字一致 ──
Physical Curve("Airfoil")  = {1, 2};
Physical Curve("Farfield") = {3, 4, 5, 6};
Physical Surface("Domain") = {1};
