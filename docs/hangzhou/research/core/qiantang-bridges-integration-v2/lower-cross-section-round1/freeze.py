from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parent;R=P.parents[5];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();d=json.loads((P/'cross-section-proof.json').read_text());source=R/'scripts/prepare_hangzhou_city.py';lines=source.read_text().splitlines();(P/'width-source-excerpt.txt').write_text('\n'.join(f'{i+1}: {lines[i]}' for i in range(68,76))+'\n')
sources=[{'id':'fuxing-paper','url':'https://siberc.fzu.edu.cn/__local/6/6F/29/7C1CCAEDC24D9BB28E4EFA81912_4886B803_FCC7B.pdf?e=.pdf','publisher':'陈宝春/福州大学 中外公路28(4),2008','reviewedAt':'2026-11-11','status':'actual PDF matches frozen SHA; figure8 and page98 text re-read','support':'same overall upper/lower widths26.4m small and32m large; central lower transport reservation and side bus/slow routes','limit':'no measured absolute WGS axis, current side lane centre or surveyed near-bank width','sha256':'f9da1571945ab9777213a466a8c435a42e778934379ce1ea8c5c8d10e2815f0c'},{'id':'maintenance-bim','url':'https://www.doctorbridge.com/bim-maintence','publisher':'上海同豪土木工程咨询有限公司 project page; names杭州市市政设施监管中心/杭州市路桥集团 as management/maintenance partners','reviewedAt':'2026-11-11','status':'search index retrieved primary page content; direct web timeout and local HTTPS self-signed-certificate failure, no verified local HTML','support':'lower central bidirectional route and two side transport/slow-route groups, maintenance BIM exists','limit':'not a dimensional section or current per-way legal access declaration; no accurate mesh/data downloaded'},{'id':'fuxing-official-history','url':'https://www.hzzx.gov.cn/zxyw/content/2026-09/20/content_9311674.htm','publisher':'上城史志/杭州政协','publishedAt':'2026-09-20','reviewedAt':'2026-11-11','status':'primary government local-history page web content read','support':'double deck, lower bus/slow/pedestrian functions, viewing platforms','limit':'does not resolve detailed central roadway mapping or lane centres; historical simplified use description does not authorize deleting source transport ways'},{'id':'fixed-osm','path':'docs/hangzhou/research/core/qiantang-bridges-round2/fixed-bridge-features.geojson','sha256':sha(R/'docs/hangzhou/research/core/qiantang-bridges-round2/fixed-bridge-features.geojson'),'sourcePbfSha256':'4eb65f64925498408faeee7eb04b60d7eb8a01c49ddb239f73070d4d282c75a9','snapshot':'2026-10-11 fixed, not updated','license':'ODbL-1.0','support':'exact stored source node coordinates and tags; source mapping positional accuracy unknown'},{'id':'runtime-default-width','path':str(source.relative_to(R)),'sha256':sha(source),'lines':[69,76],'support':'default lanes2 produces width6game independent of geographical .60; explicitly gameplay-clearance/not-surveyed','limit':'6game converts numerically to10physical metres on map but is not a measured lane width'}];(P/'sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2))
(P/'README.md').write_text('''# 复兴大桥下层：固定源横断面与通行矛盾

当前证据不能支持“再平移一次桥轴就能解决”，也不能支持删除外侧护栏、缩小角色或把侧路改成不存在。冻结三桥候选及 GLB 完全未改。

`cross-section-proof.json` 每1物理米取一次固定轴横断面，共1375处。计算两条最外源线在同一横断面的间距，再加两侧原1.15game墙距及实际护栏半径.045物理米，得到同时容纳两个原玩家中心点的必要宽度。横向平移不改变两外线间距，因此可作为独立于桥轴横移的负控。

- 658/1375处超过候选实际26.4/32m支撑宽；最大必要宽33.92331m，最大差7.52331m。
- 排除两岸，|station|≤500m的1001处仍有284处矛盾；最大差3.95921m。
- 两外线在此中段的横向中位数分别−11.54784m和+11.73661m；中间双向线−.38688m。外侧不是一条误并到上层的路：固定PBF明确各自layer1、primary、oneway=yes，中间oneway=no。
- 三条源路都没有 width、lanes、sidewalk 或 cycleway 标签。运行时 width6game来自缺省两车道×3game；生成源码明确这是上游游戏净空，独立于地理缩放，不是实测道路宽。它在地图上数值相当于10物理米，但不能据此断言现实有三条独立10m宽车道。

降低这项缺省 width **单独也不能解决**已有中心线与护栏的冲突，因为横断面必要宽度使用的是源中心位置和原玩家墙距，未使用道路 buffer 宽度。只加高上层同样不能解决下层侧向冲突。当前测试是必要条件，不是充分条件；内部拱肋、坡道弯曲和真实车辆扫掠仍可增加失败。

`source-cross-section.svg` 是固定数据计算图，不是现场照片或游戏截图。黑线为当前报告宽度支撑边界，彩线为固定源路径。它清楚区分中段侧向不足与北端额外弯曲/范围问题。

一次资料支持下层为中央通道加两侧公交/慢行组，但没有给出当前各 OSM way 对应的精确车行线或边缘。福州大学论文明确上下层同宽，不能仅为了包住源路径而任意扩大整桥。运维BIM顾问项目页在搜索索引可读，但直接访问超时/证书失败；仅把索引内容当身份/分区佐证，未取得可测量BIM。二手百科的详细横断面数字与2004报道转载只作检索线索，不据此修改模型。

下一可实施条件：取得设计/竣工横断面、可定位的多方向正交证据或运营方可测量边界后，明确侧路实际车道中心、外悬慢行板及观景平台在各跨度的独立归属；同时保留原 source nodeId/graph，用单独、显式、可审计的可驶走廊契约处理测绘误差或游戏适配。当前没有足够证据生成这个改动。不能借未确认车种权限从导航删除现有源路。

来源和抓取限制见 `sources.json`；全部 measured/estimated/unknown 边界保持。原 PBF 未更新。此补充未修改任何共享运行时、地图、模型或资产清单，也不声明视觉/驾驶验收通过。
''')
files={str(f.relative_to(R)):sha(f) for f in sorted(P.iterdir()) if f.is_file() and f.name!='package-manifest.json'};(P/'package-manifest.json').write_text(json.dumps({'kind':'independent fixed-source lower cross-section proof; no edits to frozen proposal','frozenProposalManifestSha256':sha(P.parent/'package-manifest.json'),'date':'2026-11-11','files':files},indent=2));print(sha(P/'package-manifest.json'))
