# 大莲花第二轮：主体育场来源绑定候选

本包只包含大莲花主体育场的花瓣罩棚、开口、简化看台与代表性内场。小莲花、博览中心、周边步行桥、广场架空平台、博物馆/商业和地下空间均不是本模块。当前阶段为 **evidence-ready**；CPU 几何与三视图草图不代替实际 GLB、实机、材料和地面验收。

## 来源与身份

建筑师为 [NBBJ](https://www.nbbj.cn/work/hangzhou-olympic-sports-center/) 与 **CCDI 悉地国际**；[设计方项目署名与参数](https://www.archina.com/index.php?g=works&m=index&a=show&id=3484)已通过实际 HTML 阅读核验。这不是 CCD 室内设计公司。ARCHINA 自称第三方项目提交平台，文中 CCDI 署名可追溯，但不写成官方测绘文件。[景区运营公司页面](https://www.bjatzxjq.com/)和[亚运官方转载](https://www.hangzhou2022.cn/hzhyn/mlhz/202105/t20210514_26126.shtml)分别支持主体身份/运营参数及 28 大瓣、27 小瓣。

采用固定浙江 Geofabrik `zhejiang-261011.osm.pbf`，OSM 时间 `2026-10-11T20:21:06Z`，SHA256 `4eb65f64925498408faeee7eb04b60d7eb8a01c49ddb239f73070d4d282c75a9`。地理位置来自 WGS84 OSM，未使用商业地图坐标。实际模型尺寸使用杭州公共坐标配置，并统一缩放 0.60 一次。

主关系 `relation/8718531` 的外圈成员 `way/626832662` 与内圈成员 `way/626826721` 已逐边对照辅助 OSM API 快照，拓扑一致。外圈面积矩边界约 **330.79 × 276.57 米**，内圈屋顶开口约 **194.93 × 144.92 米**；锚点为内圈面积质心 `[120.2243820151114,30.23168281200902]`，开口长轴东逆时针 **90.4885°**，近南北。外壳面积矩方向不同约 4.24°，模块保留原始边界的径向变化，不把两圈粗暴统一成一个椭圆。所有尺寸均为在 OSM 上计算的值，精度未知，保留计划用 ±5 米、轴向 ±2° 容差，不能写成现场测量精度。

## 采用参数与保留差异

| 项目 | 分类与取舍 |
| --- | --- |
| 28 大瓣、27 小瓣 | `reported`，设计方与亚运官方一致；实际建模分别生成 28 与 27 个薄壳 |
| 59.4 米 | `reported`，运营方建筑高度；候选以中性基面使用该值 |
| 60.7 米 | `reported`，设计方罩棚最高点**结构标高**；与建筑高度的基准关系未知，未强行平均 |
| 地上 6、地下 2 层 | `reported`，运营方；模块只表现罩棚后立面及碗体，不声称完整八层室内 |
| 80,800 / 80,912 席 | 两来源时期与范围不同，均保留；候选看台色带不是逐个座椅的精确计数 |
| 三层看台 | 实际官方室内照片可见；高度、径向进退、座位配色与简化排数为 `estimated` |
| 花瓣曲面、卷曲、宽度、接缝、桁架 | 多视角图像支持形体；曲线数值与厚度仅作估计，误差和方法见 `spec.json` |
| `height=2`、部分屋瓣 `height=26` | OSM 标签未核实，不用于全体育场高度；内圈 `height=3/min_height=2` 不作为场地基准 |
| 总面积与地块面积 | 运营及设计方范围不同，不能代入屋顶足印面积；NBBJ 37,000 平方米的项目字段范围也未确认 |

`photo-review.json` 记录 10 个实际查看的图像参考；其中两张为重复照片裁切/尺寸版本，一个为设计平面图。实际街面、远侧、空中和室内视角均有记录，拍摄时间与精确相机方位大多未知。不把上传年月当拍摄日期，也不把设计图方向当 WGS84 方位。公开照片只用于视觉参考，未复制到发布包或制成贴图。

## 候选与检查

独立模块为 `scripts/landmarks/big_lotus.py`，入口 `build(b,lm,spec,scale=.6)`。无需独立 `bpy`，不初始化场景，保持传入 B frame；`lm.x/z/y` 为游戏单位，真实米制参数才缩放。模块使用现有 10 个材质别名，主集成人员仍须核对与照片一致的哑光白色覆面、半透明百叶和红蓝座椅；CPU 草图调色板与 Babylon 材质不同。

当前 CPU 统计：**13,887 faces / 27,854 三角形**，固定预算 28,000 三角形 / 10 材质，无新增灯光或水面。实际 GLB 大小、三角形、材质、碰撞与帧时由串行导出后验证。有效检查包括原足印顶点与 WGS84 投影吻合、0.60 单次缩放、游戏基面平移、frame 恢复、重复缩放拒绝、五条中央下射线直接到达内场、罩棚实际射线相交、候选中性基面入口缝未用实心圆柱封闭。

`cpu-top.png`、`cpu-street.png`、`cpu-distant.png` 是 Pillow 将纯 B 面投影的**CPU 草图**，不是游戏截图。当前已查看：椭圆形主体、独立尖端、卷曲覆盖、罩棚开口与三层碗体可以辨认。曲面仍为低分段估计，接缝/遮挡投影存在绘图近似；不能据此冻结现状外观、材质、正反面运行时处理或性能。

```sh
.venv/bin/python docs/hangzhou/research/core/big-lotus-round2/validate_cpu.py
.venv/bin/python scripts/landmark_tasks.py check --job docs/hangzhou/research/core/big-lotus-round2/task-bundles/big-lotus/job.json --stage evidence-ready
```

CPU 草图可用带 Pillow 的 Python 运行 `preview_cpu.py`。当前使用已配置的 Codex workspace dependency runtime，未修改锁定依赖。冻结脚本需要指定源快照和临时下载参考仍在，运行后会重写本轮调查 JSON；不要在已导出冻结状态下盲目覆盖。

主集成实际导出命令（本 worker 未执行）：

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python scripts/build_hangzhou_landmark_candidate.py -- --job docs/hangzhou/research/core/big-lotus-round2/task-bundles/big-lotus/job.json --spec docs/hangzhou/research/core/big-lotus-round2/spec.json --module scripts/landmarks/big_lotus.py --output artifacts/cities/hangzhou/landmarks/big-lotus-v1
```

## 串行集成待办

`sourceFeatureIds` 与 `baseBuildingIdsToExclude` 精确列出主关系、内圈 part 和 39 个实际映射花瓣，共 **41 个建筑要素**。这些源足印及各自哈希/包含关系在本包中，可用于基础楼体与近景立面同步排除。39 个 OSM 屋顶片段不代表只有 39 片实际花瓣。**不排除 `way/626826731`**，它位于主体育场东侧网球区；不以整个奥体包围框删除楼体或道路。

下列事项继续 pending：真实基面和架空平台/坡道/步行桥，59.4/60.7 高度基准，精确花瓣相位和北端大开口，真实签名入口与到达道路，精确幕墙/百叶/招牌，周边地势和碰撞，当前赛事/草坪配置，夜景灯具控制及实机三视角/性能。27 小瓣分布中少一个间隔的相位是估计，并未确认成实际北入口。八项正式 validation 均保持 unknown。不能把本包称为全体育场已完成或 GTA_HZ 已验收。
