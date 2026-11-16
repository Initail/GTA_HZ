# 灵隐寺五重殿外壳候选

状态：有限范围 `evidence-ready`。独立 B 模块及 CPU 几何契约检查已交付；本轮未启动 Blender、浏览器，未生成 GLB，未通过实机验收。灵隐寺全寺仍未完成。

## 足印与身份

采用主集成固定的 Geofabrik 浙江快照，OSM timestamp `2026-10-11T20:21:06Z`，EPSG:4326。原始 PBF SHA256：`4eb65f64925498408faeee7eb04b60d7eb8a01c49ddb239f73070d4d282c75a9`。building extract SHA256：`09501385a6e22ba8605abd85886faad38928ea636c9a572865d7ab4c9e0d2f7a`。来源和足印遵循 OpenStreetMap ODbL 1.0，保留贡献者署名。

`way195189679` 带 `shop=ticket`，英文名称是寺院售票处；它是独立售票房，不是寺界或大殿。五座轴线殿堂分别采用如下足印，不能由主殿一个盒子代表寺院：

| 殿堂 | OSM way | 高度（真实米） | 高度依据 |
|---|---:|---:|---|
| 天王殿 | 434365023 | 20±6 | estimated，官方照片粗比例 |
| 大雄宝殿 | 434365024 | 33.6 | reported，寺方说明 |
| 药师殿 | 434365025 | 24±7 | estimated，官方照片粗比例 |
| 法堂/直指堂/藏经楼 | 434366739 | 23±6 | estimated，官方照片粗比例 |
| 华严殿 | 434366741 | 23±7 | estimated，屋顶参考不完整 |

第四足印的 OSM 名为“灵隐寺文物展厅”。[寺方展厅说明](https://en.lingyinsi.org/list_271.html)将它设于法堂地下一层、药师殿北侧，结合[法堂顺序](https://en.lingyinsi.org/list_145.html)核对为同一复合楼。整个五殿顺序由[寺方概况](https://www.lingyinsi.org/detail_44_7946.html)确认。坐标锚点为大雄殿 OSM 面积重心 `[120.09667203986709, 30.243079869830463]`。这些小数是对源数据的计算精度，不表示现场测量精度；规划容差取±5米/±3度。

官方资料中的 130 亩与 150 多亩存在差异，无法据此画出地籍边界。`places.geojson` 的“灵隐景区”自然保护区范围也不能作为灵隐寺围墙。全寺边界保留 pending。

## 模型和缩放

`scripts/landmarks/lingyin_temple.py` 接口为 `build(b,lm,spec,scale=.6)`。五殿分别定位，包含三/双重檐、歇山屋顶曲面、飞檐、抬高脊带、柱网、窗门格、基座和匾框，未描摹照片贴图。独立模块不导入 `bpy` 或会重置场景的 `city_mesh`。

本轮沿用 canonical `city_config`：真实建筑尺寸/偏移只乘 0.60 一次；`lm.x/z/y` 已是游戏单位；调用前后的 `B.frame` 恢复。保留 Blender 东/北/上 → GLB Y-up → Babylon 既有方向处理。

五座候选全部暂置于 `lm.y`，相对地坪为零。这只是隔离模型的中性基面，不能称为实景山地或平台高度。所有地面高差、地下层外露、真实台阶及入口由主集成在获得 DEM/路径证据后绑定。未完成这一步之前不能称为完整城市集成通过。

黄色墙面暂用现有 `gold` 材质别名；正式视觉验收前须改为哑光赭黄材质。匾额当前只有几何边框与底板，文字、复杂脊饰、斗栱和彩绘仍 pending。本模块交付的是来源绑定候选，不是最终地标成品。

## 已执行检查

```sh
.venv/bin/python docs/hangzhou/research/core/lingyin-round2/freeze_lingyin.py
.venv/bin/python scripts/landmark_tasks.py generate --source docs/hangzhou/research/core/lingyin-round2/task-catalog.json --output docs/hangzhou/research/core/lingyin-round2/task-bundles --place lingyin-temple --city-id hangzhou --agent landmark_evidence
.venv/bin/python scripts/landmark_tasks.py check --job docs/hangzhou/research/core/lingyin-round2/task-bundles/lingyin-temple/job.json --stage evidence-ready --record
.venv/bin/python docs/hangzhou/research/core/lingyin-round2/validate_cpu.py
```

CPU 检查结果为 11,460 面 / 23,844 三角形（导出前 fan 计数）、6 种现有材质、0 个灯光。有限/nondegenerate、五栋身份、逐栋 WGS84 投影、0.60 单次缩放、基面游戏单位、锚点平移、frame 恢复和暂定资源预算通过。真实 Blender 三角化、实际 GLB 字节数和实机效果尚未测定。

首次冻结脚本因项目根目录索引多一级而失败，已修正；首次 CPU 检查为 25,692 三角形，超过原 25,000 预算，简化窗格重复线后重跑通过。未提高预算、删除形体检查或填写虚假 pass。详见 `attempts.json`。

主集成可串行执行候选导出命令（本轮没有执行）：

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python scripts/build_hangzhou_landmark_candidate.py -- --job docs/hangzhou/research/core/lingyin-round2/task-bundles/lingyin-temple/job.json --spec docs/hangzhou/research/core/lingyin-round2/spec.json --module scripts/landmarks/lingyin_temple.py --output artifacts/cities/hangzhou/landmarks/lingyin-temple-v1
```

## 主集成契约与未通过项

基础楼体和近景立面仅排除 `spec.baseBuildingIdsToExclude` 的五个 ID：434365023、434365024、434365025、434366739、434366741。售票房不排除；其他殿堂未建模，不应被误删。`sourceFeatureIds` 保留 `way/` 前缀以回溯源对象。

整体寺界、辅助殿群、真实山地 DEM/平台/台阶、可达入口、完整背立面、招牌文字、夜景、碰撞、地图到达点和本轮浏览器/性能验收均未通过。stage 保持 `evidence-ready`；待实际 GLB 可检后方可推进 `modelled`。全部八项 `validation.json` 仍为 unknown，不能将 CPU 结果代替实机验收。

`source-claims.json`、`evidence.json`、`spec.json`、`photo-review.json` 与固定 OSM 子集构成新的 round2 包，不修改第一轮报告或哈希。照片只作参考，MIT 代码许可不转授照片版权。
