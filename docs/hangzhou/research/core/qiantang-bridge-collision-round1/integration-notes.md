# 三桥碰撞候选交接

唯一模块 `scripts/landmarks/qiantang_bridge_collision.py`，唯一规格为本目录 `spec.json`。冻结 `qiantang_bridges.py` 和原桥规格均未改；没有调用 Blender、游戏浏览器或修改共享配置/资产。此模块提供 CPU 碰撞与表面接口，不产生新 GLB。关联原 GLB 已通过所有五种材质的全部 float32 顶点集合对照，24,148 三角形相符。

入口使用原导出 placement：`lm.x=-1190.7513899330004`、`lm.z=-5205.802147668741`、`lm.y=0.9`、`scale=0.60`。`lm.y` 是原模型水面显示基高的游戏单位，直接加到物理高度缩放结果；不再乘 .60。修改水面基高需要同步移动外观资产，不能仅移动碰撞。

```python
from scripts.landmarks import qiantang_bridge_collision as collision
import json
spec = json.load(open('docs/hangzhou/research/core/qiantang-bridge-collision-round1/spec.json'))
lm = {'x': -1190.7513899330004, 'z': -5205.802147668741, 'y': .9}
solids = collision.ground_footprints(lm, spec, .6)
roads = collision.source_road_profiles(lm, spec, allow_estimated=True)
road_surfaces = collision.walk_surfaces(lm, spec, mode='road')
rail_bed = collision.walk_surfaces(lm, spec, mode='rail')
# 某一个 source way / 某一个运输模式；heightGame=None 表示此处存在实际几何缺口或高度不一致。
surface = collision.surface_at_game('way/4348186', x_game, z_game, lm, spec,
                                    allow_estimated=True, mode='road')
```

接口也接受精确未修改的原桥规格（`id=qiantang-bridges`）；任何改变尺寸的原规格克隆会报错。source module/spec SHA 发生变化必须重新审查。内部回放只修改独立私有模块对象，不给父渲染模块打补丁；原 B.frame 在回放后恢复。返回的碰撞/地面列表是复制件，集成端修改不会污染缓存。

`ground_footprints` 返回 7,457 个非空实体包围体：41 个桥墩、11 个墩横梁、432 根栏杆柱、16 段水平栏杆、2 条铁路钢轨、1,808 段桁架、2,319 段拱肋等构件、84 个索塔段和 2,744 段细分斜拉索。原始 tube/portal primitive 共 2,637 个；细分数量不是现场构件调查数量。每个对象提供 `polygonGame`（东/北）、`minYGame/maxYGame`（上）、`verticesGameENU`、kind、mode 与原始 face 区间。

碰撞查询必须同时使用平面与 Y 区间。禁止把 7,457 个平面投影当作从地面向上的无限建筑。尤其是复兴上层栏杆的最低 Y 大于 14，不能挡住 Y=8.1 的下层探针；之江索塔分成 84 段，中央车道上方冠部的包围体只在实际冠部高度生效。桥墩两腿之间保留空隙。

桥面不加入阻挡建筑列表。`walk_surfaces` 提供 48 个道路桥面区域和独立请求下的 1 个铁路床面区域，均给实际候选顶面高度与 `undersideYGame`。道路顶面由父路面管线生成，桥板下表面/顶面的接触由父高度表面管线处理；此处不新造路片或水片。铁路床面高度不是火车车轮轨头高度，不能将 rail mode 接入 NPC 汽车。

原渲染 `lm.y=.9` 下顶面为：钱塘公路 12.3、铁路床面 5.88；复兴上层 14.1、下层 8.1；之江 11.7 游戏单位。都是源外观规格中的照片估计水面相对高度，真实高度误差约 ±5m，水位/绝对基准未知。CPU 数值相符不提高现场精度。共享节点 `3351280499` 在公路与铁路分别保留 12.3/5.88，相差 6.42；各同层连接节点则一致。复兴共享上层节点 `1667217046` 的显式 13.7 游戏单位 override 在两条 way 都保留 13.7，但刚性原桥面仍是 14.1，查询返回高度差 -0.4 与 blocker，不修改模型来制造一致。

原共享 `prepare_hangzhou_detail_collisions.py` 需要由父集成处理两处兼容事项：它当前固定 `lm.y=0`，必须读取导出 placement 的 `baseYGame`；它拒绝 `.01` 游戏平方米以下的多边形，而真实栏杆柱截面最小约 `.000882`。这些小实体必须保留，不可为过门统一放大尺寸或静默丢弃。还有 7,457 包围体的空间索引/细碰撞性能尚待父实测；不能据 CPU 成功称性能通过。

外壳包围体使用凸平面投影乘高度区间，是保守接触候选。斜向 tube 构件按最大 4 游戏米平面跨度 / 1.2 游戏米高度差细分；索塔则保留原网格逐段结构。3D 顶点保留供父细碰撞。保守包围体可能比真实斜面更大；精确人物/车体扫掠、缆索附近行走和窄处不可据此宣布通过。

完整桥路的阻塞记录在 `source-profile-geometry-audit.json`。15 条 source road 共 118 个 way/node 项和 578 个 <=20m 插值样本缺实际主跨桥面，主要在主跨外引桥；具体 node 和缺口距离逐项给出。另有复兴上层 `way/154135290` 的 2 个节点横向超出实际候选桥面 .236–.610 游戏米，以及下层 `way/589429905` 的 10 个节点横向超出 1.674–4.648 游戏米；这不是只有主跨外的问题。既有 source road 可以保留为明确估计的道路候选，缺结构匹配不能自动解释为实际交通封禁。

最大平面缺口：钱塘源 road 120.069 游戏米；复兴 247.842；之江 `way/306360739` 902.455（全长含路接续，有限 478m 主跨不覆盖整条）。四条之江西岸续路仍在 15 行 API 中，节点 `3112466937` 和 `3112466958` 与主桥源路点/高度严格一致，父 v5 图连通审计不等于实物纵坡/地坪验收。

原模型没有实证岸台、完整引桥墩/坡道实体，本适配没有虚构这些碰撞。基础楼体排除 ID 为空。父集成仍需解决岸台、坡道结构/横向范围、绝对地坪、水岸、桥板接触、actor尺寸/道路权限、实机不穿墙不落水、白昼夜景、视角与性能。

任务实际结果：`qiantang-bridge-collision` 仅有限现有实体边界 evidence-ready，exit 0；`qiantang-bridge-passage` full scope evidence-ready 检查 exit 2，维持 planned。独立 adapter 没有伪造新的模型/verified 记录；原 bridge GLB 的 modelled 阶段归父外观任务。
