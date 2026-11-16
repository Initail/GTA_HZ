# 城市阳台公共楼板与岸端接缝数据提案

2026-11-11。只读取冻结 `city_balcony_floor_v2.py` / spec / placement / 实际GLB及当前步行接口；没有运行时源码、世界、地形、资产或Blender修改。

**已交付可接入几何**：公共上层300、下层27个源三角面，全部匹配实际GLB；136个有限高度柱/墙占用、818段实际护栏，以及6个采光窗盖板/边框的348个同层细部顶面；两条完整岸端接缝。它们不代表已经完成公众入口、身体碰撞或实机验收。

实际源GLB SHA256 **731066a06278848025c19153584eae7539e0ba7a73db49540e6eb7679ff67757**；对象模块 SHA256 **9b69526095965d6e9980967a1f242f5ce23f0130fcaa4eb982de373c76d45d48**。

## 文件与坐标

- `public-walk-surfaces.json`：上/下层独立ID、完整源公共环（排除三个玻璃体）、三角面、源字段/索引和实际GLB mesh/triangle对应。**这里的 `verticesGameXYZ=[east,up,north]`** 是明确标注的游戏轴序。
- `occupancy.json`：有限高度实体、薄护栏、采光窗细部，不能把整个楼板当全高障碍。护栏保留实际零厚度玻璃片和.051g钢框宽度，碰撞需要既有身体半径扫掠，不能仅点落面判断。
- `entry-seams.json`：西/东两组完整源端边、分段高度、外法向、两侧探点及转移规则。
- **`site-surfaces-upper-only.json`**：建议主集成使用的 `SiteSurfaceData`。`walkFloors` 包括上层300及同上层盖板/框348，共648三角，**不含下层**。
- `site-surfaces-all-public-geometry.json`：同格式的完整上下层几何，共675三角；仅供审查或下层入口将来验证后启用，**不建议直接默认加载**。
- 两份 `SiteSurfaceData` 的坐标均按新接口改为 **`[east,north,up]`**，`units='game east/north/up; scale applied once'`，不可再次.60缩放。`terrainCuts=[]` 表示本包不复制主集成的terrain数据；接入时合并 `walkFloors`，不能用空数组覆盖已准备的地形切接候选。

## 源三角面与实际GLB

| 项目 | 本轮结果 |
|---|---:|
| 下层主公共楼板 | 27三角、8814.282658g² |
| 上层主楼+两finger公共楼板 | 300三角、10205.559537g² |
| 与源公共多边形对称差面积 | 两层均0 |
| 源→GLB三角对应 | 327/327，使用实际float32世界顶点集合 |
| 公共楼板最大float32顶点误差 | .000144688g |
| 护栏片 | 818段，所有源面顶点在实际GLB中，最大误差.000154603g |
| 柱/玻璃窄占用 | 136，保留其min/maxY，不是无限高碰撞 |
| 同上层采光窗细部顶面 | 6×58=348个实际GLB三角 |

主上层5.557902003g、下层1.957902003g，相差3.6g；局部上层finger使用冻结的连续高度场。两层源玻璃体内环都不产生公共楼板。下层不复制两条finger的板，也不凭位置重合产生上/下层连接。

每个公共面只是**支撑几何**；站立还必须通过身体与玻璃墙、栏杆、柱、道具、植被的占用检查。层上的有限高度范围必须保留：例如低于上层板底的柱不能阻挡上层人物，玻璃墙/护栏也不能因valid floor被跳过。

## 两个岸端entry seam

西源端为13→14→15→16三个连续源边，总宽16.865758g；东端为9→10，总宽27.816795g。完整边界按≤1g采样，分别17/28个分段中点，再沿外法向检查内外各.3g点。

| 当前估计ground与真实模型端面诊断 | 西 | 东 |
|---|---:|---:|
| 内外探点最大高度差(g) | .004277045 | .007418419 |
| 干地/严格<.48步差诊断 | 17/17 | 28/28 |
| 固定riverside path提取中距整个seam<10g的线 | 0 | 0 |

没有近线不等于广场不可步行，也不等于已经有连通公共路线；该提取本来仅含近河路径。实际公众入口与世界道具/行人/植被清障仍未通过。

`previewSafeCenterStationsGame` 只作几何预览：端部让出walk radius .23g + 钢框半宽.0255g + float余量.001g。不能替代当前 `CityWalk.clear`、完整身体碰撞和场景阻挡检查。

转移必须实际穿越有限的已声明端边，保持previous feet height，满足原严格<.48步差及身体检查。返回地面同理。不得按XY直接选最高/最低楼层，不得从上层瞬移到下层，也不得将层=-1之江路相交解释为入口。

## 采光窗、草地与楼梯的边界

当前6个圆窗是**完整公共楼板上方的玻璃盖板/边框表达**，不是实际开洞的贯通竖井。模块明确保留下方楼板；玻璃顶约高出.021g、框最高约+.0495g。348个细部顶面直接来自实际GLB，作为同一 `city-balcony:upper` 的局部鞋底支撑候选，可沿既有<.48步差跨越。不能把它们变成通往下层的孔洞或独立楼层。

真实采光窗承载能力、内部竖井与现状使用仍unknown。此数据只忠实表达当前游戏中被实体楼板托住的薄细部，不声称现实可踩。

上层公园/草地的具体分区与真实楼梯、电梯、下层入口均unknown。本包没有生成额外草地支撑层、新楼梯/电梯、室内通道或虚构上下层边。

## 对新 SiteSurfaceData 接口的实际调用检查

`check-site-interface.mjs` 实际import当前 `CitySiteSurfaces`（检查时SHA256 `bd2dc3a0b2b68e9c2cbccc6257ce99b89266ff7d1b333d001422cae801059d73`）：

- 建议数据648个面重心查询都保留上层支撑；同层细部高度差可正常选择；远离参考高度1g不强行吸附。
- 45个岸端内外点查询可连续从ground选上层并退出，保持<.48原步差。这是接口查询，**不是实际行走或身体验收**。
- 完整楼层数据的27个下层三角在给定切低地面1.557902g时，会因为下层只高.4g而被现接口选中；**这证明 previousHeight本身不能证明下层入口合法**。建议上层only数据把这27面保持未启用，下层几何单独保存，不删除。
- 现CityCollision末尾的水/land拒绝仅可在有效当前支撑上被覆盖；玻璃、柱、栏杆等身体障碍必须仍检查。现有136个ground_footprints不含全部818段护栏，不能只装楼板就宣称可走且不穿栏杆。

参数只读核对并保留：步行1.6、跑步4.2、半径.23、步差严格<.48、出车高差.55、入车高差.8、入车路径步差.48、眼高1.53。没有添加车辆入口或上层停车点，也不放宽上下车检查。

## 重建与阶段

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-walk-surface-proposal/prepare.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-walk-surface-proposal/validate_and_adapt.py
node --experimental-transform-types docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-walk-surface-proposal/check-site-interface.mjs
```

初次脚本的缺失shape导入、numpy bool JSON类型、审查helper缺少`__file__`初始化失败均保留原日志；完成这些工具修正后正式数据与接口检查通过，没有跳过几何断言。

当前只到**数据/有限CPU接口检查**。主集成还需合并terrain cuts、有限高度占用与支撑逻辑，验证45个点之外的完整身体扫掠、两岸端公众到达、绕行/上下车规则、刷新恢复、实机昼夜三视角和性能。项目/城市阳台未完成。
