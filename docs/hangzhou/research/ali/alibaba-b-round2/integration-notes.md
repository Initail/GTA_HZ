# B 区候选：主集成串行接入

当前仅源模块/规格与 CPU 验证，实际阶段 `evidence-ready`。以下命令为待主集成执行，子任务没有启动 Blender/浏览器或写共享文件。

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python scripts/build_hangzhou_landmark_candidate.py -- --job docs/hangzhou/research/ali/alibaba-b-round2/task/alibaba-b/job.json --spec docs/hangzhou/research/ali/alibaba-b-round2/spec.json --module scripts/landmarks/alibaba_b.py --output artifacts/cities/hangzhou/landmarks/alibaba-b-round2
```

使用新空候选目录，mesh prefix `detail_alibaba-b_`。导出后记录真实 GLB/hash/buildCommand，并运行 modelled 门槛；本轮预计14,862三角形与7现有材质，只是CPU统计，实际GLB大小/材质/三角形以导出结果为准。金色共享材质为暖橙遮阳近似，最终表面色需对象级审查；不为该候选修改全城金属材质。未增加任何灯光或照片贴图。

模块 `build(b,lm,spec,scale=.6)` 从 `city_config.load_city('hangzhou')` 读取同一 WGS84换算；几何米制进入模块仅缩放一次，lm.x/z/y 已是游戏单位。lm.lon/lat 与 spec anchor 不同时通过原始地理偏移保持真实位置，frame 始终在成功/异常时恢复。Blender 东北上→GLB Y-up→Babylon现有方向流程保持，不追加整体旋转。

精确替换21IDs如下；基础 buildings 与近景 facades 均应串行排除同一集合并记录真实哈希：

```json
["way/1363020721","way/1363020722","way/1363020723","way/1363020724","way/1363020725","way/1363020726","way/1363020727","way/1363020728","way/1363020729","way/1363020730","way/1363020731","way/1363020732","way/1363020733","way/1363020734","way/1363020735","way/1363020736","way/1363020737","way/1363020738","way/1363020739","way/1363020740","way/1363020743"]
```

不排除 B parcel544285896、A/C及六期，也不排除中央 `way/1363020741` / `way/1363020742`。这两片屋顶的形体/标高/体育/食堂功能仍为独立blocker，保留基础对象等待补证。全部23源轮廓保存在快照中；21替换逐足印crosswalk见 object-groups/footprint-correspondence，23不是实体主楼数量。

`ground_footprints` 输出估计退入地面办公体、支柱、源访客与两个绿顶低房间凹多边形。架空节点整体不成为地面墙，源北侧西组凹院保持开放；不能整园区 bbox 碰撞。退入距离/柱距/低房间门洞并非实测，按当前模型体和碰撞数据核对后再接入。低绿顶房间只是外观，不新增可交互室内。B任务目标使用经过原道路图确认的外侧可达点，避免位置位于未核实门洞、屋顶或封闭室内。

街道/地面基准默认候选0m，模块 lm.y 不重复缩放。6m架空层、5.8m绿屋顶均为估计，不由 OSM layer1/layer2推断；主集成需复核 terrain与地面衔接、自动驾驶/车辆恢复/行人/e-bike避让，不靠放大剔除半径解决碰撞。

实机必须另做俯视、街面、远景，分别与NBBJ DJI0999/0456、DSF1342和DSC07936/07966现状照片核对；查看立面竖/横节奏、屋顶三角天窗/六角高差、上部折线楼臂接缝是否露内墙或叠面。昼夜颜色、字牌事实、真实门洞/绕行、帧时/冷启/内存都 pending，不能沿用深圳/C区历史截图或FPS。

保留MIT与既有材质署名，OSM衍生数据保留ODbL/贡献者署名。NBBJ/Benoy研究网页照片无游戏纹理再发布授权，发行包仅携原创几何/程序参数及已有合法材质，研究照片另留本地参考与来源链接。
