# GTA_HZ · 杭城之行

一座可以驾驶、步行、骑行和探索的杭州浏览器城市。使用 TypeScript、Babylon.js 和真实地理数据，基于 [linranff/GTA_SZ](https://github.com/linranff/GTA_SZ) 演进。

**当前为 `0.16.0-rc.3` 开源阶段候选。** 主城、地图、职业剧情与休闲系统已有实现；公交整线、部分地标及长期稳定性仍待完成。功能代码存在、自动测试通过、实机验收通过是不同状态，详见 [当前状态](docs/STATUS.md)。本项目与 Rockstar Games、杭州市政府及模型中的机构无隶属关系。

[文档索引](docs/README.md) · [开发指南](docs/DEVELOPMENT.md) · [操作说明](docs/CONTROLS.md) · [协作规范](CONTRIBUTING.md) · [Agent 入口](AGENTS.md) · [路线图](docs/ROADMAP.md)

## 快速开始

准备 **Node.js 24.13.x、npm、Python 3.8+**，桌面浏览器需支持 WebGL2。建模才需要 Blender 和额外 Python 依赖。

```sh
git clone https://github.com/Initail/GTA_HZ.git
cd GTA_HZ
npm ci
npm run assets:fetch
npm run dev
```

打开终端显示的 `http://127.0.0.1:5241/`，点击「进入杭州」。页面不会自动启动主城。首次资源下载约 465 MB（解压约 905 MB），以 [资源锁](assets/runtime-lock.json) 为准；资源不放入 Git 历史，下载后逐文件核对 SHA256。没有完整资源时，构建会明确失败。

```sh
npm test                 # 当前源码、真实夹具与八段湖畔路线
npm run test:tools       # 资源下载/解包保护
npm run build            # 资源校验、严格类型检查、生产构建
npm run preview          # 仅服务 dist
```

`npm run dev` 会构建当前源码再启动静态服务，不提供 HMR。修改源码后停止服务并重新运行，避免开发模式重复解析大型 Babylon 包。局域网测试用 `npm run dev -- --host 0.0.0.0`，访问运行电脑的局域网 IP 和端口；电脑需保持运行。不要直接双击 HTML。

## 可以做什么

- 汽车驾驶与镜头、步行/跑步、上下车、坦克炮弹、无人机和飞机；独立靶场保留独立用途。
- 地图搜索、路线、自动驾驶、观景、快速移动、收藏及杭州独立存档。
- 三种职业、六份合约、升级、关系选择、顺路故事、《最后一单》分支与咖啡馆互动。
- 自行车、湖畔游船/钓鱼与角色原型；NPC 车流、行人、信号和电动车。
- 昼夜、晴/阴/雨/雪、音效和画质设置。低画质保留 RC2 的约 540p 单次渲染、按需加载及可选特效关闭策略。

这张表描述已有代码范围，不表示每个玩法已在杭州全城完成实机终验。不要用截图或构建成功代替 [验收要求](docs/TESTING.md)。

## 工程入口

| 目录 | 职责 |
| --- | --- |
| `src/main.ts` / `src/city-world.ts` | 主城 UI、模式协调与 Babylon 世界 |
| `config/cities/hangzhou.json` | 城市投影、范围、出生点、命名空间与任务地点 |
| `src/city-*.ts` | 地图、职业剧情、车辆、环境、休闲与分块加载 |
| `tools/` | 当前可执行的安装、构建、校验和原创资源生成入口 |
| `scripts/` | 地理处理、建模、候选集成及历史研究工具，先读 [脚本索引](docs/SCRIPT_INDEX.md) |
| `tests/` | 自动回归及有来源的地理/模型夹具 |
| `data/` / `docs/hangzhou/research/` | 数据来源、地标任务包与证据，含历史候选 |
| `assets/` | 资源锁、逐文件哈希、来源和许可声明 |
| `public/` / `dist/` | 下载资源和本地构建输出，均不入 Git |
| `ue5/` | 保留实验移植源码，不是已交付的 UE5 客户端 |

## 许可与来源

代码遵循 [MIT](LICENSE)，保留上游 `linranff and the ShenChengJi contributors` 版权。上游基线为 `73603f31416de4111f10783f512c1101bd738a97`；本仓库采用新的提交历史，来源记录见 [快照说明](assets/source-snapshot.json)。

**资源不统一适用 MIT。** OSM 数据遵循 ODbL，CarConcept、原创替代角色/坦克遵循 CC BY 4.0，选用材质遵循 CC0，地形保留 Copernicus 条款。公开照片仅作参考，不作为默认发布贴图。旧试玩中的受限人物和授权不明的 Tripo 模型未随公开包分发，相关玩法改用原创模型。详见 [第三方声明](THIRD_PARTY_NOTICES.md) 和 [资源管线](docs/ASSETS.md)。

English overview: [README.en.md](README.en.md).
