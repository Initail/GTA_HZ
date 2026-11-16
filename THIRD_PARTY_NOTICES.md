# 许可、署名与分发边界

代码、数据库、模型和参考资料分开授权。根 [LICENSE](LICENSE) 是代码 MIT，不自动覆盖所有资源。运行包的实际文件由 [清单](assets/runtime-manifest.json) 锁定，历史候选或照片不会因有公开 URL 就被视为可以重新发布。

| 类别/位置 | 来源与条款 | 本项目处理 |
| --- | --- | --- |
| `src/`、`scripts/`、`tools/`、`tests/`、构建配置和项目原创 UE5 代码 | MIT；Copyright (c) 2026 linranff and the ShenChengJi (深城纪) contributors；本仓新增代码 © GTA_HZ contributors | 保留上游版权、许可与源码来源 |
| `ue5/Shenchengji/Source/TP_VehicleAdv` 中带 Epic 版权头的车辆模板 | Epic Games 的 Unreal Engine Examples，遵循 [Unreal Engine EULA](https://www.unrealengine.com/eula/unreal) 的 Examples 条款 | 保留原版权头；这些模板不重新许可为 MIT，使用 UE 仍需符合 Epic 条款；不分发引擎或导入内容 |
| 杭州道路、建筑足印、水体、绿地、地点及衍生导航/地理 JSON | © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright)，[ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/)；固定 [Geofabrik 浙江快照](data/hangzhou/source-manifest.json) | 公布来源/时间/哈希；运行包含机器可读 `source-data/hangzhou/` 及实际分块数据库；这些数据库继续按 ODbL 分发 |
| 杭州地形 | Copernicus GLO-30，详见 [两瓦片来源](data/hangzhou/dsm-source-manifest.json) 和 [许可](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DEM/resources/license/License-COPDEM-30.pdf) | 30m DSM，裁切、采样、游戏比例与接合改编；不是实测裸地 DTM |
| 主车 `cities/hangzhou/car.glb` | [Khronos CarConcept](https://github.com/KhronosGroup/glTF-Sample-Assets/tree/main/Models/CarConcept)，Darmstadt Graphics Group / Eric Chadwick，CC BY 4.0 | 尺寸、方向、材质及压缩适配；保留运行包 `licenses/carconcept-CC-BY-4.0.md` |
| 原创替代骑手、咖啡员工、坦克 | GTA_HZ contributors，CC BY 4.0；[生成与契约](assets/ASSET-CREDITS.md) | 无外部几何、纹理或动作输入；脚本 MIT；不能冒充真人或真实军用载具测绘 |
| 选用环境 HDR、材质和长椅 | [Poly Haven](https://polyhaven.com/license) / [ambientCG](https://docs.ambientcg.com/license/)，CC0；各下载来源/哈希在随包 manifests 和 `data/materials/` | 保留作者/来源及转换记录，不请求在线资源 API |
| 项目程序生成的城市几何、植被、道路设施、NPC 车、虚构咖啡馆、杭州地标 | 来源见对应 manifest 和 MIT 建模脚本；上游与本仓贡献者署名保留；含地理数据的作品同时保留 OSM/Copernicus 条款 | 以可审查脚本和来源证明制作链，不把第三方照片转为贴图；新增独立美术在 manifest 显式标许可 |
| 灵隐牌匾文字几何 | Adobe Source Han Serif TC Regular，SIL OFL 1.1，见 [字体许可](data/hangzhou/licenses/SourceHanSerif-OFL.txt) | 几何文字近似，不捆绑字体、不声称复原历史书法 |
| Babylon.js / loaders | Apache-2.0；随包保留 LICENSE/NOTICE | 从锁定 npm 依赖构建；类型声明归一化只改 import 图，保留原 API |
| meshoptimizer | MIT | 保留随包许可 |

## Copernicus 指定署名

produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved.

The organisations in charge of the Copernicus programme by law or by delegation do not incur any liability for any use of the Copernicus WorldDEM-30.

## 未分发的旧素材

旧 `characters/kuki.glb`、`characters/yelan.glb` 的原条款禁止二次配布；旧骑手、两款咖啡员工和坦克为用户提供的 Tripo 衍生素材，记录未附可验证的公开再分发授权。因此公开包不包含这六份旧模型。原创替代覆盖后四件的路径，公开构建不自动读取 `/characters`。

原试点街区的非当前入口模型未随包全部导出。研究目录只收录资料索引、几何证据及必要公开元数据，未发布下载的照片/PDF/网页镜像。外链照片的版权、拍摄者和许可仍归原权利人，参考不构成新的分发许可。

新增贡献必须提供真实来源和对应许可；署名不能替代授权。若发现来源有误，请创建 Issue，附具体文件、哈希和权利依据；维护者应暂停相关资源的后续分发并核对。
