# 原型串行集成说明

本目录与 `scripts/landmarks/hangzhou_tree_palette.py` 为唯一对象所有权；没有写共享布点、场景或总GLB。

1. 每份 `prototype-specs/<species>-lod<N>.json` 只建一个可实例化局部原型。父Blender构建器初始化一次场景/材质后，加载纯模块，调用 `build(B(),{'x':0,'z':0,'y':0},spec,.6)`，再 `finish(<species><suffix>,smooth=True)` 并独立GLB导出。full/mid/far suffix依当前runtime分别为空/-mid/-far；保持已有Y-up和runtime镜像处理。不要将24个模型合成一个失去物种/LOD边界的总网格。

2. 可使用已有默认M材质导出；若需CPU图中的色彩，父构建器先遍历 `material_definitions()`，用 `city_mesh.material(name,color,roughness,metallic)` 注册七个共享哑光色槽，然后给spec.materialMap传 `{slot:definition.name}`。注册应在一次串行构建初始完成，保持材质/光照身份稳定，无帧内重新配置，无透明排序或新灯。默认秋色/花槽落到已有绿/灰材质，仅为可运行fallback，不是颜色验收。

3. `build` 返回实际CPU triangles/materials与 `heightGame/crownRadiusGame`。导出后读取GLB实际triangles/meshes/bytes/高度再写model清单，不把CPU文件计数或预测字节当GLB stats。尺寸只在build中×0.60一次；runtime manifest/species.height/crown使用游戏单位，实例仅乘variation scale/yaw，并沿现有heightAt求地形。主布点的米制半径应先统一转换到游戏单位，不得一套半径用实米、一套用游戏米。

4. root按整体调度维护city-canopy顺序加载、thinInstances、统一颜色变化、重建门限、预算降LOD和剔除；本模块没有运行时重写。新八种canonical IDs不要沿用深圳species整数索引去读旧planting，必须父集成串行生成对应species表/placements并验证索引和asset路径。保护原8m街景文件与其哈希，若需新低层tree配置使用独立候选后接入。

5. `palette-spec.json.scenes` 是source-informed候选选择，不是概率或普查：西湖桃柳；城区樟/悬铃木/银杏/枫香；公园桂花/桃低层；山地樟/枫香/马尾松。对已有 source-certain 路段采用对应历史/规划树种时，仍核对现状；不能仅凭paper2014任意逐株指定“实测悬铃木”。OSM点无species标签时保持 inferred/estimated，具体数组位置来源、哈希、坐标系另存。

6. 冠半径真实包围每个LOD，但树枝/叶冠可能低垂。尤其willow在湖岸可用，在汽车路边要预留叶帘和镜头通行空间；桂花低圆冠也需更大道路/建筑退让。保留主干道24m带内原有分档/成簇留窗、两侧独立和基于实例scale的整个冠圈避让思路，准确常量单位由父城市适配层统一，避免再写孤立硬坐标。

7. 春/秋/冬仅作者可选静态资产，不假设运行时已有季节机制。默认summer。需要不同季相时另导出明确版本和资源预算，防止同时加载所有季相增加GPU常驻；当前精细花/叶密度与2026物候未通过，尤其近景花簇不作测绘或植物摄影真实性声明。

8. root串行验证所有24个GLB、昼夜/雨天、树冠与室内/地标/桥面/水域接合、驾驶镜头/无人机/飞机层级切换和LOD弹跳，实测cold boot/内存/帧时。CPU轮廓IoU只是结构门槛，不能填最终silhouette/browser/performance pass。

9. 精确本地树数、密度、个体高/胸径/冠幅及原生生态群落范围unknown；广西/上海或杭州远郊样方的数字不挪给本主城区。没有任何源照片贴图。研究目录references网页/PDF版权未核验发布授权，游戏公开包排除并保留引文事实/哈希。

## 银杏焊接修复交接

旧vegetation-v1银杏full实际1052tri与CPU1112不符，候选被拒收，不能复用为本版。`ginkgo-weld-fix-report.json`记录60反向重复面的诊断；新模块用12个4mm作者厚度的封闭扇叶，每叶24tri，共288tri，full1280tri。mid244/far120及其余23个summer原型预算/尺寸不变；spec/palette哈希未改。保持原smooth=True/weld策略重导出至新候选目录，逐GLB索引三角数应与新CPU统计一致，若仍不符则保留失败并继续查因。CPU17检查不等于导出/视觉通过；不得以smooth=False隐藏未解释的面数差异。
