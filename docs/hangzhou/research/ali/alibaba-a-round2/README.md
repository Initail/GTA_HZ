# 阿里巴巴西溪 A 区：当前源对象有限外观 round2

本轮按固定 WGS84 足印制作当前地图 A1–A8 主办公对象与四组 anonymous links 的外观候选。设计参考采用[隈研吾淘宝城官方项目](https://kkaa.co.jp/project/alibaba-group-taobao-city/?language=en)的真实照片、1F/2F 平面和剖面，摄影署名 ©Sadao Hotta。**当前 A1–A9 楼号不等于 2013 项目“六个办公单元”**；公开平面图上的数字是功能图例，也不是当前 A 楼号。历史各期/楼号/architect unit crosswalk 仍 blocker。

已有 `evidence-ready` 实际记录；模块及 CPU 检查完成，未启动 Blender、导出 GLB 或做浏览器/实机验收。A9、全部历史校园/完整 links 不在候选完成范围；不能宣布 A 区完成。

## 固定源、范围与身份

主源 Geofabrik 浙江 `zhejiang-261011.osm.pbf`，复制时间 `2026-10-11T20:21:06Z`，SHA256 `4eb65f64925498408faeee7eb04b60d7eb8a01c49ddb239f73070d4d282c75a9`；建筑提取 SHA256 `09501385a6e22ba8605abd85886faad38928ea636c9a572865d7ab4c9e0d2f7a`。固定 A 地块是 way/645135612，当前研究抽取 13 个主对象及 link：九个带 A1–A9 地图名的建筑与四组 links。原 A 园区另有停车楼、商城、总站、历史院落和小型服务对象，不全部精修/排除。

| 当前 mapped 对象 | source ID | 本轮状态 |
| --- | --- | --- |
| A1 | way/642355051 | 有限外观候选，26±6m estimated；历史期次未知 |
| A2 | way/642355049 | 有限外观候选，26±6m estimated；历史期次未知 |
| A3 | way/642355052 | 有限外观候选，26±6m estimated；历史期次未知 |
| A4 | relation/6752592 | 有限外观候选，26.5±5m estimated；源无内环 |
| A5 | relation/6752574 | 有限外观候选，28.5±5m estimated；源内环保留 |
| A6 | relation/6752575 | 有限外观候选，28.5±5m estimated；源内环保留 |
| A7 | relation/6750409 | 有限外观候选，28.5±5m estimated；源内环保留 |
| A8 | relation/6750407 | 有限外观候选，28.5±5m estimated；源双内环保留 |
| 西侧 link | way/642355050 | 源转折+架空编织檐/桁架，14.5±4m estimated |
| 北侧两组 links | relation/6752593、6752573 | 源多孔轮廓+架空编织檐/桁架，14.5±4m estimated |
| 东侧 link | relation/6750408 | 源多孔轮廓+架空编织檐/桁架，14.5±4m estimated |
| A9 曲线公共楼 | way/456731145 | **blocker，未建模/未排除基础**；身份/建筑师/现状高度/入口未确认 |

12 替换对象的全部外环/内环与辅助 Overpass 快照精确匹配，13 个研究对象均保留 source version/timestamp；仅允许循环首点与反向，不位移或缓冲。详见 `footprint-correspondence.json`。`measured-plan.json` 为 WGS84 ECEF→ENU 测量结果，其 measured 指 mapped geometry 的计算，不是测绘精度。实际模块使用当前 `city_config` 换算，保留源多边形完整转向；复合体的包围矩形长轴不能替代真实主立面朝向。

## 形体和参数依据

官方项目页面报告 7F、低层分散办公、约20m深/100m长的两条板、0.30m折叠玻璃、2m深铝网檐和总长超过1km的 links。这些是项目级 reported/approximate，不证明当前八栋的真实层数或完整旧新期次。OSM 的6层、min_level2标签记录原样，不自动换算为真实高度。

本候选高度由现状照片6–7个可见幕墙课程、约3.7–4.2m层间比例及屋顶构件估计，结合源足印宽度和官方板式尺寸检查。主楼26–28.5m的±5–6m误差涵盖透视、遮挡、楼层统计口径和现代扩建对应不明；links约6±2m起底、14.5±4m顶，两段可见结构层。主楼多方向照片属于2013项目资料，精确当前每面登记仍 pending，模型只称 reference-informed。

保留真实源内环，不把A5–A8内院或link孔洞封成大方盒。A1–A4源无内环，局部玻璃屋顶条为 **estimated外观**，不是新造实测庭院；地面碰撞仍使用源 occupied 多边形，玻璃条不制造虚假地面通道。

主楼玻璃用0.30m折面和深色窄梃构成，水平白挑檐为1.25±0.6m估计。Links几何包含V型桁架与两层带真实空隙的斜折编织遮阳，2m出檐来自官方 reported；斜折高差2m、网格采样1.6m、支柱/颜色配准为估计。中央两组用既有 `gold` 暖色近似橙色，其余用 `silver`；颜色、粗网格与真实细编织仍有差异，不能称全侧高精度复原。

## 实际观察与 CPU 图

`references/manifest.json` 保存14个官方参考图/照片的 URL、SHA、访问日期和 ©Sadao Hotta 署名。下载 MG_1534 原图时连接断开，没有引用该失败文件；其他本地成功快照完整留存。图片默认仅供研究，未经许可不作为游戏纹理或公开再分发图片。早年其他地址的 Alibaba/Hassell 总部与竞争提案不作为这批西溪源对象的形体依据。

| 参考 | 实际核对范围 | 未证明 |
| --- | --- | --- |
| Alibaba-plan_1F / 2F | 办公板、links、多孔平面、公共空间与地块道路组织；图例1..9为功能 | 无WGS84配准/当前A楼号，不能按数字自动等同 |
| Alibaba-section | 低层层叠、架空links/露台/院落和湿地关系 | 无逐栋现代标高/层高测量，非当前道路DEM |
| MG_6222、MG_1636 | 橙色斜折编织檐、白色板式挑檐、玻璃/立面节奏 | 精确橙色link的每面配准、真实网格丝距 |
| MG_0643 | 湿地一侧整体高度与公共层、另一方向玻璃楼体 | 不从照片反推商业地图坐标/水面标高 |
| MG_0866 | 两层V桁架桥、白色编织檐及支撑/地面空隙 | 全部四组现代link中的功能和每根柱定位 |
| MG_1352 | 铝网编织、镂空遮阳存在 | 许可作发布贴图、GPU现状采样/夜景 |
| 001 | 沿街长立面、折叠低檐/绿色停车/公开层与校园道路 | 每栋名号/完整现代停车空间改造 |

本轮检查俯视、东南、南侧三张 CPU 图及一张独立 link6752593 近景 CPU 图。源布局、孔洞、露台/桁架与两层铝网结构可辨识；图片是 painter 结构示意，无GPU深度/反射/透明材质模拟，面排序可能有遮挡伪影。**四张均不是实机截图，未作为最终视觉通过项。**

## 实际 CPU 验证与预算

```sh
python3 -B docs/hangzhou/research/ali/alibaba-a-round2/check_candidate.py
python3 -B docs/hangzhou/research/ali/alibaba-a-round2/render_cpu_preview.py
python3 -B scripts/landmark_tasks.py check --job docs/hangzhou/research/ali/alibaba-a-round2/task/alibaba-a/job.json --stage evidence-ready --record
```

13组 CPU 检查通过：13源/12排除逐环对应、A9/历史六单元/完整桥网blocker保留、有限坐标及源顶点、无场景导入/导出、单次0.60/游戏高度和标记点恢复、frame成功/异常恢复、11源孔洞屋顶/地面不封闭、凹源填充面积守恒、估计玻璃屋顶不切虚假地面孔、四组架空links地面探针、源共享边立面压制、逐栋估计高度与预算。

首版0.75m网格采样为31,640三角形，超过25,000预算；在保留主楼、两层links、V桁架、全部源轮廓/孔洞的前提下改为1.6m横向网格采样与更少连续织线段，最终 **23,912 triangles、7个现有材质、0新增灯、0照片贴图**。1896条跨檐织线与376桁架单元合并进材质组。CPU生成243地面碰撞片，有限探针不证明所有路线/门洞可走。实际GLB字节/网格、GPU色材质、浏览器、FPS/内存未测。

## 未通过项

A9及历史六单元/当前楼号/各期、完整>1km links功能与位置blocker；准确逐栋高度/层数/地坪；全侧立面/铝网密度/橙白配准；实际门洞/屋顶通行/桥净高与支柱；湿地水体/树木/照明基准；真实字牌夜景；GLB/双排除/碰撞绕行、外侧可达目标/驾驶/存档恢复、昼夜实机三视角与性能仍 pending。不得把校园中心或未核实室内当出生点/可到达点。

任务包保持 `evidence-ready`，`model.json` 没有 GLB/实际Blender构建命令；八项最终验收 unknown。串行导出说明见 `integration-notes.md`，文件哈希见 `integrity.json`。
