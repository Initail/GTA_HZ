# 杭州大剧院独立候选交接

已实际生成 Hangzhou round2 任务并运行 `evidence-ready --record`，有限外部形体证据通过。没有导出 GLB、运行 Blender 或打开游戏浏览器；`modelled` / `verified` 待 root 集成，正式八项验收仍为unknown。此范围不代表内部三厅、完整场地水景或当前入口通行已经完成。

调用 `scripts/landmarks/grand_theatre.py` 的 `build(b,lm,spec,scale=.6)`，spec为本目录 `spec.json`。模块只用共享 B 的`face`接口组合原生闭曲面、管状构件和三角形；无 `city_mesh`、`bpy`、场景导出、副作用材质创建或图片纹理。函数正常/异常均恢复 `b.frame`。坐标唯一使用 `city_config.load_city('hangzhou')` / `project()`；源WGS84与物理米在本地转换后只缩放一次，`lm.x/lm.z/lm.y`保持游戏单位。保留既有GLB方向处理。

主足印固定 `way/626838819`，面积质心 WGS84 `[120.21089643393236,30.24680828230344]`，游戏 EN `[3227.0169000834103,-1808.6365420421012]`；包络 `166.220 × 164.201m`。前圆厅映射包络 `48.995 × 48.411m`，主月体质心指向前厅质心的方位约 `218.914°`，与原论文图2“西南立面”吻合。平面±5m、方向±5°是未现场测量的地图允许误差，不是地籍精度。

精确建议排除14个实际覆盖要素：

| 要素 | 候选角色 |
| --- | --- |
| `way/626838819` | 低层底座/整个主体地面保守足印 |
| `way/626838817` | 月形主体最低水平控制轮廓 |
| `way/626838818` | 前侧低翼/大厅与檐篷包络 |
| `way/626838816` | 前侧倒锥圆厅的映射计划轮廓 |
| `way/626826745` 至 `way/626826754` | 十个嵌套月形控制轮廓；以连续曲面恢复，不作为十幢分散楼体 |

保留 `way/582256524`、`way/626826761`、`way/626838543`、`way/626838908`、`way/600800340`、`way/600800341`、`way/600800342`。它们没有凭邻近加入本对象替换范围，国际会议中心及周边塔楼由各自对象负责。`ground_footprints()` 返回 `626838819` 源多边形投影一个保守地面包络；高位壳体、外阶梯/门洞和水池/平台通行另核验。

主高度46.4m有实际读取的原论文支持：田森源等《杭州大剧院风压分布的风洞试验研究》，《实验力学》2004年19卷1期。官网下载PDF SHA256 `8b15104df197d19ecd104eb72064ed8843302c6ffa0dc33d2d78741e97b28c0e`，见 `wind-paper-review.json`。Poppler缺Adobe-GB1映射导致中文掉字，改用系统Quartz只读渲染首整页，实际读到总高度46.4m、平面和西南立面；没有将乱码当尺寸。它是`reported`设计/风洞研究高度，保留±1m报告/候选允许差异与真实地面基准未知，未声称现场测量。

源主足印`height=3`不代表整栋高度。十个嵌套部件存在`height < min_height`的非标准组合，无法直接当OSM标准总高/实测层标高；只采用地理控制轮廓及其排序，中间高度按公开46.4m最大值与实际照片层次分配，全部 `estimated ±4m`。这些轮廓沿NW尖端与SE尖端拆为内/外曲线、按弧长一致采样，形成倾斜玻璃面与连续银灰金属背壳。它不是单个半球或各级方盒堆砌。

前圆厅原生几何为两级向上外扩玻璃倒锥，中间一处外扩腰口、上部回收后再外扩，以及较宽浅盘悬挑屋顶；最高前厅约35.7m、控制高±4m/檐口±4m、径向比例±15%均为实景照片比例估计。低翼10m±2m、底座3m±1.5m、代表性32级外阶梯/栏杆的尺度和落位±25%、金属背侧有限横向排风条带、倾斜点式幕墙网格也明确估计。精确索/杆结构、幕墙分格、入口清净尺寸与内部剧场不在此验收范围。

实际查看Carlos Ott原项目正面、侧前、内部照片，合作设计方PETROFF外观/幕墙近景，以及独立2012作者外景、2019作者从市民中心高位图和2019前厅/水池近景。相同Ott/Petroff照片不重复计方向，旧拍摄/完成日期不当当前2026全侧条件。原图超时残片未采用，使用重新完整读取的Ott原图和Commons API明确给出的公开缩略图。无 bundled 照片、复制模型、临时活动横幅/气球或未知字牌。主创“钛屋面”与合作设计方“铝双曲面”口径未核完整材料层，用共享silver作有限银灰近似，未声称PBR或实际材质施工表已验证。

**水面管线边界：** 本模块0个水面、没有使用water材质。实际高位图显示浅水池环绕下沉露天剧场，池岸曲线和观众绕池路线可辨，但固定water/places在相应site bbox没有独立水池面/POI；bbox只碰到钱塘江整体面/中心线，不能替代池边。`water-boundary-review.json`将精确WGS84池界保留pending。水池、露天剧场及水中雕塑/喷泉由root基础水管线与后续对象处理，禁止叠加另一张候选水片。

纯CPU FakeB报告 `cpu-geometry-validation.json`：14,001个导出前三角形、7,128面、6种共享材质、0新增灯。检查实际源足印和凹多边形上盖面积、11个一致月形控制计划、主高度包络、两级倒锥缩放层次、无水面、有限非退化三角扇、单次缩放、游戏基高、移位lm仍锚定源计划、成功/异常frame恢复及预算。最高点测试基高2.5游戏单位时约30.381，部分有限杆件半径会比46.4m参考表面稍高但在±1m允许内。CPU不证明最终Blender三角化、GLB字节数、可见材质、GPU/碰撞或帧率。

主集成待办：实际GLB导出并绑定当前源码/证据/资产SHA256；具名俯视、道路高度与远景核对；完整玻璃反射/钛色/金属接缝/夜景；当前两侧观众路线与10道历史小门、前低厅、平台和外阶梯实际高程/入口/碰撞；水池精确边界及露天剧场；实机浏览器与性能。共享构建器、配置、总资产、排除清单、地形与运行时仅由root串行写入。

实际命令：

```sh
python3 docs/hangzhou/research/core/grand-theatre-round2/measure_theatre.py
python3 docs/hangzhou/research/core/grand-theatre-round2/validate_candidate.py
.venv/bin/python scripts/landmark_tasks.py generate --city-id hangzhou --source docs/hangzhou/research/core/grand-theatre-round2/catalog.json --place grand-theatre --agent codex-grand-theatre-round2 --output docs/hangzhou/research/core/grand-theatre-round2/task-bundles
.venv/bin/python scripts/landmark_tasks.py check --job docs/hangzhou/research/core/grand-theatre-round2/task-bundles/grand-theatre/job.json --stage evidence-ready --record
.venv/bin/python scripts/landmark_tasks.py status --job docs/hangzhou/research/core/grand-theatre-round2/task-bundles/grand-theatre/job.json
```

`stage-status.json`为实际状态查询输出，正式证据为本目录证据精确副本，CPU报告和model.json绑定当前模块/spec哈希。没有实际GLB，artifact SHA与buildCommand保持null。
