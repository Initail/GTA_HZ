# 供主集成串行接入

唯一对象写入者负责 `scripts/landmarks/cainiao_headquarters.py` 与本目录；共享世界、清单、基础楼体/立面、资产总清单与运行时没有由本任务修改。

已有 `scripts/build_hangzhou_landmark_candidate.py` 可接收本任务。下面是待主控执行的串行导出命令，本子任务未执行 Blender：

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
  --python scripts/build_hangzhou_landmark_candidate.py -- \
  --job docs/hangzhou/research/ali/cainiao-round2/task/cainiao-headquarters/job.json \
  --spec docs/hangzhou/research/ali/cainiao-round2/spec.json \
  --module scripts/landmarks/cainiao_headquarters.py \
  --output artifacts/cities/hangzhou/landmarks/cainiao-round2
```

输出目录必须新建且为空；不要复用/覆盖其他候选。主控导出后按真实产物填写 model.json 的 artifactPath、artifactMeshPrefix、GLB SHA256 和实际 buildCommand，再执行 modelled 检查。预期命名前缀严格为 `detail_cainiao-headquarters_`，underscore 模块文件名是本次所有权契约，不改变地标稳定 id。

锚点 `[119.9599997,30.26480245]` 只供模型定位。用 `city_config.project` 得到 lm.x/lm.z（游戏单位）；lm.y 已是游戏单位。模块自行把 spec 中未缩放的真实米制尺寸缩放一次，并补偿 lm 中有传入经纬度时的锚点差。不要把整组 GLB 再乘 0.60，不再旋转方向。

基础楼体与近景立面都要排除 `way/1355173307`，spec 已提供 `baseBuildingIdsToExclude` 与固定源 PBF hash。共享排除、两个基础 GLB 重建、候选接入和总哈希由主控串行完成。对象只有一个主楼源足印；不额外复制外围产业园或地产楼体。

`ground_footprints` 是有孔的环形条带、多条连接臂和中央实体，不能退化为一个覆盖全园区的 collision bbox/circle。四院数据层探针通过，实际穿行/绕行、门洞、角色和车辆高度仍须实机。门洞与罩棚为东侧中央的估计表现，不可直接成为任务/出生/快速移动目标。请从处理后的道路/步行网络中另选无水、无墙、安全且连通的外围点，经过真实驾驶/步行验证。

本模块没有铺水面。庭院水景及附近河道由基础水体管线负责；不能在地标 GLB 塞薄片后被运行时过滤。园区景观与内院全部测绘未完成，栽植与家具应按真实开放区避让连接臂和玻璃边。

主控至少保留俯视四院、街面入口、远景轮廓三张实机图，与本目录原始参考逐项核对；分别检查白天与夜景、碰撞、材质、加载、下载/显存/draw call 预算及帧时。CPU preview 不计入这三张实机截图，也不能直接用 CPU-valid 的字样填八项验收 pass。
