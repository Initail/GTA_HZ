# 钱塘江三桥有限候选交接

唯一写入者为 Codex 子任务 leifeng_candidate。只写本目录和 `scripts/landmarks/qiantang_bridges.py`；没有启动 Blender、浏览器，或改变共享城市数据、配置、资产。

实际门槛：`task-bundles/qiantang-bridges/job.json` 的 **有限结构外观** evidence-ready 通过并记录。`qiantang-bridges-decks`、`xixing-bridge-current`、`boao-tunnel-profile` 三个独立子任务真实 check --record 返回 2，保持 planned 和 blocker。没有 GLB；modelled/verified 未通过，validation.json 八项仍 unknown。

CPU 结果 `cpu-geometry-validation.json`：24,148 三角形，5 种共享材质，0 灯，0 水片，0 公路顶面。钱塘7698、复兴14592、之江1858。实际 GLB 三角化、文件大小、PBR/视觉、碰撞、夜景和 FPS 均由 root 验证。外观范围只有主结构，完整引桥/互通和近景入口等不在已通过范围。

## 模块和坐标

`build(b,lm,spec,scale=.6)` 保存/恢复 b.frame，不导入 city_mesh/bpy，不导出场景。lm.x/lm.z/lm.y 是游戏单位。**lm.y 是调用者选定的河流水面显示高度，不是地面海拔，也不是已测桥面标高。** 三桥原始尺寸以真实米保存，.60 仅缩放一次。spec.anchor 是第一桥源桥体范围的构建锚点，三个桥的中心/轴线另列 spec.bridges。世界位置来自 Hangzhou city_config.project；父任务调整 bbox 到30.15没有改变原点、投影或比例。

桥主结构站位估计误差：钱塘±45m、复兴±35m、之江±70m；平面来源约±5m。之江主桥中心使用对向源路 shape-break 区间与478m桥型/实际照片交叉约束；这些 source nodes **不是已测索塔脚点**。

钱塘江桥 16×67m 的墩距范围与65.84m计算跨径分开。10.7m 是钢桁高度；模型上层19±5m、下层8.3±5m相对照片水面只是估计，不能称净通航高程。官方历史材料不同口径的全长/宽度/无基准“高度”不混用。北3/南1历史50m引桥拱、北端Y路及电气化铁路细节待补。

复兴1376m与11个计算跨径之和1145m分开；图8有端部引桥和拱脚间隙。91.5m两端、十个平均4.8m间隙只是为了在有来源主桥范围内形成有限候选，**不是竣工墩台站表**。大拱47.5±4m/小拱12.15±2m由原论文图8比例估计；上下桥面相对水面22±6/12±4m、相隔10±2m。未画2008图中预留地铁轨道为现状地铁。

之江主桥116+246+116m、钢塔90.5m、椭圆参数73.95/22.2m、3.5m钢箱和41.36m含风嘴结构宽来自论文。90.5m钢塔高度与图1的96.5m总范围有不同基准，不能当作水面以上高度；本候选用18±5m桥面相对水面和相应钢塔脚估计。4.7km路线/3760m包含两岸高架，不能拿来当主跨。环保报告 p14 给实际最大纵坡2.98%、最短坡长350m，p12人行护栏1.1–1.2m；没有提供可直接冻结的世界桥面标高。

## 道路接口（默认含15条）

```python
from landmarks.qiantang_bridges import source_road_profiles, road_height_at, source_rail_profiles

# water_y_game、endpoint_y_game 均已是游戏单位，不再乘.60。
rows = source_road_profiles(
    spec, water_y_game, endpoint_heights_game=endpoint_y_game,
    scale=.60, allow_estimated=True,
    include_outer_continuations=True,
)
y = road_height_at('way/4348186', lon, lat, spec, water_y_game,
                   endpoint_heights_game=endpoint_y_game,
                   scale=.60, allow_estimated=True)
rail = source_rail_profiles(spec, water_y_game, scale=.60, allow_estimated=True)
```

缺少 allow_estimated=True 会明确抛出错误，因为实际测量剖面仍被 blocker 阻止。默认15行包括11条主桥/东接线以及4条之江西续路；显式 include_outer_continuations=False 返回11。每行保留 source way、nodeIds、原WGS链、points、sourceNode heights、≤20m profileSamples、sourceLayer/原tags、status=candidate-estimated、navigationAccepted=False。profileSamples 的 segmentIndex/fraction **不是新增导航交点**。

以 source way 选择桥面高度，不能按XY最近路在上下层之间猜测。公路和铁路 source node/高度表应按 mode/way/deck 分开。原PBF **way/826790145 是闭合桥体 area**，不是铁路中心线；真实铁路是 way/154142001（另804826075是南侧小铁路段，不在视觉主桥范围）。node/3351280499 在公路和铁路共享平面记录；CPU确认两层仍相隔10.7×.60，铁路不进入 source_road_profiles。

可传确切节点的世界端点高度，API按源链距离做估计插值并检查之江来源最大纵坡约束。`endpointOverridesRequireStructureAndNeighborRoadReview` 明确提醒：**修改端点后的坡道不能凭CPU检查自动与当前刚性主结构或邻路匹配**，需root复核/重设 spec.profile 后导出。默认主结构和 nominal profiles 使用同一相对水面水平高度；完整地形/邻路/多层选面仍未通过。切勿把模型与桥路一起叠加通用 layer×6m。

复兴上层4 ways：29169666/154135283与29170042/154135290，source共享1667217046/1667217050。下层3 ways：336983476/340648409/589429905。2026上城史志描述下层公交/非机动/行人，但2025公安交通组织发布会明确推荐驾车经复兴下层；不能无证封禁小车，也不能把每个lower primary的车种、中心通道用途视为已核实。逐way的 actor许可与分层选面待集成。

之江西接 node3112466937 → way306360719/589558020，node3112466958 → way306360714/306360716。已从固定PBF实际提取，spec和API包含它们。root的 `docs/hangzhou/audit/zhijiang-extended-connectivity.json` 确认扩展v5后三条之江桥路各端点均main component0。**这只解决源节点图连接，不等于物理坡道或驾驶通过。** 北东接源路306360738/306360720/306360724/306360728由root原骨架继续保留，不凭几何交叉造接点。

## 发布与材质

baseBuildingIdsToExclude=[]。桥/道路是独立要素，不删除附近普通楼、桥下公园或别的网球/展馆对象。模块没有公路顶面，root道路渲染提供 source-bound asphalt/collision；桥主结构底/侧面与下层铁路外观由候选负责。没有候选河片，水由基础水管线负责。

`suggested-materials.json` 仅使用共享 carpaint/civicred 两个 token，推荐复兴浅蓝和之江红漆；色值/PBR是参考照片估计，未作色彩标定或实机验收。照片均未发布为材质。实际原图、论文和区志仅留 `<TEMP>/qiantang-bridges-research`，本目录仅有URL、作者、日期、许可、哈希及逐图观察。政府区志彩图的建成年份不能当作拍摄日期，之江近景其他方向和每根索锚点待补。

西兴2025-11-22车辆/行人全封闭，2026-10-12资料描述2024启动、2027计划；不生成旧桥可驾驶面或未来完工桥。博奥两个源way明确地下，真实埋深/入口标高/纵坡/净高缺失；不生成表面桥或任意负6m剖面。2025发布会对隧道非机动/行人禁入有明确来源，具体portal/collision仍待核。

可复查命令（已实际执行；第3条现为记录通过）：

```sh
python3 docs/hangzhou/research/core/qiantang-bridges-round2/validate_candidate.py
.venv/bin/python scripts/landmark_tasks.py status --job docs/hangzhou/research/core/qiantang-bridges-round2/task-bundles/qiantang-bridges/job.json
.venv/bin/python scripts/landmark_tasks.py check --job docs/hangzhou/research/core/qiantang-bridges-round2/task-bundles/qiantang-bridges/job.json --stage evidence-ready --record
```

现有 `build_hangzhou_landmark_candidate.py` 可由root串行后台导出，传本目录 job/spec、模块与 suggested-materials.json，并用新的 artifacts 目录。该导出器目前 lm.y=0，只是局部候选水面基准；最终全城水/地形基准须由root放置。子任务没有运行它，不能在 model.json 填构建成功或真实GLB哈希。
