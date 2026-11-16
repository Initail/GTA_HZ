# 杭州研究与建模证据

从 [杭州地标目录](../data/hangzhou/landmarks.json)、[OSM 身份记录](../data/hangzhou/osm-identities-extended.json) 和 [研究目录](hangzhou/research/) 找到对象。地标初稿在 [data/hangzhou/jobs](../data/hangzhou/jobs/)，有详细校验的轮次另有独立任务包。研究规格中的来源陈述、从地图几何计算的量、建模估计值和待确认项使用各自的证据字段。

## 任务包与几何入口

| 对象或范围 | 定位、几何与待确认项 |
| --- | --- |
| 灵隐五殿与局部场地 | [round3 说明](hangzhou/research/core/lingyin-round3/README.md)、[任务](hangzhou/research/core/lingyin-round3/task-bundles/lingyin-temple/job.json)、[规格](hangzhou/research/core/lingyin-round3/spec.json)、[CPU 检验](hangzhou/research/core/lingyin-round3/cpu-geometry-validation.json)。五殿的相对几何、前台、台阶和字形有独立候选，每殿绝对地坪、完整寺界与连续路线仍待核实。 [后续步道接入记录](history/LINGYIN_PATH_20261113.md)。 |
| 大莲花、小莲花、市民中心、杭州之门 | [大莲花任务](hangzhou/research/core/big-lotus-round2/task-bundles/big-lotus/job.json)及[几何检查](hangzhou/research/core/big-lotus-round2/cpu-geometry-validation.json)、[小莲花规格](hangzhou/research/core/little-lotus-round2/spec.json)、[市民中心规格](hangzhou/research/core/civic-center-round2/spec.json)、[杭州之门规格](hangzhou/research/core/gate-round2/spec.json)。重点核对场馆足印、回转体/塔楼外壳对应关系及周边遮挡。 |
| 城市阳台、杭州大剧院、国际会议中心、武林广场 | [城市阳台规格](hangzhou/research/core/city-balcony-round2/spec.json)、[大剧院规格](hangzhou/research/core/grand-theatre-round2/spec.json)、[国际会议中心规格](hangzhou/research/core/international-conference-center-round2/spec.json)、[武林广场规格](hangzhou/research/core/wulin-round2/spec.json)。[滨水接入合同](hangzhou/research/coastal-adaptation-round1/export-contract/README.md)涉及台地、坡道、岸线、渲染裁切与物理通行的所有权。 |
| 西湖堤桥、断桥和雷峰塔 | [西湖堤线任务](hangzhou/research/core/west-lake-causeways-round2/task-bundles/west-lake-causeways/job.json)、[断桥规格](hangzhou/research/core/broken-bridge-round2/spec.json)、[雷峰塔规格](hangzhou/research/core/leifeng-round2/spec.json)、[雷峰场地规格](hangzhou/research/core/leifeng-site-round2/spec.json)。堤桥需区分来源道路、可走支撑及骑车、开车权限。 [白堤碰撞验证](history/WESTLAKE_COLLISION_20261111.md)。 |
| 钱塘桥、复兴桥、之江大桥、闲富路 | [三桥接入合同](hangzhou/research/core/qiantang-bridges-integration-v2/integration-contract.json)、[源高度提案](hangzhou/research/core/qiantang-bridges-integration-v2/source-height-proposal.json)、[闲富路来源平面图](hangzhou/research/xianfu-portals-round1/source-plan.svg)。桥面、栏杆、引道和洞口分别核对相接高度、方向、通行与净空。三桥报告保留 CPU 阻挡样例，实机还需独立检查。 |
| 阿里 A/B/C 区与菜鸟园区 | [片区证据说明](hangzhou/research/ali/README.md)、[A 区扩展评估](hangzhou/research/ali/alibaba-a-round3/README.md)、[菜鸟总部规格](hangzhou/research/ali/cainiao-round2/spec.json)、[园区道路证据](hangzhou/research/ali/cainiao-road-access-round1/README.md)。保留片区同名、范围和照片对应关系的不确定项。 |
| 水系、植被及公交 | [重叠水域来源决策](hangzhou/research/water-overlap-round2/decisions.json)、[植被配置研究](hangzhou/research/vegetation/palette-spec.json)、[公交候选记录](history/BUS_SERVICE_20261113.md)。水面边界、植物基高和公交站台各有独立来源、模型与接入流程。 |

## 复查和保留证据

- 运行 `python3 -B scripts/landmark_tasks.py status --job 路径`，查看当前任务的缺失来源、快照或验证结果。每轮状态从可用文件和哈希重新计算，原有 `model.json`、`validation.json` 与内文日期提供历史记录。
- 复建前使用 `check --job 路径 --stage evidence-ready`。一些冻结任务引用未入 Git 的原始地理缓存、候选模型、原创渲染记录或第三方参考文件，请按错误逐项恢复可用来源。需要替换来源时，复制任务到新轮次，记录新来源、适用范围与不确定度，再重新验证。详情见[重建步骤](REBUILDING.md)。
- 保存对象规格、证据、来源链接、来源或模型哈希、任务合同、人工判断、原创矢量图、可再分发的地图几何及相应署名。保留通过和失败的 CPU 报告，并记录各自绑定的历史版本。地理数据许可见[署名清单](../data/hangzhou/ATTRIBUTION.md)。
- 来源照片公开可查阅，转载与贴图许可按原权利人逐项确认。缺少再发布许可时，引用来源的公开页面，记录作者、发布日期、观察事实和许可状态。下载日志、网页镜像、带授权查询参数的原图地址与原始照片缓存留在本地。发布 JSON/SVG 前检查是否嵌有照片、请求凭据或本机路径。
- 公开任务使用仓库相对路径，如 `data/hangzhou/jobs/`。包内清单绑定的文件若为发布清理而修改，重新核对内容与新哈希，并保留历史记录的版本归属。依赖旧缓存或工作目录的脚本状态参见[脚本索引](SCRIPT_INDEX.md)。


Public export omits the downloaded Nihon Sekkei report text extract; its source URL and structured geometry/evidence conclusions remain. Historical source hashes refer to the original local research cache, not a file shipped here.
