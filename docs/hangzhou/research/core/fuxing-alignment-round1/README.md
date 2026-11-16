# 复兴大桥有限轴线修正候选

新模块 `scripts/landmarks/fuxing_alignment.py` 与本目录 `spec.json` 形成独立 CPU 候选。原三桥模块、规格、碰撞适配器和道路数据保持冻结。候选将原复兴主体作一次刚性平面变换，保留全部 14,592 三角形、3 材质、26.4/32m 桥宽、构件尺寸与原高度估计。源道路 WGS84、node 顺序、投影位置和高度表均不变。

相对固定数据，原模型轴线偏靠一侧车道。以中央 ±500m、每 10m 等距截面上的上层双向道路中点拟合，可得结构中心横移 **7.889m 实体米**、平面转角 **−0.04114°**。独立取下层两条外侧道路中点拟合，横移为 **7.884m**。两层可能使用相同底图，不能将数值接近解释为独立测绘；绝对位置精度仍 unknown。采用 ±5 实体米（.60 后 ±3 游戏单位）的游戏重建容差，是人为保守估计，不是测量误差或置信区间。全部样本、残差和采样窗口敏感性保存在 `axis-fit-evidence.json`。

宽度沿用陈宝春 2008 年原论文 p98 对小/大拱段 26.4/32m、上下层同宽的陈述；本次重新查看了固定缓存原 PDF 及图8，在线 PDF 复取超时未冒充成功。OSM 道路线按主车道/车行道中心抽象，不能直接视为桥面边缘，因此没有用公路线包围盒反推无限扩宽。[OSM 原生数据模型说明](https://wiki.openstreetmap.org/w/index.php?title=Way&oldid=3045544)。当前双层、两大九小拱的身份和照片也与[杭州政协公开资料](https://www.hzzx.gov.cn/zxyw/content/2026-09/20/content_9311674.htm)一致；照片不用于地理配准和贴图发布。

CPU 结果按全部七条道路审计，表中只统计原有限主桥内的横向缺口；主桥外引桥仍独立 pending。

| way | 层 | 原缺口节点/样本 | 候选缺口节点/样本 |
| --- | --- | ---: | ---: |
| 29169666 | 上 | 0 / 0 | 0 / 0 |
| 154135283 | 上 | 0 / 0 | 0 / 0 |
| 29170042 | 上 | 0 / 0 | 0 / 0 |
| **154135290** | 上 | **2 / 36** | **0 / 0** |
| 336983476 | 下 | 0 / 0 | **3 / 23** |
| 340648409 | 下 | 0 / 0 | 0 / 0 |
| **589429905** | 下 | **10 / 72** | **0 / 0** |

候选解决了指定两条 way 的主桥内横向问题，同时保留了另一条路新增暴露的 3 节点、23 样本问题。`way/336983476` 的 `3623284229`、`3440750971`、`3440750974` 分别在估计站位 −669.20、−649.86、+686.33m，距实际候选桥面约 2.294、1.908、1.570 游戏米。现有证据不能决定这是源描绘偏差、主桥局部曲线、岸端匝道/外扩，还是有限主桥站位误差，不能将道路判错、平移或禁行来过门。

最小可辨识且源中心点一致的核心为原估计站位 **[−416.9,+416.9]m**，约 **833.8m**，覆盖两座 190m 大拱与中央五座 85m 小拱；间隙和绝对站位仍沿用原估计，不是实测边界。渲染候选保留 1376m 有辨识度的主桥主体供比较，两端和全路径均未宣称通过。中心线点落在桥面内还不能证明完整车道、车体/人物宽度或可通行净空。

```sh
.venv/bin/python -B docs/hangzhou/research/core/fuxing-alignment-round1/validate_candidate.py
.venv/bin/python -B scripts/landmark_tasks.py check --job docs/hangzhou/research/core/fuxing-alignment-round1/task-bundles/fuxing-alignment/job.json --stage evidence-ready --record
.venv/bin/python -B scripts/landmark_tasks.py check --job docs/hangzhou/research/core/fuxing-alignment-round1/task-bundles/fuxing-complete-alignment/job.json --stage evidence-ready --record
```

真实结果分别为 exit 0、exit 0、exit 2。有限候选 evidence-ready；完整匹配任务仍 planned。没有导出 GLB、运行 Blender/浏览器，模型与实机验收保持 pending。接口和组装约定见 `integration-notes.md`；全部逐节点/样本结果见 `source-alignment-audit.json`，全道路前后对照见 `all-way-comparison.json`。
