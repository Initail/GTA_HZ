from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
DATE = '2026-10-12'

def source(id, url, publisher, title, date=None, provenance='primary', access='web-page-text-read', notes=''):
    return dict(id=id, url=url, publisher=publisher, title=title, sourceDate=date,
                accessedAt=DATE, provenance=provenance, accessMethod=access,
                license={'status':'unknown','notes':'未核验发布贴图/照片再分发许可；仅作资料与形体参考。'},
                use='reference-only; no photo texture generated or bundled',
                localPath=None, sha256=None, notes=notes)

sources = [
 source('som-gate','https://www.som.com/projects/greenland-hangzhou-century-center/','SOM','Greenland Hangzhou Century Center',access='search-index-text; direct fetch returned 403',notes='项目页列 2023 竣工；竣工年份不是网页发布日期。总建筑面积口径与中文项目宣传的53万平方米不同，不由面积推导足印。'),
 source('wulin-current','https://www.hzzx.gov.cn/cshz/content/2025-05/14/content_8994396.htm','杭州市政协网站 / 都市快报，记者董吕平','杭州武林广场“八少女”喷泉开始检修 5月22日恢复喷放','2025-05-14',provenance='government-hosted-original-field-report',notes='2025现场报道并回顾2016雕像复建；历史白水泥与现不锈钢喷白漆不混淆。'),
 source('unesco-westlake','https://whc.unesco.org/en/list/1334','UNESCO World Heritage Centre','West Lake Cultural Landscape of Hangzhou',access='search-index-page-text',notes='网页描述文本标CC-BY-SA IGO 3.0；本条不把该许可扩张到提名PDF或所有照片。'),
 source('unesco-nomination','https://whc.unesco.org/uploads/nominations/1334.pdf','中国缔约国提名文件 / UNESCO 发布','West Lake Cultural Landscape of Hangzhou nomination dossier',date=None,access='search-index-extract; whole PDF fetch rejected because 79,121,258 bytes',notes='申遗文件p64有白堤/苏堤尺寸与方向，p112有断桥构成平面图索引；本轮未下载/未量读图。不将网页搜索抓取日期当数据采集日期。'),
 source('ehangzhou-broken','https://www.ehangzhou.gov.cn/2018-06/14/c_242889.htm','杭州市人民政府新闻办公室英文网站','Duanqiao Bridge Remnant Snow','2018-06-14',notes='图1528770914755017832.jpg存在链接；拍摄日期与方位未核验。'),
 source('wgly-leifeng','https://wgly.hangzhou.gov.cn/art/2022/12/1/art_1229696389_58943150.html','杭州市文化广电旅游局','雷峰塔（雷峰夕照）','2022-12-01',access='search-index-page-text',notes='原文“五面八层”与设计师材料八角五层冲突，不能静默当作测绘参数。通高71米为约数。'),
 source('tsinghua-leifeng','https://www.thepaper.cn/newsDetail_forward_9592382','人文清华讲坛，原创黄薏橦 / 澎湃号平台','郭黛姮：雷峰新塔，彰显文化遗产魅力的里程碑','2020-10-17',provenance='primary-institutional-account-with-designer-statements',notes='包含新塔剖面/立面图、保护罩高度和柱网跨度。图片381.jpg/390.jpg抓取超时，396.jpg缓存未命中，本轮未读图。'),
 source('lingyin-2014','https://www.lingyinsi.org/detail_44_7946.html','灵隐寺运营方网站，编辑性恩行者','千年古寺 大慈灵隐','2014-08-08',notes='现状寺院主轴五殿；历史鼎盛期九楼十八阁等不得作为当前楼数。文章图片部分来源mzb.com.cn，不默认拥有图片再发布权。'),
 source('lingyin-grand','https://en.lingyinsi.org/detail_1141.html','Lingyin Temple 运营方','The Grand Hall','2013-01-18',access='search-index-page-text',notes='大雄宝殿面积1200m²为source reported，不由该面积假推长宽。'),
 source('lingyin-kings','https://en.lingyinsi.org/list_82.html','Lingyin Temple 运营方','The Hall of Heavenly Kings',access='search-index-page-text',notes='入口殿双檐；地址Fayun Lane Lingyin Road No.1只确认地点身份，不提供WGS84。'),
 source('civic-paper','https://global.ctbuh.org/resources/papers/download/1908-urban-mega-structure-vertical-landscape-of-hangzhou-civic-center.pdf','Linxue Li / CTBUH 2014 Shanghai Conference','Urban Mega-structure: Vertical Landscape of Hangzhou Civic Center','2014',provenance='primary-designer-conference-paper',access='search-index-extract; direct relocated PDF fetch failed',notes='旧地址https://global.ctbuh.org/resources/papers/1908-Li_2014_UrbanMegaStructure.pdf返回404。论文p224英文字段连桥85m、中文90m；100m为概括，不等同于精确建筑高。'),
 source('civic-cvu6','https://www.skyscrapercenter.com/building/hangzhou-civic-center-6/15397','Council on Vertical Urbanism / Skyscraper Center','Hangzhou Civic Center 6',provenance='primary-building-council-database',notes='建筑高109.6m、使用楼层高99.4m、26层，只直接支持本记录tower6，不把tower6映射A-F标签或其他五塔高度当已核验。'),
 source('balcony-hznews','https://hznews.hangzhou.com.cn/xinzheng/quxian/content/2012-11/02/content_4457933_2.htm','杭州网','“世界屋顶绿化最佳示范区金奖”花落钱江新城','2012-11-02',provenance='local-government-news-context',access='search-index-page-text',notes='沿岸底线宽150m、外挑80m×长320m；与考察文322m存在约数口径差，不定为测绘。'),
 source('balcony-fj','https://www.fjtb.gov.cn/focus/201707hxlw/201708/t20170829_11836501.html','福建省委台港澳工作办公室 / 海峡瞭望2017年第7期','浙江行思录','2017-08-29',provenance='government-hosted-observer-report',access='search-index-page-text',notes='主平台长约322m宽80m上下两层；不是杭州平台设计图。'),
 source('ott-grand','https://carlosott.com/?project=hangzhou-grand-theatre','Carlos Ott 设计方','Hangzhou Grand Theatre',access='search-index-full-project-text; direct fetch timed out twice',notes='列项目设计日期1999、2004完成、面积50000m²；未列建筑总高，不以歌剧厅舞台高度代替外部高度。'),
 source('hunter-conference','https://apvn.hunterdouglas.asia/project/hangzhou-international-conference-center','Hunter Douglas 幕墙产品供应商','HANGZHOU INTERNATIONAL CONFERENCE CENTER',notes='报总高85m、球直径85m、椭圆附楼13m、金玻璃/蜂窝面板；二手百科裙房12m不能静默合并。'),
 source('icc-operator','https://www.intercontinental.com/hotels/gb/en/hangzhou/hghha/hoteldetail?cid=145698&newRedirect=true&qDest=No.+2+Jiefang+East+Road%2C+Hangzhou%2C+ZJ%2C+CN&qSlH=hghha&setPMCookies=true','InterContinental Hangzhou ICC 运营方','InterContinental Hangzhou ICC',access='search-index-page-text',notes='确认金球与对面月形大剧院的组合；当前客房384和会议面积不用于建模尺寸。'),
 source('nbbj-olympic','https://www.nbbj.cn/work/hangzhou-olympic-sports-center/','NBBJ 设计方','杭州奥体中心',notes='确认与CCDI合作、三层步行空间、公园/浅色地面/地下停车。中文页面积37000m²口径不清，不采用作为足印或综合体面积。'),
 source('lotus-2021','https://www.hangzhou2022.cn/hzhyn/mlhz/202105/t20210514_26126.shtml','杭州亚运会组委会官网','杭州奥体中心：“莲花”盛放时 宾朋四方至','2021-05-14',access='search-index-page-text',notes='大莲花28大+27小，小莲花24固定+8开合；小莲花15分钟与2022页面20分钟有运行描述差异，无新增游戏机制要求。'),
 source('little-lotus-2022','https://www.hangzhou2022.cn/sssg/sscg/202203/t20220330_46200.shtml','杭州亚运会组委会官网','杭州奥体中心网球中心','2022-04-01',access='search-index-page-text',notes='网页日期2022/04/01，URL含20220330。建筑面积523000m²与其他总中心约5.2万m²冲突，疑误，不用于足印。'),
 source('little-lotus-motion','https://www.hangzhou2022.cn/xwzx/jdxw/ttxw/202206/t20220627_50173.shtml','杭州亚运会组委会官网','打卡亚运场馆“大小莲花” 高颜值场馆里藏着大智慧','2022-06-27',access='search-index-page-text',notes='官方采访转轴旋转/45°，是现有建筑能力证据，不代表上游游戏实现屋盖互动。'),
 source('ccdi-lotus','https://www.archina.com/index.php?a=show&g=works&id=3484&m=index','CCDI悉地国际项目投稿 / ARCHINA平台','杭州奥体博览城主体育场','2019-09-13',provenance='primary-designer-project-submission',access='search-index-full-project-text; direct fetch redirect loop',notes='给60.7m罩棚最高结构标高。投稿竣工年份2017、地点写萧山区青年路，与运营场馆2019启用/滨江飞虹路口径不同；不能直接混入当前邮政地址或竣工时间。'),
 source('fuxing-2026','https://www.hzzx.gov.cn/zxyw/content/2026-09/20/content_9311674.htm','上城史志 / 杭州市政协网站','寻梦上城 | 复兴大桥','2026-09-20',provenance='government-local-history',access='search-index-page-text',notes='两座190m主拱+9座85m小拱、主桥1376m、双层、上层六车道及下层组织。不是桥坡度施工图。'),
 source('xixing-2026','https://www.hzzx.gov.cn/zxyw/content/2026-10/12/content_9334487.htm','上城史志 / 杭州市政协网站','寻梦上城 | 西兴大桥','2026-10-12',provenance='government-local-history',access='search-index-page-text',notes='81m双塔、1280m主桥为旧桥；改建2024启动/2027计划。本轮日历日期与文章日期相同，不将计划作为完工。'),
 source('xixing-closure','https://www.hzzx.gov.cn/cshz/content/2025-11/10/content_9120865_0.htm','杭州市政协网站，交通组织发布会报道','时间定了！钱江三桥将全封闭断流施工！禁行范围确定，14条绕行路径公布','2025-11-10',provenance='government-hosted-traffic-announcement-report',access='search-index-page-text',notes='2025-11-22零时起旧桥全封闭断流，禁止车辆行人；本条针对历史发布的施工状态。'),
 source('xixing-firstday','https://hznews.hangzhou.com.cn/chengshi/content/2025-11/23/content_9129621_0.htm','杭州网现场报道','钱江三桥封闭施工首日周边交通情况如何？','2025-11-23',provenance='primary-field-report',access='search-index-page-text',notes='证实断流启动而非只有计划；新桥双层上层八车道是未来工程，不放进旧桥模型。'),
 source('zhijiang-transport','https://tb.hangzhou.gov.cn/art/2017/9/8/art_1510413_19832695.html','杭州市交通运输局','2015版杭州市年鉴交通篇','2017-09-08',provenance='primary-government-transport-yearbook',access='search-index-page-text',notes='线路4.7km含接线；塔90.5m主桥宽40.5m；2013通车，不声称本轮通行实测。'),
 source('qiantang-archive','https://www.zjda.gov.cn/col/col1402047/index.html','浙江省档案馆','钱塘江大桥专题',access='web-page-text-read',notes='档案页报公路1453m×6.1m、铁路1322.1m；历史建桥/修复资料，未核验现状宽度与桥坡。'),
 source('boao-naming','https://www.hangzhou.gov.cn/art/2021/11/12/art_1229063387_1804264.html','杭州市人民政府','杭州市人民政府关于对潮声路等部分道路桥梁隧道人行地道命名的批复','2021-11-12',access='search-index-page-text',notes='列博奥隧道2772m×9m和南北端位置；宽度未注明单管/整体口径。'),
 source('boao-designer','https://www.hzyjfz.cn/index.php?a=detail&g=&id=42&m=project','杭州市地下工程设计研究院相关项目网站','博奥隧道',provenance='project-design-organization',access='search-index-page-text',notes='全长约2.8km双向四车道、设计时速60km/h；网页精确机构版权未进一步核验，不据此定施工剖面。'),
]
by_source = {s['id']:s for s in sources}

def obs(kind, value, basis, ids, unit=None, uncertainty=None):
    return dict(kind=kind,value=value,unit=unit,basis=basis,sourceIds=ids,
                uncertainty=uncertainty or ('source reported; 未作本轮测量，数据对应来源所述时期。' if basis=='reported' else '尚无可冻结数据；待固定OSM/DEM及现状多视向资料。'))

def unknown(kind):
    return obs(kind,None,'unknown',[])

COMMON_BLOCKERS = [
 '尚未绑定固定哈希OSM source feature ID、WGS84 center、足印与数值朝向。',
 '未完成两个不同方向现状照片的逐图视角核验、近景入口核验及来源与建模参数冻结。',
 '本轮为资料调查；无GLB、模型脚本、实机图、碰撞、性能或八项verified验收。'
]
objects=[]
def add(id,name,type,source_ids,observations,suggestion,blockers=None,images=None,pending=None):
    objects.append(dict(schemaVersion=1,placeId=id,name=name,type=type,recordedStage='planned',
        scope='独立公开证据调查；主集成需补足坐标/模型/验收',
        identity={'status':'confirmed','sourceIds':source_ids},
        location={'crs':'EPSG:4326','center':None,'status':'unknown','sourceIds':[]},
        sources=[by_source[s] for s in source_ids], observations=observations,
        modelingRecommendation={'basis':'inference-from-recorded-sources','notes':suggestion},
        referenceImages=images or [], pendingSubscopes=pending or [],
        blockers=COMMON_BLOCKERS+(blockers or []), estimatedParameters=[],
        measuredParameters=[], sourceSnapshots={}, photosBundled=False))

add('hangzhou-gate','杭州之门（杭州世纪中心）','building-group',['som-gate'],[
 unknown('footprint'),obs('height',310,'reported',['som-gate'],'m'),unknown('orientation'),
 obs('building_count',{'towers':2,'storiesReported':64},'reported',['som-gate']),
 obs('silhouette','H形双塔；连续曲面玻璃外皮、弧形连桥下腹形成月洞门意象','reported',['som-gate']),
 obs('night_lighting','内侧幕墙6000余LED沿建筑线条延伸，可有动态彩色模式','reported',['som-gate']),
 unknown('skybridge_elevation'),unknown('entrances')],
 '先冻两塔真实足印与对江朝向，再做曲面塔体、上下非水平的拱下连桥与裙房；近景用合并网格表现幕墙节奏。灯效应复用材质/灯光预算，不新增6000个真实点光源。',
 ['总高310m应对应建筑高，未拆分屋顶与冠顶标高；连桥尺寸、端部退台与入口均未读图冻结。'])

add('wulin-square','武林广场','district',['wulin-current'],[
 unknown('extent'),obs('layout','中心八少女喷泉，少女3个中央+5个外围两组','reported',['wulin-current']),
 obs('silhouette','开敞城市广场中的喷泉与白色雕像组合；周围浙江展览馆等需分别建模','reported',['wulin-current']),
 obs('sculpture_material','2016复建雕像为不锈钢喷白色氟碳漆；旧1984白水泥不当作当前材质','reported',['wulin-current']),
 unknown('fountain_dimensions'),unknown('orientation'),unknown('entrances')],
 '先以当前广场足印组织喷泉、雕像、植物与铺装，再拆浙江展览馆、杭州剧院等独立对象；不能复制历史时期广场道路或喷泉尺寸。',
 ['未取得当前喷泉直径/梅花盆轮廓实测或施工图；36m网上常见尺寸未由本轮所选当前一手文档确认。'])

add('west-lake','西湖','landscape',['unesco-westlake','unesco-nomination'],[
 unknown('extent'),unknown('elevation_profile'),
 obs('layout','湖面、三面丘陵、两堤三岛共同构成文化景观，湖东为城市','reported',['unesco-westlake']),
 obs('silhouette','需要保留丘陵天际线与湖岸/堤/岛的整体相对关系','reported',['unesco-westlake'])],
 'OSM湖岸进入基础水体，DEM覆盖环湖丘陵；白堤与苏堤实地走向和桥孔分别建地表/碰撞。不可用椭圆薄片加小丘替代真实西湖。',
 ['提名网页的遗产范围3322.88ha并非湖水面积；不能拿作水面尺寸。湖面基准、岛岸和地形还未冻结。'],
 pending=['小瀛洲/三潭印月、湖心亭、阮公墩为景观框架证据，尚无独立精修任务包。'])

add('bai-causeway','白堤','linear-landscape',['unesco-nomination'],[
 obs('extent',{'length':987,'width':33},'reported',['unesco-nomination'],'m','提名材料p64当时尺寸，未验证2026现状；未由该尺寸替换OSM折线。'),
 obs('orientation','东西向，东连断桥，西连孤山','reported',['unesco-nomination']),
 obs('layout','白堤划分湖区；需与断桥和孤山同一坐标快照','reported',['unesco-nomination']),
 unknown('elevation_profile'),unknown('silhouette')],
 '沿真实OSM堤中心/岸边组织树列、铺面、草地与护岸；断桥、锦带桥的坡面是独立结构，不把整段堤举到同一桥高。',
 ['宽33m是堤体描述，未确认车/步行铺面宽；不得将整个33m都当可驾驶宽度。'])

add('su-causeway','苏堤','linear-landscape',['unesco-nomination'],[
 obs('extent',{'length':2797,'widthRange':[30,40]},'reported',['unesco-nomination'],'m','提名材料p64；地方历史资料可有不同量法，冻结以当期源几何为准。'),
 obs('orientation','南北跨湖，由南屏山北麓到北山','reported',['unesco-nomination']),
 obs('layout',{'stoneArchBridges':6,'causewayAboveLakeReported':0.4},'reported',['unesco-nomination'],'m','0.4m为来源时相相对湖面，不是WGS84/DEM绝对海拔。'),
 obs('silhouette','长堤与六座单孔石拱桥','reported',['unesco-nomination']),unknown('elevation_profile')],
 '六桥逐一构造桥洞、连续拱上可步行桥面与坡道；OSM标签决定车行/步行路线。湖水仍连通桥孔。',
 ['桥名/桥逐一跨度与坡度没有冻结；0.4m堤面不可替代桥面拱高。'])

add('broken-bridge','断桥（断桥残雪）','bridge',['ehangzhou-broken','unesco-nomination'],[
 unknown('footprint'),unknown('height'),unknown('orientation'),
 obs('silhouette','完整灰石拱桥；积雪在拱部先融形成断开的视觉意象','reported',['ehangzhou-broken']),
 obs('layout','白堤东端连接点','reported',['unesco-nomination'])],
 '按实际单桥足印与剖面做连续桥面、灰石栏杆、桥洞及两端无障碍衔接；“断桥”不产生破损路面或断掉的导航边。',
 ['来源p112平面图只是搜索索引定位，本轮未读该图，桥孔数量/尺寸不冻结。'])

add('leifeng-pagoda','雷峰塔（现雷峰新塔）','building',['wgly-leifeng','tsinghua-leifeng'],[
 unknown('footprint'),obs('height',{'totalApprox':71,'heritageCover':9.7},'reported',['wgly-leifeng','tsinghua-leifeng'],'m','71m是文旅约数；9.7m为设计师材料；本轮不把未经原设计论文核验的71.679m假标实测。'),
 unknown('orientation'),obs('silhouette','八角平面、外观五层楼阁式、平座腰檐、铜饰钢结构，跨遗址保护罩','reported',['tsinghua-leifeng']),
 obs('structure',{'maxColumnGridSpan':48},'reported',['tsinghua-leifeng'],'m','48m为柱网最大跨度，不是建筑足印边长或径长。'),
 obs('material','瓦、脊、柱、栏杆等薄铜构件；采用现代钢结构','reported',['tsinghua-leifeng']),unknown('entrances')],
 '先核实夕照山基面和八角台基；外观五层逐层做平座、斗拱节奏与飞檐，不用五边塔。铜材质按参考做颜色/粗糙度，图片不打包贴图。',
 ['文旅页“五面八层”疑字序错误，与人文清华设计师材料冲突；优先采用设计师说明八角五层，但精确层高/总高仍等待读剖面。'],
 images=[{'sourceId':'tsinghua-leifeng','url':'https://imagepphcloud.thepaper.cn/pph/image/93/925/381.jpg','kind':'section-and-elevation','captureDate':None,'viewDirection':'unknown','status':'fetch-timeout-not-viewed','license':'unknown'},
 {'sourceId':'tsinghua-leifeng','url':'https://imagepphcloud.thepaper.cn/pph/image/93/925/390.jpg','kind':'exterior-photo','captureDate':None,'viewDirection':'unknown','status':'fetch-timeout-not-viewed','license':'unknown'}])

add('lingyin-temple','灵隐寺','building-group',['lingyin-2014','lingyin-grand','lingyin-kings'],[
 unknown('footprint'),obs('height',{'grandHall':33.6},'reported',['lingyin-2014'],'m'),
 unknown('orientation'),obs('building_count',{'axialHalls':5,'auxiliaryBuildings':None},'reported',['lingyin-2014'],'count','轴线五殿不是全寺楼栋总数；历史九楼十八阁等不能用于当前数量。'),
 obs('layout',{'axialOrder':['天王殿','大雄宝殿','药师殿','法堂（直指堂）','华严殿']},'reported',['lingyin-2014']),
 obs('silhouette','依轴线层层递进；大雄宝殿三重歇山顶、7间面宽4间进深；天王殿双檐','reported',['lingyin-2014','lingyin-kings']),
 obs('footprint_reported_area',{'grandHall':1200},'reported',['lingyin-grand'],'m2','source reported面积；没有通过假设方形得到长宽。'),
 unknown('entrances'),unknown('terrace_elevation')],
 '把五殿作为独立足印和高度分段，随真实山坡台基递进；入口天王殿、院墙与两侧附殿必须避开行人/道路。山地不是单个合成球。',
 ['五殿分别足印/高度（除大雄）/屋顶方位和寺区边界仍缺数据；未采DEM，不称高程实测。'])

add('civic-center','杭州市民中心','building-group',['civic-paper','civic-cvu6'],[
 unknown('footprint'),obs('height',{'designerNominalTower':100,'cvuTower6Architectural':109.6,'cvuTower6Occupied':99.4},'reported',['civic-paper','civic-cvu6'],'m','100m为论文概括；CVU支持tower6记录，不自动推断其他5塔为同值。'),
 unknown('orientation'),obs('building_count',{'highRises':6,'podiumGroups':4},'reported',['civic-paper','civic-cvu6']),
 obs('extent',{'blockWidth':400,'blockDepth':400},'reported',['civic-paper'],'m','400m见方街区不是每座建筑足印。'),
 obs('silhouette','六塔围合中央庭院，上部空中连桥，四裙楼组织周边街区','reported',['civic-paper','civic-cvu6']),
 obs('skybridge_elevation',{'englishPaper':85,'chinesePaper':90,'cvuSummary':85},'reported',['civic-paper','civic-cvu6'],'m','论文中英数值差异未解决，不假定两者是底/顶标高。'),unknown('entrances')],
 '用六弧形塔楼与上部连桥恢复天圆地方视觉，再做四裙楼与可达公共庭院；入口和路边到达点不会选中央有盖不可进的建筑内。',
 ['连桥85/90m标高口径冲突；tower6不等于已确认A-F标签。未读可供量测剖面或足印。'])

add('city-balcony','杭州城市阳台（主阳台与必要两翼衔接）','district',['balcony-hznews','balcony-fj'],[
 unknown('extent'),obs('reported_dimensions',{'riverProjection':80,'lengthRange':[320,322],'bankBaselineWidth':150},'reported',['balcony-hznews','balcony-fj'],'m','80m与150m口径不同；320/322m为历史描述，不视为测绘误差已量定。'),
 obs('layout','钱江新城中轴尽端挑江主阳台双层，两翼副阳台衔接沿江景观','reported',['balcony-hznews','balcony-fj']),
 obs('silhouette','大范围架空挑江平台而非独立高楼','reported',['balcony-fj']),
 unknown('orientation'),unknown('deck_elevation'),unknown('entrances')],
 '主阳台按实际岸线方向放置，明确结构支撑、上下层地板与江堤入口；水体保留在平台下方，防止落水到达点或薄片被过滤。',
 ['没有取得平台曲线足印/柱位与上下层标高；322m不能作为随意拉长到江中的长度。'])

add('grand-theatre','杭州大剧院','building',['ott-grand'],[
 unknown('footprint'),unknown('height'),unknown('orientation'),
 obs('silhouette','月形雕塑主量体；双曲玻璃立面与钛金属屋顶，倒锥歌剧厅核心','reported',['ott-grand']),
 obs('layout','钱塘江边的新商务区首期文化建筑；室外露天剧场/周边绿地','reported',['ott-grand']),
 unknown('entrances')],
 '保留新月壳体、倾玻璃面与内部倒锥相互层次；足印和朝向确认后再分近景材质。不可用单个银色半球替代。',
 ['官方网页本轮两次fetch timeout但搜索索引有项目文字；未取得总高与足印，不能拿舞台内部高作为楼高。'])

add('international-conference-center','杭州国际会议中心（杭州洲际酒店ICC）','building',['hunter-conference','icc-operator'],[
 obs('footprint',{'sphereDiameterReported':85,'ovalAnnexPlan':None},'reported',['hunter-conference'],'m','85m是球体直径；完整建筑足印包含裙房，尚未知。'),
 obs('height',{'overall':85,'annex':13},'reported',['hunter-conference'],'m','供应商项目页口径，未实测；二手12m裙房数字不静默合并。'),
 unknown('orientation'),obs('building_count',{'sphere':1,'ovalAnnex':1},'reported',['hunter-conference']),
 obs('silhouette','金色球体与椭圆附楼，金玻璃及金色蜂窝复合板幕墙；与对面月形大剧院呼应','reported',['hunter-conference','icc-operator']),unknown('entrances')],
 '球体需按现状底部截切和窗带而非纯整球落地；建立椭圆裙房、入口/挑檐与临水空间，再做金色材质。',
 ['未确定球心标高、底部截球与裙楼衔接；与杭州国际博览中心是不同对象，不得用博览中心屋顶60m球混入。'])

nbbj_images=[dict(sourceId='nbbj-olympic',url=u,kind='official-gallery',captureDate=None,viewDirection='unknown',status='link-resolved-not-visually-reviewed',license='unknown') for u in [
 'https://www.nbbj.cn/wp-content/uploads/2022/08/100526_00_Hangzhou_N77_screenview.jpg',
 'https://www.nbbj.cn/wp-content/uploads/2022/08/100526_00_Hangzhou_Tennis_Swimming_screenview-2000x1334.jpg',
 'https://www.nbbj.cn/wp-content/uploads/2022/07/100526_00_Hangzhou_N82_screenview.jpg',
 'https://www.nbbj.cn/wp-content/uploads/2022/07/100526_00_Hangzhou_N69_screenview.jpg']]
add('big-lotus','杭州奥体中心主体育场（大莲花）','building',['lotus-2021','nbbj-olympic','ccdi-lotus'],[
 unknown('footprint'),obs('height',{'canopyTopStructuralElevation':60.7},'reported',['ccdi-lotus'],'m','设计方投稿报罩棚最高点结构标高，未取其基面定义；不是DEM海拔。'),
 unknown('orientation'),obs('component_count',{'largePetals':28,'smallPetals':27},'reported',['lotus-2021','ccdi-lotus']),
 obs('silhouette','莲花瓣围绕场馆，内部混凝土碗体与钢壳协同；三层步行空间连接网球中心和商业','reported',['lotus-2021','nbbj-olympic']),unknown('entrances')],
 '先真实椭圆足印、开放场芯、看台碗体与错位大小花瓣，材料/夜景后置；不能做单圈等大的花瓣或封顶球。用合并/实例重复瓣而非每窗独立。',
 ['CCDI投稿2017竣工与运营2019启用有口径差；NBBJ中文37000m²面积未采用。花瓣实际厚度/瓣尖高度分布未知。'],images=nbbj_images)

add('little-lotus','杭州奥体中心网球决赛馆（小莲花）','building',['little-lotus-2022','little-lotus-motion','nbbj-olympic'],[
 unknown('footprint'),unknown('height'),unknown('orientation'),
 obs('component_count',{'fixedLowerPetals':24,'movableUpperPetals':8},'reported',['little-lotus-2022','little-lotus-motion']),
 obs('silhouette','24下层固定瓣与8旋转屋盖；相邻主体育场，共享三层步行组织','reported',['little-lotus-2022','nbbj-olympic']),
 obs('roof_motion',{'rotationDirectionWhenOpening':'counterclockwise','maxAngle':45},'reported',['little-lotus-motion'],'deg','建筑现实能力；不代表上游已有该游戏互动，不要求新增玩法。'),unknown('entrances')],
 '冻一个来源明确的屋盖状态，保持上下层瓣不同节奏；花瓣有独立转轴几何但不据此宣称新增互动。外围决赛馆以外球场另按OSM。',
 ['官网523000m²建筑面积疑误，未采用；屋盖15/20分钟描述差异与本轮静态候选无关。总高与平面直径未冻结。'],images=nbbj_images,
 pending=['两片半决赛场、预赛与练习场、室内网球馆未做逐对象精修。'])

add('fuxing-bridge','复兴大桥（钱江四桥）','bridge',['fuxing-2026'],[
 obs('extent',{'mainBridgeLength':1376},'reported',['fuxing-2026'],'m'),unknown('height'),unknown('orientation'),
 obs('silhouette','双层系杆拱，多跨连拱','reported',['fuxing-2026']),
 obs('layout',{'bigArchCount':2,'bigArchSpan':190,'smallArchCount':9,'smallArchSpan':85,'upperMotorLanes':6},'reported',['fuxing-2026'],'m','跨度、车道来源reported；不由各跨和推算引桥或末跨。'),
 unknown('ramp_profile')],
 '上下桥面独立layer，分别连真实匝道；大小拱排列核对现状后冻结，柱/拱不应穿入有效驾驶净空。',
 ['下层公交/慢行与普通机动车具体口径、桥面标高和坡道需当前OSM/结构图；未实驾跨桥。'])

add('xixing-bridge','西兴大桥（钱江三桥）旧桥形体与施工状态','bridge',['xixing-2026','xixing-closure','xixing-firstday'],[
 obs('extent',{'oldMainBridgeLength':1280},'reported',['xixing-2026'],'m'),
 obs('height',{'oldTowers':81},'reported',['xixing-2026'],'m'),unknown('orientation'),
 obs('silhouette','等跨双独塔单索面斜拉旧桥、两座塔','reported',['xixing-2026']),
 obs('layout',{'oldLanes':6,'closureStart':'2025-11-22T00:00:00+08:00','newBridgePlannedCompletion':'2027年底'},'reported',['xixing-2026','xixing-closure','xixing-firstday']),unknown('ramp_profile')],
 '先决定统一呈现年代。旧桥模型可做历史参考，但当前数据快照需从车行导航中排除全封闭桥段；未来双层八车道不替旧桥。',
 ['当前施工年与完备旧桥外观存在时间冲突；主集成必须记录历史/游戏呈现或当前施工状态，不可宣称旧桥现可通。'])

add('zhijiang-bridge','之江大桥（钱江七桥）','bridge',['zhijiang-transport'],[
 unknown('footprint'),obs('height',{'tower':90.5},'reported',['zhijiang-transport'],'m'),unknown('orientation'),
 obs('reported_dimensions',{'mainBridgeWidth':40.5,'routeIncludingApproachesKm':4.7},'reported',['zhijiang-transport'],'mixed','4.7km包含线路接线，非跨江主体长度。'),
 obs('silhouette','双索面拱形钢塔斜拉桥','reported',['zhijiang-transport']),unknown('ramp_profile')],
 '按OSM桥段与引道分离后做拱形塔/双索面；桥塔不取西兴独塔模型。',
 ['未取得主体跨径和桥面标高；资料为历史交通年鉴，不证明当前通行或收费。'])

add('qiantang-bridge','钱塘江大桥（钱江一桥）','bridge',['qiantang-archive'],[
 obs('extent',{'upperRoadLength':1453,'upperRoadWidth':6.1,'lowerRailLength':1322.1},'reported',['qiantang-archive'],'m','历史档案介绍尺寸；两层长度不同，含引道口径未分解，非本轮测量。'),unknown('height'),unknown('orientation'),
 obs('silhouette','公路/铁路双层两用现代桥梁；茅以升主持设计建造','reported',['qiantang-archive']),obs('layout',{'upper':'公路','lower':'单线铁路','completion':'1937-09-26'},'reported',['qiantang-archive']),unknown('ramp_profile')],
 '用真实桥梁/铁路源线区分上下层，铁路不进入汽车路网；桁架、桥墩和道路净空须有进一步图证。',
 ['历史档案报尺寸但现状桥宽/改建变化、跨径、车道与坡道还未核实。'])

add('boao-tunnel','博奥隧道（奥体至钱江新城必要过江通道）','tunnel',['boao-naming','boao-designer'],[
 obs('extent',{'reportedLength':2772,'reportedWidthUnqualified':9},'reported',['boao-naming'],'m','官方命名批复未说明9m是单管或全体，不推定双管总宽。'),
 unknown('height'),unknown('orientation'),
 obs('layout','南起博奥路与平澜路，下穿钱塘江，北接新业路；项目介绍双向四车道','reported',['boao-naming','boao-designer']),
 obs('silhouette','水下道路隧道，不是桥面','reported',['boao-naming']),unknown('ramp_profile')],
 'layer/tunnel不能丢失，入口坡道连回地面道路；水体上不生跨江平面车道，也不允许中途与桥/地面线相交连通。',
 ['未获得水下埋深、入口坡度与实际车行净高；官方长度/宽度不能替代完整剖面。'])

(ROOT/'sources.json').write_text(json.dumps({'schemaVersion':1,'researchDate':DATE,'timezone':'Asia/Shanghai','remoteSnapshotsDownloaded':False,'sources':sources},ensure_ascii=False,indent=2)+'\n')
for item in objects:
    (ROOT/(item['placeId']+'.evidence.json')).write_text(json.dumps(item,ensure_ascii=False,indent=2)+'\n')
(ROOT/'object-index.json').write_text(json.dumps({'researchDate':DATE,'objects':[{'id':o['placeId'],'name':o['name'],'type':o['type'],'evidencePath':o['placeId']+'.evidence.json','stage':'planned','locationStatus':'unknown'} for o in objects]},ensure_ascii=False,indent=2)+'\n')
paths = sorted(p for p in ROOT.iterdir() if p.is_file() and p.name!='research-hashes.json')
hashes = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
(ROOT/'research-hashes.json').write_text(json.dumps({'algorithm':'SHA256','scope':'local research records only; not remote source/photo hashes or model validation','files':hashes},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'objects':len(objects),'sources':len(sources),'hashFiles':len(hashes),'root':str(ROOT)},ensure_ascii=False))
