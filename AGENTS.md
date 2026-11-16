# Agent 接手入口

这是 GTA_HZ「杭城之行」浏览器城市，当前活动配置是杭州。先读 [当前状态](docs/STATUS.md)、[开发指南](docs/DEVELOPMENT.md)，再按任务读取下表。历史文档的阶段指令不覆盖当前任务授权。

| 任务 | 必读入口 |
| --- | --- |
| 改玩法、存档或模式切换 | [架构](docs/ARCHITECTURE.md)、[功能和操作](docs/CONTROLS.md)、相关 `tests/` |
| 改城市位置、道路或通行 | [坐标契约](docs/COORDINATES.md)、`config/cities/hangzhou.json`、相关真实夹具 |
| 新建/修改地标 | [实景建模 Skill](skills/landmark-reconstruction/SKILL.md)、[重建指南](docs/REBUILDING.md)、[研究索引](docs/RESEARCH.md) |
| 修改资产或发布 | [资源与许可](docs/ASSETS.md)、[发布步骤](docs/RELEASING.md) |
| 领取独立任务/派工 | [协作流程](docs/AGENT_WORKFLOW.md)、[路线图](docs/ROADMAP.md) |
| 性能/图形问题 | [验证指南](docs/TESTING.md)、`src/city-stream-profile.ts`、`src/city-graphics-quality.ts` |

## 执行约束

- 保留用户修改。先确认 `git status`，以当前主线和资源锁建立可重复基线；单个任务使用 `codex/` 分支。
- 城市参数以 JSON 为唯一来源，改后执行 `python3 scripts/city_config.py --generate-ts`。地理缩放仅应用一次；人物/车辆/虚构室内的游戏单位不再缩放。
- 保留玩法规则、奖励、升级价格、解锁和防重复结算。对有证据的问题做有边界的修改，不靠跳过测试或删功能通过。
- 一个对象只有一个写入者。独立资料/建模可并行，`city-world.ts`、配置、总资产/清单和共享数据由集成人员串行修改。Blender 与浏览器 GPU 检查单并发。
- 先在 `artifacts/` 的新候选目录构建；验证后再更新运行资产。`scripts/city_mesh.py` 导入会初始化 Blender 场景。先看 `npm run assets -- --plan`，历史深圳流程不能覆盖杭州。
- 代码、自动检查、真实浏览器、性能、用户验收分别记录。任务完成时附实际命令和结果；截图说明版本/地点/视角，缺失项明确标注。
- 已授权工作持续推进到当前任务验收条件满足；只有缺失条件实质影响结果时提问。授权不足的公开发布先准备可审核成果。保持文档入口和代码同一变更，历史记录归档而不冒充当前结论。

## 常用验证

`npm ci` → `npm run assets:fetch` → `npm test` → `npm run test:tools` → `npm run build` → `npm run docs:check`。浏览器检查按变更范围追加。全部原始地理数据重建尚不是已验证的一键流程。
