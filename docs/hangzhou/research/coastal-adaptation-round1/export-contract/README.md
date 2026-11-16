# 两份杭州水岸 GLB 的最小忠实导出契约

2026-11-11。仅审计与契约，不构建GLB，不修改共享源码。输入是已复核的 `coastal-data-v1`：2132个跨水片段、26个灯位和实际岸距图。`export-contract.json`为机读边界；当前运行时名称筛选用真实 `createBayparkLook` 在Node NullEngine执行过，结果见 `name-probe-result.json`。NullEngine没有验证GPU着色。

## 两份资产各自负责什么

|资产|应包含|不得重复包含|
|---|---|---|
|`coastal-bridges.glb`|非具名桥所有者范围内的栏杆/防护柱/有明确选择依据的支撑；按sourceRoadId与pointStations/pointHeights布置|道路顶面、道路标线、街灯、已存在的通用桥壳侧面/底面、具名三桥已有栏杆/桥墩/钢结构、水面|
|`coastal-shoreline.glb`|真实水岸边界对应的地形接边、已选定的城市硬岸压顶/挡墙/护岸石，及有实际步道范围依据的岸上铺装|独立湖/江水片、南侧海面、对岸山体、整城新地面平板、道路或地标已有台阶/平台/护栏|

`park-floodlight.glb`是另外的可复用原型，继续由26个`parkLights`实例化。两份水岸资产不再烘焙26根灯或重建69,723根街灯。原型尺寸保持游戏单位，不能重新乘0.60。

原 `build_coastal_infrastructure.py` 同时覆盖roads、桥、岸墙、灯杆和对岸。它硬编码桥高2.8、径向坡70、墩底-2.5、南岸包围框和统一岸墙标高；**不能直接跑它来生成杭州两份资产**。可保留其B网格API、材质与GLB方向导出流程，另写仅两份输出的隔离候选脚本。

## 2132桥片段：保持源剖面与唯一所有权

当前片段有2521段折线，总湿区链长45448.396671 game；点高范围1.500416–46.055831 game。不能用每片段的`height`标量压平：该字段仅中点兼容值，每个顶点必须取对应`pointHeightsGame`。在一段内插入栏杆柱时，按**该段源station**线性插值，保留sourceRoadId；这些渲染采样点不是导航节点。

当前 `prepare_hangzhou_render_meshes.py` 已为tier>0道路生成asphalt顶面（源y+0.10）、concrete侧面（y-0.45至y+0.08）和底面（y-0.45）。因此补充GLB默认只做道路边缘以上的栏杆。若保留短混凝土路缘，只能在现有壳顶以上，例为源y+0.10至+0.32；不要再画旧脚本从y-0.45开始的整片侧墙。钢栏杆/立柱可保持上游游戏尺寸约y+0.10至+1.00、半径0.045/0.065，但这些是estimated造型参数，不是杭州真实栏杆测量。

按width/2+0.2偏移源线两侧，连续折点使用有限斜接/圆角，不在每段端点重复立柱。使用全片段累积station统一排柱，避免短OSM段堆积柱子。原脚本逐段每6 game约需两侧合计17,696根柱，尚未去重；应在CPU阶段统计真实去重后的三角形/节点/材质预算，不能只以2132记录数猜性能。

**具名桥存在第二层所有权问题**：三桥模块已经画桥壳和栏杆；基础道路目前又无条件画generic deck shells。新增coastal不能再叠第三层。源道路→具名桥映射见JSON（15源way；其中14个当前湿区片段落入关联集合）。这15条包含延伸引桥，不能把整个source way都冒称为主桥模型覆盖。最低安全候选：保持全部2132身份记录；对具名三桥主结构范围不生成通用栏杆/墩，按已交付模型的实际world范围、层级和source station建立占有区；范围外的源引桥另补。尚未完成这个分段表时，明确列该范围pending，不能假称已有护栏覆盖整个way。

三桥模型主范围分别约1072m、1376m、478m，模型尺寸/位置本身仍有估计误差。不能用这些长度删除基础道路顶面；公路可驶面仍由道路资产单独提供。还需主集成对已有generic shell与三桥自有shell执行一次组件级排重，不能靠深度偏移把重复壳藏住。

通用支撑不可固定从-2.5长到2.65：先查source profile、所跨实际水体、桥下其他道路/铁路及已有实体。没有河床/基础标高时，允许显式estimated可见墩段延至水面以下的有限遮挡范围，但不要称测得河床或通航净空；有桥下道路、隧道或具名结构的支撑先单独判定。不能用每35 game在任意段中间落一根柱的全城规则制造新的车道障碍。

## 岸线：闭合地形接边，不能把杭州河岸全变成海堤

以v3真实水体湿区并集外边界/岛孔生成**物理湿干边**，剔除裁切box边、源水面内部共享边、荷区/闸室语义分区内边。每段保留源水体ID及局部水位，不能整城用0.9；24组尚未决的水体交叠和无法确定唯一水位的岸段仍列pending。

最小地形接边是岸线同一XY处的窄竖向裙边：上边与当前`Surface.ground`/实际地形边界一致，下边抵局部水位以下少量遮挡深度。它补足现有地形裁水后的立面，不重新铺大地板，不新增可走平台。柔性自然岸使用土地/草土材质，不能无证全变concrete/seawall。若地面实际估计低于水面，直接报告淹没/高程矛盾，不通过抬岸或夹取min/max掩盖。

城市阳台附近可以冻结有限的estimated城市硬岸样段，以真实河岸和公共步道/平台边界为范围，分别生成`concrete`压顶、`seawall`竖面；护岸石只用于选定有依据的护岸区。铺装必须来自真实可达步道/平台足印，并扣除现有road pavement及地标平台范围；不能对整条钱塘江或西湖统一buffer成4m新步道。闸门、断桥/白堤/苏堤等现有对象交接处逐对象排重。

杭州v6仅恢复green精度，water/roads与v5实际比较一致，所以桥剖面和岸距不因v6自动失效；**公园/步道边界裁切和新岸边植被仍须使用v6并重新绑定**。不能把v1的v5 city哈希静默改成v6。

## 当前实际名称契约

|GLB内mesh名称|材质建议|当前实际效果|
|---|---|---|
|`coastal_bridge_<ix>_<iz>_concrete` / `_steel`|`concrete` / `steel`，PBR，单材质mesh|被public-lighting的`coastal_bridge_`前缀接收；加载后进入landmarks反射/阴影流程|
|`coastal_shore_<ix>_<iz>_concrete`|`concrete`，PBR|tiledReceivers=true下接入Baypark kind2：混凝土/压顶|
|`coastal_shore_<ix>_<iz>_seawall`|`seawall`，PBR|接入kind3：墙面湿痕与稀疏接缝|
|`coastal_shore_<ix>_<iz>_coastal-rock`|`coastal-rock`，PBR|接入kind4：岩石粗糙度/湿痕|
|`terrain_pavement`|`pavement`，PBR及原paving纹理/标定|当前唯一可直接接入kind1铺装的名称；只能生成一个不与既有对象同名的聚合样段，避免Blender自动`.001`|
|`coastal_shore_<ix>_<iz>_pavement`|`pavement`|**当前不接入kind1**，不能假称已有完整铺装着色|
|`terrain_<ix>_<iz>_pavement`|`pavement`|当前也不被Baypark识别|
|上述岸墙名末尾`.001`|任何|当前精确匹配失败；必须在导出前处理重名，不修改记录掩盖|

`B.finish(prefix)`会在prefix后追加`_materialToken`，因此一次传`coastal_shore_5_-4`，其concrete对象自动得到正确名称；不要再手工追加双重材料名。当前Baypark对整数ix/iz有正负号支持，不能用十进制坐标作tile后缀。

**另一个实在的能力缺口**：public-lighting当前mesh过滤不含`coastal_shore_`。跨GLB同名的concrete材料不是同一实例，不能假定roads里的插件会自动传给岸墙。推荐主集成做两个很窄的接收名补充：Baypark把去掉tile前缀后的`coastal_shore_pavement`映射kind1；public-lighting允许`coastal_shore_`。这保留现有硬绑定与每submesh门控，不修改灯光预算或每帧材质配置。若暂不补，报告对应能力pending，而不是用错名称伪装道路。

Baypark当前已经有可传`waterHeight`并在worldY中减去它，主城调用杭州0.9参考；这仅是城市阳台600 game局部样段，不能拿来统一全城岸墙湿线。selector的CPU探针使用当前生成配置中心；当前ACTIVE_CITY_ID仍是shenzhen，因此探针只证明名称匹配，**没有宣称杭州配置已激活或实际场景通过**。

## 运行时接入、方向及碰撞

- `city-world.load()`固定请求这两份文件，清空的是glTF合成根节点旋转，保留既有 Blender 东/北/上 → glTF Y-up → Babylon 根处理。输入全是game units；不再乘0.60、不再加全局负Z翻转。
- 分640 game块并保留节点局部原点，先在float64中减局部原点，再转顶点float32；UV用原world X/Z保持连续。薄栏杆、短裁切段必须在实际GLB解码后检查退化/漂移，不能仅检查Python双精度mesh。
- 导出材质为共享PBR，少数稳定材料槽；不加额外水材质、动画、灯光节点或镜面RTT。桥/岸全部非空几何、真实统计三角形、hash与边界。禁止用空GLB只让loader通过。
- 两份资产load后统一`isPickable=false`并进入`landmarks`。**GLB本身不会新增玩家碰撞**；需另产具名、带minY/maxY的护栏/挡墙碰撞，主集成在`new CityCollision(data)`之前通过既有detail/candidate合并入口接入。不要用无高度整桥box堵死下层车道，也不要把可走铺装当墙。
- landmarks默认全部进入反射候选，阴影依mesh中心距离筛选；每个GLB只有一个全城巨型mesh会导致局部阴影错误和巨大可见包围盒。按tile/material拆分保持现有视锥/阴影策略，不靠大量新实时灯或新反射目标补效果。

## 接下来可执行的顺序

1. 冻结输入哈希、15条具名桥关联与确切主结构占有范围；列出未决岸段/支撑，保留2132条清单身份。
2. CPU准备仅补充栏杆/柱与岸边带的float64网格、材质、owner/源station映射和分层碰撞sidecar，先检查与道路/地标/灯/植被的交叠。
3. 主集成完成上述两个接收名小补充，然后独占Blender在新候选目录导出两GLB；不调用旧脚本的roads/park-floodlight/opposite-shore分支。
4. 校验真实GLB名称、材质、方向、world bounds、非退化、无道路顶面/水片；用实际profile抽查栏杆高程与owner排重。浏览器验证城市阳台铺装/墙/石kind、昼夜公共光场、局部光源与水反射，最后检查桥边/桥下通行和预算。

当前结论是导出接口已可具体实施；没有宣布这两份GLB、现有桥面剖面或岸线模型已完成。
