# 主集成契约

本对象唯一模块为 `scripts/landmarks/west_lake_causeways.py`；独立任务目录为本目录。源足印、共享资产、运行时、总配置由主集成串行修改。没有在本任务调用 Blender 或浏览器。

1. 使用本目录 `spec.json` 与 `task-bundles/west-lake-causeways/job.json`。父任务可按以下命令在全新候选目录导出；该命令在本任务 **未执行**，不能提前填写 `model.buildCommand`。

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python scripts/build_hangzhou_landmark_candidate.py -- --job docs/hangzhou/research/core/west-lake-causeways-round2/task-bundles/west-lake-causeways/job.json --spec docs/hangzhou/research/core/west-lake-causeways-round2/spec.json --module scripts/landmarks/west_lake_causeways.py --output artifacts/cities/hangzhou/landmarks/west-lake-causeways-v1
```

2. `baseBuildingIdsToExclude=[]`：没有任何被该对象替换的建筑。仅对 `baseRoadIdsToSuppressVisual` 的19条源路抑制基础平面路条，保留全部源节点与导航。单独断桥 way28538289 已有另一对象负责；本清单没有它。仅在候选土地顶面确实替代基础绿地时，按 `baseGreenIdsToSuppressVisual` 的七个 source ID 抑制相应基础视觉块。不要排除整个孤山/西湖/自然保护区，也不要删除源草地布点数据或全湖水面。

3. 构建 `lm` 要用 spec的经纬度投影到杭州游戏原点，`lm.y` 必须是主城市确定的道路端点高度（游戏单位）。`lm.y` 不再次缩放。若各端点真实高程不同，当前“同端点基面”候选需扩展成逐端点基面并重新导出，不能用统一高度伪装坡度正确。

4. 接入 walkable 底面与桥面高度。模块 `bridge_height_at(lon,lat,lm,spec,.6)` 返回桥走廊内游戏高度，未命中为 `None`；`walk_surfaces` 记录19条原线、节点、净宽、桥面实米曲线、基面与缩放。转成游戏 x/z 高度查询时先按同一 canonical投影逆变换；没有自行定义另一个近似系数。一般路段顶面为 `lm.y`。不能把堤路和整个绿地环装进建筑 solid footprint，否则行人/汽车会被整条堤挡住。护栏碰撞应独立从侧边条带取得，并保留中间通行区域与进出口。

5. 依据原节点串接支路，避免边界低台阶和穿墙。两条主链用完整节点 ID 和坐标相同检查，入口邻接源路见 README。白堤断桥两侧在节点26315533与13454786643接现有模块；两对象的端点游戏高度应完全一致。苏堤六桥依北→南次序30072125/30075392/30072130/30072139/30072144/30072147，不重建或误归附近玉带桥/杨公堤。

6. 西湖水面仍由基础 water管线，源relation2308774包含草地/堤岸内环。模型的七桥洞是真实几何空隙，无水薄片，也无跨桥土地cap；保留桥孔内水体连通。草地顶面-0.03m、护岸底-1m、压顶0.06m均相对neutral道路端点；资料中的0.4m历史相对湖水不能作为新水位。以当前水材质面实际y检查墙底、拱脚/半圆与桥孔，允许候选参数调整后重新导出，不允许填假测绘值。

7. 白堤road29416781与旧湖体边缘存在源内偏差，现候选独立保持路线与岸线。必须从实机俯视/近景定位检查，若需要合并/修正岸线，应保存原源几何、推导方法与容差，更新基础湖水掩膜、候选土地与导航接合。不能只扩大land面填湖而留下来源/碰撞不一致。

8. 桃柳传统植被、准确根数、家具和灯布点仍 pending。现模块没有虚构全部树点或任何照片纹理；基础植被/林冠系统应依据七个source land strips，在道路和桥面之外恢复桃柳混植，保持其他treeLOD/实例化/街道避让规则，并控制白堤相间桃柳、苏堤密林的差别。文档桃柳描述不能当作具体树点已核实。

9. 先保存真实导出统计/哈希，再按对象task契约推进 modelled；验证水边/桥面步行、车辆路由、目的地、夜景和三视角截图后，才能填具名 final checks。CPU17检查和四图仅结构资料，不授予 verified 或最终外观通过。
