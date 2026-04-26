var parser = (function(){
	var tickets = [];   // 所有股票
	var gaiNian = new Map();   // 所有概念  元素【概念，{times，weight}】:['猪肉'， {13, 0.24}]
	
	var dateToload;
		
	var loadSheet = function(dateStr = Configure.getDateStr(Configure.date)) {
		//避免重复加载
		if(dateStr == dateToload || !workbook.sheetExist(dateStr)) {
			return;
		};
		clear();
		dateToload = dateStr;
		tickets = workbook.getSheet(dateStr);
		// 主动更新表头
		Configure.updatetitle(dateStr);
		
		///////
		var totalscored = 0;      // 出现次数*该股票的连扳数*Configure.HIGH_factor，做后面计算权重的分母
		tickets.forEach((ticket) => {
			var reasons = ticket[Configure.title.reason].split('+');
			reasons.forEach((r) => {
				var reasonWeight = ticket[Configure.title.dayNumber] * Configure.HIGH_factor;
				if (gaiNian.has(r)) {
					gaiNian.set(r, {times:gaiNian.get(r).times + 1, weight: parseInt(gaiNian.get(r).weight + reasonWeight)});
				} else {
					// 初始化这个概念, 此时的weight保存次数*股票的连扳数之和
					gaiNian.set(r, {times:1, weight:parseInt(reasonWeight)});           
				}
				totalscored += reasonWeight;
			});
		});
		totalscored = parseInt(totalscored);

		tickets.forEach((ticket) => {
			//根据概念的权重计算每只股票的得分
			var reasons = ticket[Configure.title.reason].split('+');
			ticket[Configure.title.score] = 0;   //初始化
			reasons.forEach((r) => {
				ticket[Configure.title.score] += gaiNian.get(r).weight;
			});
			ticket[Configure.title.score] = parseInt(ticket[Configure.title.score]/totalscored * 1000);
			
			var dragon = dragons.getDragonStandard(
						Configure.getDayBoard(ticket[Configure.title.boardAndDay]).b, ticket[Configure.title.code]);
			// realValue 实际流通市值
			ticket[Configure.title.realValue] = parseInt(ticket[Configure.title.value] * 
											(100 - ticket[Configure.title.orgProportion])/100);
			//实际流通市值背离率
			ticket[Configure.title.realValueDivergence] = 
					parseFloat((ticket[Configure.title.realValue] - dragon.realCirculateValue)/
					dragon.realCirculateValue).toFixed(2);
			//价格背离率
			ticket[Configure.title.priceDivergence] = parseFloat((ticket[Configure.title.price] - dragon.price)/
					dragon.price).toFixed(2);
			// 实际换手率
			ticket[Configure.title.realHandoverPercent] = parseFloat(parseFloat(ticket[Configure.title.handoverPercent]) * ticket[Configure.title.value] /
															ticket[Configure.title.realValue]).toFixed(2);
			// 总金额
			if(!ticket[Configure.title.turnOver]) {
				ticket[Configure.title.turnOver] = (ticket[Configure.title.realHandoverPercent] / 100)
														* ticket[Configure.title.realValue] ;
			}
			//筹码背离率  X10
			ticket[Configure.title.profitDivergence] = ticket[Configure.title.profitProportion] - dragon.profitProportion > 0 ? 0 : 
				parseFloat((ticket[Configure.title.profitProportion] - dragon.profitProportion)/dragon.profitProportion * 10).toFixed(2);
			// 总背离率
			ticket[Configure.title.totalDivergence] = parseFloat(Math.abs(ticket[Configure.title.realValueDivergence]) + 
														Math.abs(ticket[Configure.title.priceDivergence]) + 
														Math.abs(ticket[Configure.title.profitDivergence])).toFixed(2);
			// 封板力度
			ticket[Configure.title.boardStrength] = Configure.getBoardStrength(ticket[Configure.title.boardType], 
									ticket[Configure.title.boardPercent]);

		})
	};
	
	var getHotpoints = function(dateStr) {
		loadSheet(dateStr);
		var hotPointsArr = Array.from(gaiNian);
		hotPointsArr.sort((a, b)=> {
			return b[1].weight - a[1].weight;
		});
		return hotPointsArr;
	};
	
	var getHotpointstxt = function(dateStr) {
		var txt = '热点概念排名：<br>';
		var index = 0;
		var arr = getHotpoints(dateStr);

		arr.forEach((a) => {   // a = ['猪肉'， 13]
			if(a[1].times >= Configure.MIN_KAINIAN) {
				txt += '【' + (++index) + '】' + 
				a[0] + '  ' + a[1].times + '    score:' + a[1].weight + '  <br>\t\r\n';
			}
		});
		return txt;
	};
	
	var getTicket = function(datestr, name) {
		loadSheet(datestr);
		var ret;
		tickets.forEach((t) => {
			if(t[Configure.title.name] == name){
				ret = t;
			}
		});
		return ret;
	};
	// 获取过去num天内连续涨停n(默认是1)天以上的所有票
	var getAllBoardedTicketsFromDays = function (num, n = 1){
		var retTickets = [];
		var dateArr = workbook.getDateArr((a,b)=>{
			return b - a;
		});
		
		for (var i = 0; i < num; i ++ ) {
			var param = {
				hotpointArr: [],
				type:0,
				sort:1
			}
			var tArr = parser.getTickets(dateArr[i],param);
			tArr = tArr.filter((t1)=>{
				var isSelect = true;
				if (t1[Configure.replaceTitleDate(Configure.title.dayNumber, dateArr[i])] < n) {
					isSelect = false;
				}
				retTickets.forEach((t2)=> {
					if(t2[Configure.title.code] == t1[Configure.title.code]){
						isSelect = false;
					}
				})
				
				if(isSelect) {
					t1.selectDate = dateArr[i];
				}
				return isSelect;
			});
			
			retTickets = retTickets.concat(tArr);
		};
		return retTickets;
	}
	
	var getBandTickets = function(obj) {
		var retArr = workbook.getBandTickets();
		// sort
		retArr.sort((a, b) => {
			if (obj && obj.sort == 2) {
				var bData = rtDataManager.getRTTicketFromCode(b[Configure.title.code]);
				var aData = rtDataManager.getRTTicketFromCode(a[Configure.title.code]);
				if(bData && bData['f3'] && aData && aData['f3']) {
					return bData['f3'] - aData['f3'] ;
				} else {
					return b.increaseRate - a.increaseRate;
				}
				
			} else if (obj.sort == 0){
				return b[Configure.title.score] - a[Configure.title.score];
			} else {
				return b[Configure.title.realValue] - a[Configure.title.realValue];
			}
			
		});
		
		// gainian
		if (obj.hotpointArr && obj.hotpointArr.length != 0) {
			retArr = retArr.filter((t)=>{
				var isSelect = false;
				obj.hotpointArr.forEach((g)=> {
					if(t[Configure.replaceTitleDate(Configure.title.reason,t.selectDate)].indexOf(g) != -1){
						isSelect = true;
					}
				})
				return obj.other ? !isSelect : isSelect;
			});	
		}
		return retArr;
	};
	
	//param : {hotpointArr: ['光伏','储能'], type: 1, sort: 0, other: false}
	/*hotpointArr  热点概念排序的索引 
	/*type  0 游资 1 庄游  2排名  -1 all
	/*sort  0 得分 ， 1 高度,  2 涨速
	/*other  true 热点外的其他票
	//*/
	var getTickets = function(dateStr, obj) {
		if(obj.type == 1) {
			return getBandTickets(obj);
		};
		
		loadSheet(dateStr);
		// sort
		tickets.sort((a, b) => {
			if (obj && obj.sort == 1) {
				return b[Configure.replaceTitleDate(Configure.title.dayNumber, dateStr)]  - 
						a[Configure.replaceTitleDate(Configure.title.dayNumber, dateStr)] ;
			} else if (obj && obj.sort == 2){
				if(obj.type == 2) {
					var bData = rtDataManager.getRTTicketFromCode(b[Configure.title.code]);
					var aData = rtDataManager.getRTTicketFromCode(a[Configure.title.code]);
					if(bData && bData['f3'] && aData && aData['f3']) {
						return bData['f3'] - aData['f3'] ;
					} else {
						return 0;
					}
				} else {
					return new Date('2023-09-12 '+ a[Configure.title.boardTime]) - 
						new Date('2023-09-12 '+ b[Configure.title.boardTime]);
				}
			} else {
				return b[Configure.title.score] - a[Configure.title.score];
			}
		});
			
		// type
		var retArr = tickets;
		if (obj.type == 0){
			// type = 0, 过滤掉跌停和炸板
			retArr= tickets.filter((t)=>{
				return Configure.isFloorOrFailed(t, dateStr);
			});	
		} else {
			// do notiing
		};
		
		//  sector
		if(obj.sector) {
			if ((obj.sector & 1) === 0 ) {   // 主板
				retArr = retArr.filter((t)=>{
					return !Configure.isSHTicket(t[Configure.title.code]) &&
								!Configure.isSZTicket(t[Configure.title.code]);
				});
			} 
			if ((obj.sector & 2) === 0) {    // 科/创
				retArr = retArr.filter((t)=>{
					return !Configure.isKechuangTicket(t[Configure.title.code]);
				});
			} 
			if ((obj.sector & 4) === 0) {     // 北交所
				retArr = retArr.filter((t)=>{
					return !Configure.isBJTicket(t[Configure.title.code]);
				});
			}
		}
		
		// gainian
		if (obj.hotpointArr && obj.hotpointArr.length != 0) {
			retArr = retArr.filter((t)=>{
				var isSelect = false;
				obj.hotpointArr.forEach((g)=> {
					if(t[Configure.title.reason].indexOf(g) != -1){
						isSelect = true;
					}
				})
				return obj.other ? !isSelect : isSelect;
			});	
		}
		return retArr;
	};
	
	var loadConfFromExl = function() {
		var retArr = workbook.getEchelonsFromExcel();
		retArr.forEach((estr)=>{
			if(estr[Configure.titleEchelons.name].includes('$')) {  // 配置
				Configure[estr[Configure.titleEchelons.name].substring(1)] 
							= estr[Configure.titleEchelons.hotpoints];
			} else if(estr[Configure.titleEchelons.name].includes('#')){  // 题材库
				var echelon = {name:estr[Configure.titleEchelons.name],
							hotPoints:
							estr[Configure.titleEchelons.hotpoints].replace(/\s/g, '').split(/[,，.;；。、]/)};
				var findIndx = Configure.echelons.findIndex((e)=>{
					return echelon.name.includes(e.name);
				});
				if(findIndx > -1) { // 找到就替换
					Configure.echelons.splice(findIndx, 1, echelon); // 替换
				} else {
					Configure.echelons.push(echelon);
				}
			}
		});
	};
	
	// 根据hotpoint算出echelons
	var getEchelons = function(dateStr) {
		loadSheet(dateStr);
		if (!gaiNian) return [];
		var echelons = [];
		// 计算梯队的短线资金量
		function calEchelonFund(hotPoints) {
			var fundtotal = 0;
			var param = {
				hotpointArr: hotPoints,
				type:0,
				sort:1
			}
			var tickets = getTickets(dateStr, param);
			tickets.forEach((t)=>{
				fundtotal += t[Configure.title.realHandoverPercent] * t[Configure.title.realValue] / 100;
			})
			fundtotal = (fundtotal / 100000000).toFixed(2);
			return fundtotal;
		};
		//////
		// configure 的echelon
		var alreadyInConfig = [];
		Configure.echelons.forEach((echelon)=>{
			var e = {};
			e.score = 0;
			e.name = echelon.name;
			e.hotPoints = echelon.hotPoints.slice();
			echelon.hotPoints.forEach((hot)=>{
				for (var [name, value] of gaiNian) {
					if (name.includes(hot)) {
						e.score += parseInt(value.weight);
					}
				}
			});
			e.fund = calEchelonFund(e.hotPoints);
			alreadyInConfig = alreadyInConfig.concat(e.hotPoints);
			echelons.push(e);
		});
			
		//如果某个概念符合要求但是没在配置里面，分离出来单独做echelon.
		for (var [name, value] of gaiNian) {
			if(!alreadyInConfig.includes(name) && 
				value.weight > Configure.Echelons_show_min_score ){ 
				var newEche = {};
				newEche.name = '*' + name;
				newEche.score = parseInt(value.weight);
				newEche.hotPoints = [name];
				newEche.fund = calEchelonFund(newEche.hotPoints);
				echelons.push(newEche);
			}

		}
		echelons.sort((a, b) => {
			return b.score - a.score;
		});  
		
		var retEchelons = echelons.filter((e)=>{
			return e.score > Configure.Echelons_show_min_score;
		});
		
		return retEchelons.length == 0 ? echelons.splice(0,3) : retEchelons;
	};
	
	// 根据hotpoint算出echelons
	var getCombinedEchelon = function(dateStr, echelonNames) {
		var echelons = getEchelons(dateStr);
		var combinedEchelon = {
			name:'',
			hotPoints: [],
			score: 0
		};
		if (echelonNames) {
			combinedEchelon.name = echelonNames.toString();
			echelonNames.forEach((name)=>{
				echelons.forEach((echelon)=>{
					if (echelon.name == name) {
						combinedEchelon.hotPoints = combinedEchelon.hotPoints.concat(echelon.hotPoints);
						combinedEchelon.score += parseInt(echelon.score);
					}
				});
			});
		} else {
			combinedEchelon.name = '全部';
			echelons.forEach((echelon)=>{
				combinedEchelon.hotPoints = combinedEchelon.hotPoints.concat(echelon.hotPoints);
				combinedEchelon.score += parseInt(echelon.score);
			});
		}
		return combinedEchelon;
	};
	
	var getBandEchelonFromZTEchellon = function(dateStr, ztEchelon) {
		var bEchelon = {};
		bEchelon.score = 0;
		bEchelon.name = ztEchelon.name;
		bEchelon.hotPoints = ztEchelon.hotPoints.slice();
		bEchelon.fund = 0;
	};
	
	var getBoardHeight = function(dateStr, titleName) {
		loadSheet(dateStr);
		tickets.sort((a, b) => {
			return b[Configure.title.dayNumber] - a[Configure.title.dayNumber];
		})
		return {name: tickets[0][Configure.title.name], value:tickets[0][titleName]};
	};
	
	var clear = function() {
		tickets = [];
		gaiNian = new Map();
	};
	
	return {
		getHotpoints: getHotpoints,
		getHotpointstxt:getHotpointstxt,
		getTickets: getTickets,
		getTicket:getTicket,
		getBandTickets:getBandTickets,
		loadConfFromExl:loadConfFromExl,
		getEchelons:getEchelons,
		getCombinedEchelon:getCombinedEchelon,
		getBoardHeight:getBoardHeight,
		getAllBoardedTicketsFromDays:getAllBoardedTicketsFromDays,
	}
})();