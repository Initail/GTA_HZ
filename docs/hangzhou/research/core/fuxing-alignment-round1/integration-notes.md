# 独立候选接入约定

模块为 `scripts/landmarks/fuxing_alignment.py`，规格为本目录 `spec.json`。这是复兴主桥的独立候选，包含两座大拱、九座小拱、两层结构、桥墩/拱肋/护栏；没有新增水片或公路顶面。保留冻结原模块和原三桥 GLB 作为旧候选。本轮仅写新模块与新研究目录。

默认 placement 来自新规格：WGS84 `[120.17491023246365,30.209804734010763]`，游戏东/北 `[1149.4589569435811,-4269.899577139778]`。原模型水面显示基高 `lm.y=.9` 已是游戏单位；尺寸 `.60` 缩放一次。上/下层顶面仍为 14.1/8.1 游戏单位（原估计水面相对 22m/12m），不是测量海拔；误差保留原上层 ±6m、下层 ±4m、层差 ±2m。

```python
from scripts.landmarks import fuxing_alignment
import json
spec = json.load(open('docs/hangzhou/research/core/fuxing-alignment-round1/spec.json'))
lm = {'x':1149.4589569435811, 'z':-4269.899577139778, 'y':.9}
report = fuxing_alignment.build(b, lm, spec, .60)
solids = fuxing_alignment.ground_footprints(lm, spec, .60)
surfaces = fuxing_alignment.walk_surfaces(lm, spec, .60)
profiles = fuxing_alignment.source_road_profiles(lm, spec, allow_estimated=True)
audit = fuxing_alignment.profile_alignment_audit(lm, spec, allow_estimated=True)
```

`build` 使用原 `_fuxing` 的真实 primitive，把其原始所有顶点统一刚性变换；不会因重算竖向多边形 tube 的全局基向量而改变柱截面。原/新全部对应顶点的刚性变换最大差约 1.82e−12 游戏单位。B.frame 成功和人为异常路径均恢复，无场景或导出副作用；总构建器继续拥有导出。

`.60` 下 `ground_footprints` 提供 2,636 个非空实体包围体，均带 `polygonGame`、`minYGame/maxYGame`、`verticesGameENU`、kind。原 source face 区间作为 `originalSourceFaceRange` 留下，不冒充新网格索引。CPU 将这些边界逐项与候选实际发出的 faces 对照。碰撞仍采用保守平面凸包乘 Y 区间，细碰撞/actor尺寸及性能待父实测。细栏杆面积小于旧共享 `.01` 游戏平方米检查阈值，父应保留真实截面；高度区间与平面需同时使用。

`walk_surfaces` 提供 46 片实际桥面侧面所定义的顶面区域，含 `heightGame` 与 `undersideYGame`，不加入阻挡建筑。父道路高度表面管线处理路面和桥板下表面接触。基础楼体排除 ID 为空，复兴无新增铁路面。

`source_road_profiles` 仅返回 7 条原复兴道路。WGS、node、点、样本和既有估计高度逐字段保留；只更新对应实际候选桥面区域。其他比例的道路查询会拒绝，防止缩放或平移真实道路来配模型。刻意把模型东移 100 游戏米时源道路仍保持原位，CPU 会如实报告更大缺口。显式共享节点高度 override 同样保持游戏单位；例如节点 `1667217046` 设成 13.7，两条源道路均保留 13.7，但候选顶面仍是 14.1，审计给 −.4 差值及 unavailable。

父组装需选择新复兴实体/碰撞，并排除原三桥包中的旧复兴实体/碰撞，避免同时显示两套错位结构。原三桥 GLB 只按材质合并了桥体；单独加载新 GLB 会与旧复兴重叠。可在新的父候选组装中分别导出保留的原钱塘/之江与本复兴候选，原文件保持冻结。source way ID 和道路表无需移动或改写。

轴线修正只确认了相对固定数据的模型参数偏差：上层车行道中点拟合与下层外侧道中点交叉核对，不能确认现场绝对轴线，也不能确认 near-end source 的边界宽度。论文报告 26.4/32m，因此本候选保留该宽度；并未以线路包围盒扩大桥面。原资料显示两端和观景设施复杂，当前 actual source placement、细部边缘、匝道外扩或局部曲线均 unknown。

全七路对照保留 `way/336983476` 三个主桥内失配节点及23样本。最小源中心点一致核心约833.8m覆盖两大拱与中央五小拱，原间隙/站位误差保留。完整1376m结构两端、完整源引桥、岸台、电梯/平台、绝对地坪与纵坡、人物/车辆净空和权限、实机不穿墙不落水、昼夜/浏览器/性能，均未验收。

真实阶段：`fuxing-alignment` finite axis hypothesis/candidate evidence-ready（exit0）；`fuxing-complete-alignment` 未过门、planned（exit2）。本模块没有导出的新 GLB，未记录 modelled/verified。
