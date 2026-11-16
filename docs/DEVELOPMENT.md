# 开发与启动

## 环境

日常代码开发使用 Node 24.13.x、npm 和 Python 3.8+。推荐 `nvm use`。Windows 可在 WSL 使用同一命令；原生 Windows 的 Python 命令需提供 `python3`，或设置 `PYTHON` 给构建脚本。Blender、GDAL、osmium 与 `requirements.lock.txt` 仅用于相应地理/模型任务，不是试玩前置条件。

```sh
npm ci
npm run assets:fetch
npm run assets:verify
npm test
npm run dev
```

`npm ci` 使用锁定版本，并将 Babylon 声明中的桶式 import 改为唯一可追溯的原声明路径，生成 `.cache/babylon-types/`。它保留完整 API 与类型诊断，不使用 stub/any；这样可以降低类型检查内存。报告在 `.cache/babylon-types/report.json`。安装不下载游戏资源、不运行 Blender。

默认 URL 为 `http://127.0.0.1:5241/`。欢迎页点击后才加载主城。默认低画质；先确认驾驶稳定，再尝试较高画质。源码修改后重新运行 `npm run dev`，或者 `npm run build` 后启动 `npm run preview`。这里有意采用构建后预览，不提供热更新。

## 资源与离线安装

`npm run assets:fetch` 读取 `assets/runtime-lock.json`，下载固定 Release ZIP，核对包和全部文件哈希，原子安装到 `public/`。已有资源只校验、不覆盖。需要切换资源版本时先把旧 `public/` 移到备份位置；不要强行改清单让旧文件通过。

离线取得同版本 ZIP 后运行：

```sh
python3 tools/assets.py fetch --archive /path/to/gta-hz-runtime.zip
```

地理源数据随包在 `public/source-data/hangzhou/`，处理/重建说明见 [REBUILDING](REBUILDING.md)。`npm run assets -- --plan` 仅显示依赖与状态，不覆盖场景。

## 局域网与部署

```sh
npm run dev -- --host 0.0.0.0
# 或已有构建
npm run preview -- --host 0.0.0.0
```

其他设备访问运行电脑的当前局域网 IP，端口 `5241`；不要把 `127.0.0.1` 发给另一台电脑。端口冲突会退出，不会杀死其他服务。可用 `--port 5250` 指定空闲端口。外网部署时上传整个 `dist/` 到站点根路径，保证 GLB/BIN/JSON/HDR/纹理可按原路径读取；当前绝对资源路径不支持任意子目录部署。源码仓库本身不是 GitHub Pages 成品。

## 常见故障

| 现象 | 检查 |
| --- | --- |
| 资源校验失败 | 检查网络/磁盘与版本，保留错误文件，再重新取得固定包；LFS 指针不能替代模型 |
| 连接被拒绝 | 终端服务是否还在运行、端口是否正确；重启电脑后重新 `npm run dev` |
| 页面没出城 | 欢迎页是否点击；查看控制台首个错误和 Network 404，记录最后加载阶段 |
| WebGL context lost | 关闭本次游戏页，检查系统资源，再用低画质重试；持续出现则提交诊断，不重复整机压力试验 |
| 存档似乎消失 | 端口、协议或域名变化属于不同 origin；原 origin 存档仍在，系统不会自动读取深圳命名空间 |
| 模型脚本缺输入 | 阅读脚本索引，很多历史生成器需要显式候选/源数据；不要补假文件跳过 |

提交问题时附版本、操作、地点、浏览器、画质及控制台错误；不上传全部本机日志或个人路径。
