# 阿里 A9、完整连桥及菜鸟园区范围核查 round3

本轮固定源几何与来源调查已完成一次核查，**尚不能冻结 A9 真实外观候选**。`scripts/landmarks/alibaba_a_extensions.py` 未创建，没有新 GLB 或基础排除 ID；原 A round2 模块/规格不改。证据 CLI 实际退出 2，任务保持 `planned`，保留身份、逐层形体/高度/入口和完整连桥三个核心 blocker，见 `evidence-gate-result.json`。

## 固定源与测量

Geofabrik 浙江 `zhejiang-261011.osm.pbf`，复制时间 `2026-10-11T20:21:06Z`，SHA256 `4eb65f64925498408faeee7eb04b60d7eb8a01c49ddb239f73070d4d282c75a9`。本轮重新校验 buildings / places / roads / pois / water / green 六份提取哈希，完整源对象在 `fixed-source-objects.json`。所有坐标来自 EPSG:4326，不使用商业地图坐标。

面积、长轴和包围尺寸采用固定 WGS84 足印→ECEF→局部 ENU 计算；`measured` 只表示 mapped geometry 的计算，绝对足印误差 unknown，不能称测绘值。复核原 A round2 13 个研究对象的全部原始几何完全一致。没有平移、缓冲、补洞或排除整个园区。

| 对象 | 可确认 | 尚缺什么 |
|---|---|---|
| OSM A9 `way/456731145` | 中心 `[120.02106495,30.2815386]`；32个非重复边界顶点；面积4369.98m²；最小包围135.03×44.48m；长轴75.18°（从北顺时针、模180） | 现代业主楼号/功能与9号馆的绑定；真实高度、层数口径、各屋面高低、入口、第二个有效方向 |
| 西侧 link `way/642355050`（图L1） | mapped架空来源，已由round2覆盖 | 现代功能/净高/完整路网配准 |
| 北侧 link `relation/6752593`（图L2） | mapped多孔来源，已由round2覆盖 | 同上，不能拿多边形周长当中心线总长 |
| 北侧 link `relation/6752573`（图L3） | mapped多孔来源，已由round2覆盖 | 同上 |
| 东侧 link `relation/6750408`（图L4） | mapped多孔来源，已由round2覆盖 | 同上 |

source覆盖图 `source-coverage-alibaba-a.png` 已实际查看；蓝色是原round2替换范围，橙色是阻塞 A9，灰色对象均保留基础来源。它是 CPU 原始资料图，不是模型预览或实机截图。

## A9 的真实身份不能只靠同一个数字

[OSM历史](https://api.openstreetmap.org/api/0.6/way/456731145/history)已实际保存：v1于2016-11-30仅有building/3levels，v2次日添加Building9，v3于2024-05-10改成A9楼/Building9。三个版本的节点列表相同，且与先前辅助 Overpass 最终节点精确匹配。这证明标签和 mapped 足印的沿革，不证明开发商楼号、建筑师或真实楼高。3levels保持为 OSM reported tag，不换算成实测楼高。

[阿里云官方2024参访行程](https://resource.alibabacloud.com/event/detail?id=6370)确认No.9 Hall存在，另列A5门、A区访客中心205等地点。[CAREC官方2023会议手册](https://www.carecprogram.org/uploads/CIN-Conference-Handbook-Print.pdf)PDF29页/印刷27页说明9号馆接待/展示用途，报告2016年建成及2022年内容更新；原PDF与本地渲染页实际查看。两者都没有绑定 `way/456731145`。

[设备供应商项目案例](https://www.sentimenthifi.com/c_s.asp?cid=71)描述临水舰船轮廓，并发布一张有效外观照。实际图像可见低矮曲线灰屋顶、玻璃面、三片白色斜构件，后方办公楼标号4；与 mapped A9在A4南侧有空间相容性，属于候选对应线索，**不是已证明的配准**。同页第二张图片是橙色临时Alibaba装置及常规办公立面，未证明属于A9，不计作第二个有效A9方向。

[中欧2014参访记录](https://cn.ceibs.edu/agri-food-business-association20141122)当时列六座办公楼、两停车库及在建9号馆/计划2014启用；这是历史计划信息，不与2023手册的2016建成合并为单一竣工年，也不把六座自动映射到当前A1–A9。[W3C2018会议记录](https://www.w3.org/wiki/AB/2018-03-Hangzhou)将访客中心描述为Building5；与2024行程的A5 **门**分开，不能把门号、楼号、访客中心、9号馆互相替换。

设计方现有2013平面图中功能图例1..9不是当前楼号；该图未给 A9 后建曲线楼的现状外观。[ARTUNIT原供应商地址](https://www.artunit.cn/pages/albb.html)抓取遇到证书主机名不匹配，保留失败，不关闭TLS验证或把转载图片当已读官方现状。

## 完整连桥仍未完成核验

[隈研吾项目页](https://kkaa.co.jp/project/alibaba-group-taobao-city/)报告历史链接空间总长超过1km。固定 A 地块中符合匿名架空楼体标签的四个源对象全部已在 round2；本轮没有发现可直接新增的带标签楼体 link。源内另有38条bridge/layer/tunnel混合道路记录，其中包含地面临水桥、建筑下穿道路和负层路径，它们不是38条空中links，也不由平面交叉证明可以接入办公桥网。

必须补足：真实 links中心线与逐段标高、各节点/楼体之间的接续、功能图例对应、2013后改建部分、支柱/楼梯/门禁位置。现有四个多边形的周长、包围框或地图道路长度不能与 reported >1km直接比较。没有据此创造桥体、室内功能或可通行支线。

## 菜鸟主楼外的真实范围

详见 `cainiao-campus-scope.md`、`cainiao-source-audit.json`。本轮确认三个独立 mapped 地块：总部 `way/1228913717`、北产业一期 `way/1293416973`、东产业二期 `way/1293548829`。固定源在总部地块内只有主楼 `way/1355173307`，北、东产业地块均没有已抽取建筑足印；不是物理建筑为零。[Aedas实景全景](https://www.aedas.com/en/project/hangzhou-yuhang-headquarters-industry-park-project/)实际可见报告厅/访客体量与周围产业楼群，原照片两方向已看，来源哈希复用round2。`source-coverage-cainiao.png`为空白地块明确展示数据覆盖缺口。

## 验证、权限与下一步

运行 `audit_fixed_source.py`、`render_source_audit.py`，并运行实际 `landmark_tasks.py check --stage evidence-ready --record`。来源、原13对象、历史节点、四links覆盖检查成立；任务核心身份/高度/形体仍失败，未推入 `evidence-ready`。八项最终验收保持unknown。无 Blender、浏览器、共享场景/渲染/资产/配置写入。

来源快照仅用于研究；照片/图纸没有验证游戏贴图或公开再分发许可，发布包应排除 `references/`。下一步用业主/设计方现状总平或带楼号的多向照片解决A9绑定与屋顶/入口；为菜鸟访客、报告厅和伙伴楼群获得有坐标基准的足印。得到核心证据后再冻结独立对象scope、进入纯B候选。原 .60 单次尺度与游戏地坪 lm.y约定继续沿用，不从历史作者目录或深圳参数生成对象。
