# 白堤、苏堤有限堤岸与七桥候选

当前实际阶段为 `evidence-ready`。固定源数据、官方证据、纯 B 模块、CPU 几何检查和四张 CPU 预览已完成。没有在本任务启动 Blender 或浏览器，没有 GLB 或实机验收；七桥、水位接合、准确植被、夜景和实际步行/碰撞均须继续验证。

## 范围和对象身份

模块 `scripts/landmarks/west_lake_causeways.py` 包含白堤四段普通道路、锦带桥，以及苏堤八段普通道路与六座独立桥，共 19 个路径对象、七桥、七个固定绿地条带。断桥 `way/28538289` 只进入源节点连通性记录，几何由现有 `broken_bridge.py` 负责。本对象不创建水面，不排除基础楼体，不复制孤山、杨公堤、玉带桥、湖中三岛或周围景区。

固定浙江 Geofabrik PBF：`zhejiang-261011.osm.pbf`，replication `2026-10-11T20:21:06Z`，SHA256 `4eb65f64925498408faeee7eb04b60d7eb8a01c49ddb239f73070d4d282c75a9`。经纬度为 EPSG:4326；来源及派生数据依 ODbL 1.0，署名 OpenStreetMap contributors / Geofabrik。地理换算使用 `config/cities/hangzhou.json` 的杭州原点和 WGS84 系数，不使用商业地图坐标。

`source-geometry.geojson` 逐对象保留原始 ID、节点、标签和经纬度，`source-water-boundary.geojson` 仅作为基础湖水边界核对材料。`shoreline-correspondence.json` 记录五组绿地足印与西湖 `relation/2308774` 内环的精确坐标集合对应：苏堤 `30072122/30072129/30072136/30072142` 分别对应 holes 17/18/19/23，白堤 `28538305` 对应 hole 28。另纳入白堤西段窄条 `relation/20083745`、苏堤南段 `way/975357027`；不将整座孤山或西湖自然保护区用作碰撞足印。

固定白堤源链包括桥与孤山端延伸，总长约 **1147.466m**；苏堤约 **2699.914m**，都在未缩放米制投影上按原节点折线测得，属于 measured-on-OSM。UNESCO 的名义长度白堤987m、苏堤2797m为另一时相/端点口径的 reported 数字；本候选保留固定源坐标，没有缩放长度以匹配历史数字。两组路线均逐端点检验节点 ID 和坐标相同，无几何交叉伪路口。

端点外部道路已只读核对：白堤孤山端节点 `26315529` 接 `way4398107` / 孤山路 `1423000709`，北端 `26202730` 接北山街 `565661262`；苏堤北端 `26391524` 接北山街 `504565894`，南端 `26391522` 接南山路 `589384551`。这些外部道路保留在共享基础管线，本模块不改导航或职业任务点。建模锚点 `[120.138,30.246]` 是组合对象的局部计算原点，不能作为湖上的交互目的地。

## 官方证据与估计边界

实际读取并渲染 [UNESCO 中国提名文件](https://whc.unesco.org/uploads/nominations/1334.pdf)，原文件79,121,258字节 / 1,342页，SHA256 `5a82da9397cc7eafae35ffff8060c45c0751f6da2d5c8b40ac38ce08ad32c442`。打印页64的两张2006航拍和尺寸说明、页75的六桥/植被说明、页83图2a-22的六份独立立面支持布局、半圆单孔与桃柳堤岸。白堤33m、苏堤30–40m指整片堤地宽度，不能套给所有桥面；苏堤高于当期湖水约0.4m为历史相对水位记录，不是海拔或本轮游戏水位。

[杭州发布2022六桥说明](https://m.thepaper.cn/newsDetail_forward_19443734)是政府新闻办公室官方账号发布，资料由西湖景区管委会提供。来源照片包括长堤航拍、近处石栏、湖面侧立面；逐桥 reported 尺寸如下。测量日期和2026现状复测均未知。

| 苏堤北→南顺序 | 原始 road way | 拱体长m | 净宽m | 单孔净跨m |
|---|---:|---:|---:|---:|
| 跨虹桥 | 30072125 | 21.1 | 4.3 | 8.1 |
| 东浦桥 | 30075392 | 16.8 | 4.3 | 5.9 |
| 压堤桥 | 30072130 | 16.9 | 4.0 | 6.3 |
| 望山桥 | 30072139 | 16.9 | 7.0 | 4.7 |
| 锁澜桥 | 30072144 | 16.9 | 6.4 | 6.2 |
| 映波桥 | 30072147 | 17.0 | 7.0 | 7.4 |

UNESCO 六桥“6–8m”的概述与2022逐桥望山4.7m、东浦5.9m存在口径差异，本候选采用逐桥值并在证据中保留差异。桥的 OSM road way 长度约23.7–38.8m，包含源定义的引坡；`coreBodyLengthM` 历史拱体长与其分开保存，净跨不会被拉伸成整条路线。

锦带桥同时由 `way/28538285` 道路和 `way/1466925248` 独立桥面面积确认。[原摄影者 Nathan Holth 的2017锦带桥文档](https://historicbridges.org/bridges/browser/photos.php?bridgebrowser=china/jindaibridge/&gallerynum=2&gallerysize=2)将西侧桥的长缓坡、小单拱、条石墙体和低石栏明确标注；没有将该文档“桥长/宽不可用”改为 reported 尺寸。候选净宽8.6±1.5m、净跨6.5±2m、核心拱体长10±3m、拱位约源线50%±12m，均为 OSM 桥面宽度和成人/栏板比例辅助的 estimated 参数。断桥官方尺寸没有被挪成锦带桥实测。

七桥拱孔均按净跨半圆构造，拥有独立桥台、条石水平缝、分段拱券、连续沥青坡面和石栏。苏堤使用开口石栏及近中心实体牌板，锦带桥用低实心栏板。字牌、雕花纹样、桥灯与根数未经完整定位，没有伪造碑文/招牌。主要估计：苏堤拱脚相对端点-1.15m、拱券0.55m；锦带桥-1.5m/0.60m；铺装0.20m、石栏0.85–1.0m。拱顶约±0.9m（苏堤）/±1.2m（锦带桥），石栏±0.25m；准确拱脚、水位、地形和曲线仍 pending。

湖边绿地采用原足印，扫描线扣掉所有道路/桥体走廊的 **union**。交叉道路条带不会因 XOR 形成草地封盖；凹角不被三角扇填满。绿地表面、低护岸与石压顶是中性端点基准上的 estimated 候选，保留原始岸线，单独检查基础湖水孔洞与候选接合。

## 已执行检查

先执行任务包 `check --stage evidence-ready --record` 通过，再编写模块。实际执行命令如下；`python3` 使用本机 bundled Python 3.12，无 `bpy` / `city_mesh` 导入。

```sh
python3 -B docs/hangzhou/research/core/west-lake-causeways-round2/prepare_evidence.py
python3 -B scripts/landmark_tasks.py generate --city-id hangzhou --source docs/hangzhou/research/core/west-lake-causeways-round2/source-list.json --place west-lake-causeways --agent codex --output docs/hangzhou/research/core/west-lake-causeways-round2/task-bundles
python3 -B scripts/landmark_tasks.py check --job docs/hangzhou/research/core/west-lake-causeways-round2/task-bundles/west-lake-causeways/job.json --stage evidence-ready --record
python3 -B docs/hangzhou/research/core/west-lake-causeways-round2/check_candidate.py
python3 -B docs/hangzhou/research/core/west-lake-causeways-round2/render_cpu_preview.py
```

17项 CPU 检查通过：独立导入、有限范围、断桥外部所有权、逐路径原始节点/坐标、逐绿地足印、两条连续源链、桥两端同高、七个未封盖拱孔、源坐标高度查询、草地扣除、重叠扣除 union、`lm.y` 不重缩放、源锚点偏移一次0.60、游戏 frame 平移、成功/异常 frame 恢复、预算、有限坐标。结果36,926三角形（导出前计数）/5既有材质/0新灯/0新纹理/0水网格。实际GLB字节、GPU材质、夜景、FPS与内存均未知。

`cpu-preview-manifest.json` 绑定模块/spec与四张 CPU 俯视、远景和两处侧面图。图像没有加载基础水、树木或共享场景，不能代替实机俯视/街面/远景；画家排序可能造成遮挡近似。`validation.json` 八项最终验收全部保持 unknown。

## 串行集成与未通过项

完整接入步骤见 `integration-notes.md`，重要的是同时接道路视觉抑制、可步行高度与湖水边界，不能只放 GLB 后宣布可步行。`build(b,lm,spec,scale=.6)`、`walk_surfaces(...)` 和 `bridge_height_at(...)` 都采用相同源坐标/桥面曲线。`lm.x/z/y` 为已有游戏单位，实际尺寸仅缩放一次，frame最终恢复；不增加 Blender→GLB→Babylon 根旋转。

OSM 堤路限制 motorcar/motor_vehicle，保留标签与拓扑。车辆任务应选合法且连通的临近道路到达，再步行转移；苏堤北山街和南山路可作待验证起点，本模块没有指定湖中模型锚点为任务点。景区旅游电动车是独立交通语义，是否纳入既有电动车系统由主任务统一决定，不因本候选而删除或绕过玩法规则。

待验收仍包括当前道路/湖水高程、各拱位/引坡现状、白堤岸线与道路偏差、准确桃柳种植数量/位置与避让、碑亭/家具/入口/灯具、昼夜材质、视觉叠面/资源预算、桥面与岸边行人碰撞、真实可到达目的地、全部实机截图和性能。本候选不等于白堤苏堤全部交付，更不等于全城完成。

代码沿用项目 MIT。来源图仅归档于独立研究目录，`runtimePhotoTextures=false`；政府图、提名页和 Nathan Holth 照片的发布贴图/再分发许可未获核验，发布包须排除 `references` 图像/网页。OSM 派生几何按 ODbL 署名，具体模型资产许可由主集成清单继续记录。
