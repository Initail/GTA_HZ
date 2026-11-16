# 独立建模任务：菜鸟总部附属及产业楼群足印调查（当前覆盖阻塞）（cainiao-annex）

执行者标签：codex-ali-evidence。标签只用于派工，不表示任何应用已经安装或启动。
项目根目录：<LOCAL_HOME>/Documents/ChatGPT/GTA_HZ
任务文件：docs/hangzhou/research/ali/cainiao-annex-round2/task/cainiao-annex/job.json

先读 `skills/landmark-reconstruction/SKILL.md` 和 `docs/landmarks/agent-workflow.md`，再读 job.json 的 sourceRecord、evidence.json 以及已有对象模块。

目标：依据公开地图、官方/建筑师资料和可核查照片，提高这一对象的实际尺度、朝向、轮廓和组成关系；先形体、后立面细节。不得把估计标成实测，不得凭地点名字猜坐标。照片默认只作观察参考，不作为贴图发布。资料不足时保留 pending，并明确缺什么。

仅写 job.json 中 ownership.workerFiles / workerDirectories 指定的位置。共享城市加载、总构建器、总清单、地形准备和其他对象归主集成人员；发现需要改动时在本任务目录写 integration-notes.md，不直接改共享文件。已有对象模块须保留接口并明确本任务唯一写入者。

交付顺序：
1. 补全 evidence.json：地点身份、EPSG:4326 坐标、带来源与不确定度的形体观察；必需观察类别为 footprint, height, orientation, silhouette。
2. 运行 `.venv/bin/python scripts/landmark_tasks.py check --job 'docs/hangzhou/research/ali/cainiao-annex-round2/task/cainiao-annex/job.json' --stage evidence-ready --record`。失败时修复证据或报告阻塞，不跳过。
3. 仅在证据门槛真实通过后，在 scripts/landmarks/cainiao_annex.py 中编写可重复构建的对象模块，使用 scripts/city_mesh.py 的 B API；只有经主集成确认的调用接口才可接入。若尚无独立导出器，交付模块和参数并等待主集成导出，不能虚构 GLB。
4. 真实米制参数保留在证据中。城市坐标契约为 {"cityId": "hangzhou", "sourceCRS": "EPSG:4326", "originWGS84": [120.155, 30.274], "blenderAxes": ["east", "north", "up"], "horizontalScale": 0.6, "verticalScale": 0.6, "projection": "wgs84-local-equirectangular", "eastMetresPerDegree": 96220.11856153939, "northMetresPerDegree": 110857.07311230902, "cityConfigSha256": "94df90b13a4fd9092944aea938eed3cb03f0f3ff3b9a49790eac8a3546216b24"}；Blender 为 east/north/up，只缩放一次。旧 UTM 与商业地图坐标不能直接混入当前游戏坐标；人物、车辆和虚构室内已用游戏单位时不再缩放。
5. 填 model.json 的真实文件路径、模型 SHA256、sourceModuleSha256，执行 modelled 检查。任务预算：{"status": "provisional", "maxTriangles": 25000, "maxMaterials": 12, "maxBytes": 8388608, "maxTextureEdge": 2048}；这是暂定增量预算，不能据此声称已通过性能验收。
6. 与主集成协作生成至少俯视、远景轮廓、街面高度三个实机视角，记录逐项验收及性能数据到 validation.json。每项必须有可读取证据路径、reviewedBy、reviewedAt。verified 仅由主集成人员结合实机复核推进。

本任务的 evidence.json / model.json / validation.json 模板内 unknown 和 null 必须据实处理，不能批量改为 pass。所有模型更改都会使旧 SHA256 验收失效。若采用总 GLB，由主集成人员设置 artifactMeshPrefix 为 detail_cainiao-annex_ 来核对该对象网格；工具保留整包大小与总面数，不伪造独立GLB。

返回：改动文件、来源支持了什么、仍属估计的参数、构建/验证命令及结果、待集成事项。不要声称已调用 Grok、Cursor、ChatGPT 或 Codex 的另一个实例，除非确有调用结果。
