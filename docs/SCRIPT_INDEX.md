# 脚本索引

日常开发先用仓库根的 npm 命令。下表用于修改数据、建模和复核候选。多数脚本按路径推导仓库根，仍有部分工具把工作目录或阶段编号写死。检查入口参数与源码中的路径常量后再执行。名称为 `check_*`、`validate_*` 的脚本也可能写报告或启动浏览器。

## 地理数据与对象证据

| 阶段 | 入口 | 输入、产物 |
| --- | --- | --- |
| 城市配置 | [city_config.py](../scripts/city_config.py) | 读取 `config/cities/` 与 `config/active-city.json`。带 `--generate-ts` 会重写 `src/city-profiles.generated.ts`。 |
| 固定 OSM 快照 | [download_hangzhou_osm.py](../scripts/download_hangzhou_osm.py)、[extract_hangzhou_osm.py](../scripts/extract_hangzhou_osm.py) | 下载采用 `python3 -m scripts.download_hangzhou_osm`。提取需要 PBF 与同目录来源清单，输出地理图层、来源节点、通行标签以及提取清单。 |
| 逻辑骨架 | [prepare_hangzhou_city.py](../scripts/prepare_hangzhou_city.py)、[prepare_hangzhou_identities.py](../scripts/prepare_hangzhou_identities.py)、[prepare_hangzhou_map_places.py](../scripts/prepare_hangzhou_map_places.py) | 处理提取地理数据，以及地点目录与身份记录，生成城市、路网和地图候选。 |
| DSM、高程与道路 | [fetch_hangzhou_dsm.py](../scripts/fetch_hangzhou_dsm.py)、[prepare_hangzhou_terrain.py](../scripts/prepare_hangzhou_terrain.py)、[prepare_hangzhou_road_levels.py](../scripts/prepare_hangzhou_road_levels.py)、[prepare_hangzhou_geography.py](../scripts/prepare_hangzhou_geography.py) | 固定栅格和道路数据，生成高程采样、道路层级、地理清单。分别记录地面、桥面、隧道与高程基准。 |
| 地标任务 | [landmark_tasks.py](../scripts/landmark_tasks.py)、[研究入口](RESEARCH.md) | `generate --city-id hangzhou` 可配 `--source`、`--output`、`--place` 生成任务。先跑 `status --job`，再用 `check --job --stage evidence-ready` 核对来源。仅在任务副本使用 `--record`。 |
| 权限与到达 | [bind_hangzhou_road_access.py](../scripts/bind_hangzhou_road_access.py)、[prepare_hangzhou_access_arrivals.mjs](../scripts/prepare_hangzhou_access_arrivals.mjs)、[apply_hangzhou_access_arrivals.py](../scripts/apply_hangzhou_access_arrivals.py) | 按 OSM 道路身份处理路权，依据路网生成玩法点到达候选，接入前核对停车和步行衔接。 |

## 单体建模与分层接入

| 阶段 | 入口 | 输入、产物 |
| --- | --- | --- |
| 对象模块与 Blender 网格 | [landmarks/](../scripts/landmarks/)、[city_mesh.py](../scripts/city_mesh.py)、[build_hangzhou_landmark_candidate.py](../scripts/build_hangzhou_landmark_candidate.py) | 模块实现 `build(B, lm, spec, scale)`，常用接口为 `B.face`、`box`、`tube`、`loft`、`footprint`。Blender 导出器读取通过证据门槛的 job 与 spec，向新候选目录写 GLB 和交付记录。 |
| 定位与模型记录 | [prepare_hangzhou_placements.py](../scripts/prepare_hangzhou_placements.py)、[place_hangzhou_landmark_candidate.mjs](../scripts/place_hangzhou_landmark_candidate.mjs)、[record_hangzhou_candidate.py](../scripts/record_hangzhou_candidate.py) | 以地理表面和对象库存计算定位，绑定高程基准、定位输入、源模块和实际 GLB。历史模型记录工具生成的命令使用 macOS Blender 路径。 |
| 地标增量 | [merge_hangzhou_landmarks.mjs](../scripts/merge_hangzhou_landmarks.mjs)、[prepare_hangzhou_detail_packet.mjs](../scripts/prepare_hangzhou_detail_packet.mjs)、[prepare_hangzhou_detail_collisions.py](../scripts/prepare_hangzhou_detail_collisions.py) | 依据模型库存、地基与排除 ID 准备模型、碰撞和地标清单。检查地标范围内基础楼体和近景立面都已排除旧实例。 |
| 整理物理地面 | [prepare_hangzhou_site_input.py](../scripts/prepare_hangzhou_site_input.py)、[integrate_hangzhou_floor_candidates.py](../scripts/integrate_hangzhou_floor_candidates.py)、[integrate_hangzhou_scene_inputs.py](../scripts/integrate_hangzhou_scene_inputs.py)、[build_hangzhou_site_terrain.py](../scripts/build_hangzhou_site_terrain.py) | 输入来源道路、台阶、地形切口和对象占用合同。包括闲富路、城市阳台和桥面历史输入。输出新的物理和渲染候选，由主集成确认同一高度基准。 |
| 灵隐步道 | [fit_hangzhou_path_to_rendered_ground.py](../scripts/fit_hangzhou_path_to_rendered_ground.py)、[stage_hangzhou_site_paths.mjs](../scripts/stage_hangzhou_site_paths.mjs)、[audit_hangzhou_path_render_contact.mjs](../scripts/audit_hangzhou_path_render_contact.mjs) | 步道贴合到实际渲染地面，保留走面、通行源及增量哈希。[历史安装器](../scripts/install_hangzhou_path_candidate.mjs)默认写入旧 v15 候选，移植路径前只参考其输入与校验合同。 |
| 渲染网格和立面 | [prepare_hangzhou_render_meshes.py](../scripts/prepare_hangzhou_render_meshes.py)、[build_hangzhou_render_candidate.py](../scripts/build_hangzhou_render_candidate.py)、[build_hangzhou_facades.py](../scripts/build_hangzhou_facades.py)、[optimize_hangzhou_candidate.mjs](../scripts/optimize_hangzhou_candidate.mjs) | 将待接入的路面、地形、模型、立面分开准备和压缩。核对渲染面与碰撞面一致、网格预算和纹理来源。 |
| 城市生活对象 | [prepare_hangzhou_leisure.py](../scripts/prepare_hangzhou_leisure.py)、[prepare_hangzhou_canopy.py](../scripts/prepare_hangzhou_canopy.py)、[prepare_hangzhou_bus_service.mts](../scripts/prepare_hangzhou_bus_service.mts) | 湖畔活动、树冠与公交为不同候选。替换前确认玩法点和样式均基于同一城市配置。公交候选有数据及 CPU 测试，整条公交线路的运行接入仍待验收。 |

## 分块、测试与发行

| 阶段 | 入口 | 输入、产物 |
| --- | --- | --- |
| 数据与 GLB 切块 | [split_hangzhou_json.mjs](../scripts/split_hangzhou_json.mjs)、[partition_hangzhou_glb.mjs](../scripts/partition_hangzhou_glb.mjs)、[hangzhou_stream_glb.mjs](../scripts/hangzhou_stream_glb.mjs)、[finalize_hangzhou_stream_role.mjs](../scripts/finalize_hangzhou_stream_role.mjs) | 按角色生成分块、纹理和哈希清单。GLB 工具用文件区间提取输入，避免把整城几何读进单个缓冲。 |
| 流式高级候选 | [build_hangzhou_lod_tile.mjs](../scripts/build_hangzhou_lod_tile.mjs)、[build_hangzhou_stream_pack.mjs](../scripts/build_hangzhou_stream_pack.mjs)、[index_hangzhou_stream_packs.mjs](../scripts/index_hangzhou_stream_packs.mjs) | 独立的远景和混合物理包试验。匹配候选所需的输入版本再跑，不同实验的包索引不可混用。 |
| CPU 几何与数据 | [check_hangzhou_skeleton.mjs](../scripts/check_hangzhou_skeleton.mjs)、[check_hangzhou_detail_packet.mjs](../scripts/check_hangzhou_detail_packet.mjs)、[check_hangzhou_closed_glb.mjs](../scripts/check_hangzhou_closed_glb.mjs)、[check_hangzhou_staged.mjs](../scripts/check_hangzhou_staged.mjs) | 核对路网连通、地标及分块的绑定合同、闭合实体和候选资源。报告要关联本次输入及哈希。 |
| 自动回归 | [tests/](../tests/)、[夹具来源](../tests/fixtures/README.md) | `npm test` 运行杭州回归，读取从 Release 解出的 `public/`。测试涵盖物理、流式范围与候选接口。 |
| 历史浏览器候选 | [check_hangzhou_demo.mjs](../scripts/check_hangzhou_demo.mjs)、[check_hangzhou_bicycle_demo.mjs](../scripts/check_hangzhou_bicycle_demo.mjs)、[stage_hangzhou_demo.py](../scripts/stage_hangzhou_demo.py) | 这些入口绑定旧资产结构、端口或 Playwright 场景。针对当前实机验证时，以现行工程入口重建场景和观察目标。 |
| 当前 Release | [根 package.json](../package.json)、[资产来源及署名](../assets/ASSET-CREDITS.md) | 运行 `npm run assets:fetch`、`npm run assets:verify` 和 `npm run build`。历史 [finalize_hangzhou_demo_manifest.py](../scripts/finalize_hangzhou_demo_manifest.py) 面向早期试玩目录。 |

## 深圳上游工具

[rebuild_city_assets.mjs](../scripts/rebuild_city_assets.mjs) 的 `--plan`、[prepare_landmark_terrain.py](../scripts/prepare_landmark_terrain.py)、[build_landmark_details.py](../scripts/build_landmark_details.py)、[optimize_landmark_details.mjs](../scripts/optimize_landmark_details.mjs)、[validate_landmark_details.py](../scripts/validate_landmark_details.py) 保留深城纪流程。它们需要深圳坐标、`public/city/` 资产与对应地理源。用于了解建模合同或在完整的深圳基线上运行。当前 `npm run assets` 使用杭州 Release 的资产入口。

[上游测试](../tests-upstream/)与 [UE5 试验](../ue5/README.md)保留迁移证据和实验入口。相关历史资产可能需要单独恢复，对比时记录缺失输入。部分恢复、角色、载具和浏览器脚本以旧运行目录及本机可执行文件为前提。
