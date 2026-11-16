# P2 白堤、西湖、灵隐候选与 v13 接入盘点 · 2026-11-12

本文件只记录只读盘点结果，不修改源码、清单、候选、资产或服务。当前系统内存压力由根线程报告为 2；本轮未运行 Blender、构建、浏览器、服务或全城解析。读取内容文件上限设为 128 KiB，超过上限的 JSON/GLB/纹理仅检查文件存在和字节数，不载入、不重算大文件哈希。下列 GLB 哈希与统计来自既有交付/校验报告，未冒称本轮重验。

`reported` = 已有清单/报告明确记载；`confirmed-static` = 本轮读到配置、文件或引用链；`estimated` = 设计/几何推断；`unknown` = 当前缺证据。候选、静态接入、历史浏览器结果、当前主城验收分别记账。

## 核心结论

**v13 已继承白堤/断桥修复面、既有灵隐五殿、白/苏堤与雷峰塔等旧地标，以及原有植被与水面；没有发现新灵隐附属模型、西湖 context-v2、景区排重/AO 和白堤树冠修复接入 v13 的证据。** 这个判断来自冻结候选的资源回退与覆盖清单、版本继承审计和项目状态文档，不是本轮重新解码全部主城资产或运行浏览器所得。

P2 的主要缺口并非“完全没有模型”。已有较完整的独立模型、精确 ID 排除候选、接地提案与失败复现，但它们仍散落在不同版本。需要串行把模型、旧楼排除、旧碰撞、接地支撑、装饰和 AO 对齐到同一候选后，再取得当前资产的具名截图与通行结果。不能只安装新 GLB，留下旧高楼/旧碰撞/阴影；也不能先删整片景区来掩盖不一致。

## v13 实际引用链与已接入范围

1. `artifacts/cities/hangzhou/westlake-bicycle-v1/candidate.json` 标识 `version=demo-v13-bicycle`，`base=artifacts/cities/hangzhou/westlake-collision-v1`，`runtimeAssetsFallback=artifacts/cities/hangzhou/demo-v10/dist`。
2. v13 的资产覆盖只有 `cities/hangzhou/landmark-detail.json`、`cities/hangzhou/geography/site-surfaces.json`、`cities/hangzhou/geography/manifest.json`。本轮目录检查未见新增景区 GLB 覆盖。覆盖的两个大 JSON 未载入；引用关系以候选清单为依据。
3. `docs/hangzhou/audit/demo-ui-v10-inheritance-20261111.json` 记录 demo-v8 → demo-v10 比较 8,833 文件，仅 `src/city-story.css` 变化，物理/资产继承 v8。它不是 v13 的新浏览器验收。
4. `docs/hangzhou/WESTLAKE_COLLISION_20261111.md` 说明 v12 只增加来源绑定的六条通行走廊等规则，地形、湖水、铺装三角、护栏、地标模型和道路图未修改；`BICYCLE_PREVIEW_20261111.md` 明确 v13 从 v12 复制源码及三份 JSON 覆盖。
5. v13 的小型 `geography/manifest.json` 仍绑定 DSM 地面 `dd1ae9e…792ac`、道路层 `0db3134e…a25c1`；场地面 SHA 为 `4a56385b06b15478e0fa4b66091244d11be877b41b8854f85b32a869214d8d18`。**这不等于灵隐 ground-contact 提案已合并**：该提案锁定的是 demo-v10 的 `952ab1d9…879e0` 场地面，必须重新检查与 v13 的权限附加内容如何共存。

| 地理对象/功能 | v13 静态接入判断 | 已有证据 | 当前不能声称 |
|---|---|---|---|
| 白堤、锦带桥、断桥实际步行支撑与护栏 | 已继承修复链；v12/v13 增加机动车/自行车源权限 | `bai-route-model-v3`、`bai-route-support-v3`；demo-v9 的 `bai-integration.json` / `bai-support-refinement.json`；v8→v10 继承审计 | 当前所有画面/骑行/长时性能通过；苏堤也已修复 |
| 白堤六段准骑/禁骑 | 已进入 v13 玩法规则 | `BICYCLE_PREVIEW_20261111.md`：`way/4326974` 可骑，其余五段 `bicycle=no`；保留原始权限 | 六段全可骑，或 `cycleway=yes` 能覆盖明确禁骑 |
| 灵隐五殿 | 旧 site-v2 候选已在历史城市链内；继承到 v13 | `current-model-inventory-v8.json` 的 `lingyin-temple`；`PROGRESS.md` 的 site-v2、分殿基高及碰撞集成记录 | 全寺复原；附属楼、山林、完整台阶、寺界、入口开放性通过 |
| 白/苏堤旧模型与雷峰塔主体 | 既有地标链内 | 同一库存登记 `west-lake-causeways`、`leifeng-pagoda`；白堤另有后续局部替换 | 白堤修复自动覆盖苏堤六桥、雷峰塔全场地/入口 |
| 西湖水面、原植被 | 继承既有资源 | v13 fallback 目录存在原水/地理与 `landscape/canopy` 资源；白堤复现报告绑定该植被清单 | 水位为实测、树种逐株真实、桃柳组合或镜头遮挡已改善 |
| 灵隐 context export-v2、西湖 context-v2、景区排重/装饰/AO候选 | 未见 v13 接入证据，现有文档明确未完成集成 | 各独立合同与 `USER_REQUESTS_STATUS.md`、`ACCEPTANCE.md` | 候选 ready 等于主城交付 |

v13 的 `candidate.json` 仍记录 `browserValidated=false`、`formalViteBuildPassed=false`、`glbStreamingInstalled=false`。`LEISURE_STUDY_20261112.md` 另记录 v13 本轮加载到道路阶段后出现实际资源报警，退回入口并停止自有服务；用户认可的 v12 试玩反馈不能转记为 v13 或新景区模型通过。

## 白堤与树冠：现有修复和未完成项

### 可复用的桥面与通行结果

- `artifacts/cities/hangzhou/bai-route-model-v3/` 有 `west-lake-causeways.glb`、`broken-bridge.glb`。`bai-route-support-v3/support-report.json` 记录实际模型抽取 813 + 178 个步行三角形；`upper-envelope-report.json` 记录把 991 个源三角处理为 2,073 个支撑三角，按真实较高平面扣除覆盖，没有把游戏阈值放宽。
- `bai-route-input-v1` 的六条 OSM way 连成白堤路线。`PROGRESS.md` 明确该适配只处理白堤、锦带桥、两个白堤岸域和断桥，未把苏堤计为修复；水上干舷等是游戏估计。
- `docs/hangzhou/ACCEPTANCE.md` 记录 v8 曾沿六条源路径真实走/跑往返、上下车，步行里程 1408.849g；对应 `bai-browser-roundtrip-v8-20261111b.json`。该大报告本轮未载入，使用小型验收文档的历史摘要。历史截图明确仍存在随机高楼、树冠遮镜头和 UI 问题。
- `artifacts/cities/hangzhou/bai-base-clip-v1/` 的道路/地形局部裁剪与 `actual-context-verification.json` 可作为接缝所有权检查输入，但本轮未解码其 GLB，不提升为当前视觉通过。

### `bai_canopy_finish` 对应磁盘检查点

本轮协作状态显示此所有权任务已停止并保留检查点。当前定位到的核心成果在 `docs/hangzhou/audit/bai-camera-canopy-20261111/`，它们是问题复现与定位证据，**没有找到同范围修复后布点清单或当前资产浏览器验收**。

| 文件 | 已证明的内容 | 仍缺 |
|---|---|---|
| `placement-proof.json`（3,919 B） | 树根位于实际铺装面内，距铺装边界约 1.25656g；树根高 4.5g、铺装 5.1g，低垂叶冠覆盖可步行面 | 修复后的树点/朝向/LOD与铺装、身体、镜头联合检查 |
| `reproduction.json`（24,175 B） | 从历史异常帧关联到树实例 index 54483，引用实际 willow GLB 与 float32 实例变换 | 异常帧 pitch、距离、bob 未被记录，不能宣称精确复现原摄像机；GPU遮挡仍欠验证 |
| `actual-local-paving.json`、`actual-willow-world-triangles.json` | 局部实际网格证据路径 | 后者超过本轮小文件阈值，未载入；不是修复产物 |

`docs/hangzhou/research/vegetation/` 已有八树种、三 LOD 的原型证据与集成契约；`artifacts/cities/hangzhou/vegetation-v2/`、`planting-v2/` 有独立产物。这只能证明原型/布点管线存在，不证明白堤该树点已重放修正。保留桃柳、山林树种的来源边界；逐株位置、树高、冠幅没有调查数据时仍为 estimated。禁止以删除整片林冠代替局部布点与镜头问题修复。

## 灵隐：五殿已在旧链，附属建筑仍为独立候选

### 当前可复用的模型与明确拒绝项

- 五殿：`artifacts/cities/hangzhou/landmarks/lingyin-site-v2/lingyin-temple.glb`，库存报告 29,784 三角、2,061,944 B，SHA `6cbf09ee75b744c8350e5a396b7164ac5e5fafc587007e4a2fa705439a24b4bf`；五个 source ID 已绑定。它是五殿外壳、估计台阶/平台和有限文字几何，不是全寺。
- 附属模型：`artifacts/cities/hangzhou/lingyin-context-v1/export-v2/lingyin-context.glb`，交付报告 30,423 三角、2,179,632 B，SHA `71269a6f01ae42a05c25ee6fe6a653e64c841c1b213476398e37025507d8d43c`，31 个来源 ID 映射 30 个唯一实体。`integration-contract.json`、`delivery-manifest.json`、`export-v2/glb-validation.json` 为当前交接入口。
- **拒绝 export-v1**：其 relation/9388591 与 outer way/676045757 重复发几何并覆盖内楼。v2 保留关系内环，outer 仅为名称别名，`way/676045758` 独立发几何；不能把内环解释成已证实露天院落。
- `lingyin-context-batched-v1/context.glb` 是上述 export-v2 的材质合批候选，907,728 B、同 30,423 三角，primitives 157→9；`batch-report.json` 记录属性/材质/解压三角一致，`browserAccepted=false`。节省 primitives 不是 FPS 或显存实测。

### `lingyin_finish` 对应接地检查点与 blocker

`artifacts/cities/hangzhou/lingyin-context-v1/ground-contact-v1/` 已有后续接地证据，不能只停留在较早 README 的 demo-v3 采样：

| 路径 | 已有成果 | 未完成项 |
|---|---|---|
| `input-lock.json` | 主绑定明确为实际 demo-v10，分别保留 demo-v3 与 render-input-v10；模型/spec 哈希明确 | 不能把 render-input-v10 代替当前服务地面；后续 v13 场地覆盖需重新绑定 |
| `served-runtime-validation.json` | 2,431 个采样与服务端快照计算一致；实际基础地形 183 个局部投影三角覆盖这些点；最大网格/采样差约 0.03623g | 报告明确是 CPU 验证；该局部没有 terrainCuts、terrainPatches、walkFloors、solidSlabs 或 roadSurfaces。不是入口已接入 |
| `entry-support-proposal.json` | 独立局部 walkFloor/实体等提案 | 状态明确不得当完整入口网络安装；还需合法路径、台阶、坡地、碰撞和上下层关系 |
| `building-ground-options.csv`、`foundation-audit.json` | 逐栋接地选择/旧高裙边问题保留 | 灰色实心裙边不是实际高台；禅堂旧 baseY 与最低采样地面差可达 5.4968g，仍须设计与证据约束 |

模型来源边界：仅罗汉堂总高 25 m 来自寺方 reported，其余 29 个实体高度 estimated；完整屋顶形制仍有 25 个 unknown；没有每栋两方向完整配准。伽蓝殿、客堂、济公殿等有部分寺方照片依据；旧售票房当前用途 unknown，不应加“售票处”新牌。照壁有图片，但无精确地理落位；不得补造寺界/山门。原图没有贴图授权，候选未打包照片。

碰撞与排重必须同时处理：`integration-contract.json` 要求精确 31 IDs 从基础楼、近景立面、屋顶装饰、旧高楼碰撞、通用高处招牌中排除，保留原五殿。不能用 100 m 圆或整块寺区删除；不能在 0.60 已施加的绝对游戏坐标上再次缩放。合同 `physics.status=pending`、`physicalEntryVerified=false` 仍适用。

`cpu-*.png` 和 `cpu-visual-review.json` 是 CPU 深度投影及带开放问题的审阅；不含完整地形/五殿场景，不是游戏截图。本轮只盘点文件，不做新的视觉复核。当前新附属模型的俯视、街面、远景、昼夜、接地与入口实机截图仍缺。

## 西湖附属建筑：v2 已有，合批与放置不能混用

### `westlake_finish` 对应成果

协作状态显示该任务已停止并保留磁盘检查点。`artifacts/cities/hangzhou/west-lake-context-v2/` 是本轮应优先复用的新版候选，而不是重新制作同一七个足印：

- `west-lake-context.glb`：41,634 三角、2,196,780 B、47 meshes、12 材质、0 贴图；`model.json` / `actual-glb-validation.json` 记录 SHA `76d352c4a6ef231c949af127ebfbba349ce926229b84550d9f3eaa246f4b0650`。
- 范围：明鉴楼 `way/1466923702`；白苏二公祠四个足印 `way/830131766–830131769`；蒋经国旧居两栋 `way/706867392`、`way/706867393`。这些是来源支持/部分身份推断的七个候选，不是整个西湖建筑普查。
- v2 改进明鉴楼屋顶、上层退台、侧翼屋顶与弧形阳台。`actual-six-preservation.json` 证明其余六栋实际顶点/索引/材质/变换保留；不能把整个包称作六栋全新复原。
- 现有 `artifacts/cities/hangzhou/west-lake-context-batched-v1/context.glb` **输入是旧 context-v1**，34,384 三角、755,884 B，SHA `ed4aa65a90539a23aa81d998fa700aabf68be03a9f1e9cccbe6de8344b0a357f`。它不含 v2 明鉴楼改进，不能因名字相似直接取代 v2。

### 不能放入真实主城的未定位组件

`unplaced-kits.glb` 有白苏门、廊模块和三处解释性标识，387,760 B；`component-manifest.json` 明确 `anchorGame=null`、`runtimePlacementEnabled=false`、`cityIntegrationAllowed=false`，要求新版本先核对场地锚点与朝向。

门洞尺寸、廊开间只是照片比例估计；一侧长廊在航拍可见，另一侧被树遮挡，不能对称复制。三块地面牌是使用有来源名称的新解释牌设计，不是现状历史标牌复原，也没有入口箭头和开放状态证据。应保留组件成果，先补真实落位，不得把展台偏移坐标直接当主城坐标。

`evidence.json` 明确三处建筑绝对高度没有实测；使用 2020/2021 和未定日期/2022 目录照片，2026 状态未核实。`actual-*.png` 是实际 GLB 的 CPU 投影，`*-candidate.png` 是候选 CPU 图；它们不补足新模型主城接地、碰撞、入口、昼夜和性能验收。其余约 65 个源对象仍保留 unknown 任务记录，不能统一降高并伪造身份。

## 精确排重、装饰与 AO 已准备到哪一步

| 产物 | 状态与范围 | 接入前注意 |
|---|---|---|
| `context-exclusion-input-v2/scenic-context.json` | 精确 35 IDs：灵隐 31 + 西湖当前基础楼中存在的 4；声明不改服务资产 | 与新版模型及目标候选重绑，不按景区半径删楼 |
| `scenic-base-exclusion-v1/exclusion-report.json` | 基础楼与近景立面排除候选 `pass=true`，源为 demo-v10 | 不代表已换模型/碰撞/地坪；不要与旧 `lingyin-base-exclusion-v2` 顺序叠套后丢失来源 |
| `scenic-decor-exclusion-v1/decor-exclusion-report.json` | 屋顶 props、lookup、通用标牌排除候选 `pass=true`；`browserAccepted=false` | pending 仍包括 AO、旧碰撞移除、替换模型、接地和浏览器验收 |
| `scenic-ambient-input-v1` / `scenic-ambient-bake-v1` / `scenic-ambient-runtime-v1` | 后续 AO 候选确实已存在；`scenic-ambient-locality-v1-20261111.json` 记录局部范围外字节保持等离线检查通过 | 不应仅因早期 decor 报告仍写 AO pending 就说没有 AO 成果；但没有主城安装/浏览器验收。运行包报告 mipmap GPU 预算约 90.2 MB，不能在压力 2 时盲目加载 |

西湖另三栋 `way/706867393`、`way/830131766`、`way/830131768` 在旧候选被过滤，见 `west-lake-context-v1/integration-candidates.json` 的 `proposedRestoredSourceIds`；35 条旧楼排除清单不包含它们并非自动漏项。模型语义/物理中仍需保留七栋身份；如果目标基础资产重新生成、三栋重新出现，应重新检查精确排重。该合同 `applyAutomatically=false`，不是运行数据。

## 下一步串行接入清单

当前压力 2 时仅保留以下可执行交接，不启动任何构建或实机加载。资源恢复并经过根线程统一调度后，按局部顺序推进：

1. **冻结目标及继承关系**：以 `westlake-bicycle-v1/candidate.json`、其小型 `geography/manifest.json` 和现有 v12/v13 保护记录为输入，在新隔离候选绑定模型/场地/排重版本。杭州当前坐标原点 `[120.155,30.274]`、east 系数 `96220.11856153939`、north 系数 `110857.07311230902`、scale 0.60，来自 v13 自身 manifest；不能套用旧深圳原点或二次缩放。
2. **先修 P1 到达区的白堤局部**：以 `bai-camera-canopy-20261111/placement-proof.json` 和原实例/实际铺装证据定位布点；保留既有桥面与六段源权限。分别记录改后的树点、低垂冠/身体与镜头遮挡，而非只改镜头近裁面。新码头接岸面仍须另行核对，见本目录 `docks-evidence.md`。
3. **西湖七栋主模型**：使用 `west-lake-context-v2/model.json` / `actual-glb-validation.json` / `actual-six-preservation.json` 作为输入证据。需要合批时从 v2 新做保留属性与三角门禁，禁止复用旧 batched-v1 冒充 v2。先处理基础 4 栋排重与 3 栋恢复，再绑定七栋低层外壳碰撞、接地与 AO；未定位 kits 保持关闭。
4. **灵隐逐栋接地而非整体升降**：保留五殿，使用 context export-v2 的精确 31→30 身份映射；优先罗汉堂 `way/195072255`、旧售票房 `way/195189679`、伽蓝殿 `way/435009581`、客堂 `way/435009582` 的 `ground-contact-v1` 局部输入。先补真实/估计边界清楚的台阶、挡墙和前场，再接闭合外壳与步行支撑；不能把局部入口提案安装为完整寺院通路。
5. **统一排重链**：重新核对 `scenic-context.json`、base/facade、decor、AO 对同一目标版本的输入哈希；旧高楼碰撞必须移除，替换模型碰撞按唯一实体重建；保留 unrelated/source-unknown 对象，不扩大删除范围。
6. **补当前资产验收**：每处保存来源对照与当前俯视/街面/远景、白天/夜晚截图；白堤实际步行和骑行权限、码头步行到达、灵隐公共路停车—步行入口、模型接地和相机遮挡分项验证。真实从道路进入，不以调试瞬移跨过缺口；同时记录冷启动、内存、帧时。失败维持具名 blocker，不能把历史 v8 通行或 CPU 图转录为新模型通过。

## 本次检查范围与保留事项

已检查的是小文件内容、清单指向与目录存在性，没有重读 `city.json`、`landmark-detail.json`、大型 spec/mesh JSON 或解码 GLB。`ground-contact-contract.json`、`ground-probes.json`、`exported-base-probes.json`、`source-faces.json` 等大输入保留原路径，未来须在资源预算内按局部读取；没有在本轮补造其结论。

所有权任务名称只用于追溯已保留成果，不表示任务最终完成。当前可确认的结束状态是停止并保存检查点；本报告不将 `bai_canopy_finish` / `westlake_finish` 名称中的 finish 当成验收标记。`lingyin_finish` 的接地文件按实际内容盘点，不推测未落盘工作。

本轮唯一写入为本文件。未更新计划、状态表、总清单或运行资产；没有宣告主城、西湖、白堤或灵隐验收完成。
