# 主集成交接

本轮为证据调查；没有 `alibaba_a_extensions.py`，没有候选GLB，无新排除ID。不要把 `extension-scope.json` 当作可构建spec或把unknown填成候选高度。

1. A9 `way/456731145` 保留基础楼体；原A round2主楼/四links不改。原排除范围应继续逐source排除，不能把本轮灰色停车/历史院落/商城/公交站随园区整体删除。
2. A9的OSM3levels只证明标签。馆名/楼号/门号/访客中心的 crosswalk 未确认；官方参访目的地存在不证明图中坐标是可达入口。不要绑定任务到A9中心或新增室内场所。
3. 全部四个带匿名架空标签的 source link 已在round2。38条混合bridge/layer/tunnel道路分别按真实语义保留，不新造空中连廊；导航级别不由XY交叉决定。
4. 菜鸟主楼之外仍缺已建访客/报告厅和产业楼群，不能宣布完整菜鸟园区完成。三mappedparcel的固定几何和公开实景来源已保存。未来新增对象要先做有误差/基准的足印配准，unknownsourceID不得用整个parcel作为baseBuildingId排除。
5. 将 `source-coverage-*.png` 标为CPU资料图；本轮没有模型街面/远景/昼夜实机图、碰撞、性能或真实驾驶通过项。
6. `references/` 中照片/PDF仅供研究，许可未验证，公开发布不打包图片；保留OSM/Geofabrik及各资料署名和URL。

具体下一项可独立拆为 A9 source crosswalk与多向现状外观，或菜鸟东访客/报告厅足印配准。证据门槛实际未通过时继续调查，不生成猜测主体。得到核心证据后沿用 `build(b,lm,spec,scale=.6)`、实米参数单次0.60、lm.y游戏单位与frame恢复，主集成串行导出。
