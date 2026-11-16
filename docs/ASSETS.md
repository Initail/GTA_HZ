# 资源获取、来源和更新

## 当前运行资源

源码仓库不跟踪 `public/`、`dist/` 或历史 `artifacts/`。Release 提供 `gta-hz-runtime.zip`，版本、URL、大小和包 SHA256 由 [runtime-lock](../assets/runtime-lock.json) 固定；[runtime-manifest](../assets/runtime-manifest.json) 记录每个文件的 SHA256 和长度。`npm run assets:fetch` 在临时目录解包、拒绝清单外文件和不安全路径，全部通过后再安装。

现有 `public/` 不自动覆盖；本地建模更改需作为新候选校验。锁定包是现有可运行资产快照，不声称已验证全部原始源重建。资源与源码必须匹配；切换分支后先运行 `npm run assets:verify`。

## 来源与许可

详见 [第三方声明](../THIRD_PARTY_NOTICES.md)。OSM 时间为 `2026-10-11T20:21:06Z`，不是下载时间也不是每个对象的实测日期；源 PBF SHA256、范围与坐标系在 [源清单](../data/hangzhou/source-manifest.json)。扩展裁切后的 GeoJSON 随运行包放在 `source-data/hangzhou/`，实际游戏 JSON 块亦可机读，按 ODbL 提供。OSM 数据与 Copernicus 地形不是无误差实测模型。

牌匾/招牌、照片、纹理分别记录来源。公开照片默认仅作参考。角色公开包不含旧 MMD 和授权不明的 Tripo 文件，使用 `tools/original-assets/generate-assets.mjs` 的原创输出；其生成位置是 `artifacts/original-assets/`，不会直接覆盖运行资产。生成后以当前 `check-assets.mjs` / `check-babylon.mjs` 契约核对，再由集成人员发布。

## 更新流程

1. 确认对象身份、输入哈希、许可和阶段，使用 [重建指南](REBUILDING.md) 输出独立候选。
2. 校验几何/材质/尺寸/方向/动画，地标同步校验基础楼和近立面排重、道路/步行碰撞、入口、到达点、植被和地图。
3. 保存当前资产的实机俯视/街面/远景与昼夜截图。仅构建成功或 NullEngine 导入不足以推进视觉验收。
4. 集成人员串行替换已通过的运行文件，更新 manifest 与包哈希；每次新包使用新版本，不覆盖旧 Release 的同名内容。
5. 执行 `npm run assets:verify`、回归、构建和 [发布检查](RELEASING.md)。下载后的新目录再次校验，避免只有本机缓存可用。

`npm run assets -- --plan` 是只读依赖/状态入口。上游 `scripts/rebuild_city_assets.mjs` 仍保留深圳全流程研究用途；不能原封运行它覆盖杭州。原始数据/Blender 的完整端到端源重建继续是待补工程，不以发布 ZIP 代替源重建证明。
