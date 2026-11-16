城市阳台主挑台独立候选，2026-10-14。

本轮固定浙江 Geofabrik 2026-10-11T20:21:06Z 快照的 `relation/8718551`，以及三个内环对应的 `way/626826744`、`way/626826741`、`way/626826742`。WGS84 中心为扣除内环后的面积质心 `[120.21258014878033,30.24424700302543]`，长轴为从东逆时针 50.331189759°。源主轮廓约 28,348.8m²，最小旋转包围框约 325.1×162.9m；框含岸侧连接，不等同于报道的“向江面挑出80m”。320/322/332m 与 2万/2.4万/2.8万m² 的报道差异在 `osm-measurements.json` 保留。

业主项目页、政府门户、浙大教学点说明和总工施工采访支持对象身份、主/副阳台范围与双层结构；实际查看了摄影师石上清流的九张街面照片，以及政府和洲际酒店两张夜间航拍。摄影师照片提供沿江相反方向、玻璃护栏、架空入口桥梁、玻璃房与圆形采光窗细节；两张官方图的阳台位于背景，不能作为完整立面或精确剖面。页文日期不等于照片拍摄时间，不能声称2026现状测绘。来源链接、响应/照片哈希和逐视角观察在 `source-claims.json`、`photo-review.json`。

候选含真实足印的主挑台、上下公共层、两个可明确定位的岸侧指状连接、三处源足印玻璃体、透明栏板与细横杆、代表性柱梁、滨江铺地带和圆形玻璃采光窗。玻璃体与公共楼板法线已检查。下层不复制岸侧桥下的整片楼板。模型没有水面、湖面薄片或虚构公园底板；钱塘江 `relation/8227206` 由基础水体管线处理。

明确估计：下层以孤立基准0m表示，上层6±2m；玻璃头部高出上层3±1.5m；柱网14±4m、柱宽1.25±0.5m、玻璃栏板1.2±0.25m。OSM主height6及玻璃part min_height6/top14、9、10仅是未核实标签，没有当作实测楼高。玻璃头部剖面、圆窗数量/位置及下层完整结构仍待核对；当前六个圆窗为表面代表性表达，未声称完成贯通采光井。模型不凭空安置楼梯、坡道或电梯，也不把2007拟建博物馆/艺术/餐饮内容当作当前已实现交互。

`scripts/landmarks/city_balcony.py` 只使用 B.face 和 math；不导入会初始化场景的 city_mesh。模型参数是未缩放真实米制，lm.x/z/y 已经是游戏单位，水平/高度只乘0.60一次，原东/北/上方向保持。可复用接口：

```python
build(b, lm, spec, scale=.6)
deck_height_metres(u, v, spec, level='upper')
deck_height_game(x, z, lm, spec, scale=.6, level='upper')
ground_footprints(lm, spec, scale=.6)
```

`u/v` 为本对象未缩放米制轴；`x/z` 为城市世界游戏坐标。台面接口要求明确 upper/lower，返回该公共层高度或 None，源玻璃房内不返回公共台面。`deck_height_game` 输出世界游戏高度；lm.y 不重复缩放。`ground_footprints` 返回 `polygonGame`、`minYGame`、`maxYGame`、kind、basis与sourceFeatureIds，共136条本候选柱/玻璃墙窄条占用，不能把整个主阳台当圆形或整片地面障碍。实际运行时应结合高度范围使用；返回值不是已验证的路线或碰撞。

只排除上述主关系与三个 building part，不删除相邻波浪文化城 `relation/8718552`、无名楼 `way/626891122`、ICC、剧院、道路、绿地或水体。`way/157967583` 与 `way/157967585` 是之江路 layer=-1 隧道；平台与道路几何相交不证明平面连接。上下层绝对高程、当前楼梯/坡道/门口、陆侧步行网络与无障碍到达均待主集成核对；两个岸端中点只是候选连接位置。

已执行的主机验证为 CPU 合约检查：12,622 faces、25,192 三角形、5材质，预算28,000/7在检查前固定。验证源足印投影、0.60只一次、lm平移/baseY、frame恢复、完整约束三角化面积、楼板和玻璃屋顶朝上、公共层API/玻璃房空腔、岸侧桥下不封整板、占用区域窄条及来源ID、无水/灯/虚构台阶。首次28,438超预算后去掉相邻栏杆内部不可见端面，最终低于原预算，未调高预算。约束裁切边界的数值零面积三角形在生产几何时剔除并核对总面积，测试没有跳过退化面。

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python docs/hangzhou/research/core/city-balcony-round2/freeze_balcony.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python docs/hangzhou/research/core/city-balcony-round2/record_review.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python docs/hangzhou/research/core/city-balcony-round2/validate_cpu.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/landmark_tasks.py check --job docs/hangzhou/research/core/city-balcony-round2/task-bundles/city-balcony/job.json --stage evidence-ready
```

冻结脚本依赖已存在的Shapely2.1.2约束三角化，未改依赖锁。公共网页/图片临时缓存未打包；重建源规格需先按来源合法取回相同参考缓存。最终纯B模块只读取已冻结spec，不依赖网络/照片/Shapely。

建议由主集成人员串行导出，以下命令本worker没有执行，`model.buildCommand`仍为空：

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python scripts/build_hangzhou_landmark_candidate.py -- --job docs/hangzhou/research/core/city-balcony-round2/task-bundles/city-balcony/job.json --spec docs/hangzhou/research/core/city-balcony-round2/spec.json --module scripts/landmarks/city_balcony.py --output artifacts/cities/hangzhou/landmarks/city-balcony-v1
```

阶段为有限主挑台外观 `evidence-ready`。CPU俯视/街面/远景草图已实际查看，属于几何排版草图，Pillow遮挡/透明材质不等于实机渲染。没有启动Blender或浏览器，没有修改共享源码、清单、配置和总资产，未制作照片贴图。八项具名验收仍unknown：绝对高程、入口台阶/坡道、玻璃体精确形体、下层场所、全侧立面、家具/植被、夜景、实际GLB、碰撞、到达和性能均未通过；不能据此宣布城市阳台完整交付。
