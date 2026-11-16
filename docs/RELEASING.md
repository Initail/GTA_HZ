# 阶段版本发布

发布权限归仓库维护者。使用 `rc` 版本表示阶段候选；只有功能、地标、视觉和稳定性验收条件满足后才能称为稳定正式版。当前未通过项保留在 [STATUS](STATUS.md)。

1. 以当前主线创建发布分支，确认 `git status` 和资源锁，核对 [第三方声明](../THIRD_PARTY_NOTICES.md)、脱敏报告及每件新增素材的授权。保存旧候选。
2. 串行集成已验收资源，生成 `assets/runtime-manifest.json`，逐项记录路径、长度、SHA256。只包含可分发文件，拒绝 LFS 指针和未经许可的旧角色。
3. 执行 `npm test`、`npm run test:tools`、`npm run build`、`npm run docs:check`、`npm run release:check`。实机检查按风险记录版本与资产哈希。未跑的检查写明。
4. 运行 `python3 tools/assets.py pack --archive artifacts/gta-hz-runtime.zip`，将输出 SHA256/字节数写入 `assets/runtime-lock.json`，URL 指向新 tag 的 Release。固定包不可变。
5. 提交源码、文档和资源清单，创建 tag，推送到已确认的仓库。创建 GitHub prerelease 并上传资源包；Release 说明区分已验证与未通过项。保留原 MIT 与资源署名。
6. 从远程新克隆执行 README 流程；用下载后的 ZIP 验证哈希，确认 CI、远程 commit/tag 与资源锁一致。发布完成再提供链接。

GitHub Release 可以附独立二进制资源，适合将运行包与源码历史分开，参见 [GitHub Releases 文档](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)。当前部署需站点根路径；本步骤不自动部署公网游戏站点。

首次建库时，push 触发的 CI 可能早于第一个资源包公开，`assets:fetch` 会返回 404。保持失败记录，待包发布后重跑；不要跳过资源校验或把缺失资源计为成功。正式向用户交付前确认对应 CI 已通过。

回退：检出上一个源码 tag，保留当前资源目录到备份位置，再获取旧 tag 对应的锁定包。不要直接用旧包覆盖新清单；浏览器存档回退兼容需单独核对。
