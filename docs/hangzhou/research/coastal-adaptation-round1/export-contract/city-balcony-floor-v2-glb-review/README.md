# 实际城市阳台 floor-v2 GLB 与局部岸体所有权

2026-11-11。独立读取主集成实际导出；本审查没有启动 Blender 或浏览器，也没有修改共享世界、旧岸v2或对象模块。

## 实际 GLB 结果

绑定 `artifacts/cities/hangzhou/landmarks/city-balcony-floor-v2/city-balcony.glb` SHA256 **731066a06278848025c19153584eae7539e0ba7a73db49540e6eb7679ff67757**。actual delivery 的源码、spec、baseY 与冻结候选一致。

- 实际26,026 triangles、5mesh、5材质，与CPU预算一致；下层base1.9579020031420153g。
- CPU→GLB、GLB→CPU双向逐顶点最近距离最大0.000168786g；没有超.002g容差的新增/缺失顶点。
- 300个明确上层三角形按世界float32顶点集合精确全命中，缺失0。完整端边与内缝实际顶点见`actual-terminal-contacts.json`。
- UV/法线全部有限，无零面积三角形。没有新增水面、楼梯或平台源足印。
- 当前实际GLB对四岸的3D表面相交为 **0 / 0 / 625 / 0**。625对仍全部在城市阳台岸段：concrete500、darkglass64、landmarkglass18、steel43、roof0。数据在`actual-four-shore-intersections.json`。所以这不是碰撞或接入通过。

这里独立解码GLB坐标与节点，再做几何比较；不是只信 delivery 数字。CPU上层板闭合检查保留在上一包，当前实际整栋包含有意双面玻璃等开放组件，不以“整栋闭合”假断言代替分部验收。

## 可执行的最小岸体裁切契约

`ownership-contract.json` 与下列8份GeoJSON均绑定上述当前实际GLB哈希。**坐标是已缩放的杭州游戏 ENU，GeoJSON XY=east/north，第三维若有=up；不是EPSG:4326经纬度，禁止再次.60缩放。**

| 文件 | 精确用途 |
|---|---|
| `source-floor-support.geojson` | 源主楼envelope与扣除三玻璃体后的public lower footprint分别列出；finger不在主楼mask里 |
| `hardware-allowance.geojson` | 源主楼边加明确.03g当前模型硬件余量的clip envelope，以及只增加的环带 |
| `pillar34-subtraction.geojson` | 唯一相关代表性柱record34的原方形及+.001g序列化余量扣除形状，含min/maxY |
| `shore-owned-mask.geojson` | 原.12g岸实体与clip envelope的交区，以及减去柱后的可封闭候选平面 |
| `source-shore-stations.geojson` | 原岸线准确站距和原前缘坐标，不新增道路/OSM节点 |
| `dry-main-terrain-cut.geojson` | 仅现有干地主楼范围的terrain cap，不生成水中陆地 |
| `west-finger-terrain-cut.geojson` | 西源finger完整足印及102个三角形的明确3D terrain上限 |
| `east-finger-terrain-cut.geojson` | 东源finger完整足印及113个三角形的明确3D terrain上限 |

为什么不能只用无余量源边：实际下层钢栏与岸的交点有0.025610007g越过源足印，float32亦有微偏移。明确采用**.03g模型硬件余量**，不是把建筑真实足印改大或伪造测量。最初无余量契约保留为`ownership-contract-v1.json`，不能拿它覆盖最终契约。

1. 只处理原600g岸线的 **station198.4367730578943至393.4376262379045g**（含硬件余量）。无余量原源建筑范围为198.467880729235至393.407327925590g。裁切以完整mask的几何交为准，不把四舍五入站距当布尔几何。
2. 范围内岸顶取 `min(originalTop, 1.5579020031420152g)`。该上限=`lowerFloor1.9579020031420153 - slabThickness.39 - hiddenClearance.01`。保留岸底0.6g和水面0.9g；每个切口重封闭。1cm余量属于隐藏接触的明确游戏几何容差，不是实测缝隙。
3. 柱record34穿过此高度区间，必须再扣其实际模块方形+.001g序列化容差。柱minY=.15790200314201552、maxY=5.167902003142014g；源线投影约station265.024750591315–265.834834019532g。它是来源足印内代表性估计柱位，不能称为实测结构位置。
4. 受控岸实体面积仅23.398966951g²；其余48.599157629g²原岸平面和另外三岸保留。不能删除整条600g岸、移动水界或把源河面改成陆地。
5. 修改后重新生成封闭实体并检查实际GLB的正体积交叠/接触；已有625对相交中的1250个交点均落入提议的高度cap或柱扣除域，未覆盖点0。但这只是**旧交点覆盖检查，不是新实体零相交证明**。

## 地形接入规则：切低，不填下层

岸体仅.12g宽。只裁岸模型而保留同位置原terrain/脚下高度会留下隐形阻挡，因此对应视觉与物理所有权必须一致。

- 主楼：在`dry-main-terrain-cut.geojson`精确干地范围内，`newTerrain=min(oldTerrain,1.5579020031420152g)`。保留水掩码、下层实际楼板与上层独立查询，不把玻璃体内部当公共楼层。当前1g样本5031点显示需降低约2.092198–4.274091g，**这是相当明显的source building volume游戏改编**，不是DSM证明的真实开挖；不能宣称当前地形已经接上。
- finger：每个三角形第三维已经给出 `upperProfile - .39g - .01g`。在精确源finger内，按三角重心插值取得上限，再取`min(oldTerrain,cap)`；不抬地、不添加桥下下层板。西当前采样需降低.399707–.676427g，东.163813–.434872g。这样板厚不会穿入现有terrain；端边脚下仍由上层板与外部ground接合。
- 不扩大到相邻广场、绿地或道路；不连接layer=-1之江路；玻璃体内部功能、实际下层入口、主楼边界的保土/墙体接触仍未知。source masks只赋予建筑体积所有权，不授权虚构室内入口。
- 主集成应先在新隔离候选中构造这一几何/物理接合，再验证路径、人物层选择、碰撞和落水。旧shore-v2保持不变，不能只隐藏冲突面来假通过。

## 重算与剩余门槛

`check.py` 为实际GLB/3D相交审查；`ownership.py`从当前精确几何和实际交点计算受控范围；`freeze_masks.py`输出mask并检查旧交点覆盖。输入、脚本与产物哈希在清单中。

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-floor-v2-glb-review/check.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-floor-v2-glb-review/ownership.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-floor-v2-glb-review/freeze_masks.py
```

仍待实际新岸体/terrain候选、局部墙体接合、上下层脚下查询、真实入口可达、GLB导出后复核、浏览器身体接触/昼夜/三视角/性能。当前结论为**实际GLB与候选一致；局部所有权可实施，运行与视觉未通过**。
