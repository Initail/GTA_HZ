# 杭州国际会议中心第二轮：金球与裙楼候选

当前为 **evidence-ready**，范围是金球外观、玻璃开口/穹顶、圆弧裙楼和两个入口外形。没有本 worker 的 GLB 导出、浏览器或性能验收；正式八项验证保持 unknown。真实地面与通行、酒店/会议室内部、地下层、喷泉及雕塑不在本轮候选范围。

## 身份和来源

[PETROFF 项目官网](https://www.petroff.com/projects/hangzhou)说明其项目建筑师/主顾问职责及 Carlos Ott 的概念设计角色。[中国建筑学会刊载结构工程师葛家琪的报告](https://www.chinaasc.org.cn/news/117011.html)对应 Carlos Ott / 中国联合工程公司，支持外网格球壳、内部钢框架及双 C 形功能关系。[幕墙供应商 Hunter Douglas](https://ap.hunterdouglas.asia/project/hangzhou-international-conference-center)支持金玻璃/金色蜂窝板、85 米直径与总高、13 米椭圆裙房；英文设计字段的 GS / Xia Bangjie 与前两来源有差异，保留原记录，不把供应商字段直接确定为最终设计署名。[运营方 IHG](https://www.ihg.com/intercontinental/hotels/cn/zh/hangzhou/hghha/hoteldetail)确认洲际酒店 ICC 及与大剧院的日月对应关系。

政府 CUC 项目关联只从滨江政协检索摘录获得，直接页读取失败，不拿它证明尺寸。[浙江在线 2017 年现场采访](https://town.zjol.com.cn/czjsb/201712/t20171214_6044540.shtml)提供构造/楼层及灯槽描述；[清华大学 2016 年项目说明](https://www.tsinghua.edu.cn/info/2066/68498.htm)支持逐层暖色 LED 与遮光措施。后两者不证明当前灯具数量、坐标或节目控制状态。

`photo-review.json` 包含 **12 个实际查看**的供应商、设计方、运营方与采访参考，其中包括侧面街景、入口近景、后侧空中、朝大剧院的玻璃正面、顶部天窗内部及场所配景。内部/雕塑图不计作额外外立面方向，精确拍摄日期及相机标定大多未知。全部参考图只存临时缓存，未放入本包或发布贴图。

## 固定足印与参数

采用 Geofabrik 浙江 `zhejiang-261011.osm.pbf`，时间 `2026-10-11T20:21:06Z`，SHA256 `4eb65f64925498408faeee7eb04b60d7eb8a01c49ddb239f73070d4d282c75a9`。OSM WGS84 位置和轮廓使用杭州公共投影系数，真实米制尺寸进入游戏时缩放 0.60 一次；没有把 GCJ-02/商业地图坐标当作 WGS84。

| 内容 | 值及依据 |
| --- | --- |
| 主裙楼足印 | `way/626838544`；OSM 面积矩包围约 181.35 × 140.84 米；不是球体直径 |
| 锚点 | 标为“金球”的下层 part `way/626838542` 面积质心 `[120.20903333135745,30.244770848310754]`，不是入口 |
| 裙楼轴 | 东逆时针 143.4492°，来自主足印面积矩；朝大剧院的玻璃侧为 NE、约 53.4492° |
| 85 米直径、85 米总高 | `reported`，工程师及供应商资料；没有把完整 85 米球叠在 13 米裙楼上得到 98 米 |
| 13 米裙楼 | `reported`，供应商与现场采访；源主足印 `height=20` 未核实，不直接采用 |
| 球心 46 / 低截 20 / 金皮上沿 81.5 米 | `estimated`，按上述约束及侧面/空中比例拟合；±3–5 米，未获真实断面测量 |
| 朝大剧院的玻璃楔面 | 照片直接支持；半角 0.39 rad、内退 1.8 米为估计，宽度 ±0.12 rad、内退 ±1.5 米 |
| 15 条球体代表窗带 | 工程师报告的球体范围；采访 18 层、历史整体 19 层口径未统一，不称为现状逐层核验 |
| 顶部天窗 | 实际设计方内景及运营空中照片可辨认；浅穹顶几何仍是估计 |
| 入口连接 | source-bound 外段接到候选中央玻璃基座，真实相交边线保留；补足中间局部连接为有误差说明的估计 |

`osm-measurements.json` 保存 32 个具体要素、原标签、质心与逐要素哈希。某些分层源轮廓约 **108 米**、顶部 tag **88 米**，与 85 米资料差异明显；它们不是本轮测绘值，不进行无说明缩放。下层“金球”足印约 83 × 82 米仅用于锚点绑定，球的真实形体尺寸优先采用公开工程资料。所有地图计算仍有源精度未知、规划用 ±5 米位置/裙楼误差、朝向 ±5° 限制。

## 模块和 CPU 结果

`scripts/landmarks/international_conference_center.py` 使用独立 `build(b,lm,spec,scale=.6)`，不导入 `bpy/city_mesh` 或重置共享场景。模型包含退台金带/凹入窗带、高玻璃楔面、浅玻璃穹顶、两个有弧形断面的裙楼翼体、两个玻璃入口及雨棚。它未创建水面、铺满场地的公园板、酒店室内玩法或未经核验的招牌。

当前纯 CPU 统计 **10,066 faces / 20,073 fan 三角形、4 材质、0 灯、0 水面**，低于事先固定的 26,000 三角形/7 材质预算。真实 GLB 三角形、文件和运行时 draw call 尚待导出。已通过：所有源足印点与 WGS84 投影吻合、0.60 单次缩放、游戏基面平移、frame 恢复、拒绝重复缩放、85 米顶部高度、85 米球体范围、NE 玻璃表面射线、天窗顶部射线、实际退台半径差、圆裙楼高低曲面、入口连接上向法线与射线。射线不是运行时碰撞或可进入验收。

`cpu-top.png`、`cpu-street.png`、`cpu-distant.png` 是 **Pillow CPU 草图**，并非游戏截图。已实际查看，球体截切、窗带、玻璃前面、低翼体与入口可以辨认；草图只用简单不透明颜色和三角形 painter，透明反射、凹多边形遮挡、实时阴影和实际 Babylon 光照不在其能力范围。正式视觉、纹理与夜景不能标 pass。

现有 `gold/darkglass/landmarkglass/steel` 材质为暂用别名：尤其 `darkglass` 未匹配照片中的**金色玻璃**，必须由主集成人员通过正式材料过程改善并实机核验。虽然来源证实灯槽/暖色逐层灯光，本模块仍为 0 新灯，待主集成确定位置、控制与资源预算。

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python docs/hangzhou/research/core/international-conference-center-round2/validate_cpu.py
.venv/bin/python scripts/landmark_tasks.py check --job docs/hangzhou/research/core/international-conference-center-round2/task-bundles/international-conference-center/job.json --stage evidence-ready
```

CPU 草图用带 Pillow 的配置 Python 运行 `preview_cpu.py`，未变更 npm/Python 锁定依赖。冻结脚本会重写本轮调查 JSON，依赖固定快照及临时参考缓存；已有导出后不得盲目重跑覆盖冻结记录。

## 主集成接管

仅排除 `spec.json.baseBuildingIdsToExclude` 的 **32 个 ICC 主体/部件 ID**，同时处理基础楼体与近景立面，不留分层叠楼。**不排除**用于方向参考的杭州大剧院 `way/626838819` 或交通入口 N2 `way/1023947435`，不删除整个广场/新城范围。

推荐串行命令（worker 未执行，model.buildCommand 保持 null）：

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python scripts/build_hangzhou_landmark_candidate.py -- --job docs/hangzhou/research/core/international-conference-center-round2/task-bundles/international-conference-center/job.json --spec docs/hangzhou/research/core/international-conference-center-round2/spec.json --module scripts/landmarks/international_conference_center.py --output artifacts/cities/hangzhou/landmarks/international-conference-center-v1
```

继续 pending：真实地势/基面/台阶/入口可达性，85 与 108 米源差异和准确剖面，完整窗格/曲面与署名角色，实际招牌与金玻璃，当前灯控及昼夜实机三视图、碰撞和性能。该有限候选不等于全会议中心或 GTA_HZ 完成交付。
