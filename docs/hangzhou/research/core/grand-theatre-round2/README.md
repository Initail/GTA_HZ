# 杭州大剧院 round2

来源绑定的有限外部候选：连续月形金属背壳与倾斜玻璃面、两级倒锥前圆厅/浅悬挑顶、实际低翼包络及代表性外阶梯。实际 `evidence-ready --record` 已通过；没有GLB，`modelled` / `verified`待主集成。

- `spec.json`、`evidence.json`：14个精确覆盖ID、原论文reported46.4m高度与明确估计/误差。
- `photo-review.md`、抓取记录、`wind-paper-review.json`：实际多向看图和原论文复核，照片/PDF图不打包为纹理。
- `measure_theatre.py`、`measurements.json`、`geofabrik-theatre-features.geojson`：固定源测算；地图不等于现场测绘。
- `scripts/landmarks/grand_theatre.py`：纯B API模块，无场景/导出副作用。
- `validate_candidate.py`、`cpu-geometry-validation.json`：14,001三角形、6材质、0新灯、0water面的纯CPU检查。
- `water-boundary-review.json`：水池精确WGS84边界pending，基础水面管线负责，不加候选水片。
- `task-bundles/grand-theatre/`、`stage-status.json`、`integration-notes.md`：真实任务状态、主集成调用及待办。

完整内部三厅、露天剧场/水池、当前入口/平台/地形/碰撞、材质夜景、实际GLB/具名视觉/浏览器和性能仍pending。
