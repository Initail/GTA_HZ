# 杭州市民中心 round2

有限核心候选：六塔真实地图平面与公开109.6m/26层轮廓、上部环形桥、四L形裙楼、中央曲面环罩与开放屋顶花园、两映射屋顶小体和代表性水景/步道。真实 `evidence-ready --record` 已通过；尚无GLB，`modelled`/`verified`待主集成。

- `spec.json`：尺寸、估计误差与13个精确替换ID。
- `evidence.json`、`photo-review.md`：来源、实际看图记录和未完成范围。
- `measure_civic.py`、`measurements.json`、`geofabrik-civic-features.geojson`：固定源环体/组件测算；地图不等于现场测绘。
- `scripts/landmarks/civic_center.py`：独立纯B API模块，`build(b,lm,spec,scale=.6)`。
- `validate_candidate.py` / `cpu-geometry-validation.json`：22,021三角形、10种共享材质的纯CPU检查。
- `task-bundles/civic-center/`、`stage-status.json`：正式任务与真实阶段状态。
- `integration-notes.md`：主集成调用、排除范围、桥标高冲突、待办和运行命令。

桥85/90m口径、裙楼/中央平台/环罩及花园细部均保留明确估计。完整G/G1/G2、地下道、地形高程、全部入口/碰撞、真实材质/夜景、GLB/具名视觉/浏览器/性能仍pending。照片没有bundled或贴图；既有深圳 `scripts/landmarks/civic.py` 未改。
