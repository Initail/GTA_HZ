# shore clip v3 独立实际GLB审查

2026-11-11。**限定 CPU 几何检查通过**：原始三维相交836→楼坪v2下625→岸体裁切v3下0。实际四组GLB无退化面、无未配对有向边；另外三岸有向世界三角集合精确保留。没有启动Blender/browser，没有修改共享源码/数据/资产。

绑定实际 `artifacts/cities/hangzhou/shore-glb-v3/coastal-shoreline.glb` SHA256 **0c683dd694ac4a3b5b19fbd46cabb330fb81775c474cb0a6536cdc86bb66d65c**，20,076 triangles、847,272bytes、4mesh。实际城市阳台 `floor-v2` SHA256 **731066a06278848025c19153584eae7539e0ba7a73db49540e6eb7679ff67757**。producer manifest、源码、原NPZ manifest、冻结ownership与所有mask哈希均另行核对一致。

## 实际几何检查

| 项目 | 结果 |
|---|---|
| 滨江有源挡墙 | 8964 triangles，原有向世界三角集合精确不变 |
| 滨江公园 | 3148 triangles，原集合精确不变 |
| 奥体 | 3812 triangles，原集合精确不变 |
| 城市阳台岸 | 4152 triangles，局部cap和柱扣除；闭合、有向边成对、正体积 |
| 所有实际mesh | 0退化面、0未配对边；UV/法线有限，UV三角0退化 |
| 三维相交复现 | 旧岸+中性阳台836；旧岸+floor-v2阳台625；新岸+实际floor-v2阳台**0** |
| 裁切外高度差 | 2453条射线最大1.406119e-6g |
| cap范围 | 1203条射线最大高度差2.464928e-8g |
| 柱洞 | 159条射线均空；距柱mask内边1mm范围投影残留面积0 |
| 受控边界 | 另8个距布尔边界1mm内的射线样本单列跳过，不记通过 |
| 源前缘 | 扣除柱所有权间隙后，最大边界偏移0.000052562g |
| 预期平面边界 | 排除派生数值伪孔后，Hausdorff约0.000038998g，低于固定1mm阈值 |

垂直射线以原实际岸实体的上下交点为基线：mask外保持原区间；mask内顶为`min(oldTop,1.5579020031420152g)`；柱洞为空。共3815个有效样本，失败0，不是只对比总面积或bbox。所有新顶点的cap、原底高、水平足印容差检查通过。

当前阳台岸被贯穿窄带的柱扣除分为两个闭合实体，因此组合Euler为4；这不是未封口。`connected-components.json`分别记录各组件拓扑和正体积。

原岸顶与新布尔切口使用float32，投影相对预期对称差约.0012564g²、投影外扩约.0012467g²，均已记录，不能宣称布尔后数学上的零坐标变化。三段无修改岸的三角集合则是精确保留。目标岸mask外投影对称差约1.96e-5g²，射线高度误差见表。

## 初次派生投影失败与解释

`check.log` / `validation-initial.json` / `csg-geometry-initial.json` / `check-initial.py` 保留首次检查失败：`footprintBoundaryMatchesExpectedWithin1mm=false`，原始Hausdorff=.059873697g。

独立诊断发现：把三维三角形投影后进行二维GEOS union，内部产生12个面积**5.17e-26至3.10e-25g²**的伪孔环。这些几乎零面积的环在.12g窄带中央，使“所有边界”距离虚报约半带宽。三维实际网格的边闭合检查与射线区间没有缺口。

只对**派生二维投影的边界距离度量**使用1e-10g精度归一化；伪孔消失后误差3.899811e-5g。1e-9、1e-8、1e-7g独立交叉诊断一致，记录在`projection-diagnostic.json`。没有改模型、mask、射线、三维相交算法，也没有放宽原1mm阈值。最终复验保留为`check-run2.log` / `validation.json`；原始数值仍在最终`csg-geometry.json`。

## 复现

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python docs/hangzhou/research/coastal-adaptation-round1/export-contract/shore-clip-v3-review/check.py \
  --new-glb artifacts/cities/hangzhou/shore-glb-v3/coastal-shoreline.glb \
  --manifest artifacts/cities/hangzhou/shore-glb-v3/asset-manifest.json
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python docs/hangzhou/research/coastal-adaptation-round1/export-contract/shore-clip-v3-review/diagnose.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python docs/hangzhou/research/coastal-adaptation-round1/export-contract/shore-clip-v3-review/components.py
```

实际3D比较使用独立GLB解码、节点变换、XY空间索引及三维边-面重心相交，复现历史两项失败数量后才对新资产判定。脚本没有读取producer声称的pass作为结果。

## 尚未通过

这只解除“实际岸体GLB与当前阳台GLB”的局部几何相交项。基础terrain仍需按冻结source masks切接；视觉与脚下采样若不采用一致的所有权，仍可能阻挡下层。人物上下层选择、入口/碰撞/落水、任务可达、实际日夜材质、三视角与性能未验收。不得把本报告升级成阳台、杭州城市或项目完成。
