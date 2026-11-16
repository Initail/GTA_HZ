# 雷峰塔场地 round2 交接

唯一写入者 Codex 子任务 leifeng_candidate。只写本目录和 `scripts/landmarks/leifeng_site.py`。原 `leifeng_pagoda.py` 与 `leifeng-round2/spec.json` 没有修改，前后SHA由本轮规格及CPU检查绑定。没有 Blender、浏览器、共享配置/渲染/数据/总资产操作。

## 实际状态与范围

`task-bundles/leifeng-site/job.json` 有限映射公园地形/源通道/静态外部扶梯候选实际 evidence-ready --record 通过。**完整广场/门洞/塔内电梯/安全入塔** 是独立 `leifeng-site-entry` 任务：实际检查返回2，仍planned并保留blocker。没有 GLB；modelled/verified 未通过，八项validation仍unknown。不能将前一项有限证据门槛当成后者完成。

CPU：1,279 三角形，7材质（land/pavement/concrete/rubber/steel/silver/landmarkglass），0灯，0水片。terrain参考837个源网格裁切三角形，全部959个地形/铺装三角形加静态两中轴带、两侧楼梯/扶手；没有把场地建为普通空平板或椭球。梯级数依据估计高差/.18m作有限形体表达，未取得实际梯级/坡度/宽度。

## 地图、地形和水岸

固定Geofabrik快照2026-10-11，公园way/975360504“雷峰夕照”、夕照山peak node/5580634151、塔way/229726934。公园范围不是测量山脚或完整广场边界。terrain由现有 `terrain-glo30-v3` 的真实50m采样网格三角面构成，只做矢量地块/水界裁切；源DSM为30m，增加岸线顶点和插值不提高地形实测分辨率。

西湖relation/2308774、放生池way/62124950均作为父水体管线的源身份。场地干地 mask 减去这两个水体及2m缓冲，所有候选地坪三角形的平面面积均未覆盖源水域；2m是保守游戏候选边距，岸线本身约±5m，未证明真实护岸/水位或玩家不会落水。没有生成新的湖面、池面或无来源挡水墙。

现有grid采用EGM2008真实米高度，根地形的3×3min→max→mean是裸地估计，宽林冠和坡面偏差仍在。塔点分片线性插值得到 **32.92470741027066m EGM2008**，原DSM同点值另列measurements.json。误差±12m是保留林冠/屋顶/50m网格偏差的工程调查估计包络，**不是测量置信区间/地坪完成标高**。建筑剖面的0、负基座层不能直接当EGM2008。

原塔候选外轮廓周边3±2m窄地面apron为基座地坪有限估计，使用同一估计塔点高度；它不代表完整广场。terrain去掉源建筑足印和该apron，保留附近已映射楼/亭的原资产，`baseBuildingIdsToExclude=[]`。

## 高度与接口

site `lm.x/lm.z/lm.y` 全是游戏单位。**site lm.y 是EGM2008零点对应的游戏高度，不是原塔基座高度。** 源高度真实米 ×.60一次再加site lm.y；Blender east/north/up不另旋转。给原塔传入 `tower_placement` 的 y 后，原塔模块自身相对71m再缩放一次即可，不再缩放传入 y。

```python
from landmarks import leifeng_site
site_lm = {'lon':spec['anchor']['lon'], 'lat':spec['anchor']['lat'],
           'x':anchor_x_game, 'z':anchor_z_game, 'y':egm_zero_game_y}
tower_lm = leifeng_site.tower_placement(site_lm, spec, .60)
# egm_zero_game_y=0 时，tower_lm.y=19.754824446162396游戏米，仍是估计。
# root调用原leifeng_pagoda.build时仅取tower_lm的lon/lat/x/z/y。
surfaces = leifeng_site.walk_surfaces(site_lm, spec, .60,
              allow_estimated=True, include_terrain=True)
candidate = leifeng_site.walk_surface(lon, lat, site_lm, spec, .60,
              allow_estimated=True, source_way_id='way/975357010')
footprints = leifeng_site.ground_footprints(site_lm, spec, .60) # []
```

walk_surface/surfaces 缺显式 allow_estimated=True 会抛出异常；返回值包含 estimated、heightErrorGame、traversalAccepted=False。三角坐标采用 **[east,north,up]**，不是Babylon [x,y,z]数组。可选source_way_id只查指定源通道，平面交叉不新增导航接点。wholehill不是solidbuilding，因此ground_footprints空，root须按高度表面/水体/具体障碍组织碰撞。

根全城已经有相同GLO30-v3地形时，避免叠加第二层草面：root在自己的集成规格副本设renderTerrain=False，保留本候选铺装/静态扶梯；或以本地精确mask替换对应根地形面。不要修改冻结塔模块/规格来掩盖来源；导出规格变更应重新记录哈希和对应验收。所有入口、建筑地坪与水岸高度仍需root实际复核。

## 不可绕过的入口阻塞

南侧way/975357010通过node/3479012381精确接way/340652169。后者源tag是highway=steps、name=电梯；设计方南面真实照片可见中轴两条扶梯及左右石阶，所以模型仅表达**静态外形**，不是运行电梯/自动扶梯玩法。

mainlift北端node/3479012380为[120.1450384,30.2335066]，距映射塔基14.115757308842218m；固定roads里无其他源way接该北端。东方steps way/1448327495接way/1448327494，但另一端也未提供塔门的精确连接。不能凭最近距离造入塔边。

原塔保护基座有连续实体墙和保守wholefootprint碰撞。场地模块不能自动开门、移除墙、证明通过；即使在入口画透明通道也会导致无来源穿墙。因此未补虚构门洞或跨缺口桥面，未把玩家抵达/进塔标为pass。准确门洞位置、宽/阈值、古塔保护罩各层地坪、完整广场/票门及塔内电梯均待补。运营方两个HTTPS入口证书校验失败，未取得当前官方游线图；来源失败已记录，没有用失效内容或第三方旅游广告替代当前尺寸。

设计方真实南面与北侧湖上两方向照片及建筑剖面已在本轮实际打开，拍摄日期未知，树/屋顶遮挡部分低处入口，不能称当前全侧/完整场地照片。图片仅在/tmp作参考，未拷贝、裁剪发布为材质。

## 三桥只读复核

`bridge-profile-recheck.json` 保留最新桥梁模块/规格SHA及15road IDs检查，包括之江4条外接306360714/306360716/306360719/589558020。原nodeIds/WGS序列与已提取固定PBF一致；rail未混入道路；所有profile保持 candidate-estimated、navigationAccepted=False。没有修改三桥模块、规格、任务包或资产，也没有新增桥梁驾驶验收。

## 验证及资料声明

已实际执行：

```sh
.venv/bin/python docs/hangzhou/research/core/leifeng-site-round2/prepare_source.py
.venv/bin/python docs/hangzhou/research/core/leifeng-site-round2/validate_candidate.py
.venv/bin/python scripts/landmark_tasks.py check --job docs/hangzhou/research/core/leifeng-site-round2/task-bundles/leifeng-site/job.json --stage evidence-ready --record
.venv/bin/python scripts/landmark_tasks.py check --job docs/hangzhou/research/core/leifeng-site-round2/task-bundles/leifeng-site-entry/job.json --stage evidence-ready --record
```

最后一条返回2并保留真实blockers。CPU仅核对缩放、frame、三角形、干地mask、查询/缺口及预算，不能证明实际不穿墙/不落水、Blender/GLB、GPU、三视角视觉、夜景或FPS。

数据源声明：produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved。完整源许可URL/原栅格/处理网格哈希在evidence/spec/父manifest中。地面估计的游戏适配和责任边界不改变源数据许可。
