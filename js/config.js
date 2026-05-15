/**
Sub 一键批量取消工作表隐藏()

Dim sht As Worksheet

For Each sht In Worksheets

sht.Visible = xlSheetVisible

Next

End Sub
*/

var Configure = (function(){
	var debug = false;
	var Debug = function(msg) {
		if(!!Configure.debug) 
			console.log(msg);
	};
	var version = 'dev';
	var date = new Date();
	var mode;       // 0 复盘模式， 1 盯盘模式, 2 移动端
	var modeType = {
		FP: 0,
		DP: 1,
		MP: 2,
	}
    
    // echelon 
	var echelons = [
		//赛道
		{name: '风光', hotPoints:['光伏','有机硅概念','风电', '绿电']},
		{name: '电力', hotPoints:['智能电网', '特高压', '虚拟电厂', '电力','电力行业']},
		{name: '储能', hotPoints:[ '储能', 'HJT电池','钒电池', 'TOPCon电池','盐湖提锂', '锂电池', 'TOPCON电池']},
		{name: '新能源车', hotPoints:['新能源车', '新能源汽车', '汽车零部件', '汽车热管理','一体化压铸', 
					'比亚迪', '毫米波雷达', '汽车激光雷达']},
		{name: '环保', hotPoints:['环保', '环保行业', '污水处理','固废处理','绿色发电']},
		
		//大科技
		{name: '半导体芯片', hotPoints:['汽车芯片', '半导体', 'PCB概念', '国产芯片', '半导体概念',
				'第三代半导体', '中芯国际概念','芯片','集成电路',  '光刻机', '光刻胶', '先进封装', 'chiplet']},
		{name: '机器人', hotPoints:['机器人', '智能制造', '减速器']},
		{name: '传媒', hotPoints:['传媒','文化传媒', '游戏', '云游戏','手机游戏']},
		{name: 'MR', hotPoints:['元宇宙', 'VR', '虚拟现实', '空间计算', 'OLED' , '裸眼3D']},
	
		{name: '数据要素', hotPoints:['数据要素','数据确权','信创', '数字经济']},
		{name: '算力', hotPoints:['算力','数据中心','云计算', '东数西算']},				
		{name: '人工智能', hotPoints:['AI','人工智能','AIGC','ChatGPT', '百度文心一言']},
		{name: '军工', hotPoints:['航天航空', '军工','大飞机','国产航母', '卫星导航', '北斗','卫星通信']},
		{name: '通讯', hotPoints:['通信设备','5G', '6G', '5G概念']},
		{name: '存储', hotPoints:['数据存储','固态存储', '存储芯片', '存储器芯片']},
		{name: 'CPO', hotPoints:[ 'CPO概念', '光通信', '光模块', '光芯片', '光模块连接器']},
		{name: '脑机接口', hotPoints:[ '脑机接口', '人脑工程', '类脑芯片', '神经元网络', '脑科学']},
		
		// 消费
		{name: '白酒', hotPoints:['白酒','啤酒概念','白酒概念', '烟草']},
		{name: '医药', hotPoints:['新冠药物', '医药', '中药', '新冠治疗', '维生素','医疗器械', '减肥药', '肝炎概念', '创新药', 'CRO', '中药概念']},
		{name: '消费电子', hotPoints:['消费电子','智能穿戴','无线耳机', '智能音箱']},
		{name: '家电', hotPoints:['白色家电','黑色家电', '小家电', '家电行业']},
		{name: '农业', hotPoints:['农业种植', '大豆', '玉米', '农产品加工', '养殖']},	
		{name: '大消费', hotPoints:['酒店旅游', '乳业', '食品饮料', '零售']},	
		
		//周期能源
		{name: '能源', hotPoints:['煤炭','石油','天然气','煤化工']},
		{name: '金属', hotPoints:['有色金属','黄金','小金属概念', '钴', '金属锌', '金属铜', '金属铅', '金属镍']},
		{name: '化工', hotPoints:['化工']},	
		{name: '硅材料', hotPoints:['硅', '硅橡胶']},	
		
		//大金融
		{name: '基建', hotPoints:['建筑材料', '建筑装饰', '水利', '装配式建筑', '公路铁路运输']},
		{name: '地产', hotPoints:['房地产开发', '房地产', '物业管理', '新型城镇化']},
		{name: '金融', hotPoints:['银行', '保险', '证券', '券商', '券商概念', '金融']},
		
		// 服务
		{name: '服装', hotPoints:['服装加工']},	
		{name: '酒店旅游', hotPoints:['酒店及餐饮']},
		{name: '教育', hotPoints:['在线教育', '职业教育', '教育信息化']},		
		{name: '航运', hotPoints:['机场航运', '港口航运']},
		
		// 风格
		//{name: '带路中特估', hotPoints:['一带一路', '国资','中字头','国企改革', '中特估']},
		{name: '次新股', hotPoints:['注册制次新股', '科创次新股', '次新股']},
		{name: '半年报预增', hotPoints:['半年报预增']},
		// 其他
		{name: '供销社', hotPoints:['供销社', '乡村振兴']},
	];
	var gaiBlackList_verbose = ['注册制次新股','科创次新股','专精特新','昨日触板','昨日连板',
				 '昨日涨停', 'ST股','破净股','百元股','科创板做市商', '科创板做市股', '国企改革', '央企改革',
				];
	var gaiBlackList_critical = ['-', '融资融券', '深股通', '创业板综', '预亏预减', '预盈预增', '富时罗素',
				'沪股通', '华为概念', '机构重仓', '基金重仓', '区块链', '标准普尔',
				'深成500', '物联网', '大数据','QFII重仓', '送转预期','深证100R', '股权转让',
				'MSCI中国', '中证500','上证50_', '深圳特区','股权激励', '转债标的', '上证380', 
				'贬值受益','内贸流通','参股新三板','AH股','证金持股','AB股','上证180_', 'HS300_',
				'壳资源','参股期货','高送转','债转股',  '沪企改革',
				'昨日连板_含一字','昨日涨停_含一字',
				];
	
	/* @AI emotion v2 
	/	a情绪角度（d7）	b情绪level(M8,2)	c亏钱效应	d上证角度(d5)	
	/	e情绪指数角度(d5)	f涨停数量	g跌停数量	h炸板数量	
	/	i连扳背离	j连扳高度	k连扳数量	l连扳晋级(M10,2.5) m短线资金
	/
	/  @param
	/   min  max  currentMin  currentMax  days minDays
	*/
	var bandConditions = [{k:{days:5, minDays:4, max:5}},
							{j:{days:5, minDays:4, max:5}}, 
							{f:{days:5, minDays:3, max:30}},
							{m:{days:5, minDays:4, max:200}}
							];
	var icePoint = [{c:{days:2, minDays:1, max:-0.5}},
						{d:{days:1, minDays:1, max:-20}}, 
						{k:{days:1, minDays:1, max:5}},
						{i:{days:1, minDays:1, max:4}},
						{m:{days:1, minDays:1, max:200}}
		];	
	var winCtxts = ['启动','分歧','确认', '加速', '加歧', '博傻', '冰启', '冰加', '冰衰'];
	var getColorFromWinC = function(str) {
		var retObj = {};
		if(str.indexOf('w') >= 0 ||  str.indexOf('W')>=0) {
			var index = str.indexOf('w') >= 0 ? str.indexOf('w') : str.indexOf('W');
			var i = parseInt(str.substr(index+1, index + 1));
			var color;
			switch (i) {
				case 0:
					color = 'black';
					break;
				case 1:
					color = 'grey';
					break;
				case 2:
					color = 'Orange';
					break;
				case 3:
					color = 'OrangeRed';
					break;
				case 4:
					color = 'Peru';
					break;
				case 5:
					color = 'Red';
					break;
				case 6:
					color = 'DarkSeaGreen';
					break;
				case 7:
					color = 'Darkgreen';
					break;
				case 8:
					color = 'green';
					break;
			}
			retObj.color = color;
			retObj.des = winCtxts[i];
		}
		return retObj;
	}
	var cangMap = new Map([
		['启动', {conditions:[{b:{max:0}, j:{days:7, minDays:3, min:4}},
							{a:{currentMax:45},b:{max:1},m:{days:7, minDays:4, max:100}, f:{days:3,minDays:2, min:25}}
								], context:['博弈']}],
		['冰衰', {conditions:[{a:{max:0,currentMax: -5}, b:{max:1}, c:{days:4, minDays:3, min:0.25}}], context:['博弈']}], 
		['确认', {conditions:[{a:{currentMin:15},b:{max:1},e:{min:0}}], context:['博弈']}],	
		['分歧', {conditions:[{a:{ currentMin:15}, b:{max:1}, f:{min:25}, k:{min:5}}], context:['主升']}],  
		['加速', {conditions:[{a:{currentMin:30}, b:{min:1,max:2}, i:{min:5}, j:{min:3}}], context:['主升']}],
		['加歧', {conditions:[{a:{min:0, currentMax:0}, b:{min:2,max:3}, c:{max:0.3}, l:{days:3, minDays:3, min:5}}], context:['主升']}],
		['博傻',{conditions:[{a:{min:0, currentMin:0}, b:{min:2,max:3}}], context:['主升']}],
		['冰启', {conditions:[{a:{currentMax:0}, b:{min:2,max:2}, f:{max:40}}], context:['退潮']}],
		['冰加', {conditions:[{b:{max:1}}], context:['退潮']}],
		['', {conditions:[{}], context:['主升']}]
	]);
	var getContextDescription = function(str) {
		str=str.replace('M', '周期');
		str=str.replace('s', '阶段');
		str=str.replace('S', '阶段');
		str=str.replace('m', '下跌');
		str=str.replace('b', 'b浪反弹');
		str=str.replace('H', '混沌');
		str=str.replace('P', '炮灰');
		str=str.replace('Q', '趋势');
		str=str.replace('T', '锚点');
		str=str.replace('t', '预置锚点');
		if(str.indexOf('w') > 0 ||  str.indexOf('W')>0) {
			var index = str.indexOf('w') >= 0 ? str.indexOf('w') : str.indexOf('W');
			str = str.substr(0, index) + winCtxts[parseInt(str.substr(index+1, index + 1))] + 
					str.substr(index+2, str.length);
		} else if (str.indexOf('w') == 0 || str.indexOf('W')==0) {
			str = '';
		}
		return str;
	};
	/// 

	/**
     * 格式化excel传递的时间
     * @param numb 需转化的时间 43853
     * @param format 分隔符 "-"
     * @returns {string} 2020-1-22
     */
	var formatExcelDate = function(numb, format = "-") {
		// 如果numb为空则返回空字符串
		if (!numb) {
			return "";
		}
		let time = new Date(new Date("1900-1-1").getTime() + (numb - 1) * 3600*24*1000);
		const year = time.getFullYear() + '';
		const month = time.getMonth() + 1 + '';
		const date = time.getDate();
		if (format && format.length === 1) {
			return year + format + (month < 10 ? '0' + month : month) + format + (date < 10 ? '0' + date : date)
		}
		return year + (month < 10 ? '0' + month : month) + (date < 10 ? '0' + date : date)
	};
	
	var getDateStr = function(d, separator='') {   // ex. 20220704
		var month = d.getMonth() + 1 < 10 ?
					'0' + (d.getMonth() + 1) : 
					d.getMonth() + 1;
		var day = d.getDate() < 10 ? 
					'0' + d.getDate() :
					d.getDate();
		return d.getFullYear()+ separator + month + separator + day;
	};
	
	/**
	 * 计算两个日期之间的天数
	 *  date1  开始日期 yyyy-MM-dd
	 *  date2  结束日期 yyyy-MM-dd
	 *  如果日期相同 返回一天 开始日期大于结束日期，返回0
	 */
	var getDaysBetween = function(date1,date2){
		var  startDate = Date.parse(date1);
		var  endDate = Date.parse(date2);
		if (startDate>endDate){
			return 0;
		}
		if (startDate==endDate){
			return 1;
		}
		var days=(endDate - startDate)/(1*24*60*60*1000);
		return  days;
	};
	
		
	var datesAreOnSameDay = function(first, second) {
		return first.getFullYear() === second.getFullYear() &&
				first.getMonth() === second.getMonth() &&
				first.getDate() === second.getDate();
	};
	
	var getWeek = function (d) {
        curYear = d.getFullYear();
        startDate = new Date(curYear, 0, 1);

		var startWeek = startDate.getDay(); // 1月1号是星期几:0-6
		var offsetWeek = 0; //用来计算不完整的第一周，如果1月1号为星期一则为0，否则为1

		if (startWeek != 1) {
			offsetWeek = 1;
			if (!startWeek) {
				startDate.setDate(1);
			} else {
				startDate.setDate(8 - startWeek); // (7 - startWeek + 1)
			}

		}
		var distanceTimestamp = d - startDate;
		var days = Math.ceil(distanceTimestamp / (24 * 60 * 60 * 1000)) + startWeek;
		var weeks = Math.ceil(days / 7) + offsetWeek;
		return weeks;
	};
	
	var updatetitle = function (dateStr) {
		if(dateStr) {
			Configure.title.reason = '涨停原因类别' + '[' + dateStr + ']';
			Configure.title.dayNumber = '连续涨停天数' + '[' + dateStr + ']';
			Configure.title.boardPercent = '涨停封成比%' + '[' + dateStr + ']';
			Configure.title.handoverPercent = '换手率%' + '[' + dateStr + ']';
			Configure.title.profitProportion = '收盘获利%' + '[' + dateStr + ']';
			Configure.title.boardTime = '最终涨停时间' + '[' + dateStr + ']';
		};
	};
	var replaceTitleDate = function(t, dateStr) {
		return t.replace(/\[[\d]*\]/g, '[' + dateStr + ']');
	}
	
	// 封板力度算法
	var getBoardStrength = function(bType, bPercent) {
		var retObj = {v:0, description:'--'};
		switch (bType) {
			case '一字板':
				if (bPercent > 5) {
					retObj.description = '很强'
				} else {
					retObj.description = '强';
				} 
				break;
			case 'T字板':
				if (bPercent > 20) {
					retObj.description = '很强'
				} else {
					retObj.description = '强'
				} 
				break;
			case '换手板':
				if (bPercent > 50) {
					retObj.description = '强';
				} else if (bPercent > 20){
					retObj.description = '一般';
				} else {
					retObj.description = '弱';
				}
				break;
			default:
				break;
			} 
		switch(retObj.description) {
			case '很强':
				retObj.v = 4;
				break;
			case '强':
				retObj.v = 3;
				break;
			case '一般':
				retObj.v = 2;
				break;
			case '弱':
				retObj.v = 1;
				break;
			default:
				break;
			}
		return retObj;
	};
	
	var getDayBoard = function(number){
		return {d: parseInt( number % 65537 + number / 65537), 
			b: parseInt(number / 65537)};
	};
	
	var getAngle = function(p2, p1) {
		var radian = Math.atan2(p1.y - p2.y, p2.x - p1.x); // 返回来的是弧度
		var angle = 180 / Math.PI * radian; // 根据弧度计算角度
		return angle;
	};
	
	var map = {'f2':'最新价','f3':'涨跌幅','f4':'涨跌额','f5':'成交量(手)',
				'f6':'成交额','f7':'振幅','f8':'换手率','f9':'市盈率(动态)',
				'f10':'量比','f12':'代码','f14':'名称','f15':'最高',
				'f16':'最低','f17':'今开','f18':'昨收','f20':'总值',
				'f21':'流通市值','f23':'市净率', 'f103':'概念', 'f100':'行业', 'f101':'龙头',
				'f24':'60日涨幅', 'f109':'5日涨幅', 'f110':'20日涨幅', 'f160':'10日涨幅',
				'f26':'上市时间'};
	var title = {
		code: '代码',
		name: '    名称',
		price: '现价',
		value: '流通市值',
		totalValue:'总市值',
		turnOver:'总金额',
		reason: '涨停原因类别' + '[' + 
				getDateStr(date) +
				']',
		boardType: '涨停类型',
		boardPercent: '涨停封成比%'  + '[' + 
				getDateStr(date) +
				']',
		dayNumber: '连续涨停天数' + '[' + 
				getDateStr(date) +
				']' ,
		handoverPercent: '换手率%'  + '[' + 
				getDateStr(date) +
				']' ,
		profitProportion: '收盘获利%' + '[' + 
				getDateStr(date) +
				']' ,
		orgProportion: '机构持股比例合计%',
		fboardTime : '首次涨停时间' + '[' + 
				getDateStr(date) +
				']' ,
		boardTime : '最终涨停时间' + '[' + 
				getDateStr(date) +
				']' ,
		boardAndDay:'几天几板',
		score:'题材得分',                //根据reasion 算出来的概念评分
		realValue: '实际流通市值',
		realValueDivergence: '实际流通市值背离率',  //与dragon对比的背离率
		priceDivergence:'价格背离率',   		 // 与dragon对比的背离率
		profitDivergence: '筹码背离率',			 // 与dragon对比的背离率   这个值越大越好，只有小于dargon才会有值
		totalDivergence: '背离率',              // 总背离率
		realHandoverPercent: '实际换手率',
		boardStrength: '封板力度',
		selectDate: '最近涨停日期',
		increaseRate: '平均涨速',
		
		// 实时数据，通过抓取东方财富数据
		f3: '今日涨跌幅',
		f2: '今日价格',
		f8: '今日换手率',
		f6: '今日金额',

		// 涨幅排名独有
		rise_1:'涨幅',
		rise_5: '5日涨幅',
		rise_10: '10日涨幅',
		rise_20:'20日涨幅',
		industry:'所属行业',
		gainian:'所属概念',
		gainianDragon:'概念龙头',
		time: '上市日期',
		index: '排名',
		dragonTag: '龙头标记',
		riseTotal: '涨幅和',
	};
	var title2 = {
		date: '日期',
		erban: '二板数',
		height:'高度',
		lianban:'连板',
		jinji:'连板晋级率',
		qingxuzhishu:'情绪指数',
		lianbanzhishu:'连板指数',
		zhangtingzhishu:'涨停指数',	
		ma5:'5日线',
		beili:'背离率',
		sz:'SZ',
		qadq:'全A等权',
		floored:'曾跌停数',    
		jumped:'曾超跌数',    // 盘中跌超-5%
		leader: '排名股选入个数', // 5日涨幅大于20%或者10日涨幅大于30%或者20日涨幅大于40%
		boardsR: '昨连扳收益率',
		boardR: '昨涨停收益率',
		boardedR: '昨涨停过收益率',
		
		noon:'0.午评和下半场看点',
		context:'1指数与情绪',
		qst1:'2.趋势连扳和特点？',
		qst2:'3主流和次主流？',
		qst3:'4情绪周期及锚定？',
		qst4:'5龙头阶段及买点',
		currentOpt:'6今日操作',
		objOpt:'7目标操作',
		optReason:'8原因',
		nextOpt:'9明日交易计划',
		
		
		echelons:'echelon',   // 记录当天echelon排名
		boardHeight: 'height',   // 记录当天最高高度   BH_Draw_title
		dragon: 'dragon',   // 记录当天的龙头名字
		boardnum: '涨停数',
		boardnum_20cm: '20cm涨停数',
		boardednum: '曾涨停数',
		floornum: '跌停数',
		failednum: '炸板数',
		failedRate: '亏钱效应',   // （炸板+跌停板）/ （炸板+跌停板 + 涨停板）
		totalFund: '短线资金',
		
		
		subBeili:'涨停指标背离率',
		subMa5:'涨停指标5日线',
	};
	
	var titleCycles = {
		cycles: '时间周期',
		hotpoint: '热点',
		date: '日期',
		//dragon:'龙头'
	};
	var titleEchelons = {
		name: '名字',
		hotpoints: '值',
	};
	var titleTactics = {
		context:'窗口',
		param:'参数',
		contextType: '窗口类型',
		tractic:'模式',
		market:'指数和题材',
		emotion:'市场情绪',
		ticket:'个股形态',
		name:'名称',
		condition: '能见度',
		selectTicket:'选股',
		buy:'买点',
		stop:'止损',
		sell: '止盈',
		description: '说明'
	};
	
	var titleGainian = {
		name: '概念名称',
		ticketNum: '股票数量',
	//	ticketsCode: '股票代码',
		score: '得分',
		weight: '权重',
	};
		
	var site_color = 'black';
	var sz_color = 'purple';
	var boardHeight_color = 'black';
	var line_color = 'red';
	var echelon_color = ['#FFA500', '#E89AF5', '#FF6347', '#9D97FF', '#008000', '#FFFF00', '#1E90FF'];
	
	var MIN_LB_NUMBER = 2;
	var MIN_KAINIAN = 2;     // 最少出现的次数
	var HIGH_factor = 1;     //连板数对概念权重的影响因子， 影响股票最后的得分
	
	/**
	/  情绪指标
	/	title2.lianbanzhishu        连扳，针对市场大盘环境差，游资连扳纯投机环境。
	/	title2.zhangtingzhishu      涨停，针对市场短线和趋势博弈环境
	/	title2.qingxuzhishu         同花顺情绪指数，市场趋势行情主导
	/*/
	var ZHISHU_TITLE = title2.qingxuzhishu; 
	///
	var ZHISHU_SUB_TITLE = ZHISHU_TITLE == title2.zhangtingzhishu ?
			title2.lianbanzhishu : title2.zhangtingzhishu;   // 情绪指标 title2.zhangtingzhishu
	var MAX_BEILI = ZHISHU_TITLE == title2.zhangtingzhishu ? 8 : 
						ZHISHU_TITLE == title2.qingxuzhishu ?  1000 : 10;    //最大背离率 ,  影响canvas纵坐标
	var MIN_BEILI = ZHISHU_TITLE == title2.qingxuzhishu ?  850 : 0;
	
	var Days_Show_reserved_lengh = 5;  //预留的天数，为了算显示第一天的MA5
	var Days_Max_lengh = 250;   // 最大期限
	
	var SZ_zero = 3100;    // sz 0轴坐标
	var SZ_MaxOffset = 400;   // 纵轴
	
	var LEAER_NUM_MaxOffset = 200; 
	var Fund_MaxOffset = 800;
	
	var BH_Draw_title = title2.height;  // title2.height or title2.boardHeight
	var BH_zero = BH_Draw_title == title2.height ? 
							 	0 : 0 * 65537;    // boardHeight 0轴坐标
	var BH_MaxOffset = BH_Draw_title == title2.height ? 
							10 : 10 * 65537;   // boardHeight 纵轴

	
	var Min_echelon_score = 0;    //Echelons_show_type == 'score' 时draw 的条件  
	var Max_echelon_score = 40;
	var Min_echelon_fund = 0;    //Echelons_show_type == 'fund' 时draw 的条件  
	var Max_echelon_fund = 150;
	
	// 左右窗口
	var WinXFactor;     //  左边窗口占比 
	var WinFactor = 0.25;    // 上下窗口的比率 
	
	var Echelons_Draw_NUM = 2;
	var Echelons_ticket_NUM = 7;     // 画出来的数量
	var Echelons_handover_factor = 10; // 换手放大便于观察
	
	var Echelons_miss_tickit_period = 3; //连扳检查断板的期限  ’几天几板‘ 是3
	var Echelons_tickit_period = 1;    // 连扳选出股票的期限
	var Echelons_show_min_score = 12;  // 最小显示限制
	var Echelons_show_type = 'score';   //  'fund' or 'score'
	
	// rt
	var WinRTfactor = 0.4;   //canvas RT 窗口占比
	var RT_show_min_rank_ticket_num = 10;  // rt最小显示限制
	var RT_GAI_rank_max_length = 100;			// rt 概念排名记录的最大长度 , 不能太大，存储限制
	var RT_GAI_show_weight_maxOffset = 7;			    // weight min
	var RT_GAI_show_weight_min = 0;		        // weight max
	var RT_data_length = 240;					// 多少个点
	var RT_canvas_record_days_num = 4;			// rt 记录数据的天数
	var RT_canvas_show_days_num = 4;            // 显示的天数
	var RT_canvas_show_echelons_num = 4;            // 显示的最大个数
	var RT_echelons_max_num = 6;            // 生成的个数
	var RT_echelon_contain_config = true;       // 是否加上config的echelon
	
	var Request_interval = 1000;    // 请求数据时间间隔
	var Request_suspend_duration = 0;    // 请求数据时间间隔
	var Request_pagesize = 100;
	
	var Band_tickit_period = 11;    // 趋势选出股票的期限      SED + TFD
	var Band_Max_LENGTH = 22;    // 趋势选出股票画出的长度。    (SED + TFD)  * 2
	var Band_miss_tickit_period = 11;    //趋势检查断板的期限     SED + TFD
	var Band_tickit_filter_period = 1;   //趋势票涨停过滤期限     0 是一个涨停
	var Band_MA_NUM = 5;    //MA5
	var Band_Min_Value = 15000000000;  // 趋势票最小流通市值
	
	var AI_Default_Factor = 50;        // 超短选票默认因子   越大结构权重越大，越小题材权重越大
	var AI_Default_Band_Factor = 2;   // 趋势选票默认因子  越大涨速权重越大，越小题材权重越大
	var Dead_Handover = 55;				// 过滤掉死亡换手
	var Min_handover = 3;				// 过滤掉太低的换手，买不进去
	
	var EmotionAngleDeafultDays = 7;    //情绪指标计算拐点的期限
	
	var LocalStore_history_period = 7;   // locastory 保留数据的期限，需要清理。
	
	var TpiontLine = 'TtQMHP';
	var TpiontShow = 'TtM';                 // 需要显示周期节奏的锚点符号
	var emotionProgress = '[0, 2, 4, 6, 8]';  // 9天标准周期节奏。数值T+n,分别对应启动（轮动）、分歧、确认加速、2次分歧、退潮E。
	
	var selectIndicators = [
							
							//	{name:'全A等权'}, 
								{name:'上证指数'}, 									
							//	{name:'收益率%'},
								{name:'涨停背离'},
								{name:'涨停数量'},
								{name:'赚钱效应'},
							//	{name:'连扳高度'},								
							//	{name:'连扳数量'},
							//	{name:'跌停数量'},
							//	{name:'炸板数量'},
							//	{name:'超跌数量'},
								{name:'亏钱效应'},
							//	{name:'连扳背离'},
								
							];  
	var isAfterNoon = function() {
		return new Date().getHours() > 12;
	};
	var isAfterTrading = function() {
		var d = new Date();	
		return d > new Date(d.getFullYear(),d.getMonth(),d.getDate(),15,0,0);
	};
	var isNight = function() {
		var d = new Date();	
		return d > new Date(d.getFullYear(),d.getMonth(),d.getDate(),20,0,0);
	};
	var isWeekend = function(today = new Date()) {
		return today.getDay() == 0 || today.getDay() == 6;
	};
	var isBidding = function(d = new Date()) {
		var startD = new Date(d.getFullYear(),d.getMonth(),d.getDate(),9,15,0);
		var endD = new Date(d.getFullYear(),d.getMonth(),d.getDate(),9,30,0);
		if(d >= startD && d < endD) {
			return true;
		}
		return false;
	};
	var isPreBidding = function(d = new Date()) {
		var startD = new Date(d.getFullYear(),d.getMonth(),d.getDate(),8,45,0);
		var endD = new Date(d.getFullYear(),d.getMonth(),d.getDate(),9,15,0);
		if(d >= startD && d < endD) {
			return true;
		}
		return false;
	};
	var isHalfBidding = function(d = new Date()) {
		var startD = new Date(d.getFullYear(),d.getMonth(),d.getDate(),9,15,0);
		var endD = new Date(d.getFullYear(),d.getMonth(),d.getDate(),9,20,0);
		if(d >= startD && d < endD) {
			return true;
		}
		return false;
	};
	var isKeTicket = function(code) {
		return (code.substr(0, 2) == 'SH' && code.substr(2, 2) == '68') || 
					code.substr(0, 2) == '68';
	};
	var isChungTicket = function(code) {
		return (code.substr(0, 2) == 'SZ' && code.substr(2, 2) == '30') || 
					code.substr(0, 2) == '30' ;
	};
	var isKechuangTicket = function(code) {
		return isChungTicket(code) || isKeTicket(code);
	};
	var isSHTicket = function(code) {
		return code.substr(2, 2) == '60' ||
				code.substr(0, 2) == '60';
	};
	var isSZTicket = function(code) {
		return code.substr(2, 2) == '00' ||
				code.substr(0, 2) == '00';
	};
	var isBJTicket = function(code) {
		return code.substr(0,1) == '8' ||
				code.substr(0,1) ==  '9' ||
				code.substr(0,1) == '4';
	};
	var isFloorOrFailed = function(ticket, dateStr) {
		return ticket[replaceTitleDate(title.dayNumber, dateStr)] > 0;
	};
	var isNew = function(dateStr, d = 60) {   //上市时间小于60的为新股   dateStr = 20230303;
		dateStr += '';
		if(!dateStr || dateStr.length != 8) return false;
		var  startDate = Date.parse(dateStr.slice(0,4) + '-' + dateStr.slice(4,6) + '-' + dateStr.slice(6,8));
		return (Configure.date - startDate)/(1*24*60*60*1000) < d;
	};
	var isSuspend = function(price) {   //停牌
		return !price || price == '--';
	};
	var isBoardDone = function(rtData) {   // 判断实时数据是否涨停
		if(!rtData || !rtData['f18'] || ! rtData['f2']) return false;
		var per = isBJTicket(rtData['f12']) ? 1.30 :
					isKechuangTicket(rtData['f12']) ? 1.20 : 1.10;
		return  Math.round(rtData['f18'] * per) == rtData['f2'];
	};
	var calScoreFromRtData = function(rtData) {
		if(isBoardDone(rtData)) {
			return HIGH_factor * 7;
		} else if(rtData['f3'] > 600) {
			return HIGH_factor * 3;
		} else if(rtData['f3']  > 0) {
			return HIGH_factor * 1;
		} else {
			return 0;    // <0
		}
	};
	
	var showInTableTitile, bandShowInTableTitile, rankShowInTableTitile;
	var setMode = function(type) {
		mode = type;
		if(mode == modeType.FP) {    // 复盘配置
			this.showInTableTitile = ['name',  'realValue','score','totalDivergence',
							'realHandoverPercent','turnOver', 'boardTime','boardStrength','reason', 'boardAndDay'];
			this.bandShowInTableTitile = ['name', 'realValue','score','price','increaseRate','totalDivergence',
							'selectDate','reason'];
			this.rankShowInTableTitile = ['index', 'name', 'price', 'rise_1', 'rise_5','rise_10',
									'rise_20', 'value', 'gainianDragon', 'time'];
									
			this.WinXFactor = 0.6;
			this.Echelons_Draw_NUM = 2;   
		} else if(mode == modeType.DP)   {                      // 盯盘配置
			this.showInTableTitile = ['name', 'f2',  'f3','f8','f6','realValue','score','totalDivergence', 
							'boardStrength','reason', 'boardAndDay'];
			this.bandShowInTableTitile = ['name', 'f2', 'f3','f8','f6','realValue','score','totalDivergence',
						'selectDate','reason'];
			this.rankShowInTableTitile = ['index','name', 'f2', 'f3','f8','f6', 'rise_5','rise_10',
											'rise_20', 'value','gainianDragon'];
			this.WinXFactor = 0.3;
			this.Echelons_Draw_NUM = 1;
		} else {
			this.showInTableTitile = ['name','realValue', 'score','boardTime','reason', 'boardAndDay'];
			this.bandShowInTableTitile = ['name', 'realValue','price','increaseRate',
							'selectDate','reason'];
			this.rankShowInTableTitile = ['index', 'name', 'rise_1', 'rise_5',
									'rise_20', 'value'];
									
			this.WinXFactor = 1;
			this.Echelons_Draw_NUM = 0;   
		}
	};
	var getMode = function() {
		return mode;
	}
	
	return {
		date: date,
		debug: debug,
		Debug:Debug,
		version:version,
		setMode:setMode,
		getMode:getMode,
		modeType:modeType,
		winCtxts: winCtxts,
		getColorFromWinC:getColorFromWinC,
		cangMap: cangMap,
		bandConditions:bandConditions,
		icePoint:icePoint,
		showInTableTitile:showInTableTitile,
		bandShowInTableTitile:bandShowInTableTitile,
		rankShowInTableTitile:rankShowInTableTitile,
		MIN_LB_NUMBER:MIN_LB_NUMBER,	
		MIN_KAINIAN:MIN_KAINIAN,
		HIGH_factor:HIGH_factor,
		title:title,
		title2:title2,
		titleCycles:titleCycles,
		titleEchelons:titleEchelons,
		titleTactics:titleTactics,
		titleGainian:titleGainian,
		Days_Max_lengh:Days_Max_lengh,
		Days_Show_reserved_lengh:Days_Show_reserved_lengh,
		echelons:echelons,
		gaiBlackList_critical:gaiBlackList_critical,
		gaiBlackList_verbose:gaiBlackList_verbose,
		selectIndicators:selectIndicators,
		LocalStore_history_period:LocalStore_history_period,
		MAX_BEILI:MAX_BEILI,
		MIN_BEILI:MIN_BEILI,
		ZHISHU_TITLE:ZHISHU_TITLE,
		ZHISHU_SUB_TITLE:ZHISHU_SUB_TITLE,
		SZ_zero:SZ_zero,
		SZ_MaxOffset:SZ_MaxOffset,
		LEAER_NUM_MaxOffset:LEAER_NUM_MaxOffset,
		Fund_MaxOffset:Fund_MaxOffset,
		BH_zero:BH_zero,
		BH_MaxOffset:BH_MaxOffset,
		BH_Draw_title:BH_Draw_title,
		AI_Default_Factor:AI_Default_Factor,
		AI_Default_Band_Factor:AI_Default_Band_Factor,
		Dead_Handover:Dead_Handover,
		Min_handover:Min_handover,
		WinXFactor:WinXFactor,
		WinFactor:WinFactor,
		WinRTfactor:WinRTfactor,
		Min_echelon_score:Min_echelon_score,
		Max_echelon_score:Max_echelon_score,
		Min_echelon_fund:Min_echelon_fund,
		Max_echelon_fund:Max_echelon_fund,
		Echelons_Draw_NUM:Echelons_Draw_NUM,
		Echelons_tickit_period:Echelons_tickit_period,
		Echelons_show_min_score:Echelons_show_min_score,
		Echelons_show_type:Echelons_show_type,
		RT_show_min_rank_ticket_num:RT_show_min_rank_ticket_num,
		RT_GAI_rank_max_length:RT_GAI_rank_max_length,
		RT_GAI_show_weight_maxOffset:RT_GAI_show_weight_maxOffset,
		RT_GAI_show_weight_min:RT_GAI_show_weight_min,
		RT_data_length:RT_data_length,
		RT_canvas_show_days_num:RT_canvas_show_days_num,
		RT_echelons_max_num:RT_echelons_max_num,
		RT_canvas_record_days_num:RT_canvas_record_days_num,
		RT_canvas_show_echelons_num:RT_canvas_show_echelons_num,
		RT_echelon_contain_config:RT_echelon_contain_config,
		Request_interval:Request_interval,
		Request_suspend_duration:Request_suspend_duration,
		Request_pagesize:Request_pagesize,
		Band_tickit_period:Band_tickit_period,
		Echelons_miss_tickit_period:Echelons_miss_tickit_period,
		Band_miss_tickit_period:Band_miss_tickit_period,
		Band_tickit_filter_period:Band_tickit_filter_period,
		Band_Max_LENGTH:Band_Max_LENGTH,
		Band_MA_NUM:Band_MA_NUM,
		Band_Min_Value:Band_Min_Value,
		Echelons_ticket_NUM:Echelons_ticket_NUM,
		Echelons_handover_factor:Echelons_handover_factor,
		EmotionAngleDeafultDays:EmotionAngleDeafultDays,
		TpiontLine:TpiontLine,
		TpiontShow:TpiontShow,
		emotionProgress:emotionProgress,
		site_color:site_color,
		boardHeight_color:boardHeight_color,
		sz_color:sz_color,
		line_color:line_color,
		echelon_color:echelon_color,
		getDateStr:getDateStr,
		getDaysBetween:getDaysBetween,
		datesAreOnSameDay:datesAreOnSameDay,
		getWeek:getWeek,
		getAngle:getAngle,
		getBoardStrength:getBoardStrength,
		formatExcelDate:formatExcelDate,
		updatetitle:updatetitle,
		replaceTitleDate:replaceTitleDate,
		getDayBoard:getDayBoard,
		isWeekend:isWeekend,
		isAfterNoon:isAfterNoon,
		isAfterTrading:isAfterTrading,
		isNight:isNight,
		isPreBidding:isPreBidding,
		isBidding:isBidding,
		isHalfBidding:isHalfBidding,
		isKeTicket:isKeTicket,
		isChungTicket:isChungTicket,
		isKechuangTicket:isKechuangTicket,
		isSHTicket:isSHTicket,
		isSZTicket:isSZTicket,
		isBJTicket:isBJTicket,
		isFloorOrFailed:isFloorOrFailed,
		isNew:isNew,
		isSuspend:isSuspend,
		isBoardDone:isBoardDone,
		calScoreFromRtData:calScoreFromRtData,
		getContextDescription:getContextDescription
	}	
})();