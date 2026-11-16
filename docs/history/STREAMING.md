# 基础城市分块候选与恢复边界

2026-11-11，继续正式开发；旧 demo-v3/v10 保持关闭，根入口仍为恢复页。该页不是可玩版本。保留全部玩法源码、任务参数、存档结构和历史模型，不以删减道路/楼体来降低启动负载。

## 当前实物

| 层 | 候选 | 分块数 | 原三角数量 | 分块 GLB 总字节 |
|---|---|---:|---:|---:|
| 地形/基础水面 | `artifacts/cities/hangzhou/stream-mesh-v1/terrain` | 700 | 4,775,907 | 87,532,068 |
| 道路/标线/原灯具 | `artifacts/cities/hangzhou/stream-mesh-v1/roads` | 681 | 7,901,542 | 227,239,736 |
| 普通楼体 | `artifacts/cities/hangzhou/stream-mesh-v2/buildings` | 531 | 5,934,858 | 113,833,724 |

全部8,477个基础源节点恰好归属一个分块，全部18,612,307个三角保留。独立检查器实际解码每块，比较全部访问器字节/索引、类型/归一化、节点变换、材质关联、图片内容，并用解码顶点核验游戏世界包围盒。原根节点方向处理不变，未再次缩放。每层finalize重新流式核对整份源SHA和每块SHA；`manifest.json`生成前必须有全部逐块校验报告。

输出总磁盘体积反而略增：跨城共享的压缩索引被切成局部精确索引，避免运行时为了一个街区解码整份共享索引。目标是降低同时驻留量，不是声称总下载更小。最大单块GLB为2,067,184字节；贴图按层共享路径，7张JPEG合计5,767,168像素，最大1024×1024。贴图、运行时材质图集、帧缓冲及其他玩法资源须另算。

`stream-data-v1/city`：60,088,452字节源拆为117块，86,467条数组记录；`stream-data-v1/road-levels`：28,005,820字节源拆为54块、33,848条道路。逐块payload与连续源字节范围一致，分隔符和顺序检查确保无丢失/重复/重排。最大JSON块1,526,720字节。完整路图与碰撞数据最终仍驻留；这是传输/解析分块，不是完整JS堆内存优化。

## 已写入但尚未放行的运行时

- `city-json-chunks.ts`串行读取、有字节/条目上限、源身份及分块哈希、取消、逐块让出事件循环；不回退大文件。world/geography有可选接入参数，旧调用接口保留，恢复入口不会调用world。
- `city-stream-residency.ts`只有一个加载槽，待完成资源也计入预算；隐藏和卸载分开；移动/取消/销毁后到达的旧结果被释放；预算不足时明确缺块，不伪称ready，不自动重试失败块。当前模型预算24MiB编码/64MiB逻辑/100万面/32块是临时门槛，不是系统实测内存。
- `city-stream-assets.ts`核验GLB头/逻辑预算和已登记图片，JPEG原生解码前核尺寸；按固定哈希读取，流超限取消。
- `city-stream-glb.ts`为独立候选加载器。共享有界图片URL、恢复原根旋转、等待导入完成、处理失败/取消/卸载。它尚未接入完整世界的共享材质、反射、观景拾取和动态图块清单，不能作为可玩交付。
- `city-stream-manifest.ts`需要外部固定的manifest SHA及源SHA，不把清单中的pass字段当准入证明。清单读取与源身份已纳入21项轻量测试。

## 本轮验证与失败记录

- 17项轻量测试通过：完整数据顺序、缺块/乱序/篡改/超限拒绝、取消、串行/预算/卸载/迟到资源、三层真实出生块的二进制保持、真实JPEG尺寸。`stream-assets-tests-v1.json`，0.82秒，采样RSS93,136KiB。没有浏览器/GPU结论。
- JSON读取/预算/二进制守卫三个纯模块类型检查通过，`stream-pure-types-v1.json`。包含Babylon声明的检查以及全工程检查分别触及256MiB临时线而被终止；不是通过，不提高限额。完整类型/构建仍待完成。
- 497个批量提取/校验任务中，496成功、1真实逻辑失败。最大采样RSS210,896KiB、最长1.86秒，未触10秒/256MiB退出线。另有初始证明和最终覆盖检查，独立保存日志。
- 楼体v1在`-14,4`因两个材质共享访问器255而重复计算索引预算（12996对12852）失败；修复按唯一访问器计内存后创建v2，保留失败包，所有531块重新提取校验。渲染三角仍按实例/primitive计算。增加负控回归。
- 地形第一次finalize严格比较遇到JSON把`-0`写成`0`；仅在JSON边界归一化符号零后重新通过，无几何修改、无误差放宽。
- 首次esbuild调用误将本机Mach-O当Node脚本，未构建成功，日志保留。修正命令尚待压力正常后运行。
- 后续观察到系统内存压力2（警告），停止新构建与浏览器操作；启动时间仍13:52:32。新的作业包装器增加系统压力准入/运行中退出，不终止其他应用或共享工具进程。

## 可重建入口

先使用新的候选目录和报告文件，禁止覆盖已校验版本。每个命令外包`run_hangzhou_bounded.py`，固定10秒、256MiB、1MiB输出上限，默认统计自己启动的进程树。系统内存压力不正常时不启动。

```sh
python3 scripts/run_hangzhou_bounded.py --report NEW-report.json -- \
  node --max-old-space-size=128 scripts/partition_hangzhou_glb.mjs \
  plan SOURCE.glb terrain artifacts/cities/hangzhou/NEW/terrain
# batch DIR START COUNT（COUNT<=8），然后check_hangzhou_stream_batch.mjs DIR START COUNT。
# 全部完成后运行finalize_hangzhou_stream_role.mjs DIR，缺校验或哈希不符会失败。
# JSON：split_hangzhou_json.mjs SOURCE NEW_DIR，再check_hangzhou_json_chunks.mjs NEW_DIR。
```

现有候选支持`run_hangzhou_stream_batches.py --root ROOT --reports NEW_REPORT_DIR --roles terrain roads buildings`串行续作。它在首个失败处停止，不自动绕过失败或提高预算。

后续实际结果：`stream-runtime-tests-v2.json`的21项测试及`stream-pure-types-v2.json`的四个纯模块检查通过；原地理12项与安全入口/图片/阶段记录13项回归分别通过。独立加载器首次有效打包通过（`stream-loader-bundle-v2.json`）；之后缩窄到3个glTF扩展的版本尚待重新打包。应用自身源码使用packages external打包通过，只证明本项目源码转译/链接，不是完整正式构建。完整打包以及包含Babylon声明的类型检查仍被固定资源门槛阻断，已保存失败日志；缩窄后160MiB V8堆的检查发生子进程堆耗尽，不等于宿主watchdog根因。

暖态用户标签恢复页与真实8×8 PNG已分别通过有限资源检查，详见`CONTROLLED-VALIDATION.md`、`recovery-warm-user-v1-result.json`和`tiny-raster-v1-result.json`。前两次恢复页冷态检查仍失败（515MiB与572.1875MiB应用族RSS增长），不扣除工具增长改判。缺页面到PID及私有内存映射，不能算成游戏内存。P1后系统压力再现2，GPU单块、真实大图和整城继续待验证。

用户的景区形态、堤桥通行、封闭园区、标牌/门楼、公共交通及天气要求仍有效；历史白堤/天气操作结果与本轮稳定性门禁分开。地标候选未被本轮覆盖，完整项目未完成。
