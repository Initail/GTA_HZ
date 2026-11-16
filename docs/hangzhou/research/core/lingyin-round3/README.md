# 灵隐寺五殿独立基高与有限场地细部候选

本轮提供可供主集成调用的独立高度适配入口，以及局部殿前平台、挡墙、台阶、石栏、铺地、牌匾文字和代表性屋脊细部。五殿足印、朝向、既有形体及来源沿用冻结 round2。候选没有可证明的真实绝对地坪、连续寺院通路或全寺边界；场地接合和正式验收仍未通过。

新模块为 `scripts/landmarks/lingyin_site.py`，使用纯 B 接口，不导入 Blender。`build(b,lm,spec,.6)` 从 `lm.hallBaseYGame` 取得五个绝对游戏单位基高；也可以调用 `build_with_hall_bases(b,lm,spec,heights,.6)`。键必须完整包含 `kings`、`grand`、`medicine`、`dharma`、`huayan`，并且每值都有限。缺少、null、NaN 或重复缩放均在写几何前报错。

每个基高对应原五殿 **0.5 米台基的底面**；殿门槛候选高度为 `baseYGame + 0.5 * 0.60`。传入的游戏 Y 不乘 0.60，也不加 `lm.y`。X/Z 仍是游戏单位，原足印偏移和建筑尺寸仍是未缩放米值，只在同一处缩放一次。父集成可以把有来源的地面/门槛结果转换为这个基高接口；“有传值”不等于“地坪已经实测”。本规格五个值故意为 null，不能直接导出并假称接地。

`floor_height_game(x,z,lm,spec,hall_id,.6)` 只查询指定殿堂局部前台和生成的台阶。`ground_footprints(lm,spec,.6)` 返回实际候选实体的世界游戏平面多边形和 `minYGame/maxYGame`。石栏中央台阶口保留；原冻结殿体仍为闭合外壳，没有制造虚假的开门和室内通路。这两个接口仍需主集成与地形、地坪、角色控制器一起验证。

候选包含原五殿，集成时应替换原 `lingyin-temple`，不能把新旧殿体叠加。基础楼体/近景立面只排除以下五个来源，不整片删除寺院、山林或周边路径：`way/434365023`、`434365024`、`434365025`、`434366739`、`434366741`。售票房 `way/195189679` 不作为寺院，也不在本候选替换范围。

[寺院运营方 2011 年介绍](https://www.lingyinsi.org/detail_22_673.html) 与 [布局研究论文](https://www.wochmoc.org.cn/upload/file/202004/1588058384711036046.pdf) 支持天王殿、大雄宝殿、药师殿、法堂/藏经楼、华严殿的中轴次序。论文 PDF 第四页（印刷页 60）的现代图为进香线路图重绘，无地理控制点、比例尺和绝对高程；本轮没有用它描出 WGS84 寺界。同页表格是清代建筑尺寸，没有挪作现状数据。文件元数据创建日期为 2020-03-08，上传路径含 202004，刊期和原现场调查日期仍未知。

本轮实际复核了六幅运营方照片，涵盖殿前、斜侧、石台和屋脊近景，见 `photo-review.json`。牌匾转录为：天王殿“靈鷲飛來 / 雲林禪寺”，大雄宝殿“大雄寶殿 / 真如妙相”，药师殿“藥師殿”，法堂“直指堂 / 藏經樓”，华严殿“華嚴殿”。采用照片所见右向左次序，以 [Adobe Source Han Serif](https://github.com/adobe-fonts/source-han-serif) 的开放字体生成文字几何，保留 `SourceHanSerif-OFL.txt`。字形仅表达文字身份，历史书法、实际比例、彩绘和未辨认的上层匾额待核实；没有复制照片笔迹或打包照片贴图。

所有新增平台、台阶和石栏尺寸均为 estimated。照片没有标定镜头、真实步阶数量或地面控制点。局部前台宽度以冻结 OSM 屋面宽的 0.96 为建模约束，并不等于真实台基宽；深度、落差、步阶、栏板节奏的估计方法和宽泛误差写入 `spec.json`。步数由估计落差除以最大建模踢面 0.18m 生成，不是观察或测量所得。屋脊近景的具体殿堂未确认，新增弧形端头只作代表性细部，真实雕刻未完成。

`context-check.json` 对照了 terrain-glo30-v3：EGM2008、30m 原始 DSM、50m 实距采样。三次 3×3 min/max/mean 运算的依赖范围可达 7×7 样点、中心跨度 300m；它不是殿前地坪分辨率。药师殿与法堂在最近格点读到相同值，不能据此认定同高。每殿的实际阈值和实际步数均为 null；没有把 EGM2008 与黄海/其他高程基准直接混合。

CPU 检查通过，29,784 三角面、6 材质、0 灯、348 个有垂直边界的候选实体；正式 GLB 三角化仍由主集成核实。测试保证等基高时原五殿 B.face 输出逐项相同，单殿抬高不影响其他殿，WGS84 中心与单次缩放正确，台阶/前台查询匹配生成几何，错误参数在写几何前失败。初次 31,858 三角超预算已记录并修正，预算一直保持 30,000。新预算用于增加场地细部的独立 scope，原 round2 源模块/规格不变。

`cpu-top.png`、`cpu-street.png`、`cpu-distant.png`、`cpu-grand-plaque-close.png` 为实际查看过的原创 CPU 草图，使用明确虚构的高度测试接口。它们不是实机截图，也不证明地面、材质、昼夜、碰撞、路线、性能通过。八项正式验收均保持 unknown，没有启动 Blender 或浏览器。

复核命令（项目现有依赖，不导入 `city_mesh.py`）：

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python docs/hangzhou/research/core/lingyin-round3/check_context.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python docs/hangzhou/research/core/lingyin-round3/validate_cpu.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/landmark_tasks.py check --job docs/hangzhou/research/core/lingyin-round3/task-bundles/lingyin-temple/job.json --stage evidence-ready
```

实际待办保留在 `source-claims.json` 的五个 full-site blocker：地坪高程与基准、全寺真实边界、真实中轴台阶/连续路径、安全无障碍到达、完整装饰精度。冻结包是有限适配与细部候选的 evidence-ready，不是灵隐寺场地 verified，也不是 GTA_HZ 完工。
