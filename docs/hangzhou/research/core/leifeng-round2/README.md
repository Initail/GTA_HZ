# 雷峰塔 round2

此目录为来源绑定的有限外观候选和 CPU 检查，不是全对象完成或实机验收。

- `evidence.json`：来源、数字地图测量、逐图实看、冲突与不确定度。
- `spec.json`：候选参数；所有未实测尺寸逐项保留估计误差。
- `measurements.json` / `geofabrik-leifeng-features.geojson`：固定快照足印与南/东访问线。
- `photo-review.md`：南侧正面、湖上北/东北方向、设计剖面有限复核。
- `cpu-geometry-validation.json`：真实 FakeB 结果和模块/规格 SHA256。
- `task-bundles/leifeng-pagoda/`：以 `--city-id hangzhou` 实际生成的阶段契约；仅 evidence-ready。
- `integration-notes.md`：主集成入口、排除 ID、尺度、pending 和实际执行命令。

唯一对象模块为 `scripts/landmarks/leifeng_pagoda.py`。没有写公共资产、共享运行时、总清单或城市配置；没有启动 Blender 或游戏浏览器。远端照片只作临时研究参考，没有复制到仓库或 public，也没有作为贴图使用。
