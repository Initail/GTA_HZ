# 城市阳台局部切地分区与垂直边界 v1

2026-11-11。**仅 CPU 候选，尚未实际导出 GLB、接入全城或运行角色/浏览器。** 不修改任何共享源码、OSM、源 TIN、物理合同、总资产或 Blender 场景。

冻结输入为 `artifacts/cities/hangzhou/render-input-v7`，site-surfaces SHA256 `f3b6ce4ee5fba89a79c305bb4207ed24903680dfb5f6745bd17de783e843ac81`。输出 `local-terrain.npz` SHA256 **b53962b53b145e6c87b17cdbbf5113eaf213dddd9db905ef77b6f0587fb42a91**，坐标 `[east,north,up]` 游戏单位，已应用 .60；不得再缩放。

## 范围与高度归属

局部矩形 `[3251.0920671851886,-2072.263134140863,3381.647878908849,-1880.6207393499228]` 仅包围三组 cut 加 6g 检查边缘，不替代全城。面积 25020.0284126g²，其中原干地 14950.7157263g²、水体 10069.3126863g²；二者无洞、无叠，当前渲染器的 bbox−water 与 `city.land` 相同。

原三组 cut 为 main 11、west 102、east 113 个源三角，并集 6417.7924711g² 全在干地。main 与 west/east 分别重叠 .657361878/.741716979g²，是既有硬件 allowance 的结果。必须按 `min(F1, 所有覆盖 cut planes)` 求值；不能按组覆盖。main 在这两条窄带仍取 1.5579020031420152g，而非被 finger 抬高。

先实际调用共享 `SitePartition.split(dry, Surface.uncut_ground)`，获得 367 个源归属片。派生网格统一 noding 后，根据原片确定归属，顶点使用归属面自己的高度 closure：cut 内取 min，域外保持 F1。不能用全局 `ground()` 查询切割外侧的共边顶点，否则高侧被拉向低侧，产生虚构斜坡。

- **41906 顶面三角**，`top-provenance.json` 给每面的源 owner / land 或 park 材质。
- **1716 垂直侧面三角**，856 段高低边，`vertical-boundaries.json` 给两侧 owner、高低端点和壁面索引。
- 侧面只连接同一条 XY 边的两个高度，不跨越地面插出坡面；使用土地材质，属于估计的地形切面，不冒充有测绘证据的挡墙。
- 地板、下层空间、柱子、玻璃、栏杆、原道路和水面没有新建或删除。低层仍不启用步行入口。
- 钱塘江水位仍 .9g，水面保持原管线。岸界由 `shore-glb-v3` 负责；这里不重复造岸墙/水片。
- 局部 crop 边界与水岸有明确开放所有权，不能把此包称为封闭整块土壤实体。

## 数值规整与原始边界

三类几何必须区分：源 OSM/TIN/physics 不变；派生渲染线网使用 **1e-8g 网格**；指标统计另外使用 1e-10g 临时几何清理布尔回折，后者不写回资产。

直接反复布尔差集产生约 1e-13g 宽的残余面；这些面在原查询容差下可能选到相反的高低侧，不能保留成实质地形。统一 1e-8g noding 只用于派生计算。原 dry/water 外边界和原顶点在输出前恢复；恢复过程的 3 对重复岸界节点距离不超过 **8.6648558e-9g**，统一后仅消除 3 个零投影面积的派生三角。没有删源 TIN 面或移动源物理边界。

最终顶面并集与**原干地**的对称差面积为 **0**，水体覆盖 **0**；内部 cut 归属边最大实际位移 **6.3252e-9g**。各组原/派生边界、增减面积、材质域变化在 `ownership-boundary-differences.json` 和 `boundary-validation.json`。主楼/west/east/F1 的指标规整后边界 Hausdorff 均小于 6.35e-9g；land/park 小于 6.97e-9g，材质域对称差约 1.52e-6g²。

原始 GEOS 指标对 F1 / land 曾给出 24.676g / 1.838g 的 Hausdorff 异常，同时面积差仅纳米边界量级；直接测量全部实际侧墙到两侧原边界的距离仍只有 6.3252e-9g。原始指标失败保存在 `raw-metric-*`，只对临时测量几何以 1e-10g 消除布尔零宽回折，另以 1e-9g复算得到相同量级。**`rawBoundaryMetricPassed=false` 保留，不将原始指标改写为通过。** 正式接入采用实际线段距离、域面积、拓扑及明确规整后的指标共同验证。

## 当前检查结果与边界高差

`validation.json`：293342 个顶点/边中点/内部探点，源归属顶点误差最大 7.45e-11g，普通插值误差最大 **.0059496817g**（预算 .01g）；正面积重叠 0，水体覆盖 0，退化三角 0，内部开边 0、多重边 0、同向共边 0。数值拓扑复核使用 1e-9g，原始精确边 incidence 同时记录；剩余开放边 492 条归岸线、390 条归局部裁切。

高度不连续边不能纳入“平滑误差”平均：

- 距所有原归属边 >2e-8g：283292 点，最大高度差 .0059496817g，>.01g 的 0。
- 边界窄带 ≤2e-8g：10050 点单列，3316 点与全局 physics 最低闭边高度差 >.01g，最大 **4.27787321g**。
- 高侧 closure、低侧 closure 与全局 `ground()` 在同一 XY 的值不同是显式台阶语义；现网格以真实竖直侧面封闭，不能把这些多米高差称作纳米高度误差，也不能宣称全域同 XY 高度完全相同。

`float32-preflight.json` 是**模拟**局部原点 `[3316.369973047019,-1976.441936745393,3.767477681446]` 的导出，最大顶点误差 4.93e-6g，退化 0。它不是实际 GLB 结果；采用另一分块原点须重新验证。

## 接入契约

1. 顶面渲染采用所属 closure，并在原三组 cut 边界先分区。这个检查包只对局部 crop 有所有权；全城原域外仍用 F1。
2. 保持 source plane 的 min 规则；共享顶点不能只存一个全局 y。高低同 XY 使用不同顶点，并添加本包明确侧面。
3. 使用统一线网 noding 和源边恢复，不能按独立三角最长边切分后留下 T 接缝。普通顶面是 1g 网格及原 DSM 对角线细分；这不是提高 DSM 实测分辨率。
4. crop 外侧必须和原基础地形共同分割/匹配。本包 crop 边无侧墙，不应围成突起的孤岛。
5. source floor 的所有局部干地投影均落在 cut 域内（上层残差 8.6e-14g²）；水上部分仍依赖原地板/柱与岸线，不铺新陆地。
6. 原 `.01g` 楼板底隐蔽间隙、真实下层公共空间与源足印保留。柱基础与土体接触不能当作“所有三维对象互不相交”的证据。

主线仍需实际局部 GLB 导出、localFloat 拓扑、岸线/地板连接、角色身体与栏杆间隙、基础渲染分块接合，以及浏览器实机验收。这里没有触发全城重建。

## 失败保留与复验

`initial-failed/`：原始网络分类漏域 .020741738g²。`raw-closed-domain-failed/`：精确补齐域后仍有亚纳米残余面及浮点焊接问题。`snapped-network-exact-clip-failed/`：仅规整部分流程导致微缝。`closed-cpu-float-risk/`：CPU闭合但模拟float32退化3面。`build-run*.log`、`raw-metric-*`保留各轮结果。

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-terrain-partition-v1/build.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-terrain-partition-v1/validate.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-terrain-partition-v1/check-boundaries.py
```

重建可能改变 NPZ 容器时间戳，接入必须绑定当次哈希；本冻结包不得原地重新生成后继续沿用旧哈希。
