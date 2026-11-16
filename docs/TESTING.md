# 验证与验收

## 自动检查

```sh
npm ci
npm run assets:fetch
npm test
npm run test:tools
npm run typecheck
npm run build
npm run docs:check
npm run release:check
```

`npm test` 执行当前 `tests/*.test.ts`，串行避免真实资产解码相互争用。夹具来源见 [tests/fixtures](../tests/fixtures/README.md)。湖畔八段路线在当前源码和数据上按顺序重新计算，校验前链哈希、连贯性、步行支撑与路线结果，失败报告留在 `artifacts/test-route-evidence/`。这是 CPU 物理/路线检查，不是浏览器输入验收。

`tests-upstream/` 保留迁移前完整测试源作对照，其中深圳专属路径/参数未全部接到本仓当前命令；`tests/upstream-*.test.ts` 是已移植、默认执行的有意义上游回归。新增迁移必须说明原断言如何对应真实杭州数据，不能批量删失败测试。

原创资产单独检查：`node tools/original-assets/check-assets.mjs`、`node tools/original-assets/check-babylon.mjs`。后者使用 NullEngine 真正导入骨骼/动画，验证实例独立性与节点契约，仍不证明 GPU 材质/外观。

## 实机矩阵

按风险选择当次范围，但项目最终验收需覆盖：

1. 冷启动、加载、低/中/高画质、context lost 恢复、内存/帧时和长会话。
2. 真正键盘驾驶/刹停/接触反馈、步行跑步、第一第三人称、上下车；坦克/无人机/飞机/弹药/碰撞/爆炸。
3. 地图搜索、路线、自动驾驶、观景、快速移动、收藏和刷新恢复；跨江与高架连接、园区入口、车行/步行路权。
4. 三职业六合约、升级、关系、三段顺路故事、《最后一单》两条分支、重复结算防护。
5. 咖啡馆门口/地板/墙体/相机/角色互动；自行车/游船/钓鱼与原模式互斥。
6. 每个地标的俯视、街面、远景，昼夜表现、来源对照、排重、碰撞、到达点和预算。

调试传送可用于定位镜头，但需单独记录，不能计入真实驾驶/任务完成。性能报告记录设备、浏览器、画质、版本/资产哈希、冷暖态、采样时间、平均及高分位帧时。应用进程族 RSS 不等于页面专属内存；历史 FPS 不用于当前结论。

只开一个重型 GPU 检查；不与 Blender 并行。发生系统级异常时停止重复压力试验，记录失败，不通过调高退出线或隐藏异常宣告通过。正常自动测试无需修改用户其他应用或浏览器偏好。

本轮具体结果见 [RC3 验证记录](validation/open-source-rc3.md)。


Optional smoke: start the production preview, then run `node tools/browser-smoke.mjs` with Chrome installed. It uses an isolated profile and software WebGL. Reports and screenshots go to `artifacts/validation/browser/`; this is not a hardware performance test.
