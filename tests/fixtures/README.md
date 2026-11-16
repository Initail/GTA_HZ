# 测试夹具

这些夹具跟随源码分发。保留 JSON、GLB 和 BIN 的原始字节，来源路径按迁移前项目记录。历史候选里的路径用于追溯来源，测试从当前仓库读取实际文件。

| 当前位置 | 来源（迁移前相对路径） | 测试用途 |
| --- | --- | --- |
| `baseline-driving/` | `artifacts/cities/hangzhou/demo-v11-loading/src/{driving,road-access,city-types}.ts` | 白堤路权测试的旧碰撞实现，用同一组地形、道路和车辆输入与当前实现对照。 |
| `fixture/` | `artifacts/cities/hangzhou/release-v16-rc2/fixture/` | 白堤附近的裁剪城市、地标碰撞和路线。测试核对 `provenance.json` 中的哈希。 |
| `fixture-physical-v1/` | `artifacts/cities/hangzhou/release-v16-rc2/fixture-physical-v1/` | 白堤旧版地形高程、道面和步行支撑，供碰撞负对照及接入前后几何比较。测试核对来源哈希。 |
| `westlake-baseline/site-surfaces.json` | `artifacts/cities/hangzhou/westlake-bicycle-v1/public/cities/hangzhou/geography/site-surfaces.json` | 对照新版白堤的车行限制，保护独立编制的原通行走廊与高度。 |
| `site-path/` | `artifacts/cities/hangzhou/release-v16-rc2/site-path-ground-fit-v2/site-surfaces-candidate.json`、`site-path-integration-v2/geography/staging-report.json` | 灵隐步道接入增量及其哈希。测试验算当前地理文件对基线与增量的保留。 |
| `terrain-v10/manifest.json` | `artifacts/cities/hangzhou/demo-v10/dist/cities/hangzhou/geography/manifest.json` | 湖畔测试所用原始地形网格参数。高程二进制与当前运行时文件字节相同。 |
| `bus/generated-bus-mesh-v4.json` | `artifacts/cities/hangzhou/bus-depot-profile-v2/contact-v4/generated-bus-mesh-v4.json` | 公交候选模型的网格、车体尺寸与车门坐标。用于车体和乘车状态测试。 |
| `shenzhen-autopilot/` | `public/city/{city,landmark-detail,navigation}.json` | 上游深圳自动驾驶的固定实际路网，保留原版路线及目标点覆盖。 |
| `stream-spawn/` | `artifacts/cities/hangzhou/stream-mesh-v1/{terrain,roads}/`、`stream-mesh-v2/buildings/` 的 `plan.json` 与 `0,-1` 格网元数据 | 检查真实城市分块、纹理尺寸和缓冲区验证。三块 GLB 和全部共享纹理从当前运行资产读取。 |
| `pack-pilot/` | `artifacts/cities/hangzhou/city-leisure-v15/pack-pilot-v1/output/` 的描述文件和目标 GLB | 解析由地面、道路和建筑合成的真实包，核对源节点和二进制几何。 |
| `base-far-pilot/` | `artifacts/cities/hangzhou/release-v16-rc2/public/base-far-pilot/roads/` 的描述文件和目标 GLB | 远景道路候选，检查 Meshopt 压缩元数据和预算。 |
| `xianfu-thin-floor-boundaries.json` | `artifacts/cities/hangzhou/release-v16-rc2/tests/fixtures/` | 闲富路薄道面边缘的查询样本，覆盖车辆与步行支撑。 |
| `history/` | `artifacts/cities/hangzhou/release-v16-rc2/tests/` 的 `route-section-*.json`、`route-proof-v1/`、`pre-partition-walk-check.txt` | 历次湖畔路线证据和旧验证代码。 |

八段湖畔路线测试按次序使用当前源码和数据重新计算，逐段校验输入哈希、上一节哈希、路线衔接和实际行走结果。证据临时生成于 `artifacts/test-route-evidence/run-*/`，通过后清除该次报告。失败前已完成的分段留在临时目录，供定位断点。

其他随测试携带的记录包括 `tests/main-city-fixture*.json` 中的杭州主城碰撞与高程样本，以及 `tests/canopy-camera-witnesses.json` 中的树冠摄像机几何见证。后者核对当前运行时的柳树和香樟模型，并保留原始每例来源。城市夹具的 OSM 数据署名为 © OpenStreetMap contributors，适用 ODbL。
