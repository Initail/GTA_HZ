# coastal-data-v1 实际数据独立复核

2026-11-11。实际读取 `artifacts/cities/hangzhou/coastal-data-v1/{infrastructure.json,manifest.json,shore-distance.png}`，先审阅producer，再使用独立 GEOS、NumPy、PNG解码及实际Node运行时函数验证。所有写入仅在此目录，未改共享源码或资产；没有浏览器或Blender。

**本次列出的有限CPU检查通过。** 这只证明当前序列化候选的数据与检查范围相符，不能宣布模型外观、桥梁可驾驶、GPU贴图或全项目完成。逐项状态在 [validation.json](validation.json)，来源哈希在 [input-bindings.json](input-bindings.json)。

## 桥段：2,132项逐一检查

- 对应2,049条源道路，所有sourceRoadId/sourceId以及完整nodeIds与输入一致，没有新增导航节点。湿区切点是几何裁切点，未被写成source node。
- 每点独立投影回源折线并按源链距离插值高度；最大point/station误差约9.1e-13 game，逐点高度、标量中点高度和链长误差均为0。ramp均0，width与源道路一致。
- 源桥湿区覆盖无缺项、无越界；非桥/隧道没有被加入桥面清单。仅有源身份和估计剖面通过，不代表真实桥面与刚性主结构对齐。

结果：[crossings.json](crossings.json)。

## 灯位：26个实际序列化坐标

每个灯位重新构造半径0.8 game、64分段/象限的基座盘，验证源公园足印、实际干地区和水体距离。26项均通过；基座边到水面的最小距离4.683403 game。

在producer原有障碍类别之外，补查54,613棵树的按实例缩放树冠范围、12,000棵基础树的实际GLB节点变换/position accessor包围圈、148,443个原始草丛/花灌/观赏草和54,737个排水篦/井盖。后两类按实际GLB保守外包络与实例缩放计算。还检查全部44,264基础楼、33,848道路、23地标到达区、112座椅、7,037信号灯臂位置、69,723街灯、21,275停放电动车、职业/咖啡馆区域及到达点，以及**9,155个细化碰撞对象的XY和高度范围**。在这些保守包络内没有命中。开放植被清单已读取并绑定；当前可替换树索引均为0，没有漏掉具名开放模型实例。

“无包络命中”不意味着所有道具逐三角形物理验收。信号灯、街灯、车、座椅沿用对应placement保护包络；公园灯完整杆头与实际网格碰撞还需导出/运行时检查。动态车流、行人以及运行时新生成的路边树不属于这批静态输入。

公共路径独立建立真实OSM共享节点图，种子额外排除private/no、禁止步行、motorway/trunk、桥和隧道的地面道路。全部26个源path均能连到这样的公共道路，报告保存实际节点序列和终点源道路ID。灯位到所属path的直线段全部在干地；这仍不是玩家实走验收。

地面采样没有导入producer的`Surface`：独立使用GEOS查找邻近道路段、源高度插值及栅格三角形重心插值。序列化groundY最大差8.9e-16 game。每灯在0.4/0.8/1.0 game三个半径、32方向共96点复查，最大坡度0.054606，小于0.12。它是有限采样，不证明点间连续地形所有极值。

全部逐灯记录、路径证据、96点坡度、道具类别数量、GLB包围范围见 [lights.json](lights.json)。

## 岸距PNG：读取真实字节再解码

独立校验PNG chunk CRC、IHDR、IDAT解压、实际行filter=0，不使用producer编码函数。得到8192×4847 RGB8、3,410,730个湿像素；G只有0/255，B为0。

以固定随机种子抽样并增加四边条带，共11,569个像素中心：湿/干分类无不一致，岸距R编码没有超过1个红通道量级的误差（120/255≈0.4706 game）。独立将真实水体并集边界拆为线段，只剔除两端明确同处裁切box边的段；没有用box减大陆生成海面，也没有把内部源水面边界当岸。

182个边界湿像素被强制检查。示例：南侧row0/col4209离crop边约1.304 game，但真实岸距≥120，PNG仍为R255；没有把crop边制造成近岸泡沫。独立剔除边长4745.291878 game，与producer的buffer端部处理只差约0.000020 game。

钱塘江中心样本为湿，垂直翻转后为干；小瀛洲岛体样本为干，翻转后为湿，因此可用于随后实机检查方向。西湖中心、水域孔洞、武林干地样本也保存了WGS84、game坐标、row/col和RGB。结果在 [png.json](png.json)。CPU行坐标正确不能替代Babylon实际上传后的invertY、采样、纹理就绪和反射视觉验证。

## 实际运行时校验器及负控

使用Node直接导入并调用`validateCoastalManifest(data,manifest,'hangzhou')`，没有用本审计的重写版本替代运行时函数。

初版接受真实候选，也正确拒绝径向ramp、错点、错逐点高度、错120编码及错12m灯高，但未拒绝标量height、length、nodeIds、sourceId的四个破坏性内存克隆。初次结果完整保留在 [runtime-validator-result.json](runtime-validator-result.json)，源码SHA256为 `2eeeef3d9609fd48c62395bd340a72f264d5335e6e0c1b03c4bb428d2e3485a8`。

主集成修复后另存 [runtime-validator-result-v2.json](runtime-validator-result-v2.json)：源码SHA256为 `326dce1dcdd7a9c8b29a58669b1444748aa3a128d03cea0004d7dff78ebf26f7`，真实候选仍接受，全部9项负控均拒绝。没有覆盖初次缺口证据或修改候选。

## 哈希与执行记录

producer manifest的全部输入/输出哈希均匹配，见 [producer-hash-checks.json](producer-hash-checks.json)。独立追加的碰撞、道具、GLB和配置均另行绑定。`check.py`不导入producer，只写本目录；Node脚本要求新结果文件名，防止覆盖既有结果。

```sh
.venv/bin/python -B docs/hangzhou/research/coastal-adaptation-round1/actual-v1-check/check.py
node --experimental-transform-types docs/hangzhou/research/coastal-adaptation-round1/actual-v1-check/runtime-validator-check.mjs runtime-validator-result-next.json
```

初次Python环境缺Pillow，错误原样留在`check.log`；随后改为标准库独立PNG解码，不安装/升级项目依赖。成功运行记录在`check-run2.log`和补基础树GLB包络后的`check-run3.log`。仍未通过项目级水体剩余24组交叠、桥/隧道剖面、实际道具模型接触、浏览器视觉和GPU预算门槛。
