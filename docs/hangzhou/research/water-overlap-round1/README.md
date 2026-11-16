# 杭州水面重叠固定源审计 round 1

截止日：2026-10-16。本包只读审计固定源与 `runtime-data-v4`，没有修改共享数据、脚本或资产，没有运行 Blender 或浏览器。

**结论：原 55 对中，38 对由逐对象 `simplify(.3)` 制造面积交叠；17 对在未简化源中已有面积交叠。恢复源边界后，全城还会显露 10 对此前被简化隐藏的源交叠，因此全局仍有 27 对原始源交叠待核，不能把它们平均高度或按 feature 大小任意裁切。**

## 固定输入与逐 part 对应

- `artifacts/cities/hangzhou/runtime-data-v4/city.json`，SHA256 `4f86e589f4df927eceecd7cbadbbff26e464aad9f2b3bdfc84ee84c917ae7617`，与父任务 55 对审计绑定完全一致。
- `data/processed/hangzhou-261011-extended/water.geojson`，SHA256 `e820b199c45012d9ba441ffccb135c5f1aaf6f29e2599f0a6262a0ddb231c4f1`。
- Geofabrik `zhejiang-261011.osm.pbf`，复制时间 `2026-10-11T20:21:06Z`，WGS84 / EPSG:4326，SHA256 `4eb65f64925498408faeee7eb04b60d7eb8a01c49ddb239f73070d4d282c75a9`。

使用 city 元数据内杭州原点、经纬系数和 0.60 缩放投影固定水体，按原流程裁切 bbox、只取 Polygon part、在简化之前过滤面积 `<20 game²` 的小 part。对同一 feature 的多个 Polygon，逐个选择与当前运行时 part **相交面积最大**的未简化源 part，并检查匹配唯一性：

**2,153 当前 part ↔ 2,153 合格未简化源 part，全部 1:1；没有未匹配、重复映射或多候选正面积相交。** 另 10 个过小源 part 被原构建规则过滤，已单列，不能伪称本次保留全源所有细小水体。2,153 个当前 part 全部与独立 `simplify(.3,preserve_topology=True)` 再四位小数取整的结果相符。

完整匹配表：[all-parts-crosswalk.json](all-parts-crosswalk.json)。它绑定运行时索引、源 feature ID、源 part 索引、交集/并集、顶点预算及边界变化；没有用数组顺序猜对应。

## 全部 55 对来源与关系

[all-55-pairs.md](all-55-pairs.md) 列出全部原始问题对；[pair-review.json](pair-review.json) 对每对保存：双方原始 version/timestamp/tags、成员 way、共同 OSM node、附近水道中心线和水工要素、测得几何距离、处理优先级及具体 blocker。

原始 PBF 已提取问题涉及的 **90 个对象（65 way、25 relation）**、相关关系的全部边界成员，总计 296 条 way，外加城区水工标签要素。所有请求对象和成员均取得，原始标签与 processed 标签没有值差异；libosmium area 回调仅省略关系的 `type=multipolygon`。这 55 对没有任何一对是同一边界 way 被另一水面关系直接重复引用，不能套用“关系优先、删成员 way”去消除它们。

| 分类 | 对数 | 可采用处理 | 仍未证明 |
| --- | ---: | --- | --- |
| 源共享边界、简化后相交 | 35 | 恢复对应未简化 part，保留原边界与孔洞 | 同一实际水位、闸坝现状 |
| 源近邻／点接、简化后相交 | 3 | 恢复源缝隙或点接，不能额外焊接 | 真实连通口及水位关系 |
| 源含闸室重叠 | 1 | 单列闸室及闸门，当前 hold | 上下游／闸室水位与运行状态 |
| 源有明确 layer 标签差异 | 1 | 保留标签差异，当前 hold | 真正上下层结构及高差 |
| 西湖与断桥荷区 | 1 | 保留荷区身份，优先补同一水面语义核实 | 精确岸线及单独控水情况 |
| 其他源面积交叠 | 14 | 按对象补岸线与水系身份，当前 hold | 交叠归属与水位基准 |

**17 对源交叠全部 `automaticClipApproved=false`，55 对全部 `automaticAverageHeightApproved=false`。** 无闸门标签、缺省 layer 相同、共同节点、相同河名或同属流域，都不能单独证明可统一水位。共同节点仅是来源拓扑证据；附近中心线或闸门距离仅是地图距离。

## 三个优先对象

### 断桥荷塘 way/975870009 与西湖 relation/2308774（第 1 对）

原始对象分别是 `v2 / 2025-08-05` 和 `v37 / 2026-02-12`。荷塘标签为 `name=断桥荷塘,natural=water,water=pond,salt=no`；西湖为 `natural=water,water=lake` 多面关系。荷塘不是西湖关系的 inner 或 outer 成员；但其完整未简化面被西湖源水面覆盖：约 **1,911.561469 game²（5,309.892968 m²）**，并共享 9 个源节点。

[杭州政府网站 2022 年报道](https://www.hangzhou.gov.cn/art/2022/2/15/art_812268_59049995.html)称其为北里湖断桥荷区，报道水域管理处为保护西湖水质收割残荷。[杭州政协网 2024 年报道](https://www.hzzx.gov.cn/cshz/content/2024-04/16/content_8716273.htm)说明断桥为西湖荷区清塘首站，作业前抬高拦网底端供鱼游出。这些资料支持“西湖荷区／围网管理区”的身份；不提供该 OSM 足印的工程测绘，也没有证明独立 1.5 米控水高差。

当前荷塘水面为 **5.399102 game**，西湖为 **4.5 game**，差 **0.899102 game**。两者来自不同的暂定 DSM 采样／参考策略，差值不是真实测得水位差。未来若确认同一湖面，应保留荷区为植被／材质语义区，以规范西湖水面承载；不能叠出第二个较高水面，也不能把荷塘身份和荷花区域删除。按主集成当前决定，本轮不裁切、不改高度。

### 闸室 way/662789923 与河道 way/520199008（第 2 对）

闸室 `v1 / 2019-01-13` 明确 `natural=water,water=lock`；河道 `v4 / 2021-03-19` 为 `water=river`。源河面包含整个闸室：约 **181.524239 game²（504.233998 m²）**，共享 5 个源节点。

固定 PBF 还有 `662789912,662789916,662789921,662618623` 的 `waterway=lock_gate`，以及穿过闸室的 `662789918`（`lock=yes,name=东河,waterway=canal`）。这些是可追溯的闸室／闸门边界证据，不是普通河面重复块。当前差 **0.788298 game** 同样只是两次 DSM 估计的差。

未来水平分区可优先保护明确闸室 footprint，再从泛河面扣除闸室重复覆盖；但必须另外确定闸室状态与上下游基准，不能平均水位、把闸室整个融入上游或下游，或把这次 DSM 差当作船闸设计落差。当前 hold。公开资料关于东河等闸门排涝的报道仅为控水背景，不凭河名将某篇工程说明绑定到本 footprint。

### layer=-1 的 way/552611233 与 way/642559807（第 3 对）

前者 `v8 / 2020-08-19` 为 `layer=-1,natural=water`，后者为未显式标 layer 的 `water=river`，源重叠 **57.402143 game²**。附近源线 `552611348` 亦为 `layer=-1,waterway=canal`，与余杭塘河中心线相交。该水面本身没有 tunnel/bridge 配套标签。

[OSM layer 文档](https://wiki.openstreetmap.org/wiki/Key:layer)定义的是局部层序，不能提供真实高差；负层也不能自动当作地下。这里既不能丢弃层级差异，也不能仅凭一个标签宣布已有真实双层水道。当前较低 layer 对象的 DSM 面反而更高，恰说明不能用这些估计反推真实层级。保留跨层／历史标注歧义 blocker，当前不裁切、不平均。

## 可追溯处理顺序

1. **先修制造的几何误差。** 从逐 part crosswalk 恢复未简化源边界；同一源共享节点保持相同投影、同一次取整。保留 inner rings、独立 pond、桥下线形，不进行二维吸附或跨对象焊接。该步骤不需要选择某个水面“赢”。
2. **先保护水工与层级约束，再讨论重复覆盖。** 闸室、闸门、涵洞、跨层水道分别保留；`layer` 不转为米数。不得按当前较高 DSM 面决定遮挡或裁切胜方。
3. **确认同一水体后再规范平面。** 明确属于同一湖面的荷区可改为同一水面上的语义区；连续河段需按闸坝分段，而不是对所有相交 Polygon 连通分量统一平均。当前所有源高程标签均缺失，真实高度仍须来源和基准绑定。
4. **源岸线冲突按对象冻结决定。** 对其余交叠，记录保留／扣除双方 source ID、part、版本、面积及证据。不能采用“relation 永远优先”“最大面永远优先”“最后写入优先”等无对象依据的规则。证据不足时保持 blocker。
5. **集成后重新全局审计。** `restored-source-global-overlaps.json` 已对全部 2,153 未简化 part 做 STRtree 复算：**27 对**源正面积重叠，原 55 对留下 17，另新显露 10 对。最大新增是 `way/641855998 ↔ way/642559807`，约 `0.605646 game²`；其余 `0.044755..0.001728 game²`。这 10 对另补取 12 个原始对象元数据，但水工语义尚未独立完成；不自动裁切。

## 取消 simplify 的预算与边界变化

| 二维源环指标 | 当前简化后 | 保留未简化源 | 增量 |
| --- | ---: | ---: | ---: |
| Polygon part | 2,153 | 2,153 | 0 |
| ring | 2,309 | 2,309 | 0 |
| hole | 156 | 156 | 0 |
| 坐标数（含闭环重复点） | 76,610 | 88,752 | +12,142 / +15.8491% |
| 顶点数（每环除去闭环重复点） | 74,301 | 86,443 | +12,142 |
| 无 Steiner／无共线消除的理论三角形数 | 70,307 | 82,449 | +12,142 |

这是二维输入预算；理论公式不等于实际 GLB 面数、合批结果或 GPU 开销，没有做导出／FPS 通过声明。

以全部边界原顶点及每条边百分之一间隔加密采样计算双向离散 Hausdorff，最大变化仍为 **0.366193497 game（0.610322496 真实米）**，位于 `way/642157074` 的 runtime part 454。它是固定几何间的采样变化量，不是连续 Hausdorff 的数学上界，也不是真实世界测绘误差。不能仅用 simplify 参数 0.3 推断所有边界变化都小于 0.3。

水位也应单独绑定：本次保留当前高度复核几何，未重采样。如果重新运行 geography 流程，恢复边界后 `representative_point()` 可能变化，DSＭ采样点和估计高度亦可能变化，必须单独记录，不能宣称只改了顶点而所有水位自然不变。

## 高度、许可与验收边界

原始问题涉及的 90 个水面对象均无 `ele/height/water_level/depth` 等明确高度标签。当前水位标记为 `estimated-not-surveyed`；窄渠和闸室取 30m DSM 代表点，西湖／钱塘江取既有暂定 EGM2008 参考。黄海基准报道值、EGM2008 DSM 估计和当前潮位不能混同，继续沿用既有水位研究包的基准转换 blocker。本包没有新增假定水位或允许全城平均。

[validation.json](validation.json) 的 **17/17 CPU 来源／对应／计数检查通过**，仅证明此次有限审计可核对。最终水面仍 pending：27 对源几何交叠、水工控制与层级身份、统一基准下的代表水位、岸线与地形／干地遮罩、渲染预算、反射及当前实机画面。没有任何共享修改或运行时通过声明。

OSM 及派生几何遵循 ODbL-1.0，署名 © OpenStreetMap contributors。政府／媒体资料仅作参考与 reported 证据，公开图片未下载为模型贴图或发布资产。网络抓取失败与直接 web 读取的区别保留在 `reference-fetches.json` / `online-evidence-observations.json`。

离线重现顺序（全部输出仅写本目录）：

```sh
.venv/bin/python docs/hangzhou/research/water-overlap-round1/measure_pairs.py
.venv/bin/python docs/hangzhou/research/water-overlap-round1/map_all_parts.py
.venv/bin/python docs/hangzhou/research/water-overlap-round1/review_pairs.py
.venv/bin/python docs/hangzhou/research/water-overlap-round1/freeze_report.py
```

原始 PBF 身份另由 `extract_raw.py` 获取，已有摘录可直接复用。所有输入与源码哈希见 [sources.json](sources.json)，完整 55 对数值在 [pair-measurements.json](pair-measurements.json)，全部版本／标签／关系见 [source-catalog.json](source-catalog.json) 和 [raw-osm-evidence.json](raw-osm-evidence.json)。
