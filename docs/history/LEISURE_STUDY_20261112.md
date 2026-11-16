# 湖畔休闲操作样片 · 2026-11-12

当前用户优先级保持：①骑行/游船/钓鱼，②西湖与灵隐实景，③NPC 与互动，④公交，⑤园区/景区通行和标识。本文只记录本阶段的新进展，不替代主城验收。

## 可体验内容

独立候选 `artifacts/cities/hangzhou/westlake-leisure-v1`：船工与志愿者交谈、登船、前划/倒划/转向/刹停、完整船身采样避岸、泊位下船、抛竿/提竿/控线/放流，以及单独手账的刷新恢复。原职业钱包、汽车里程和结算模块没有接入或修改。场地是明确标注的虚构操作测试区，模型为程序生成的中间稿，不声称复原西湖，也不代表现实垂钓许可。

本机 http://127.0.0.1:5206/ ，同一局域网 http://30.113.3.207:5206/ 。本次服务北京时间 10:27:20 启动，11:27:20 到期。双击项目根目录 `启动湖畔休闲体验.command` 可以重新启动，自动获取当前局域网 IP、复用已有入口或选择空闲端口；不关闭其他服务。入口不会自动加载场景。

WASD / 方向键行走或划船；E 交谈/登船/靠岸下船/放流；Q 抛竿或收竿；空格刹船或提竿、按住收线，松开降低张力；C 近远镜头；Esc 暂停。垂钓区在码头右侧。只有成功放流才记入手账，切走、收竿、超时或断线不结算；没有职业金钱奖励。

## 本轮验证

| 项目 | 本轮结果与边界 |
|---|---|
| 规则自动检查 | 13 通过，0 失败/跳过。覆盖登船距离与高度、船身边缘、接岸/倒划、长帧、停泊下船、垂钓时窗/断线/取消、唯一放流、坏存档。 |
| 严格类型 | 纯玩法模块通过。带 Babylon 渲染层的 3 次检查都触及固定 256 MiB 限制，未计通过；没有提高阈值或伪造结果。 |
| 预览构建 | esbuild 使用现有锁定依赖成功；不等于整个项目的正式 Vite 构建。 |
| 真实浏览器 | Codex 内置浏览器，使用可见页面按键/按钮，没有写入游戏内状态。登船、前划、转向、刹停、湖中拒绝下船、真实倒划回泊位下船、船尾碰岸停止均观察到。 |
| NPC 与导向 | 实际步行到船工及志愿者旁交谈，检查两块标识牌、距离提示。仅两个原型角色，不算城市 NPC 多样化完成。 |
| 垂钓与保存 | 两次实际收鱼并放流；一次 27 cm、一次 37 cm。重复 E 不重复计数，刷新仍显示 2 尾/最大 37 cm。等待超时和错失咬钩也真实出现，未清掉失败记录。 |
| 日落/夜晚/暂停 | 实际切换并观察，夜间文字对比不足已修复；Esc 暂停有可见状态。切后台自动暂停有代码，未单独给出实测通过。 |
| 运行日志 | 最后检查未返回浏览器 error 日志；不等于全模式回归。 |
| 资源 | 前 90 秒 18 次采样均无既定报警，应用进程族 RSS 增量峰值 282608 KiB（约 276 MiB），压力 1；后续沿用原始基线复查仍正常。属主机/应用级观测，不能归因成游戏独占内存，也没有给出 FPS 或长期稳定性通过。 |
| 网络 | 本机经局域网 IP 校验入口、HTML、最终 JS 字节与 SHA，源文件/越界路径 404。没有冒充其他同学设备的联网验收。 |

第一次长时间分步收线超过 18 秒，鱼逃脱；最终复测一次咬钩等待工具超时，下一次根据 UI 浮漂状态即时提竿后完成。这些是具体操作结果，不用测试代码强制变更阶段。

实机发现的两项改善：接岸提示保留 2.5 秒；添加人物牌面和泊位距离。样片渲染上限 30 帧/秒、暂停时 4 帧/秒，模拟仍使用原时间步，不修改主城画质或操作参数。实际 FPS 尚未测量。

截图：`audit/leisure-20261112/boat-night-final.jpg`、`fishing-final.jpg`、`journal-restored-final.jpg`。此前 `fishing-release-v1.jpg` 是补标识前的版本，不能拿它替代最终截图。

## 与主城的关系和下一阶段

v12 的 144 份源码、v13 的 145 份源码及原主包逐一复核未变化，记录在候选的 `protected-baselines.json`。新规则是独立模块，不改变已有玩法接口。尚未接入主城的码头、水域数据、任务互斥、NPC 模型和相机；本轮不将游船/钓鱼列为主城已实现。

v13 主城本轮曾真实开始加载，在道路阶段观察到应用进程族 RSS 增量 964032 KiB 并随后出现压力 2，因此退回入口并停止本次自有 5205 服务。没有把它扩大为 v12 用户试玩失败。v13 的加载页还残留 v12 角标，下一主城候选须改正。完整驾驶/骑行实机、职业/剧情、景点等验收仍欠缺。

下一阶段按顺序：确定并核验杭州真实码头及步行到达点；用当前水体/桥梁/岸线约束接入游船与垂钓；补人物、船桨/坐姿/鱼竿动画及道具；联合验证与骑行、汽车、无人机、任务、刷新恢复的互斥。西湖/灵隐实景、公交、真实门禁仍在前五项中，未取消。

## 重建

候选 `delivery.json` 固定源文件、预览和测试哈希，最终 JS 3606307 字节，SHA256 `8156845c30ce47934b7544b671836dd32504c829319272d839d44744b36f829b`。没有新装依赖或外部照片贴图，原项目 MIT 和资产署名保留。

```sh
python3 scripts/run_hangzhou_bounded.py --report NEW_RULES_REPORT.json -- node --experimental-transform-types artifacts/cities/hangzhou/westlake-leisure-v1/tests/leisure.test.ts
python3 scripts/run_hangzhou_bounded.py --report NEW_TYPES_REPORT.json -- node --max-old-space-size=128 node_modules/typescript/bin/tsc -p artifacts/cities/hangzhou/westlake-leisure-v1/tsconfig.rules.json
# 使用新的输出目录，不覆盖已验收预览：
python3 scripts/run_hangzhou_bounded.py --report NEW_BUILD_REPORT.json -- node_modules/.bin/esbuild artifacts/cities/hangzhou/westlake-leisure-v1/src/leisure-preview.ts --bundle --format=esm --platform=browser --target=es2022 --outfile=NEW_OUTPUT/leisure.js
python3 scripts/open_hangzhou_leisure_preview.py --no-open
```

另保留 `stream-world-v2` 的两个加载取消/卸载缺陷修复，两条原先失败用例现通过；仍是独立候选，未把未验收流式加载混入用户试玩。
