# 市民中心独立候选交接

已实际生成 Hangzhou round2 独立任务并运行 `evidence-ready --record`，有限核心证据阶段通过。没有 GLB、Blender 场景或游戏浏览器结果，`modelled` / `verified` 待 root 串行集成。此阶段不表示整个建筑群、全部入口或实机外观已经完成。

模块为 `scripts/landmarks/civic_center.py`，参数为本目录 `spec.json`，入口 `build(b,lm,spec,scale=.6)`。`lm.x/lm.z/lm.y` 是游戏单位，源坐标与尺寸经 `city_config.load_city('hangzhou')` / `project()` 换算，物理米只乘`.60`一次；模块在成功和异常路径恢复 `b.frame`，没有 `city_mesh` / `bpy` / 场景导出副作用。现有 `scripts/landmarks/civic.py` 是深圳市民中心，不应混用，也没有改它。

总环体固定源 `relation/4762996` 外轮廓减孔的面积质心 WGS84 `[120.20521943442597,30.248993004078663]`，游戏 EN `[2899.2719607361264,-1663.3214251025686]`。外圈半径约 `97.424..99.306 m`，内圈 `66.784..69.839 m`，角度和所有塔/裙楼足印在 `measurements.json`。固定地图不是现场测绘，平面留`±5m`、方向留`±3°`。高层桥对映射环形足印作极坐标曲率插值，属于有限平滑近似；六塔和四裙楼保留实际源多边形，凹L形上盖采用原生耳切三角化，没有填成包围盒。

建议精确排除13项，本模块实际恢复其上层/地上形体：

| 来源 | 模块中角色 |
| --- | --- |
| `relation/4762996` | 六塔围合总环体 / 高层环形连桥包络 |
| `way/336830558`、`way/336830559`、`way/336830561` | A、B、C弧形塔楼 |
| `way/336830562`、`way/336830564`、`way/336830565` | D、E、F弧形塔楼 |
| `way/336828914`、`way/336828913`、`way/336828912`、`way/336828911` | H、J、K、L低层L形裙楼 |
| `way/582480145`、`way/582480146` | 屋顶花园中心圆穹顶 / 边侧椭圆小体 |

固定OSM字母与现场导览牌布局相互核对。CVU的1..6序号没有自动对应A..F；本轮独立读取了全部六条记录，均为建筑高109.6m、最高使用层99.4m、26层。因此统一高度无需假定序号与字母对应。源塔楼120m与H裙楼80m标签未经核实，不采用。中央源“G”21m宽足印只是照片圆顶小体的形状，不是整个G会议中心/庭园的外边界。

`way/336828917` 与 `way/336828929` 标`layer=-1`，未靠邻近关系加入本对象地上排除；地下结构和运行时显示处理交主集成核对。周边地铁入口、其他相邻楼体不在本模块排除范围。`ground_footprints()` 只提供六塔、四裙楼源多边形和一个半径64m的估计中央会议体保守包络。不能把上层环桥 annulus 投影成地面整环实体，也不能把此包络当精确门洞或花园通行验收。

外观包含六片弧形玻璃塔体、银灰逐层分带/有限竖缝、开放格构冠部、高位封闭环桥，四低L形玻璃裙楼及代表性绿屋顶。中央建有曲面环罩、不规则园地开口、原生圆玻璃穹顶/椭圆小体、弯曲水道和石岸、步道、短台阶、少量树与坐凳。这些景观不是拷贝照片贴图，也不是全部园地测绘。圆罩只环绕花园，桥与罩棚没有封盖中心天空。

最高塔轮廓109.6m是公开`reported`值，未声称实测。玻璃主体终止99.4m±3m、裙楼16m±3m/4层代表性带、连桥底85m与顶92m各±4m、中央平台24m±4m、中央包络半径64m±6m、环罩开口51m±5m及曲面波幅、两小体高度、路径/绿化分布均标`estimated`。85m来自CVU，设计者项目索引称90m；中英文论文85/90口径差异未解决，具体候选底/顶并不代表将两条报道解释成两个实测标高。

实际查看同济供图南向外景、庭院远景/斜俯，LDG设计方环罩/水景/路径近照，独立2023作者西向东WGS84照片和现场导览牌。CVU/LDG拍摄日期未知，重复图没有计作独立方向，LDG设计平面没有当现状测绘。World-Architects直接403和CTBUH论文404没有绕过；不假称读到完整施工图。2009西门下载超时的残片未采用。全部图片临时参考、`bundled=false`，没有发布未授权图像或材质。

纯CPU报告 `cpu-geometry-validation.json`：22,021个导出前三角形，11,185面，10种共享材质，0新灯。FakeB检查了数量、有限非退化面、真实源塔/凹裙楼投影与面积、桥中心留空、单次缩放、`lm.y`游戏基高、移位`lm`保持源锚定、成功/异常`frame`恢复及预算。最高点按测试基高2.5游戏单位为68.26；基高不是现实场地高程。没有GLB大小、最终Blender三角化、draw call或GPU性能结论。

主集成待办：实际GLB导出并绑定当前模块、证据和资产SHA256；核对真实桥底/顶、主塔楼板/幕墙/PBR与夜景；完整G/G1/G2礼仪厅、四裙楼入口和地下/地铁关系；地面高程、中央平台通道/台阶与到达/碰撞；具名俯视、远景、地面高度实机外观及性能。总资产、配置、排除清单、地形和运行时仅由root写入。

实际运行命令：

```sh
python3 docs/hangzhou/research/core/civic-center-round2/measure_civic.py
python3 docs/hangzhou/research/core/civic-center-round2/validate_candidate.py
.venv/bin/python scripts/landmark_tasks.py generate --city-id hangzhou --source docs/hangzhou/research/core/civic-center-round2/catalog.json --place civic-center --agent codex-civic-center-round2 --output docs/hangzhou/research/core/civic-center-round2/task-bundles
.venv/bin/python scripts/landmark_tasks.py check --job docs/hangzhou/research/core/civic-center-round2/task-bundles/civic-center/job.json --stage evidence-ready --record
.venv/bin/python scripts/landmark_tasks.py status --job docs/hangzhou/research/core/civic-center-round2/task-bundles/civic-center/job.json
```

`stage-status.json`是实际状态输出，正式证据与本目录证据精确相同；CPU报告和任务model.json绑定当前模块/spec哈希。正式八项验收仍为unknown，GLB哈希与buildCommand保持null。
