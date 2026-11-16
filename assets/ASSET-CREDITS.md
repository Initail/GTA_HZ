# 杭城之行原创替代模型

**署名** · © 2026 GTA_HZ contributors
**许可** · [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/)

| 资产 | 公开版用途 |
| --- | --- |
| `cities/hangzhou/rider/rider.glb` | 玩家原创通勤骑手。保留待机、行走、奔跑动画。 |
| `cities/hangzhou/bamboo-cafe/characters/maid.glb` | 原创咖啡员工模型。知夏和望舒分别实例化并独立播放动画。 |
| `cities/hangzhou/bamboo-cafe/characters/jk.glb` | 原创深色制服咖啡员工模型。用于小岚。 |
| `cities/hangzhou/tank/tank.glb` | 原创虚构履带车辆外观，保留游戏所需转动节点。 |

这些 GLB 由`tools/original-assets/generate-assets.mjs` 编写并生成，所有多边形、材质色、骨骼以及动画关键帧均在该脚本中定义。既有文件名及节点名用于兼容游戏加载器。再分发时请保留署名、许可链接，并注明后续改动。游戏其余素材各自保留原有许可。

从具备 `@gltf-transform/core` 以及游戏 Babylon.js 依赖的项目中运行下列命令即可重建和检查。

```sh
node tools/original-assets/generate-assets.mjs
node tools/original-assets/check-assets.mjs
node tools/original-assets/check-babylon.mjs
```

Generator writes to artifacts/original-assets; check scripts validate the integrated public/cities/hangzhou snapshot. Integration is a separate reviewed step.
