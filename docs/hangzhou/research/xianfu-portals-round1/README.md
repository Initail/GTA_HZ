# 闲富路下穿通道：固定源证据与洞口 blocker

调查日期：2026-11-11。对象仅为 `way/697096305`、西南端 `node/6547053710`、东北端 `node/6547053711` 及相邻闲富路。当前阶段为 **source-topology-confirmed / portal-dimensions-and-appearance-blocked**；没有模型、正式集成、实机或外观验收。本目录只新增研究结果，保留此前 P1 报告。

## 可交给主集成的结论

固定 OSM 数据把该对象记录为住宅支路机动车下穿通道：`highway=residential / tunnel=yes / layer=-1`。西引道 `way/1418959639` 与西南口共享 node6547053710；东引道 `way/697096306` 与东北口共享 node6547053711。**低道路连续，闲富路与低路在两个平面交叉点均不共享源节点，不是可转弯路口。** 依据是完整固定 PBF 中实际抽取的 node/way/relation，不是当前地图显示推测。参见 [固定源抽取](fixed-osm-context.json)、[复算结果](measurements.json) 和 [中心线示意图](source-plan.svg)。源对象在线身份页为 [way697096305](https://www.openstreetmap.org/way/697096305)，在线页可能随编辑更新，以本地固定版本为准。

有一项新增用途证据：2482 路往返两个 OSM 公交关系 `19412493`（v3）与 `19412494`（v2）均包含连续的 `[1418959639,697096305,697096306]` 三个 way 成员。两关系源更新时间均为 2025-12-07 06:28:50 UTC；分别以沈家坞和闲林公交总站为 from/to。这支持 **源地图将它作为机动车/公交可通过道路使用**，不能把它改成步行洞口。但 OSM 关系不是运营方公告，本轮未核实 2026-11-11 实际班次、车型、临时停运及现场通行限制；两关系局部成员顺序相同，不能把关系列表直接当成已经验证的行车方向。参见 [关系19412493](https://www.openstreetmap.org/relation/19412493)、[关系19412494](https://www.openstreetmap.org/relation/19412494)。

**用途证据没有解除尺寸与层间绝对高度 blocker。** `layer=-1` 表示上下关系，不是 -1 米，更不等于净空 6 米；OSM 官方标注说明也明确区分层级与标高。[OSM layer 语义](https://wiki.openstreetmap.org/wiki/Key:layer)。此前 DSM/道路平滑得到的 gameY 必须继续标为 estimated game adaptation，不能通过把低隧道抬向闲富路来反向“确认”真实高度。

## 固定数据与复算

| 项目 | 值 / 边界 |
|---|---|
| PBF | `data/raw/hangzhou/zhejiang-261011.osm.pbf`，90,463,400 bytes |
| 原始来源 | [Geofabrik 固定快照](https://download.geofabrik.de/asia/china/zhejiang-261011.osm.pbf) |
| replication timestamp | 2026-10-11T20:21:06Z；研究时未更新 PBF |
| SHA-256 | `4eb65f64925498408faeee7eb04b60d7eb8a01c49ddb239f73070d4d282c75a9`，本轮抽取前已实际重新计算并与原 manifest 核对 |
| CRS / 授权 | EPSG:4326 WGS84；© OpenStreetMap contributors / [ODbL-1.0](https://www.openstreetmap.org/copyright) |
| 抽取范围 | WGS84 `[119.978,30.198,119.991,30.209]`；80 个相交带标签 way、25 个范围内带标签/目标 node、4 个直接包含目标道路的 relation |
| 转换 | 读取 `config/cities/hangzhou.json`，东 96220.11856153939 m/°、北 110857.07311230902 m/°、原点 `[120.155,30.274]`；game 统一乘 0.60 一次 |
| 元数据限制 | 原 PBF 中抽得的 changeset 为 0；不当作真实 changeset ID，也不据此推断作者身份。版本/时间字段保留原值 |

`measure_context.py` 使用已有项目 `.venv` 中 pyproj 3.7.2、Shapely 2.1.2。所有参数从本地源/城市配置读取，没有商业地图坐标或新 OSM 数据注入。

```sh
.venv/bin/python docs/hangzhou/research/xianfu-portals-round1/extract_context.py
.venv/bin/python docs/hangzhou/research/xianfu-portals-round1/measure_context.py
.venv/bin/python docs/hangzhou/research/xianfu-portals-round1/freeze_report.py
```

第一步遍历固定浙江 PBF，仅重写此目录的抽取文件；后两步生成测量/示意与哈希。图中线宽仅用于可读性，**不是道路真实宽度或洞口外轮廓**。

## measured / reported / estimated / unknown

“measured” 以下只指从固定源坐标计算的几何，不是现场测绘。OSM 节点位置误差未知，坐标小数位和计算精度不代表实测精度。

| 参数 | 分类 | 结果 / 使用范围 |
|---|---|---|
| 西南口 node6547053710 | reported（OSM） | WGS84 `[119.9840438,30.2035938]`；gameXZ `[-9869.655499698503,-4683.015156575961]`；仅与低隧道/西引道共享节点 |
| 东北口 node6547053711 | reported（OSM） | WGS84 `[119.9843344,30.2037816]`；gameXZ `[-9852.878559826138,-4670.523781577727]`；仅与低隧道/东引道共享节点 |
| 两口中心线长度 | measured（源几何） | WGS84 椭球测地线 34.87668 m；城市投影 34.86084 m，即 20.91650 game；两节点之间没有源中间曲线点 |
| 西南→东北方向 | measured（源几何） | 起始方位角 53.35000°（从北顺时针） |
| 上方道路身份 | reported（OSM） | 两幅单向 `trunk` 闲富路 `G235;G320`：way358503184 / way697096309；两者无显式 layer/bridge 标签 |
| 两中心线交叉位置 | measured（源几何） | 自西南口沿低路 9.27370 m / 25.85614 m，详细 WGS84 见 JSON；均无共享源节点 |
| 洞口中心至最近上路中心线 | measured（源几何） | 西南 7.23077 m / 东北 7.23027 m；不是到挡墙/车道边距离 |
| mapped 机动车用途 | reported（OSM） | residential + 两个 bus 关系；本轮没有运营方/现场二次确认 |
| 原候选低口 gameY | estimated（既有游戏地形） | 西南 30.312741858342783 / 东北 28.974011552373543；来自旧 DSM 推导与道路平滑，非真实标高 |
| 原候选路宽 6 game | estimated（既有游戏默认） | 相当于 10 m；PBF 没有该宽度依据，不能写入 measured 宽度 |
| 真实道路宽、洞口净宽/净高、车道数 | unknown | 低隧道没有 width/maxwidth/height/maxheight/lanes 标签；不能据“公交”反推具体数值 |
| 墙线、墙高、护栏、边坡、顶板厚度、洞口形状、材料/灯光 | unknown | 无能绑定此对节点的工程图或多向照片；源标签也无 embankment/cutting/surface/lit |
| 现场绝对高程、纵坡/横坡、上/下净空 | unknown | 没有 ele/incline；DSM 不可区分两层；不能利用高路混合地面反推低路 |
| 现时运营/车辆限制 | unknown | 未取得可绑定通道的官方运营/限高公告 |

## 防止认错对象

下穿小通道 **不是万丈山主隧道**。固定源中 `way/371748017` 和 `way/697096310` 才有 `name=万丈山隧道`，它们连接闲富路双幅主路，最近的映射北端点在本通道中点以南约 288.66 m / 285.78 m。它们与小通道无共享节点。网上闲富公路/万丈山隧道资料中的单洞净宽、净高与公里级隧道长度不能移植到约 34.9 m 的住宅支路下穿。附近还有其他不同隧道对象，本轮不拿同片区“隧道”关键词作为身份匹配。

## 对 P1 修复的有限建模依据

沿用 [P1-minimum-repair](../../audit/review-20261016/landmark-evidence/source-selection-v2/P1-minimum-repair.md) 的源身份和双表面分支判断。此轮证据足以支持：保留低路两端共享节点；保留低路与闲富路两个独立纵向道路表面；禁止根据 xz 相交新增转弯边；以统一配置投影和 scale 转换中心线；若生成验证候选，低进路、隧道口和高路必须按 sourceRoadId/source 区间分别绑定采样、碰撞和渲染。

它 **不足以支持**：把默认 10 m 路宽认作真实；为消除重叠擅自缩窄路面；给源引道添加假 layer/bridge/tunnel；给原道路再加一次名义净空；画一对混凝土挡墙就称真实入口完成；把 DSM 候选标高当测量。即便先做 game-adaptation 洞口候选，也应显式记录尺寸估计及误差未知，不能把它作为最终具名外观交付。

仍保持 `source-surface-overlap` blocker。解除所需证据至少为同一节点两端的可定位照片/工程平面（有明确道路或构筑物对应）、洞口/引道/闲富路边界与可量化尺度、上下层纵断面或可靠标高依据。随后还要执行 P1 已列的全断面、源节点/方向/图连接不变、Python/TS/mesh 同点误差、实机真实驾驶与视觉复核；本目录没有代替这些验收。

## 本轮公开资料检索边界

检索了“严潮坞/源峰街里东路口 + 2482/杭州公交/闲富/涵洞”及政府、杭州公交域名；没有找到可绑定两个目标节点的官方运营公告、洞口尺寸或多角度照片。此结论只说明本轮未取到，不说明公开资料不存在。站点聚合页中同名公交站和 2482 信息作为检索线索保留在 [sources.json](sources.json)，不作为运营现状和尺寸证据。

网上转载《浙发改函〔2009〕387号》是主公路工程总体标准；本轮未找到原发政府页面，也没有明确绑定这个小下穿的桩号或图纸，因此不纳入尺寸依据。没有下载、制作或发布公开照片贴图。照片证据计数 **0**，现场/实机截图 **0**。

## 校验范围

`freeze_report.py` 验证本包文件可解析、源 SHA 与固定快照声明一致、抽取器哈希、目标节点与 way 坐标一致、两口真实连接集合、两处交叉无共享节点、两个公交关系包含连续三段。`validation.json` 记录实际检查与全部文件 SHA。这是研究包的一致性校验；没有宣称物理几何、驾驶、性能或外观通过。
