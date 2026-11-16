# RC3 开源工程验证

本轮开始于 2026-11-15，发布验证延续至 2026-11-16。源码来自 RC2，公开资产采用原创替代。具体远程提交以发布 tag 为准。

## 已执行

- 新目录 `npm ci`：44 个锁定包安装成功；Babylon 2,213 份声明中 158 文件只归一化 import，0 stub。
- `npm test`：412 项通过、0 失败、0 跳过；约 67 秒。含真实地理夹具、上游回归与当前输入重新计算的八段湖畔路线。
- `npm run typecheck`：完整严格类型检查通过。
- `npm run test:tools`：3 项资源解包/完整性保护测试通过。
- 原创角色/坦克静态检查与 Babylon NullEngine 实际导入通过；骑手行走动画和咖啡员工独立骨骼已校验。

Production build passed, including full typechecking and verification of 10,793 runtime files. A browser test found a missing Meshopt decoder in the initial export; it was restored and a focused regression passed. The current full suite therefore contains 413 tests (412 full-suite passes plus the new decoder test locally; remote CI result is recorded below when available).

The isolated Chrome software-WebGL smoke test passed: manual startup, current main-city rendering, real keyboard driving (0.3366 game units, observed speed 2.2408), keyboard braking, map capture, and loading the original public rider into walking mode. No missing resources or uncaught page errors were observed. This short software-rendered test is not a hardware performance benchmark, a full driving route, or landmark acceptance.

The first browser attempt failed on the missing decoder. A later input attempt ran before loading had released its input guard; the harness now waits for reveal and focuses the canvas. These failures were retained locally rather than counted as passes.

[Machine-readable result](browser-rc3.json) · [Welcome](images/welcome.png) · [Map](images/map.png) · [Walking](images/walking.png). Screenshots: GTA_HZ rendering; map data © OpenStreetMap contributors / ODbL, artwork credits in THIRD_PARTY_NOTICES.md.

Remote download and CI verification remain to be recorded after publication.

## 未覆盖

全部任务/模式、公交整线、指定地标视觉终审、中高画质和长时间稳定性仍未通过当前版本的完整实机验收。NullEngine 不是 GPU 或外观验收。旧 RC2 驾驶结果仅为历史记录。历史录制工具未完成杭州迁移，保留源码且不随默认生产构建发布。
