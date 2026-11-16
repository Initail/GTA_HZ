# 断桥单拱与引道候选

有限范围 `evidence-ready`。来源、独立 B 模块与 CPU 几何检查已经交付；本轮未启动 Blender 或浏览器，未生成 GLB，实机/步行/碰撞/性能仍未验收。水面只由主城市基础水体管线负责。

## 地理身份与桥体范围

固定 Geofabrik 浙江数据 timestamp：`2026-10-11T20:21:06Z`，EPSG:4326，ODbL 1.0。原 PBF SHA256：`4eb65f64925498408faeee7eb04b60d7eb8a01c49ddb239f73070d4d282c75a9`。

`road way28538289` 与 `area way1466925249` 都标为断桥，分别具有 `bridge=yes` 与 `man_made=bridge`，共享南端原始点，北端亦对应同一走廊。原道路线节点 `26315533` / `13454786643` 连通白堤 `way28538286` / `way28538290`。`geofabrik-bridge-features.geojson` 保留这些真实源对象、原节点 ID 和属性。

道路约长 122.6366 米，朝向北顺时针约 36.6889 度。该线面描述的是包含引道的长廊；不能把资料中 8.8 米拱体拉伸成 122.6 米。锚点为道路线端点中点 `[120.14703035,30.26090085]`。测量仅发生在 OSM 数据上，源精度未知，规划容差取±5米/±3度。OSM 边界宽度约 7.7–11.4 米，不能直接当作现状铺装净宽。

原始 [UNESCO 提名文件](https://whc.unesco.org/uploads/nominations/1334.pdf)已实际下载并按 PDF 技能渲染，SHA256 `5a82da9397cc7eafae35ffff8060c45c0751f6da2d5c8b40ac38ce08ad32c442`，79,121,258 字节 / 1,342 页。打印页 105（PDF 第100页）给出单孔半圆石拱、矩形条石、缓坡沥青路面和拱体长8.8米/宽8.6米/净跨6.1米。打印页112–113（PDF107–108）的图2a-59/2a-61可见长引道与近中部小拱孔，并有北箭头、尺标。这里记录 reported 值，没有称其为本轮现场实测。

## 形体与估计

模型包含一处小半圆拱孔、连续缓坡沥青桥面、石桥台、分段拱券和石质栏杆。没有断裂路面，没有水薄片，没有公园地台。`spec.estimates` 明确估计方法和误差：

| 参数 | 候选值 | 依据 / 误差 |
|---|---:|---|
| 拱位（从南端计） | 45%走廊 | 纵立面比例估计，±5%（约±6.1米） |
| 拱脚相对端点 | -1.5米 | 图与照片粗比例，±0.7米；真实高程未知 |
| 拱券厚度 | 0.60米 | 图中比例估计，±0.25米 |
| 铺装厚度 | 0.20米 | 几何估计，±0.15米 |
| 拱顶桥面高于端点 | 2.35米 | 前述候选关系，约±0.9米 |
| 栏杆高 | 1.0米 | 图与成人尺度粗比例，±0.25米 |
| 栏柱间隔 | 2.7米 | 立面重复节奏，±0.7米；实际根数未知 |

政府[2018年夜雪侧向图](https://www.ehangzhou.gov.cn/2018-06/14/c_242889.htm)和[2020年湖面侧向图](https://www.ehangzhou.gov.cn/2020-06/05/c_271613_2.htm)已实际查看，补充长坡、完整桥体和小单孔关系；[2023年入口夜景](https://www.ehangzhou.gov.cn/2023-08/17/c_286564.htm)确认连续步行坡面及路灯，但人群遮挡了精细构造。没有 EXIF 或相机标定，照片不宣称精确方位/摄影测量。旧申遗图与这些照片不是2026年现场测量。来源 URL 和临时缓存哈希见 `photo-review.json`，不交付原图/贴图。

## 构建与检查

模块：`scripts/landmarks/broken_bridge.py`，接口 `build(b,lm,spec,scale=.6)`。真实尺寸只乘0.60一次；`lm.x/z/y` 是已有游戏单位。桥面两端严格落在原道路线节点对应位置，高度均为 `lm.y`；`B.frame` 恢复。保持 Blender 东/北/上 → GLB Y-up → Babylon 的既有方向处理。

本轮实际执行并通过：

```sh
.venv/bin/python scripts/landmark_tasks.py check --job docs/hangzhou/research/core/broken-bridge-round2/task-bundles/broken-bridge/job.json --stage evidence-ready --record
.venv/bin/python docs/hangzhou/research/core/broken-bridge-round2/validate_cpu.py
```

CPU 结果：3,613面 / 7,226三角形（导出前 fan 计数）、3材质、0灯光、0水网格。检查了非退化/有限坐标、真实WGS84端点、单次缩放、基面游戏单位、frame恢复、资源预算、单拱穿桥射线畅通、邻接桥台存在及拱上连续坡面。首次13,806三角形超出12,000暂定预算后，将石缝标记从闭合棱柱改为朝外立面标记，保留桥体/栏杆/拱孔检查后通过。未提高预算或跳过检查。

供主集成串行导出（本轮未执行）：

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python scripts/build_hangzhou_landmark_candidate.py -- --job docs/hangzhou/research/core/broken-bridge-round2/task-bundles/broken-bridge/job.json --spec docs/hangzhou/research/core/broken-bridge-round2/spec.json --module scripts/landmarks/broken_bridge.py --output artifacts/cities/hangzhou/landmarks/broken-bridge-v1
```

## 主集成与未通过项

保留 `way28538289` 导航连通性；若基础平路面与坡面叠置，应仅抑制该基础视觉条带，不删除拓扑。模块返回 `deckProfileMetres` 和 `deck_height_metres` 函数，主集成需据此绑定步行地面/碰撞；不能将射线 CPU 检查写作浏览器步行已通过。

该源路为 pedestrian，明确禁止 motor_vehicle/motorcar。职业/导航车辆到达应选允许车辆通行的附近道路，再步行转移；北端源节点可作为待验证的步行交互点，不应把拱体中心填成已验收汽车目的地。

真实端点/水位高程、当前拱位、精细栏杆、两侧石桥台入水、碑亭/水榭/景观、路灯与夜景、正式GLB、实机俯视/街面/远景、碰撞、到达点及帧时/内存均 pending。`validation.json` 八项保持 unknown。代码及既有材质沿用项目许可；政府照片和提名图版权未获发布贴图授权，均只作参考。
