# 武林广场有限候选交付

独占模块 `scripts/landmarks/wulin_square.py`；规格 `docs/hangzhou/research/core/wulin-round2/spec.json`；任务 `docs/hangzhou/research/core/wulin-round2/task-bundles/wulin-square/job.json`。

已实际以 `--city-id hangzhou` 生成任务并通过 `check --stage evidence-ready --record`。主范围限定为固定地图南部广场边界、五瓣抬高池与浅环沟、三中央舞带人物和五外围奏乐人物、环/轴铺装与有限花盆样本。没有实际 GLB；modelled、verified 保持 pending。

## 坐标与身份

固定 PBF SHA256 `4eb65f64925498408faeee7eb04b60d7eb8a01c49ddb239f73070d4d282c75a9`，2026-10-11T20:21:06Z。广场 `way/589390765`、喷泉 `node/4228526321` 的原 OSM API 坐标与该快照逐点相同。

广场映射中心 `[120.15865041655836,30.27335428045256]`，当前杭州投影游戏EN `[210.74610842652575,-42.949547448529835]`。喷泉点 `[120.1586003,30.2734489]`，游戏EN `[207.85277571439437,-36.655999795258786]`。模块中重新用 `load_city('hangzhou')+project()` 计算，不复制深圳坐标或商业地图坐标。

独立现状照片 `File:Wuling Square Fountain.jpg`（Takashishin，2026-04-30）有 WGS-84 手机 GPS 相机位置 `[120.158539,30.273672]`、真向174.924°。相机位于固定喷泉点北侧约25.4m，向南实拍，支持该对象位置。手机GPS精度没有公布，不当喷泉中心/直径测量。

固定邻接：浙江展览馆 `way/27752370` 北侧、杭州剧院 `node/3386064852` 西侧、地铁 `node/9826798534` 东北侧；杭州地铁官方介绍与政府交通说明、实际2026全景一致。OSM仍非现场测量，平面误差允许±5m。未经核验的30.28x记忆、商业GCJ、Wikidata缓存/粗精度DMS均未改写坐标。

## 模块接入

- `build(b,lm,spec,scale=.6)` 只写 B 原语；无 `bpy/city_mesh` 导入、初始化、导出或全场景副作用。调用者负责finish/export。
- `lm.x/lm.z/lm.y` 为游戏单位；几何米制参数仅缩放一次。`lm.lon/lat` 若传入必须与游戏锚点相符。成功和异常均恢复 `b.frame`，保持东/北/上与既有GLB根方向处理。
- `plaza_outline()` 是真实地图广场边界；`ground_footprints()` 只返回喷泉保守外包络，不把整个开敞广场当实心楼体。该包络未通过车/人绕行或进入验收。
- `baseBuildingIdsToExclude` 为空：`way/589390765` 不是楼体。不要排除展览馆或杭州剧院；本模块未替换它们。
- 前缀建议 `detail_wulin-square_`，与真实任务对象ID对应。照片、字体、外部模型、贴图和新增灯均为0。
- 当前共享材质9个：`bark,civicred,concrete,leaf,pavement,roadline,roof,steel,water`。白漆不锈钢用非金属浅色 `roadline` 作近似；不是把雕像材质记作水泥，也不是校准后的最终氟碳漆外观。

## 外观与误差

现状实照支持抬高、内收的深色五瓣池壁，顶部水面、外围低浅环沟，以及3尊高舞带少女和5尊较矮坐/蹲奏乐少女。原创建模使用连续裙身、头/发体积、弯臂、开放双舞带环和五种不同乐器，没有用照片贴图或下载雕塑网格。人物比例、手指、面部、裙褶和艺术品细节仍为有限近似。

池平均半径14.3m、波瓣幅度2.7m、环沟宽1.5m、墙高1.45m均是实照/地图粗比例估计：平面±20%，沟宽±.5m，墙高±.35m。中央7m/外围3.2m群雕高是报道约数与实照形体参照的候选估计，非现物实测；分别保留±1m/±.5m。外围乐器集合有来源，具体顺时针落位未知，当前顺序是估计。

20盆花是报道100余盆与高位图启发的稀疏近区样本，不能宣称数量、位置或季节植物复原完成。北展览馆广场、东西完整花床/树群、东部下沉庭院、地下开口、坡阶与全部周边建筑单列 pending。不得用普通盒楼冒充这些对象。

## 实际执行与边界

`python3 docs/hangzhou/research/core/wulin-round2/measure_wulin.py`

`python3 docs/hangzhou/research/core/wulin-round2/validate_candidate.py`

`.venv/bin/python scripts/landmark_tasks.py generate --city-id hangzhou --source docs/hangzhou/research/core/wulin-round2/catalog.json --place wulin-square --agent codex-wulin-round2 --output docs/hangzhou/research/core/wulin-round2/task-bundles`

`.venv/bin/python scripts/landmark_tasks.py check --job docs/hangzhou/research/core/wulin-round2/task-bundles/wulin-square/job.json --stage evidence-ready --record`

CPU：18,798 triangles、8,455 faces、9材质、0灯。通过三加五角色、有限/非退化面、凹多边形铺装面积、源地图投影、单次缩放与游戏基面、偏移锚点、异常frame恢复及无场景导入检查。

主集成统一后台Blender导出、当前模型俯视/地面南北视角、地形基面/导航/碰撞、喷泉水柱、夜景和性能。CPU统计不等同实际GLB、艺术品形体、游戏加载或FPS验收。
