# 三桥实体碰撞适配候选

交付 CPU 模块 `scripts/landmarks/qiantang_bridge_collision.py`，规格 `spec.json`。现有三桥模型经独立回放与已导出 GLB 全部 float32 顶点集合对照，实际 24,148 三角、5 材质均相符。返回 7,457 个非空、有明确上下高度的实体包围体，以及 48 道路/1 铁路桥面区域。模块不渲染新桥面或水面，不修改冻结桥模块。

```sh
.venv/bin/python -B docs/hangzhou/research/core/qiantang-bridge-collision-round1/validate_candidate.py
.venv/bin/python -B scripts/landmark_tasks.py check --job docs/hangzhou/research/core/qiantang-bridge-collision-round1/task-bundles/qiantang-bridge-collision/job.json --stage evidence-ready --record
.venv/bin/python -B scripts/landmark_tasks.py check --job docs/hangzhou/research/core/qiantang-bridge-collision-round1/task-bundles/qiantang-bridge-passage/job.json --stage evidence-ready --record
```

前两项实际成功；第三项实际 exit 2，完整通行证据仍有 blocker。`stage-status.json` 与各任务 `evidence-ready-result.json` 保存真实工具结果。未知标高、岸台、引桥及实机接触未改为 pass；没有运行 Blender 或浏览器。

`cpu-validation.json` 记录所有来源/模块/关联 GLB SHA、逐材质顶点对照、实体计数和 CPU 检查。`source-profile-geometry-audit.json` 逐项给 15 条 source road 的原 node、高度、缺实际桥面的位置及差距；`source-profile-summary.json` 是简表和四条之江西岸续路共享节点检查。`negative-controls.json` 给外部 node 高度与刚性原模型不一致、铁路/公路分离、上/下层栏杆、索塔开口探针结果；探针不代表实机 actor 验收。

使用方式、原模块薄杆面积兼容问题、保守包围体局限及父待办见 `integration-notes.md`。`representative-solid-volumes.json` 只保存各类型一个例子；完整非空碰撞由模块 API 生成，未将示例文件当完整资产。来源照片均沿用原 `qiantang-bridges-round2/photo-review.json` 的具名观察记录，未打包或发布照片贴图。
