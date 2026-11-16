# A 区当前源对象：主集成串行接入

当前为 `evidence-ready` 的12源对象外观候选，不是全部现代A校园或历史六单元交付。子任务没有Blender/GLB/浏览器结果。待主集成在新空目录执行：

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python scripts/build_hangzhou_landmark_candidate.py -- --job docs/hangzhou/research/ali/alibaba-a-round2/task/alibaba-a/job.json --spec docs/hangzhou/research/ali/alibaba-a-round2/spec.json --module scripts/landmarks/alibaba_a.py --output artifacts/cities/hangzhou/landmarks/alibaba-a-round2
```

mesh prefix `detail_alibaba-a_`。CPU23,912三角形、7已有材质不代替真实GLB统计；导出后登记实际hash/buildCommand并推进modelled。软件检查不替代屋檐/玻璃/孔洞/PBR昼夜的具名视觉评审。

接口 `build(b,lm,spec,scale=.6)` / `ground_footprints(lm,spec,scale=.6)`。WGS84尺寸保持米制，模块仅缩放一次；lm.x/z/y是游戏单位。城市投影来自city_config，标记点lon/lat不同时使用源偏移恢复真实落位，frame在成功/异常恢复。保持现有Blender东/北/上→GLB Y-up→Babylon方向，不追加整体旋转。

基础buildings和近景facades双排除仅以下12IDs，各外环/内环都已逐点match：

```json
["relation/6750407","relation/6750408","relation/6750409","relation/6752573","relation/6752574","relation/6752575","relation/6752593","relation/6752592","way/642355049","way/642355050","way/642355051","way/642355052"]
```

不得排除 A9 way/456731145、整个A地块645135612、B/C、停车楼/商城/总站/遗留院落/服务对象。A9身份/建筑师/现状与高度仍blocker。地图A1–A8仅当前mapped标识，historicalUnitNumber和phase全部null；不能把当前八个物体冒充一期六单元，不能将官方平面功能图例数字当楼号。

地面碰撞使用mapped办公实体减mapped孔洞、links只有估计支柱；11源内环不能被基础楼体/近景立面/碰撞/屋顶重新封堵。A1–A4源无内环，玻璃屋顶条是外观估计，不为它创造地面可通行院落。Links起底6m、顶14.5m、斜折2m均候选估计，building:min_level2不能证明净高。主集成实走/实驾检查桥下支柱和路面基准，不能靠整园区圆形碰撞绕过这一步。

所有本体采用candidateBase0m与lm.y游戏高度；不能再乘0.60或把OSM层号当海拔。院内水面/湿地进入基础water管线，本模块没有水薄片。公园、家具、近景植被/实际入口/台阶由世界集成结合source地面衔接安排。职业/故事目标取经过原道路图核实的外侧可达点，避免校园anchor、楼体、未知门洞和水中。

实机重点：KKAA照片MG6222/MG1636的斜橙檐、MG0866双层V桁架、MG1352镂空织网、MG0643湿地侧主楼和001街面长立面。检查薄面正反向、镂空远近可见性、gold比真实橙色偏暗的差异、main银色挑檐/玻璃折面。当前照片每面地理配准与全侧材料仍pending，不为夜景捏造灯。若现有GLB加载强制背面剔除，编织薄面需单独实机看上下两侧，不能只凭CPU俯视通过。

至少保存当前GLB俯视/街面/远景+昼夜，复核双排除哈希、尺度/朝向/结构/碰撞/可达路、真实浏览器控制台、内存/冷启/帧时。当前未改全城材质/灯光/反射/特效资源池，不借深圳历史FPS和截图宣布通过。

研究照片©Sadao Hotta/KKAA只作本地参考，无游戏纹理/公开再分发授权；发行包保留事实链接与署名，排除研究JPG。程序几何遵循工程MIT；OSM数据保留ODbL与贡献者署名，既有材质按原许可。
