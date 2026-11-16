# 城市阳台单值上包络与楼板实体 v2

2026-11-11。已交付可复验的数据候选，不修改GLB或共享运行时。

唯一接入文件：`site-surfaces-envelope.json`，SHA256 **4710642be132ba1a83d77ea393341bb48bbf70714936931c9642a8093baa3b03**。

- `walkFloors`只有一个ID **city-balcony:upper**，1626个单值上包络三角。
- `solidSlabs`为原下层27、原上层300个板顶三角，均`thicknessGame=.39`；不以采光窗顶面去假造.39g厚的盖板。
- 下层仍不在`walkFloors`；不能把新增下层实体防穿板误称下层入口已开放。
- 坐标为`[east,north,up]`游戏单位，`.60`已经应用，不能再次缩放。
- `terrainCuts=[]`只表示此包不重复交付地形，主集成应合并候选，不覆盖已有cuts。

## 真实最高支撑面

上层原主板在6处玻璃盖板/钢框顶面投影内扣除被遮住的低面；细部依据实际GLB高度取最高面。玻璃盖顶5.578901767730713g、钢框顶5.6074018478393555g，主板5.557902003142015g；finger仍保持原冻结高度场。

131个统一平面线网单元生成覆盖分区，再与原主板域及finger组成1626三角。只对内部细部布尔线网使用**1微米(1e-6g)坐标网格**统一节点，消除远小于GLB float32精度的病态分割；没有改GLB、外部公共floor域、模型高度或添加坡面。完整floor域对称差面积为0，三角面积和与并集差仅1.82e-12g²，正面积重叠（>1e-12g²）为0。

采光窗薄细部始终属于同一个上层deck，不作为可连续“踏上”的新楼层。旧包的相互覆盖支撑三角不能混入此新`walkFloors`。

## openEdges与真实台阶边

楼板→盖板→框是原GLB的真实竖直台阶，本包没有把它们改成缓坡。面积裁切后，闭合三角在共享边上仍会同时带有高/低高度，因此使用root新接口的逐三角字段：

```text
openEdges[i] = [edge0, edge1, edge2]
edge0: a→b
edge1: b→c
edge2: c→a
true=open（该边不属于本三角），false=closed
```

低面台阶边open，高面closed。低面在台阶顶点周围的内部扇区也需要有序半开，否则仅打开外边仍会从某个低面内角返回低高度。本包用联合布尔约束处理所有共享边/顶点：内部共享边不能两侧都open；每个低层顶点引用必须被至少一个相邻open边排除；每个最高顶点必须至少有一个闭合归属。599个台阶顶点、656条可直接配对台阶边，最终1445个open标记；未解决归属0。边/点明细在`step-boundaries.json`。

三角高度仍用原重心插值。包含/open判断必须与当前TS/Python一致，采用每条边的**真实世界有符号距离**`cross/edgeLength`：包含>=−1e-9g，open排除abs<=1e-9g。不能把这个1e-9误换成按不同三角高度放大的barycentric容差。

## 失败与修复保留

初期独立裁切产生微小缝或台阶顶点漏归属，原日志`build*.log`保留；数据未在这些失败阶段交付接入。

统一分区和组合归属完成后，旧barycentric EPS的实坐标查询仍失败315/11865：165处双高度、150处无归属。世界坐标约3300的舍入误差，在极薄三角中被放大成不同的重心残差，使同一物理边的两侧不一致。真实反例：`[3296.21693925,-2056.29489825]`低面残差约3.44e-9，高面约−1.14e-12。

root将TS/Python统一为世界边距后，**同一1626面数据**重验全部通过，步差、nearest previousHeight、速度和楼层规则未变。`validation-bary-eps.json`、`ownership-query-failures-bary-eps.json`、`validate-bary-eps.py`保留失败；`validation.json`及`validate-world-eps.log`为修复后独立结果。

## 实际验证范围

| 项目 | 当前结果 |
|---|---:|
| floor域增加/遗漏面积 | 0 |
| 正面积重叠>1e-12g² | 0 |
| 顶点、每边四分点/中点、三角内部点 | 11,865 |
| 空支撑/不同高度并存 | 0 / 0 |
| 最大归属高度差 | 2.66e-15g |
| 实际TS双高/低previous hint查询 | 23,730，失败0 |
| 同点重复静止更新 | 94,920，跳层/抬人0 |
| 楼板实体站顶/头顶/穿入查询 | 1,308，失败0 |

实际TS验证绑定`src/city-site-surfaces.ts` SHA256 **c15dde1cd092355d88d4b26c8a947f96df6a4e06ac3d627217c210a036733d7a**。独立Python和实际TS采用同一世界距离语义；`runtime-validation.json`仍只代表接口查询，不是浏览器身体移动。

所有支撑高度均能在实际源GLB的1mm平面配准容差内找到对应原顶面，高度误差最大约**.0000019993g**，平面距离最大约**.000144688g**，均低于.001g。

在不允许任何平面配准误差的固定XY竖线比较中，1573个台阶/边界样点可能命中相邻较低面：源公共双精度坐标与GLB float32边界存在微偏移，细部布尔还有上述1微米节点规整。**这项原始差异保留在验证结果，不能声称所有不连续边界的严格同XY高度完全一致。** 对这些点，本报告验证的是对应GLB原顶面在明确1mm平面容差内、高度误差<=.001g；没有用错误层的高度补造坡道。GLB保持原字节。

## solidSlabs来源与含义

两个实体组使用原模型真正的上下板顶，不采用上包络细部顶面：

- `city-balcony:lower-slab`：27三角，板顶1.957902003g。
- `city-balcony:upper-slab`：300三角，主板顶5.557902003g及原finger坡面。
- 厚度统一来自原spec的slabThicknessM=.65×.60=**.39g**，只向下挤出。该厚度是已实现模型参数且GLB顶底实证一致，**不是建筑实测结构厚度**。
- 实际GLB中327组顶/底三角全部对应，缺失0，见`slab-glb-correspondence.json`。
- 下层不复制finger板，三个源玻璃体内环仍无公共板；本数据不新增墙体或填满两层间空间。

`blocked`测试验证站在板顶不会被自身板挡住，身体/头部从下方进入板体会被拒绝。接入时仍须高度感知的栏杆、柱、玻璃占用和身体半径；板实体不能替代这些，也不能变成全高碰撞。

## 重建与接入

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-walk-envelope-v2/build.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-walk-envelope-v2/validate.py
node --experimental-transform-types docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-walk-envelope-v2/check-runtime.mjs
```

主集成可以按此哈希准备v7隔离输入，将本包`walkFloors`替换旧叠面提案并合并`solidSlabs`。不能自动启用下层入口或改变CityWalk原.48步差、速度、上下车行为。

草地分区、真实楼梯/电梯、下层入口仍unknown。818段栏杆和136个有限高度实体沿用上一占用包，不因这次上包络而删除。连续岸端45个地形接合探点仍沿用已冻结seam契约，但公众到达、角色身体扫掠、入口/落水、刷新恢复、实机昼夜与性能仍未验收。

## 有限边段高度求值复验

主线进一步限定容差域外点只能投到距离<=1e-9g的有限边段，避免极薄三角延长线外推。候选数据字节不变；当前TS SHA256 **82f93649d9a834cef7aa4b805d4c9dd3a43797023b98a5115847fe0c50b88bb0**，11,865点/23,730双hint/94,920静止查询及1,308楼板案例全部0失败，最大高度误差6.22e-15g。结果单独保留为`runtime-validation-finite-edge.json`，此前世界边距结果未覆盖。
