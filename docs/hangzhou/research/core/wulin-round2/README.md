# 武林广场 round2

来源绑定的有限近区广场与八少女喷泉候选。正式任务仅 evidence-ready；没有实际GLB或实机验收。

- `spec.json` / `evidence.json`：参数、来源、逐图观察、估计方法和待核实范围。
- `photo-review.md`：2025南北地面、2026高位与带WGS84 GPS现状照片复核。
- `coordinate-crosscheck.json`、原始OSM API/Commons元数据：定位交叉核验，避免仅凭标签或坐标记忆。
- `measurements.json` / `geofabrik-wulin-features.geojson`：固定映射广场足印与喷泉POI。
- `cpu-geometry-validation.json`：纯FakeB实际结果，绑定当前源码/规格SHA256。
- `task-bundles/wulin-square/`：正式阶段契约，未伪造GLB或八项验收。
- `integration-notes.md`：接入接口、开放广场碰撞边界、材质和后续验证。

唯一对象模块 `scripts/landmarks/wulin_square.py`。未改共享城市/运行时/资产/配置，未启动Blender或游戏浏览器。照片只留临时参考缓存，没有当贴图或发布资源。
