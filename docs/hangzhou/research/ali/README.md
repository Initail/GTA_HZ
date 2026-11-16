# 菜鸟总部与阿里西溪 A/B/C 区证据包

调查日期：2026-10-12。范围为公开建筑与地块资料，不含内部办公系统、人员信息或私有参考图。本目录只提供研究和 WGS84 足印；没有修改城市配置、模型、资源总清单或运行时，也没有完成地标实机验收。

结论：四个对象可以分别建立。阿里西溪 A、B、C 是三个不同地块；C 区是日本设计的西溪五期全球总部，不能把 NBBJ 四期蜂巢形方案挪给 C 区。A 区当前地图范围包含早期园区及扩建配套，不能把“淘宝城一期”的楼数和面积覆盖整个 A 区。B 区实名已核实，具体楼号、建筑高度和各分块的功能仍有 blocker。

## 可核对产物

- `sources.json`：来源、用途、许可状态及快照哈希。
- `evidence.json`：四个独立对象的 measured / reported / estimated / unknown 观察、未通过项和建模建议。
- `site-footprints.json`：四处地块和阿里楼群的完整 EPSG:4326 环；保留孔洞与 relation 成员 ID。
- `measure_osm.py`：从已冻结的原始 OSM JSON 重算米制足印、最小旋转包围矩形和方向。
- `snapshots/`：官方文字页面、公开设计报告、OSM 原始结果和查询，以及只供审计的报告页渲染。照片没有作为发布贴图接入。

重算命令：`python3 docs/hangzhou/research/ali/measure_osm.py`。输出是未缩放的真实米制研究参数；主集成应经统一城市适配层缩放一次。这里的 bbox 中心只用于测量，不能直接作为出生点、任务到达点或导航落点。

## 身份与地块

| 对象 | 已核实名义 | OSM 地块 ID | 地块 WGS84 包围盒中心 [经度,纬度] | 图上面积 |
| --- | --- | --- | --- | --- |
| 菜鸟总部 | 菜鸟官方联系地址为余杭区凤新路 501 号；Aedas 设计的总部 | way 1228913717 | [119.9606604, 30.26480725] | 108,199.67 m² |
| 阿里 A 区 | 淘宝天猫等国内电商业务总部；地图名“阿里巴巴西溪A区” | way 645135612 | [120.021274, 30.2815813] | 393,608.29 m² |
| 阿里 B 区 | 阿里巴巴数字生态创新园；地图 alt_name 与此一致 | way 544285896 | [120.02267895, 30.27828295] | 130,767.29 m² |
| 阿里 C 区 | 阿里巴巴杭州全球总部、西溪五期 | way 645093961 | [120.0185145, 30.28575155] | 268,904.23 m² |

名义依据：[菜鸟](https://www.cainiao.com/en/about-us-contact-us.html?from=subHeaderClick)、[阿里业主说明](https://www.alibabagroup.com/zh-HK/document-1586194337035714560)、[开园报道](https://finance.people.com.cn/n1/2024/0510/c1004-40233098.html)、[日本设计五期说明](https://www.nihonsekkei.co.jp/think/ideas/case-study_17626/?lang=en)、[ASPECT 的 Park C 项目](https://www.aspect-studios.com/au/projects/alibaba-xixi-campus-park-c)。OSM ID 原始快照在本目录保存；面积是对志愿者绘制的 polygon 计算，不能称为实测地籍面积。

## 对象观察与建模边界

### 菜鸟总部

[Aedas 当前项目页](https://www.aedas.com/en/project/hangzhou-yuhang-headquarters-industry-park-project/)报告主办公楼五层，入口有分层鸟喙形雨棚，木纹涂层铝板和 low-E 幕墙。[中建交付记录](https://www.cscec.com/zgjz_new/xwzx_new/zqydt_new/202305/3671552.html)统计一期为一栋五层总部、一栋四层报告厅及地下一层。两者公布的总面积口径不同（164,286 与约296,000 m²），本轮保留差异，不由面积反推楼高。

OSM 主楼 way 1355173307 的外轮廓最小旋转包围矩形约 234.87 × 234.37 m；其 mapped 外形不是完整 courtyard/atrium 测绘。旧“杭城记·菜鸟园区”副本的 216 × 200 m 和 4.2 m 层高属于玩法估计，不能转作本轮 measured。主楼真实高度、报告厅对应足印、入口精确方位与四个内院的 WGS84 环尚未核实。优先保留环体、院落、中央连通空间和分层入口；禁止将外轮廓整块实心拉高当最终模型。

### 阿里 A 区

[隈研吾项目页](https://kkaa.co.jp/project/alibaba-group-taobao-city/)支持淘宝城的低层分散办公、六个办公单元和连桥体系；其标记 7F。[业主说明](https://www.alibabagroup.com/zh-HK/document-1586194337035714560)支持 A 区湿地与水体景观。当前地图有 A1–A9 命名楼体、两座多层停车楼和多组连桥/配套，但并不意味着九栋都是一期六个办公单元中的主楼。地图部分标记六层，与设计方 7F 统计口径也需核对。

A4–A8 等足印为有孔的 multipolygon；连桥另有 `building:min_level=2`，不能当落地墙体。主体常见边线约向东偏北 17°；`minimumRotatedEnvelope` 的长轴是包围矩形方向，有退台、双条板时可能与立面主轴不同。建模应保留一栋一个子对象、楼号映射、双条板/内院和高架 links，先建立“设计方六单元 → 现行楼号”的 crosswalk，再固定各楼高度和退台。

Blocker：A 区的现行楼号与一期/二期/三期范围及设计单元尚未逐一确认；逐楼高度、roof/入口的多方向现状证据不齐。393,608 m² 的当前 OSM 园区范围不能被一期约26万m²口径替代。

### 阿里 B 区

OSM 地块内本轮关联 23 个 mapped building/roof ways（1363020721–1363020743）；其中有办公分块、细长连接构件和单独屋盖，不能当 23 栋独立主楼。全部缺少高度和层数标签。地图几何保留多边形节点布局，可用于 footprint/朝向检查。[NBBJ 合伙人公开访谈](https://2021.archcy.com/interview/designer/36732c329dc31c9d)对西溪四期的蜂巢节点、露台和屋顶花园作说明，但“该四期全部等于当前 B 区且编号逐一对应”的 primary 地块证据仍不足。

Blocker：当前 B 区 named polygon 与具体 NBBJ 四期楼号/范围的 crosswalk、楼数统计、各楼高度、退台层高与真实入口未核实。继续研究时只冻结已知 footprint，不复制 C 区的六栋 cube/长南侧屋顶。relation 7777930 位于 B 区南侧邻地，已从本对象剔除。

### 阿里 C 区

[日本设计方案说明](https://www.nihonsekkei.co.jp/think/ideas/case-study_17626/?lang=en)给出六办公楼加访客中心、朝南开放的中庭、二层交流环和沿南侧主路的长屋顶。OSM 对应 C1–C6 的六个 relation 与访客中心 way 1363020716；南侧线形构件 way 1363020718 的旋转包围矩形约 486.40 × 16.09 m。C1–C6 外包尺度均约104 m长，宽约71–79 m，常见主边轴线约73°（自北顺时针）。主体中庭孔洞必须保留。

2026 日本设计公开报告的实体项目页 49–50（PDF 第28页）经图上核对明确标记 15F / B2F / Height 80m。这个数值作为 reported 的园区项目高度；不能假定六栋每栋均为80m。报告末尾 awards 页出现与上海项目相同的140m/520,000m²数据，与主体项目页冲突，不能据自动检索表格把 C 区变成140m。[景观设计方](https://www.aspect-studios.com/au/projects/alibaba-xixi-campus-park-c)明确园区景观建在多层 podium 上；地坪、桥、入口和水系需按该立体关系接入。

现状参考已检查报告页的街面庭院与空中全景，玻璃网格、平整盒形体、开放绿地和长屋顶可辨；这些参考方向未附测绘方位，不能冒充所有立面已验。Blocker：逐楼高度/退台、当前入口坡道与地坪标高、roof 的竣工尺寸（早期480m与后期约400m描述）、楼号标识和夜间照明仍待补证。

## 坐标、许可和未通过项

OSM 三次成功查询的数据库时间分别为 2026-10-12 09:20:35 / 09:27:36 / 09:28:41 UTC；下载时间对应本轮调查。坐标按 OSM WGS84 / EPSG:4326 接收，未使用百度、GCJ-02 或 BD-09 坐标。测量脚本使用 WGS84 椭球 ECEF 到局部 ENU 的转换；源 plan 位置精度未知，数值转换精度不等于测绘精度。原始 JSON 保留版本、修改时间、changeset 和哈希。

OSM 数据为 ODbL，交付需保留 OpenStreetMap contributors 署名并审查衍生数据库的许可要求。建筑方/业主照片版权未取得发布贴图许可，目录里的 HTML/PDF/页图为研究快照；没有把参考照片接入 public 或模型纹理。程序原创几何和材质可沿项目 MIT 管理，但不能由此覆盖来源照片权利。

四个对象当前均不是 verified：未建模、未集成、没有俯视/街面/远景游戏截图，没有碰撞、可达性、昼夜、资源预算及性能通过证据。A/B/C 的 nominal identity 已确认，剩余 crosswalk、逐栋参数和入口 blocker 单独保留；这些不阻止菜鸟/C 区已知形体和其他独立地标继续实施。
