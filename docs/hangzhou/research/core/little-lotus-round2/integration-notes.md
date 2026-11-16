# 小莲花独立候选交接

本目录与 `scripts/landmarks/little_lotus.py` 由小莲花对象执行者独占。已实际运行任务生成与 `evidence-ready --record`，有限外观/内碗证据阶段通过；没有生成 GLB，`modelled` 与 `verified` 仍待主集成。此阶段不表示全场馆、屋顶运动或实机外观通过。

入口：`build(b, lm, spec, scale=.6)`；spec 为本目录 `spec.json`，`lm.x/lm.z/lm.y` 均为游戏单位。源尺寸保留物理米，使用 `city_config.load_city('hangzhou')` 和 `project()`，只缩放一次。函数在成功与异常路径恢复 `b.frame`，模块没有 `city_mesh`、`bpy`、场景导出或公开资产副作用。`ground_footprints()` 返回固定地图足印的游戏坐标包络；它是保守轮廓，不能表示门洞、通道或精确碰撞验收。

固定 Geofabrik `relation/9874418` 足印的面积质心为 WGS84 `[120.22899373961485, 30.229821337017597]`，Hangzhou 游戏 EN `[4271.811839131474, -2938.510363346632]`。48 点轮廓闭合为49个坐标，平面包络 `139.558 × 139.225 m`，映射面积 `14266.935 m²`。第一外瓣尖角相对东轴 `-176.192°`，24 个外瓣尖保留实际轮廓的角度和半径。地图轮廓未现场测量，平面留 `±5 m`、瓣相位留 `±3°`；源 `height=5` 仅是未核实标签，没有当完整屋盖高度。

基础楼体仅建议排除 `relation/9874418`。`way/626826731` 的顶点均值 `[120.2261784375, 30.2324974375]`，距小莲花质心 `401.735 m`、足印约 `13.163 × 40.973 m`，不在小莲花轮廓内，不是其内碗或屋顶部件，保留。周边半决赛馆、训练馆、其他球场与大莲花不属于本模块。源数据在小莲花质心110m内只找到该 relation，没有按邻近关系删除其他对象。

候选包含24个连续弯曲固定墙/屋面瓣、8个上层曲面瓣、中心开口、低层玻璃环廊、代表性门厅头部、红色上看台与灰色下看台、原生网格网球场线和球网。上层状态为 `open-static`，以机构实际开盖内景为参考；真实屋盖能力的24固定+8可动、逆时针最高45°有官方/运营报道支持。候选曲线不表达真实转轴、45°刚体构型或机械轨迹，`roofAnimationImplemented=false`、`mechanicalAxesVerified=false`。无需在运行时添加屋顶动画玩法。

高度最高点 `40 m ±4 m` 取自运营经理所述约40m屋盖运行高度及照片比例，它不是实测总高。开口半径 `30 m ±5 m`、固定瓣纵横曲线/扭角、上部瓣参数/相位、平台 `5 m ±2 m`、看台层级与门厅均在 spec 中标为 estimated，写明方法与误差。网球比赛矩形按 ITF 规范 `23.77 × 10.97 m` 表达，但现实内场绝对朝向待核验；候选长轴沿北/南留 `±45°`，不能据此声称已校准场地朝向。代表性看台不等于真实10000座逐座模型。

实际查看了机构公开的闭盖俯视、地面不同方向外观、开盖/闭盖内景、红灰看台与官方赛事高位外景，见 `photo-review.md`、抓取记录与 referenceImages。官网CDN拒绝的图片没有绕过或假称已查看；NBBJ临时泳池图没有当现状网球场。许可未知的照片只作参考，全部临时存于 `<TEMP>/little-lotus-research/`，没有发布贴图、第三方模型或 bundled 照片。

纯 CPU FakeB 报告为 `cpu-geometry-validation.json`：19,078 个导出前三角形、9,563 个面、9 种既有共享材质、0 新灯。检查实际源轮廓投影、24+8角色、开口、有限非退化面、一次缩放、游戏基高、移位 lm 锚定、正常/异常 frame 恢复和预算。它不验证 Blender 的最终三角化、GLB 字节大小、PBR金属质感、当前相机外观、物理或帧率。

主集成待办：实际 GLB 导出并绑定当前 module/evidence/artifact SHA256；平台地形高程与连桥/台阶/入口；真实场地轴向、完整观众流线和门洞碰撞；具名俯视/轮廓/地面高度实机外观；夜景及性能。现阶段的共享 silver/concrete/red/blue 材质只是有限近似，金属接缝与真实反射尚待调整。总资产、配置、楼体排除清单、地形和运行时仅由 root 串行修改。

实际命令：

```sh
python3 docs/hangzhou/research/core/little-lotus-round2/validate_candidate.py
.venv/bin/python scripts/landmark_tasks.py generate --city-id hangzhou --source docs/hangzhou/research/core/little-lotus-round2/catalog.json --place little-lotus --agent codex-little-lotus-round2 --output docs/hangzhou/research/core/little-lotus-round2/task-bundles
.venv/bin/python scripts/landmark_tasks.py check --job docs/hangzhou/research/core/little-lotus-round2/task-bundles/little-lotus/job.json --stage evidence-ready --record
.venv/bin/python scripts/landmark_tasks.py status --job docs/hangzhou/research/core/little-lotus-round2/task-bundles/little-lotus/job.json
```

最终 CPU 报告与任务 model.json 绑定当前模块/spec 哈希；`stage-status.json` 为真实状态命令输出。不能用该状态代替具名外观/实机验收。
