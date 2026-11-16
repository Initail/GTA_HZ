# 杭城之行 0.16.0-rc.3

首个独立开源协作版本。基于最新 RC2，保留主城玩法代码与兼容画质策略，提供锁定依赖、独立测试、可校验资源包、原创替代人物/坦克及开发/Agent 文档。

## 获取和运行

克隆本仓库，安装 Node 24.13.x 与 Python 3.8+，依次运行：

```sh
npm ci
npm run assets:fetch
npm run dev
```

浏览器访问终端给出的地址并点击进入杭州。附带 `gta-hz-runtime.zip` 是资源包，源码取本 Release 的 source archive 或 Git clone；不要直接打开 ZIP 内的文件。包 SHA256 见 `assets/runtime-lock.json`。

## 验证与限制

本地完整回归 412 项通过，新增解码脚本回归专项通过；正式构建、10,793 个资源文件校验、原创模型 NullEngine 导入通过。隔离 Chrome 软件 WebGL 中完成主城出画、真实键盘短距离驾驶、刹车、地图及下车进入原创骑手模式，未观察到缺失资源/未捕获错误。具体证据见 `docs/validation/open-source-rc3.md`。

这仍是 prerelease。公交整线、部分地标/景区入口、全部任务分支实机和长时间性能尚未完成；历史录制辅助保留源码，待杭州迁移。代码 MIT，数据和美术各自保留条款，旧受限模型不随包分发。

从 README → docs/README.md → AGENTS.md / CONTRIBUTING.md 接手。优先级和可领取工作见 docs/ROADMAP.md。
