# 雷峰塔有限外观候选交付

独占模块：`scripts/landmarks/leifeng_pagoda.py`。
规格：`docs/hangzhou/research/core/leifeng-round2/spec.json`。
正式任务：`docs/hangzhou/research/core/leifeng-round2/task-bundles/leifeng-pagoda/job.json`。

已实际通过 `landmark_tasks.py check --stage evidence-ready --record`；有限主范围是宽八角外基座、五层塔身、五道主屋檐、四道平座腰檐和塔刹。全景区、入口精细、室内、地形和最终验收在 pendingSubscopes。没有实际 GLB，任务没有推进到 modelled / verified。

## 接入契约

- 使用 `build(b,lm,spec,scale=.6)`；不导入 `city_mesh`，不初始化或导出场景，调用者 finish/export。
- `lm.x/lm.z/lm.y` 是已经缩放的游戏坐标与基面；`lm.lon/lm.lat` 若传入必须为 WGS84。位置来自 `load_city('hangzhou')` 和 `project()`。`lm` 水平锚点与地理锚点要一致。
- 模块恢复共享 `b.frame`，包括异常中断；全部形体米制参数缩放一次。Blender 东/北/上，保留既有 GLB Y-up 与根节点方向处理。
- 中心 WGS84：`[120.14501471758403,30.23388616474085]`；当前 config 投影为 `[-576.4710347609545,-2668.141420883383]` 游戏东/北。后续由相同配置重新投影，不复制旧深圳或研究 UTM 坐标。
- 基础楼体排除唯一 `way/229726934`。地图足印约 `58.069×56.260m`、`2663.049m²`，含宽基座/平台的解释仍是估计，不能套给上部塔身。
- `ground_footprints()` 返回保守的八角外部包络；没有门洞可穿行、台阶碰撞、可站立露台或到达点验收。入口中轴和东阶道有来源，碰撞/导航应由集成人员复核后接入。
- 共享材质仅 `concrete,darkglass,gold,roof,steel`；无新照片贴图、字体、纹理或灯。铜饰及暗瓦观感仍需当前材质/光照下视觉检查。
- 总构建器对象名建议 `detail_leifeng-pagoda`，以便任务检查匹配 `artifactMeshPrefix: detail_leifeng-pagoda_`。若集成 GLB 命名不同，要统一真实对象前缀，不能借其他网格过门。

## 当前证据与估计

固定 Geofabrik PBF SHA256：`4eb65f64925498408faeee7eb04b60d7eb8a01c49ddb239f73070d4d282c75a9`；本轮测量脚本重新核对该文件及三个裁切 GeoJSON 哈希。

设计师来源与真实参考图支持八角五层、平座腰檐、现代钢结构铜饰和 9.7m 遗址保护罩。文旅约 71m 高度保留 ±1m，不采用未验证 OSM 71.7m 标签或二手材料 71.679m 作实测。文旅页「五面八层」与 OSM 英文别名错误有明确冲突处理。

主层标高 ±2m、屋檐/柱网半径 ±15%、基座收分系数 ±.06、构件节奏均是照片/设计剖面参考估计。48m 是设计师所述最大柱网跨度，未当成足印径长。地面高程、完整入口、铭牌、斗拱细纹、屋瓦曲率和夜景光源继续 pending。

## 已实际运行

`python3 docs/hangzhou/research/core/leifeng-round2/measure_leifeng.py`

`python3 docs/hangzhou/research/core/leifeng-round2/validate_candidate.py`

`.venv/bin/python scripts/landmark_tasks.py generate --city-id hangzhou --source docs/hangzhou/research/core/leifeng-round2/catalog.json --place leifeng-pagoda --agent codex-leifeng-round2 --output docs/hangzhou/research/core/leifeng-round2/task-bundles`

`.venv/bin/python scripts/landmark_tasks.py check --job docs/hangzhou/research/core/leifeng-round2/task-bundles/leifeng-pagoda/job.json --stage evidence-ready --record`

FakeB 当前统计：17,710 triangles，8,499 faces，5 材质，0 灯。71m 形体最高处相对基面为 42.6 游戏单位。通过有限顶点、非退化扇三角形、源足印投影、偏移锚点、半比例模型、成功/异常 frame 恢复与无场景导入检查。

这些是 CPU 原语检查，不能替代 Blender 导出后的真实三角形/文件大小、当前 GLB 具名外观、入口/绕行碰撞、浏览器错误和 FPS。主集成人员统一执行后再填写 model.json / validation.json。
