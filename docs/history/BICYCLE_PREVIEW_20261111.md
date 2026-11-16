# 阶段一 · v13 骑行试玩 · 2026-11-11

用户将诉求 1—5 设为最高优先级，并要求分阶段给体验版。本阶段提供独立玩家单车，原始 GTA_HZ 总目标和其余四项优先工作没有取消。工程尚未完成。

## 启动和体验

- 本机入口：<http://127.0.0.1:5205/>。
- 本次局域网入口：<http://30.113.0.92:5205/>；仅主机 HTTP 检查通过，另一台设备是否可达仍需同学实测。
- 本次服务 19:35:18 启动，20:35:18 自动停止（北京时间）。之后在项目目录双击 `启动骑行试玩.command`：启动器优先复用现有 v13，不延长其时限；否则检查资源、选择空闲的 5205–5210 端口，输出新地址并打开手动入口。保留终端窗口。
- 入口不会自动加载游戏，需要点击“进入 v13 骑行试玩”。默认低画质。
- 这是另一个端口，其浏览器存档与 v12 分开；v12 资产和存档保留。本阶段未修改存档格式、职业奖励或升级价格。

汽车先停稳，按 **F** 下车。到平整开阔的岸上位置，按 **N** 或点击“取出单车”。**W/↑** 踩踏，**A/D 或 ←/→** 转向，**S/↓ 或空格** 刹车，**C** 切换跟随镜头远近。停稳后按 **F/N** 下车；单车留在原处，车旁可再次按 N 骑行，或点击“收起单车”后步行。在允许骑行的地方再取出。取车是免费的试骑功能，不代表真实租赁站或折叠机构建模。

建议先在出生点公共道路试一圈，确认汽车没有跟随移动。再通过地图到白堤周边道路停车，下车试骑；六段已有源权限中，`way/4326974` 允许自行车，其余五段明确 `bicycle=no`，即使同时带 `cycleway=yes` 也必须下车。禁骑提示、湖水阻挡、桥面支撑分别判断。来源沿用 v12 的 `site-access-provenance.json` 与其已绑定 OSM 快照，没有新造测量值。

## 本阶段实现

- 独立单车状态、速度和里程，最高 7 游戏米/秒；踩踏、滑行、转向、刹车及小步长碰撞。
- 身体九点与轮端空间、桥面/道路身份和高度连续性、机动车/行人/树干/建筑/咖啡馆/水域避让；安全侧下车及原路返回取车，车旁收起。
- 复用现有 `ebikes.glb` 的自行车和坐姿骑手薄实例，不加载第二份模型，不新增材质或灯光；既有 NPC 车流不改参数。
- 汽车留在原处，不增加汽车里程。职业帧明确 `inVehicle=false`；接送仍需要真实驾车。原本允许实际步行完成的送餐等任务，继续沿用其原规则；交谈前需下车。
- 新增 N 操作和按钮、骑行帮助、单独里程、跟随相机。原 K 录屏显隐鼠标等快捷键保留。无人机/飞机临时接管后返回骑行；观景时单车刹停。快速移动仍使用原调试 epoch，收起单车，不能绕过结算规则。

## 候选与重建

目录 `artifacts/cities/hangzhou/westlake-bicycle-v1`，从冻结 v12 `westlake-collision-v1` 复制源代码及三个 JSON 覆盖，不更改 v12。

- 共 145 份源文件，8 个新增或修改：`city-bicycle.ts`、`city-world.ts`、`city-ebikes.ts`、`main.ts`、`city-career-experience.ts`、`city-hud.ts`、`city-hud.css`、`city-quicktips.ts`。
- `checkpoint.json`、`candidate.json`、`source-changes.patch` 保留来源及差异；基础大模型沿用冻结 v10，JSON 分块沿用 `stream-data-v1`。锁定 Babylon 8.56.2，没有新增依赖或改动本轮依赖锁。
- 主包 1,187,581 字节，SHA256 `bc9b22de32b9bff4bd1635668421b246ba50b703771f75c004bf4ea13dd1b4a1`。
- 现有 MIT、模型和资产署名继续适用；没有新增照片贴图。

所有重建/验证仍用 `scripts/run_hangzhou_bounded.py`，固定 10 秒 / 256 MiB，系统内存压力正常才启动。为每次运行选择新的报告和输出目录；不要改写正在服务的候选。

```sh
# 可重复的阶段测试；REPORT 必须是尚不存在的新文件路径
python3 scripts/run_hangzhou_bounded.py --report "$REPORT" -- \
  node --experimental-transform-types artifacts/cities/hangzhou/westlake-bicycle-v1/tests/phase-one-suite.mjs

# 外部依赖的预览打包；OUT 必须是新的隔离目录
python3 scripts/run_hangzhou_bounded.py --report "$REPORT" -- \
  node_modules/.bin/esbuild artifacts/cities/hangzhou/westlake-bicycle-v1/src/main.ts \
  --bundle --format=esm --platform=browser '--external:@babylonjs/*' \
  '--define:import.meta.env={}' --target=es2022 --outdir="$OUT" --metafile="$OUT/meta.json"

# 当前冻结预览的兼容性核对；CHECK 是候选下的新报告文件名
python3 scripts/run_hangzhou_bounded.py --report "$REPORT" -- \
  node --max-old-space-size=128 scripts/check_hangzhou_bicycle_demo.mjs "$CHECK"

python3 scripts/serve_hangzhou_bicycle_demo.py --host 0.0.0.0 --advertise 30.113.0.92 --port 5205
```

上面的预览打包使用本地 ESM 依赖，不能写成正式 `npm run build` 通过。

## 验证结果与失败记录

冻结源码的 `tests-frozen-v1.json`：210 项通过，0 失败、0 跳过，约 4.56 秒，采样峰值 223040 KiB、内核子进程高水位 224544 KiB。包含骑行控制 13、实际世界方法/职业适配 5、NullEngine 实例与实资产角色 2、既有回归子集 184、白堤源数据/桥面检查 6。NullEngine 和 CPU 方法检查均不是实机画面或 FPS 测试。

骑行纯模块严格类型检查通过；预览打包通过；361 个实际 ESM 导入符号、145 份源哈希、未改经济/操控模块、数据绑定与最终文件 SHA 通过。`http-verification-v1.json` 验证主机 LAN 手动入口、拒绝无票据/错误来源、有效进入、最终脚本/CSS/数据/模型字节；没有执行浏览器 JavaScript 或打开 GPU 游戏。

失败记录保留：首次白堤检查把桥上的角色初始化到湖底，随后发现新骑行采样也需要继承步行的道路与桥面身份，已修正并通过六段实际源检查。职业防冒充测试最初误选本就允许步行的送餐任务，纠正为要求真实驾驶的接送任务，原职业规则未改。兼容性检查两次因额外 `--experimental-transform-types` 的进程开销超过固定 RSS 门槛终止；回到原 v12 检查命令所用的 Node 原生类型剥离后，相同完整兼容检查通过，采样峰值 159216 KiB、内核高水位 194240 KiB，没有提高限制或删检查。

## 仍待验证或实现

- 本轮代理未打开完整游戏：新增骑行实机外观、车与骑手贴合、手感、窄屏显示、长时间性能和浏览器恢复待测。用户先前认可的是 v12，不能转记为 v13 通过。
- 当前为既有坐姿骑手，尚无独立脚踏/车轮动画或个性化骑手；单车位置、单车里程不跨刷新保存。原有职业/故事/收藏存档接口保留，完整刷新恢复仍需实机回归。
- 当前玩家单车不提供骑行自动导航、真实租赁站、多人联机；与其他电动车/单车的完整动态碰撞尚待补充。
- 完整类型检查、正式 Vite 构建、整城自动驾驶回归及全模式/全任务实机验收仍未完成。原画面模型尚未完成按需加载；历史整机卡顿问题未宣告消除。
- 下一阶段推进游船、钓鱼和 NPC 互动，同步处理西湖岸线、入口与景区实景；灵隐、公交、园区门禁与标识持续处于最高优先级，不以本次骑行替代完成。
