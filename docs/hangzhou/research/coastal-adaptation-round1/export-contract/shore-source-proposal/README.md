# 固定 OSM 岸线结构证据与有限建模选段

2026-11-11。全部调查使用已有 `zhejiang-261011.osm.pbf`，SHA256 `4eb65f64925498408faeee7eb04b60d7eb8a01c49ddb239f73070d4d282c75a9`，没有联网更新或替换快照。对照 `water-data-v3/city.json`，SHA256 `b8d04810aa8f26f9020794a53def59e35e2aeaba0061d30284d59833d1f2ff47`。只写本研究目录，没有改共享数据、建模或导出。

**推荐首批采用4个独立连续岸段：一个有明确挡墙标签的滨江段，以及钱江新城、奥体、滨江公园各600 game的真实湿干边界段。** 它们各自连续，不是把两岸连成一条跨江曲线。后三段不能宣称已有真实挡墙结构证据；可先做地形接边及明确标为estimated的有限艺术岸面。

完整精确WGS84/game几何、原节点、源版本和邻近步道见 [proposals.json](proposals.json)。坐标仅按现有投影/.60转换一次；几何数值误差不是源地图测量误差。

## 优先结构段：滨江樱花大道邻接挡墙

- **墙源：`way/157906999`，`barrier=retaining_wall`，version 3，2012-04-14T08:54:12Z。** 这是固定2026快照内保留的源标签，不能据其编辑时间宣称2026实地检查。
- 全源线3039.091717 game，与钱塘江河面关系 `relation/8227206` 的边界成员 **`way/638705820`共享30个原始节点**。
- 冻结其中**源node索引15..28（含端点），segment索引15..27**，连续长度 **1635.486891 game**，约2725.81真实米的游戏投影长度。
- 起点 **[120.1493461, 30.1945061]**，node **1710977133**；终点 **[120.1752514, 30.2030268]**，node **27572803**。全部14个选中节点都在河面边界成员中，保留原序、没有新导航节点。
- 每段21点对照水体边界，最大距离约 **4.54e-13 game**。沿源方向作左右0.5 game探针，所有段左侧为水、右侧为干地；可据此生成面法线和干侧顶缘，不能据此推出墙高。
- 邻接主要步道 **`way/157906996` 樱花大道**，最近1.289 game；标签含 `highway=footway`、`foot=yes`、`lit=yes`、`width=5`、`surface=塑胶`。5m只是reported OSM值，非本轮测量；**不能把这条塑胶步道擅自套成实测石材铺装**。附近另有`way/839204274`桥上樱花大道，明确`bridge=yes,layer=1,paving_stones`，必须另按桥层处理。

完整墙线还有部分与当前水面边界偏离1.119、24.612至25.695 game的段，本次没有强行吸附或补成整条可靠墙。另一段source segments0..9的970.995778 game也数值贴合，但暂保留为后续扩展。源结构几何与地图边界吻合不等于实测挡墙脚/顶线。

**可实施范围**：按选中原线制作带高度来源记录的挡墙候选，墙顶取当前地面估计、下沿取局部0.9 game暂定水面以下有限遮挡值；这些高度和厚度全部`estimated`。标签没有height/material/顶底测点，故混凝土、砌石、压顶尺寸、夜景灯和栏杆样式均未知，不能标为实景复原通过。

## 其他三段：有真实岸界，墙型仍为艺术估计

以下各段沿真实河面外环在具名锚点最近岸站左右各取300 game。端点为边界线性插值点，是本轮选择范围，不冒称原OSM节点；JSON保留原边界成员完整几何和nodeIds。

|选段|水界源成员|起点WGS84|终点WGS84|结构/路径证据|
|---|---|---|---|---|
|钱江新城·城市阳台|`way/582931239`|[120.20978039007107,30.240458585331137]|[120.21529745685294,30.248092044972353]|选段60 game内未找到明确墙/堤线；最近步道`way/592090661`约8.899 game，`pedestrian,paving_stones,lit=yes,bicycle=designated`|
|奥体·大莲花临江岸|`way/638705820`|[120.22355193152147,30.23874632196501]|[120.21851477465528,30.232383398802003]|有`way/611867838`坝线距岸3.714 game，但坝不等于整段岸墙；`way/582244982`为paving_stones步道，最近11.079 game|
|滨江公园临江岸|`way/638705820`|[120.20465118681975,30.218445768156542]|[120.19592278322139,30.213941994247634]|有`way/159843400`码头pier与岸交汇，不能据码头推定整段墙；步道`way/652437248`最近3.787 game，`way/582244982`最近2.808 game|

这三段首先适合补**已有地形裁水边界的接边几何**；如为画面制作墙面/压顶/护岸石，须明确是有地理依据、结构参数未确认的艺术估计。原路径中心线、已知桥层与道路/地标平台保留，不在岸界上凭空平移/扩大成新步道。JSON的`nearbyPublicPaths`只表示标签允许且地理相邻；本轮没有对每条邻近路径做全图通行验收，不能由距离判断已连通。

## 其他真实标签：保留但不能错放

- `way/815833660`：`man_made=embankment`，424.634 game，位于约120.2672–120.2732 / 30.2936–30.2956，距河边最近2.513 game。它在更东北的岸段，不能复制到城市阳台。
- `way/1103296758`：`man_made=embankment,highway=service`，649.691 game，约120.2860–120.2926 / 30.2979–30.3021，距河边3.635 game。土堤/堤路标签不证明竖直混凝土墙。
- `way/1522614942`：`man_made=quay,name=城市阳台水上客运中心`，源version2，2026-08-10。全长133.481 game，但线在现水面内部、距河边最近50.862 game；应作为码头/水上设施独立对象，不能吸附成岸墙。
- `way/1522614944`：`man_made=quay,name=奥体中心码头`，55.145 game，距河边2.127 game。精确几何保存在结构提取文件，可作为后续独立码头候选。
- 发现9条`natural=cliff`线及多个cliff点，但钱塘江边界180 game范围内没有cliff线；不能用山地悬崖标签给这些城市岸段赋岩壁结构。
- 全城道路/铁路的`embankment=yes/right`只说明其所在高起土工关系，不自动成为滨水防洪墙。

## 提取完整性与可复现文件

processed扫描见 [processed-availability.json](processed-availability.json)：道路里只有56项相关属性，另外少量dam/weir、城墙/区域记录，**未包含独立挡墙线157906999**。因此本轮确实重新读取固定PBF，而非在processed缺失时假定无墙。

PBF本轮提取：全城282条结构相关way、钱塘江边180 game内30条结构way、临江180 game内642条步道/骑行线、13个当前河界成员way，以及9个相关结构点。每条保留原tags/version/timestamp/nodeIds，几何同时保存WGS84与game X/Z。

进一步对全省20个相关结构relation的48个way成员逐一补取几何：48/48齐全，**没有一个成员几何与本城市范围相交**。因此没有遗漏一个恰位于候选岸段但仅标在relation上的挡墙证据；这不是声称固定OSM完整记录了现实全部岸墙。

- `structures.geojson`：结构way，含全部原始节点及与水界关系。
- `riverside-paths.geojson`：临江路径，原标签保留桥/层级/材料信息。
- `river-boundary-members.geojson`：relation/8227206边界成员线。
- `tagged-relation-geometry.json`：所有相关relation成员几何范围复核。
- `proposals.json`：优先有标签墙段及三个有限岸界窗口。
- `validation.json`、`package-manifest.json`：范围和哈希记录。

```sh
.venv/bin/python -B docs/hangzhou/research/coastal-adaptation-round1/export-contract/shore-source-proposal/extract.py
.venv/bin/python -B docs/hangzhou/research/coastal-adaptation-round1/export-contract/shore-source-proposal/relation_context.py
.venv/bin/python -B docs/hangzhou/research/coastal-adaptation-round1/export-contract/shore-source-proposal/propose.py
```

初次提取把岸界buffer放在循环内，主动中断后移到循环外，记录留在`extract.log`；优化后的完整运行在`extract-optimized.log`。无数据源变化。OSM几何保留ODbL署名；没有新增照片或发布贴图。最终GLB、墙体高程/碰撞、步行、昼夜画面及性能仍待主集成验收。
