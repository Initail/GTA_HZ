# 主集成串行接入说明

状态为 `evidence-ready` 的源绑定外观候选。子任务不启动 Blender/浏览器，不修改城市配置、总清单、基础楼体和运行时。以下是**待主集成执行的命令**，不是已完成导出的记录。

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python scripts/build_hangzhou_landmark_candidate.py -- --job docs/hangzhou/research/ali/alibaba-c-round2/task/alibaba-c/job.json --spec docs/hangzhou/research/ali/alibaba-c-round2/spec.json --module scripts/landmarks/alibaba_c.py --output artifacts/cities/hangzhou/landmarks/alibaba-c-round2
```

输出目录必须为新建/空候选目录。主集成导出后，将真实 GLB / SHA /实际构建命令写入任务 `model.json`，运行 `modelled` 门槛；不得让源码候选提前继承 modelled/verified 状态。GLB mesh prefix 为 `detail_alibaba-c_`，预期按 6 个现有材质合并，源码报告只是 CPU 面数，实际导出统计另行核对。

模块接口：`build(b,lm,spec,scale=.6)`，lm.x/z 是游戏平面坐标，lm.y 是已缩放游戏地面高度，不能再次乘 0.60。几何尺寸保持真实米制，由模块统一缩放一次；坐标读取 `city_config.load_city('hangzhou')`。lm.lon/lat 缺省时采用 spec anchor；有不同 marker 时使用 WGS84 偏移，不改变实际地理位置。保留 Blender 东/北/上→GLB Y-up→Babylon 现有根方向处理，不再添加整体旋转。

仅以下 source IDs 进入**基础建筑与近景立面**排除；逐环映射在 `footprint-correspondence.json`：

```json
["relation/18754982","relation/18754983","relation/18754984","relation/18754985","relation/18754986","relation/18754987","way/1363020716","way/1363020718"]
```

不能排除整个 C parcel way/645093961，不能排除 A/B、六期或匿名中央景观对象。基础楼体存在 relation 成员重复时，应由主集成核对真正生成的 source ID，不能按地块全删。源8对象内环逐点保留，六中庭不允许被基础碰撞、立面或 roof 重封。Media Roof 使用源长条外轮廓，主体是 12±4m 顶的薄板与稀疏估计柱，桥面为 6.2±2m 顶的外部连接段；OSM layer2 不代表真实高度。

数据层碰撞可调用 `ground_footprints(lm,spec,scale)` 获取楼体带/访客凹多边形及估计柱。桥面/长檐不生成全覆盖地面阻挡。它不证明真实门洞、地下室或内部能走；不要把该输出直接当精确室内导航。支柱位置是候选，仍可能需要避让实际可达道路。目标点应在经主集成确认的连通街道外侧，不采用校园 anchor 或未核实访客入口。

当前主体统一以地面0m候选建模。官方现状有多层景观基座，不能假定园内地面与外围街道同高；请先核对 terrain/路面基准再安放 lm.y，不在对象模块里偷加 unscaled 高程。中央湖进入基础 `water` 数据/材质管线；本模块没有水薄片，景观不能靠 landmark runtime 过滤幸存来渲染。

实机待检查：8 对象基础+立面双排除哈希；俯视、街面、远景至少3视图与官方参考；六楼高度比与立面三层节奏；访客凹口/长檐开放；桥段端部与地形；昼夜玻璃和招牌事实；CPU碰撞实际绕行；到达点、车辆恢复、自动驾驶；冷启动内存/帧时与同线路基线比较。当前未新增灯光、材质定义、反射设置或特效池，保留上游性能接口。

研究图片仅作参考，版权/摄影署名记录在 references manifest，不得未经许可纳入可发布游戏贴图库。发布资产只有原创程序几何及项目既有材质；OSM 衍生数据保留 ODbL 与署名。
