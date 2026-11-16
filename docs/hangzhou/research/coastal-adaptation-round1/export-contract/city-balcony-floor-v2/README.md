# 城市阳台 floor-v2：源指状连接对象候选

2026-11-11。独立新增模块 `scripts/landmarks/city_balcony_floor_v2.py`，旧 `city_balcony.py` 与共享世界/清单/地形/碰撞均未改动。按项目实景建模 Skill 的独立对象与阶段边界交付。本轮没有运行 Blender 或浏览器。

**已实现**：固定候选下层 datum1.9579020031420153g、主上层5.557902003142015g；在两条既有源足印内制作连续上层连接，完整岸端宽边按当前估计 ground 采样。保留 build / ground_footprints / deck_height_game 接口，以及上/下层语义、虚空、栏杆、玻璃、柱梁、材质与来源轮廓。**未解决**：局部地形切接、实际入口、下层岸线所有权与上下层碰撞/行走；不是完整阳台验收。

## 端边所有权已核实

全部索引指冻结 spec 的 `upperOuterUVMetres`，均源自 relation/8718551。

- 西 finger 多边形 `[12,13,14,15,16,17]`。完整岸端是 **13→14→15→16** 三条源边，不是13→16弦线；内接主台面的边是17→12；侧边12→13和16→17。
- 东 finger 多边形 `[7,8,9,10,11]`。岸端9→10；内接边11→7；侧边7→8→9保留源拐点8，以及10→11。
- 两多边形并集与原上层减下层的几何差面积为0；未另画连接足印或下层桥下平台。

`placement.json` 保存原索引、每条边归属、所有采样点与高度。每条源边（包括全宽岸端及侧边/内接边）采样步长≤1g。岸端样本使用当前独立 GEOS+三角插值 ground；内接边严格共同主上层；侧边按各自真实源折线弧长在两端间插值。只对这些冻结边界做约束三角化，西102、东113个上层坡面三角形。没有把中心诊断高度场当作最终网格。

所有 ground 和绝对 datum 都是明确 **estimated 的游戏改编**。30m DSM与道路平整不提供建筑实测楼坪或台阶证据，端边点仍未证明是运营入口。

## 新模块与参数

`candidate-spec.json` 在旧spec之上嵌入显式 `floorPlacement`；模块缺少此参数会拒绝构建。`placement.json` 是同内容独立可审查参数，含输入哈希。模块纯 Python/math 与 B.face，不导入 Blender，也不读网络或隐藏当前地形。

- `build(b,lm,spec,scale=.6)`：源 ENU/轴向保持；lm 是游戏单位，局部尺寸与高度只缩放一次。上层三角面与板底（保持.39g厚度）同步；源侧封口、栏杆、横梁和代表性桥墩顶部跟随高度场。上层装配体角点允许在源边外1m**未缩放局部米**的有限高度延拓，供梁/栏杆半宽使用，不扩大公共楼板足印。
- `deck_height_game(..., level='upper'|'lower')` / `deck_height_metres`：上层返回相同分片线性坡面；下层保持独立楼坪。源外边界明确归属该楼板；玻璃房足印及边界仍不作为公共楼板。没有凭平面交叠建立隧道或上下层连接。
- `ground_footprints`：保留原136条柱/玻璃窄区域及下界。仅接近段代表性柱头按实际顶面取保守maxY；不新增整片障碍，不填充下层公共空间。
- 原主台面分色材质面积保持。原铺地分色三角化在外轮廓已有细分点，新候选同步细分对应侧封边，修复上层板T接缝；源轮廓不变。下层与玻璃体形体仍沿旧模块。

模块仍支持 lm 的整体平移，便于标准坐标测试；因此正式导出必须使用下述明确 placement，不能沿用 exporter 的默认base0。

## 可重建与主集成导出入口

本包脚本只写本目录。先 CPU 生成参数，再 CPU 复核：

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-floor-v2/prepare.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-floor-v2/check.py
```

下面命令是提供给主集成的**未执行导出命令**。`exporter-placement.json` 使用当前 exporter 的现有schema，并绑定模块/spec/profile/terrain manifest哈希；它与内部 `placement.json` 用途不同，不要混用。

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python scripts/build_hangzhou_landmark_candidate.py -- \
  --job docs/hangzhou/research/core/city-balcony-round2/task-bundles/city-balcony/job.json \
  --spec docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-floor-v2/candidate-spec.json \
  --module scripts/landmarks/city_balcony_floor_v2.py \
  --placement docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-floor-v2/exporter-placement.json \
  --output artifacts/cities/hangzhou/landmarks/city-balcony-floor-v2
```

若目标目录已存在，使用新的隔离目录，不覆盖。沿用既有证据ready job只复用身份/来源/足印证据，不表示本轮高度与运行验收已经通过。模型必须重新计算hash并由主集成接入。

## 实际 CPU 检查

最终 `check-run4.log` 成功，`cpu-validation.json`：

| 检查 | 本轮结果 |
|---|---|
| 模型三角数/旧预算 | **26,026 / 28,000**，未提高预算 |
| 材质 | 5，保持原具体材质 |
| 公共上层平面面积误差 | 约1.31e-12g² |
| 全宽岸端/内侧接缝楼板查询误差 | 0 |
| 坡面三角内部查询误差 | <1.8e-15m |
| 坡面最大精确三角梯度 | 2.227524%，仅几何值，不是无障碍认证 |
| 上层板单体 | 988 triangles，全部1482条几何边方向配对；CPU 1e-9g量化，无开边 |
| 未涉及装配面 | 10,862面逐面保留 |
| 碰撞区域 | 136，平面与minY保持；柱头更新 |
| 负控 | 缺少placement、重复.60缩放均拒绝 |
| 方向/尺度 | 源轴向与整体ENU平移、game-baseY仅应用一次通过 |
| 新独立水面/道路/楼梯/电梯/灯 | 0 |

`cpu-triangles.npz` 是本轮 CPU B 记录器扇三角化的可审查几何，不是 GLB，也不替代 Blender 实际多边形三角化。上层板拓扑检查不覆盖整栋透明双面栏板等设计为开放的组件。实际 GLB float32拓扑、根节点方向与UV仍需导出后检查。

`check-run3.log` 保留了新增上层板拓扑检查首次发现6条T接缝的真实失败；在候选生成器同步细分源侧封边后，最终`check-run4.log`通过。没有删除旧失败或放宽该检查。

## 地形与岸线：保留未通过项

继续使用冻结的1g独立地面样本，**模型顶面减当前地面**：西728点范围 `[-.276426757,+.000292904]g`；东881点 `[-.034872030,+.236187137]g`。西仍有约.276g埋入，东有局部悬空。必须在明确的源 finger/最小接边带内处理 terrain/脚下层选择，不能整体填满下层公共空间。此模块没有改世界地形来伪装接缝已完成。

两个源 finger 与城市阳台岸前缘分别相距28.164935g、26.863746g，独立见`finger-shore-separation.json`；它们的重建不可能自动消除主台面下层的岸体冲突。上一包 `city-balcony-datum-proposal` 已冻结相同base刚性移位下的625对三维残余相交、公共楼板74.331953g岸源区间和三个玻璃体区间。这仍是本对象的blocker；本轮没有用删除整岸或填低层解决它。

需要主集成后续：按源公共下层/玻璃/柱的不同体积冻结岸体和地形所有权；局部接边、导航/到达与上下层碰撞同步；导出后重新算真实三维冲突。上层finger倾斜不能作为下层已可进入的证据。

最后仍须实际GLB、入口/人物接触、浏览器俯视/街面/远景、昼夜、任务可达及性能验收。本轮状态为**独立模块与CPU候选可交付，项目未完成**。
