# 杭州资产重建

日常玩法开发使用 Release 提供的运行资产，见仓库根的 npm 命令。先执行 `npm ci`、`npm run assets:fetch` 和 `npm run assets:verify`，再用 `npm run dev` 开发，或用 `npm run build` 生成浏览器构建。构建使用现成的城市分块、模型与地理数据。整城原始数据和大型中间候选另行获取，现阶段没有经过验证的一键全源重建流程。

对建模工作，从[研究入口](RESEARCH.md)选定对象与证据版本，再按[脚本索引](SCRIPT_INDEX.md)确定需要复用的管线。地标建模以对象为单位生成候选。道面、桥面、道路高程、地形切口和分块的接入由一个集成人员串行完成。

## 环境与输入

- Web 开发和 CPU 回归使用 [仓库固定的 Node 版本](../.node-version) 与 `npm ci`。下载运行资产和证据门槛检查需要 Python 3。地理提取、栅格和几何处理另需 `osmium`、`shapely`、`numpy`、`rasterio`。完整地理脚本原环境使用 Python 3.12。在单独虚拟环境中按[历史依赖锁](../requirements.lock.txt)安装，并核对当前平台有对应版本的依赖。
- GLB 导出入口在独立的 Blender 后台进程内执行。按 `blender --version` 核对环境。历史建模记录使用 Blender 5.2.2。Blender 中的 Python 与地理处理虚拟环境是两个运行环境。
- 杭州使用 [城市配置](../config/cities/hangzhou.json) 中的 WGS84 原点 `[120.155, 30.274]`、本地经纬度换算系数和 `0.60` 比例。调用 [city_config.py](../scripts/city_config.py) 可生成浏览器配置。经纬度差、真实尺寸只在转为游戏坐标时缩放一次。已有游戏单位的基高不再缩放。Blender 东/北/上经 glTF Y-up 交给运行时现有的根方向处理。
- OSM 使用 [浙江固定快照清单](../data/hangzhou/source-manifest.json)，DSM 使用 [Copernicus 两图幅清单](../data/hangzhou/dsm-source-manifest.json)。保留实际快照日期与 SHA-256。变化的 URL 或快照需重新核对来源并建立另一轮候选。图幅是 DSM，接地、道路高程和室外台阶仍需要独立验收。署名见[数据来源与许可](../data/hangzhou/ATTRIBUTION.md)。

## 复建一处地标候选

1. 在仓库根运行以下只读检查。灵隐 round3 的任务包给出五殿与局部场地的规格和冻结证据。检查以当前源码与快照文件为准。上游绘制的历史缩略图不参与这个命令。

   ```sh
   task=docs/hangzhou/research/core/lingyin-round3
   python3 -B scripts/landmark_tasks.py status --job "$task/task-bundles/lingyin-temple/job.json"
   python3 -B scripts/landmark_tasks.py check --job "$task/task-bundles/lingyin-temple/job.json" --stage evidence-ready
   ```

2. 跑新研究轮次时，先把任务包复制到 `artifacts/` 下单独的工作目录。保留其中已经记录的来源。核对 [规格](hangzhou/research/core/lingyin-round3/spec.json) 中的锚点、形体、误差和排除项。目标的纯建模脚本在 [scripts/landmarks/](../scripts/landmarks/)。灵隐 round3 的 [几何检验器](hangzhou/research/core/lingyin-round3/validate_cpu.py) 会写回相邻报告，建议在独立工作副本运行。全程保留旧报告和失败样例。
3. 核对实际导出输入。现有 [共享网格和材质](../scripts/city_mesh.py) 在导入时清空 Blender 场景，并读取旧目录 `public/city/textures/` 下的 `office.jpg`、`residential.jpg`、`stone.jpg`、`grass.jpg`、`road.jpg`、`paving.jpg` 和四张 `sign-{west,east,bay,center}.jpg`。相关 emissive 文件如存在也会使用。杭州运行包放在 `public/cities/hangzhou/`，建模前须确认旧材质路径有获得许可并记录哈希的本地输入，或在独立候选中明确迁移该路径。单纯下载运行包无法补齐四张牌面材质。
4. 为指定对象备好 job、spec、module 与基高再导出。以下命令约定当前目录为仓库根，`$placement` 指向你准备的定位 JSON。

   ```sh
   mkdir -p artifacts/cities/hangzhou/landmarks
   blender --background --factory-startup --python-exit-code 1 \
     --python scripts/build_hangzhou_landmark_candidate.py -- \
     --job "$task/task-bundles/lingyin-temple/job.json" \
     --spec "$task/spec.json" \
     --module scripts/landmarks/lingyin_site.py \
     --placement "$placement" \
     --output artifacts/cities/hangzhou/landmarks/lingyin-site-local
   ```

   [导出器](../scripts/build_hangzhou_landmark_candidate.py)接受 `--palette`、`--base-y` 或 `--placement`。单基高对象可提供 `--base-y`。已有定位 JSON 时用 `--placement`，文件须匹配对象 ID、锚点、单位说明和源输入哈希。灵隐 round3 另需 `landmark.hallBaseYGame` 给出五个可核对基高，规格中的空值需保留，直到定位证据齐备。输出必须是 `artifacts/` 下的新目录，包含模型 GLB 与 `model-delivery.json`。
5. 让任务包绑定当前 GLB、源码、规格和输入哈希。如果要用 [record_hangzhou_candidate.py](../scripts/record_hangzhou_candidate.py) 记录导出，在本地任务副本指定 `--job`、`--delivery`、`--log`。该工具写入 `model.json`，要求记录匹配的 Blender 成功退出与模型哈希，生成的历史命令带 macOS Blender 路径。导出状态只推进到模型阶段。

## 重新提取部分城市数据

安装上述 Python 依赖，在隔离工作副本根执行。路径示例中的 `rebuild-a` 是新的候选编号。重新运行使用新的目录后缀。

```sh
python3 -m scripts.download_hangzhou_osm --snapshot 261011 --connections 1
python3 scripts/extract_hangzhou_osm.py \
  --source data/raw/hangzhou/zhejiang-261011.osm.pbf \
  --output data/processed/hangzhou-rebuild-a
python3 scripts/prepare_hangzhou_city.py \
  --input data/processed/hangzhou-rebuild-a \
  --output artifacts/cities/hangzhou/skeleton-rebuild-a
node --experimental-transform-types scripts/check_hangzhou_skeleton.mjs \
  artifacts/cities/hangzhou/skeleton-rebuild-a \
  artifacts/cities/hangzhou/skeleton-rebuild-a/check.json
```

`extract_hangzhou_osm.py` 校验 PBF 同目录的 `source-manifest.json`。提取范围来自当前城市配置。下载失败时保留已有固定快照和报告，重新取得字节一致的输入后再继续。`check_hangzhou_skeleton.mjs` 用 CPU 检查几何、路网与目标到达点，报告可能包含待修道路。道路网络按 OSM 原始节点连边，二维相交本身不能建立路口。

地形准备使用 [prepare_hangzhou_terrain.py](../scripts/prepare_hangzhou_terrain.py) 的 `--city-source`、`--output`、`--step`。它从 DSM 来源清单读取本地文件与哈希，可用 [fetch_hangzhou_dsm.py](../scripts/fetch_hangzhou_dsm.py) 补齐缓存。抓取脚本也会生成来源清单，使用隔离副本对比已提交的快照记录。原样取得 DSM 后，可传 `--city-source artifacts/cities/hangzhou/skeleton-rebuild-a/city.json --output artifacts/cities/hangzhou/terrain-rebuild-a` 生成地形候选。网格采样间隔和插值精度不能当作实测分辨率。

## 串行集成与验收

1. 以冻结的 Release 或已校验候选作为输入，保留原文件与摘要。检查目标新增足印、原楼体与立面排除 ID、道路权限、道路层级、合理到达点和真实接地。
2. 通道、桥、地下通行与台阶关联合约中的走面、阻挡、道路高程与渲染网格。按内容修改选择 [脚本索引](SCRIPT_INDEX.md) 中对应阶段，显式准备其输入和输出。部分历史工具指向旧版固定目录、旧资产清单或原先的环境，先读脚本的路径定义和 CLI，再在候选目录运行。冻结发行资产保持原样，直到新候选通过当前改动所需检查。
3. 由集成人员同步更新清单、关联哈希与浏览器加载路径，然后运行 `npm test` 和 `npm run build`。离线结果可证明所覆盖的模型合同和玩法。实际路线、视角、三张具名视图、昼夜、资源和长时表现仍需按新资产单独验证。
