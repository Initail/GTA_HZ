# 城市坐标契约

唯一配置源为 `config/cities/hangzhou.json` 与 `config/active-city.json`。TypeScript 读取 `src/city-profiles.generated.ts`，Python 使用 `scripts/city_config.py`。改动配置后执行 `python3 scripts/city_config.py --generate-ts`，同时提交生成结果。

当前杭州参数：WGS84 / EPSG:4326，原点 `[120.155, 30.274]`，经度系数 `96220.11856153939 m/°`，纬度系数 `110857.07311230902 m/°`，统一地理缩放 `0.60`。研究范围 `[119.93,30.15,120.3,30.34]`；较早源清单的南界为 `30.16`，扩展处理范围另见源提取清单，不能混称完全相同裁切。

```text
east  = (longitude - originLongitude) * eastMetresPerDegree  * scale
north = (latitude  - originLatitude)  * northMetresPerDegree * scale
```

配置系数来自原点处 WGS84 椭球曲率近似，城市尺度内采用平面坐标；不是 GCJ-02/BD-09，也不是旧 EPSG:32649 研究坐标。商业地图坐标必须确认坐标系后转换，不直接当 WGS84。

地理/建筑原始米数只缩放一次。人物、车辆、虚构咖啡馆等已经以游戏单位制作的资产保持尺寸。Blender 东/北/上 → GLB Y-up → Babylon，保留加载器根节点方向转换，避免对每个对象再次镜像。

道路几何交叉不等于可转弯。导航需要源连接、oneway、bridge/tunnel/layer 与道路高程共同确认；跨水道路还需桥面/坡道支撑。目标 arrival 应在连通、无障碍的道路或交互区域，不能直接使用地标建筑中心。

改动投影/地形后需重验出生点、车辆恢复、任务地点、顺路路线、咖啡馆、景区入口、植被根高和材质世界坐标。坐标或对象身份不明时标 blocker，继续其他独立对象。
