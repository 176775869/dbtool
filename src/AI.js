
var AI = (function(){
	var recommendText;
	var storeNamePrefix = 'ai';
	var objStorage = LocalStore.getAll();
	var dataStorage = {};
	
	var RectifyDay_num = Configure.Days_Max_lengh;
	var Rectify_factor = 7;
	
	var boardedTickets_10day = [];   //记录10天内所有涨停过的票
	var boardedTickets_3day3 = [];   //记录5天内所有连续涨停3天的票
	
	var getAndUpdateLoacalstorage = function() {
		var dateArr = workbook.getDateArr((a,b)=>{
				return b - a;
		});
		var datestr = dateArr[0];
		var preDatestr = dateArr[1];
		if (objStorage[storeNamePrefix + preDatestr]) {
			var sucessNum = 0;
			objStorage[storeNamePrefix + preDatestr].tickits.forEach((name)=>{
				var ticket = parser.getTicket(datestr, name);
				if(ticket) {
					sucessNum ++;
				}
			})
			objStorage[storeNamePrefix + preDatestr].sucessRate = parseFloat(sucessNum / objStorage[storeNamePrefix + preDatestr].tickits.length).toFixed(2);
			//重新set更新后的结果
			LocalStore.set(storeNamePrefix + preDatestr, objStorage[storeNamePrefix + preDatestr]);
		}
		
		RectifyDay_num = dateArr.length > RectifyDay_num ? RectifyDay_num : dateArr.length;
		var num = 0;
		var total = 0;
		for (var i = 0; i < RectifyDay_num; i ++) {
			var obj = objStorage[storeNamePrefix + dateArr[i]];
			if(obj && obj.sucessRate >= 0.5) {
				total += obj.scoreFator;
				num ++;
			}
		}
		// 计算 scoreFator
		var aveage = total/num;
		if (objStorage[storeNamePrefix + preDatestr] && objStorage[storeNamePrefix + preDatestr].sucessRate) {
			dataStorage.scoreFator = aveage && objStorage[storeNamePrefix + preDatestr].scoreFator - aveage > 0 ? 
										aveage  - Rectify_factor : aveage + Rectify_factor;
		} else {
			dataStorage.scoreFator += Rectify_factor;
		}
		// 计算 bandScoreFator
		var param = {
			hotpointArr: [],
			type:0,
			sort:1
		}
		var tickets =  parser.getTickets(datestr, param);
		for(var i = 0; i < Configure.Band_miss_tickit_period, objStorage[storeNamePrefix + dateArr[i]]; i ++) {   
			// 检查过去Band_miss_tickit_period天内是否有票出现在今天的首板
			objStorage[storeNamePrefix + dateArr[i]].band_ticktes.forEach((bandTicket)=>{
				tickets.forEach((t)=>{
					if(bandTicket.name == t[Configure.title.name]) {
						var priceIncrease = (t[Configure.title.price] - bandTicket.price)/bandTicket.price;
						var startFator = objStorage[storeNamePrefix + dateArr[i]].bandScoreFator;
						var preFaotor = objStorage[storeNamePrefix + preDatestr] ? 
											objStorage[storeNamePrefix + preDatestr].bandScoreFator :
																Configure.AI_Default_Band_Factor;
						dataStorage.bandScoreFator = preFaotor - startFator > 0 ? 
										preFaotor + parseInt(startFator * priceIncrease) : 
										preFaotor - parseInt(startFator * priceIncrease);
								
					}
				})
			})
		}
	};
	
	var saveLoacalstorage = function(dataStorage) {
		Configure.Debug(dataStorage);
		var datestr = workbook.getDisplayLastDate();
		if (LocalStore.get(storeNamePrefix + datestr)) {
			LocalStore.remove(storeNamePrefix + datestr);
		}
		LocalStore.set(storeNamePrefix + datestr, dataStorage);
	};
	
	var getEmotionSuccessRate = function(emotion) {
		var dateArr = workbook.getDateArr((a,b)=>{
			return b - a;
		});
		var total = 0;
		var num = 0;
		var totalValue = 0;
		for (var i = 1; i <= RectifyDay_num; i ++) {
			if (objStorage[storeNamePrefix + dateArr[i]] ) {
				total ++;
				if(objStorage[storeNamePrefix + dateArr[i]].emotion == emotion) {
					num ++;
					totalValue += parseFloat(objStorage[storeNamePrefix + dateArr[i]].sucessRate);
				}
			}
		}
		
		return num == 0 || 'NaN' ? '' : '前' +  total + '天出现' + 
			num + '次,成功率' + parseInt(totalValue * 100/num) + '%。';
	};
	
	var getLevel = function(point) {
		return Math.floor((point.value- Configure.MIN_BEILI) * 4/(Configure.MAX_BEILI - Configure.MIN_BEILI));
	}
	
	var checkZBHigherDays = function(title, days, minDays, minThreshold) {
		var zbPoints = canvas.getLastZBPoints(days, title);   
		var n = 0;
		for(var i = 0 ; i < days ; i ++) {
			if(zbPoints[i].value > minThreshold) {
				n ++;
			}
		}
		if(n >= minDays) {
			return true;
		}
		return false;
	};
	var checkZBUnderDays = function(title, days, minDays, maxThreshold) {
		var zbPoints = canvas.getLastZBPoints(days, title);   
		var n = 0;
		for(var i = 0 ; i < days ; i ++) {
			if(zbPoints[i].value < maxThreshold) {
				n ++;
			}
		}
		if(n >= minDays) {
			return true;
		}
		return false;
	};
	
	var checkCondition = function(condition) {
		var ret = true;
		var emotionPoints = canvas.getLastEmotionPoints(Configure.EmotionAngleDeafultDays + 1);  
		var emotionSumAngle = canvas.sumAngleFromPoints(emotionPoints);
		var emotionAngle = emotionPoints.length >= 2 ?
						Configure.getAngle(emotionPoints[0].point, emotionPoints[1].point) : 0;
		var emotionLevel = emotionPoints.length >= 1 ? getLevel(emotionPoints[0]) : 0;
		
		var szAngle = canvas.sumAngleFromPoints(canvas.getLastZBPoints(Configure.Band_MA_NUM/*, Configure.title2.qadq*/));
		var eAngle = canvas.sumAngleFromPoints(canvas.getLastZBPoints(Configure.Band_MA_NUM, Configure.title2.qingxuzhishu));
		for (var i in condition) {
			var value = currentValue = -1;
			var title;
			switch(i) {
				case 'a':
					value = emotionSumAngle;
					currentValue = emotionAngle;
					break;
				case 'b':
					value = emotionLevel;
					break;
				case 'c':
					title = Configure.title2.failedRate;
					break;
				case 'd':
					value = szAngle;
					break;
				case 'e':
					value = eAngle;
					break;
				case 'f':
					title = Configure.title2.boardnum;
					break;
				case 'g':
					title = Configure.title2.floornum;
					break;
				case 'h':
					title = Configure.title2.failednum;
					break;
				case 'i':
					title = Configure.title2.subBeili;
					break;
				case 'j':
					title = Configure.BH_Draw_title;
					break;
				case 'k':
					title = Configure.title2.lianban;
					break;
				case 'l':
					title = Configure.title2.jinji;
					break;
				case 'm':
					title = Configure.title2.totalFund;
					break;
				default:
					break;
			}
			// min  max  currentMin   currentMax
			if((condition[i].min!=undefined && value !=-1 && value < condition[i].min) ||
				(condition[i].max!=undefined && value != -1 && value > condition[i].max) ||
				(condition[i].currentMin!=undefined && currentValue !=-1 && currentValue < condition[i].currentMin) ||
				(condition[i].currentMax!=undefined && currentValue !=-1 && currentValue > condition[i].currentMax )) {
			//		Configure.Debug('checkCondition failed for ' + (i =='a' ? '情绪角度' : '情绪level') + 
			//			' value:' + value + '  currentValue:' + currentValue);
					ret = false;
			}
			
			// days, minDays, min max.
			if(ret && title && (condition[i].min!=undefined || condition[i].max!=undefined)) {
				var days = condition[i].days!=undefined ? condition[i].days : 1;
				var minDays =  condition[i].minDays!=undefined ? condition[i].minDays : 1;
				ret = condition[i].min!=undefined ? checkZBHigherDays(title, days, minDays, condition[i].min) : ret;
				ret = condition[i].max!=undefined ? checkZBUnderDays(title, days, minDays, condition[i].max) : ret; 
				if(!ret) {
			//		Configure.Debug('checkCondition failed for ' + title);
				}
			}			
		}
		return ret;
	};
	var getEmotions = function() {
		try {
			Configure.cangMap.forEach(function(item, key){
				item.conditions.forEach((condition, index)=>{
				//	Configure.Debug('=> start check ' + item.stage + ' index ' + index);
					if(checkCondition(condition)) {
						dataStorage.emotion = key;
				//		Configure.Debug('Check done, ' + item.stage + ' index ' + index + '  selected!');
						throw new Error('LoopInterrupt');
					};
				});
				
			});
			if (dataStorage.emotion == '') {
				Configure.Debug('Failed match emotions !!!')
			}
		} catch(e) {
			if(e.message != 'LoopInterrupt') throw e;
		}

		// 从配置获取周期M 阶段S 环境C 窗口W 
		var context = workbook.getEmotionalCycles(Configure.getDateStr(Configure.date, '-'));
		if(context.cycles && Configure.getColorFromWinC(context.cycles).des) {   // 如果有配置w 就使用配置的
			dataStorage.emotion = Configure.getColorFromWinC(context.cycles).des;
		}
		var contextstr = context.cycles ? Configure.getContextDescription(context.cycles) : '';
		var contextTypeAndParam = context.cycles ? workbook.getContextTypeAndParam(context.cycles) : null;
		if (contextTypeAndParam) {   // 根据窗口重新设置一下模式，如果没有使用默认的模式
			var obj = Configure.cangMap.get(dataStorage.emotion);
			obj.context = [contextTypeAndParam.type];
			Configure.cangMap.set(dataStorage.emotion, obj);
			contextstr += '[' + contextTypeAndParam.type + '],';
			contextstr += contextTypeAndParam.param ? contextTypeAndParam.param + '.' : '';
		}
		contextstr += context.hotpoint ? '热点' + context.hotpoint + ',' : '';
		var emotionstr = dataStorage.emotion == '空白' ? '' : '情绪' + dataStorage.emotion + '。';
		return  contextstr  + emotionstr + getEmotionSuccessRate(dataStorage.emotion);
	};
	
	// 根据题材、背离率、连扳和 封板强度 算最后的得分    
	var getFinalScroe = function(t, dateStr) {
		var emotionPoints = canvas.getLastEmotionPoints(1); 
		return parseInt(parseInt(t[Configure.title.score]) - 
				t[Configure.title.totalDivergence] * dataStorage.scoreFator + 
				// 情绪高位，板块越向低位找
				(((Configure.MAX_BEILI - Configure.MIN_BEILI) / 2 - emotionPoints[0].value) * 3)* t[Configure.replaceTitleDate(Configure.title.dayNumber, dateStr)] +
				t[Configure.title.boardStrength].v * 10) +    // 封板强度 X10
				(Configure.isSZTicket(t[Configure.title.code]) ? 100 : 0);   // 深市票
	};
	
	var getSZEnv = function() {
		// 算斜率
		var szPoinsts = canvas.getLastZBPoints(Configure.Band_MA_NUM/*, Configure.title2.qadq*/);    
		var sumAngle = canvas.sumAngleFromPoints(szPoinsts);
		var sumValue = canvas.sumValueFromPoints(szPoinsts);
		dataStorage.sz_average_angle = parseFloat(sumAngle / Configure.Band_MA_NUM).toFixed(2);
		// 算sz和MA的背离率
		var MA_value = (sumValue + parseInt(szPoinsts[Configure.Band_MA_NUM - 1].value))/Configure.Band_MA_NUM;
		dataStorage.sz_ma_beili = parseFloat((szPoinsts[0].value - MA_value) / MA_value).toFixed(4);
		
		return '指数' + (dataStorage.sz_average_angle > 0 ? '向上' : '向下，') + 'MA' + 
				Configure.Band_MA_NUM + '背离率' + (dataStorage.sz_ma_beili*100).toFixed(2) + '%。';
	}
	
	var isBandTicket = function(code) {
		return boardedTickets_10day.findIndex((t)=>{
			return t[Configure.title.code].includes(code);
		}) == -1;
	};
	var isBoardsTicket = function(code) {
		return boardedTickets_3day3.findIndex((t)=>{
			return t[Configure.title.code].includes(code);
		}) > -1;
	};
	
	var getBandtickets = function() {
		//选出趋势票
		var tickets = parser.getBandTickets({hotpointArr:[], sort:2});
		tickets.sort((a, b)=>{
			return window.GetBandFinalScroe(b, dataStorage.bandScoreFator) - 
						window.GetBandFinalScroe(a, dataStorage.bandScoreFator);
		});
		if (/*Configure.debug*/false) {
			Configure.Debug('AI趋势得分排名:');
			tickets.forEach((t)=>{
				Configure.Debug(t[Configure.title.name] + '  ' + window.GetBandFinalScroe(t));
			})
		}

		var num = tickets.length >= 2 ? 2 : tickets.length;
		var txt = '关注趋势波段：';
		for(var i = 0; i < num; i ++ ) {
			txt += tickets[i][Configure.title.name] + ' ';
			dataStorage.band_ticktes.push({name:tickets[i][Configure.title.name], price: tickets[i][Configure.title.price]});
		}
		
		return txt;
	};
	var getTickits = function() {
		var dateStr = workbook.getDisplayLastDate();
		var echelons = parser.getEchelons(dateStr);
		var hotpoints = [];
		hotpoints = hotpoints.concat(echelons[0].hotPoints);
		//在排名靠前的梯队里面找
		echelons.forEach((echelon)=>{
			if (echelon.score > Configure.Echelons_show_min_score){
				hotpoints = hotpoints.concat(echelon.hotPoints);
			}
		})
		
		var param = {
			hotpointArr: hotpoints,
			type:0,
			sort:1
		}
		var tickets =  parser.getTickets(dateStr, param);
		tickets = tickets.filter((t)=>{
			return t[Configure.title.realHandoverPercent] < Configure.Dead_Handover &&       // 过滤掉换手率不符合的票
					t[Configure.title.realHandoverPercent] > Configure.Min_handover; //&&
					//t[Configure.replaceTitleDate(Configure.title.dayNumber, dateStr)] > 1;   //过滤掉1连扳的票，只能做趋势
		}); 
		tickets.sort((a, b)=>{
			return getFinalScroe(b, dateStr) - getFinalScroe(a, dateStr);
		});
		if (/*Configure.debug*/false) {
			Configure.Debug('AI超短得分排名:');
			tickets.forEach((t)=>{
				Configure.Debug(t[Configure.title.name] + '  ' + getFinalScroe(t, dateStr));
			})
		}
		var txt = '关注连板接力：';
		var num = tickets.length >= 3 ? 3 : tickets.length;
		for(var i = 0; i < num; i ++ ) {
			dataStorage.tickits.push(tickets[i][Configure.title.name]);
			txt += tickets[i][Configure.title.name] + ' ';
		}
		return txt;
	};
	var getTaticsTxt = function() {
		var retTxt = '';
		// 获取明天的交易计划
		var arr = workbook.getDatesSheet();
		var d = arr[arr.length-1];
		var titles = [Configure.title2.noon, Configure.title2.context, Configure.title2.qst1, 
				Configure.title2.qst2, Configure.title2.qst3, Configure.title2.qst4, 
				Configure.title2.currentOpt, Configure.title2.objOpt,
				 Configure.title2.optReason, Configure.title2.nextOpt];
		titles.forEach((t)=> {
			if (d[t]) {
				retTxt += '【' + t + '】:  ' + d[t] + '<br>';
			}
		});
		retTxt += '--------------------------------------------------------------------------------------<br>';
		// 获取窗口详细说明
		var context = workbook.getEmotionalCycles(Configure.getDateStr(Configure.date, '-'));
		var contextItem = context.cycles ? workbook.getContext(context.cycles) : null;
		var titles = [Configure.titleTactics.tractic, Configure.titleTactics.market, 
				Configure.titleTactics.emotion, Configure.titleTactics.ticket];
		for (var prop in contextItem) {
				if(titles.indexOf(prop) == -1) {
					if(prop == Configure.titleTactics.context) {
						retTxt += '【' + prop + '】:  ' + 
						Configure.getContextDescription(contextItem[prop]) + '<br>';
					} else {
						retTxt += '【' + prop + '】:  ' + contextItem[prop] + '<br>';
					}
				}
			}
		// 获取策略
		Configure.cangMap.get(dataStorage.emotion).context.forEach((t)=>{
			var tactic = workbook.getTactics(t);
			if(tactic) {
				Object.keys(tactic).forEach(key => { 
					if (tactic && tactic[key]) {
						retTxt += tactic[key] ? '【' + key + '】:  ' + tactic[key] + '<br>' : '';
						}
				})
			}
			retTxt += '<br>';
		});
		return retTxt;
	};
	var clear = function() {
		dataStorage = {
		emotion:'',
		tickits:[],
		sucessRate:0,
		scoreFator: Configure.AI_Default_Factor,         // 默认值，localstorage没有值使用它；
		
		sz_average_angle:0,
		sz_ma_beili : 0,
		bandScoreFator: Configure.AI_Default_Band_Factor,   // 默认值，localstorage没有值使用它； 
		band_ticktes:[]
		};
		
		boardedTickets_10day = [];
		boardedTickets_3day3 = [];
	};
	var isBandInCharge = function() {
		var ret = false;
		Configure.bandConditions.forEach((c, index)=>{
			//Configure.Debug('start check bandConditions index = ' + index);
			if(checkCondition(c)){
				ret = true;
			};
		});
		return ret;
		/*return checkZBUnderDays(Configure.title2.lianban, 5, 4, 5) ||    // 连扳数量
				checkZBUnderDays(Configure.BH_Draw_title, 5, 4, 3) ||    // 连扳高度
				checkZBUnderDays(Configure.title2.boardnum, 5, 4, 20);*/    //涨停数量
	};
	var isIcePoint = function() {
		var ret = true;
		Configure.icePoint.forEach((c, index)=>{
			//Configure.Debug('start check icePoint index = ' + index);
			if(!checkCondition(c)){
				ret = false;
			};
		});
		return ret;
	};
	var getRecommend = function() {
		clear();
		boardedTickets_10day = parser.getAllBoardedTicketsFromDays(10);
		boardedTickets_3day3 = parser.getAllBoardedTicketsFromDays(3, 3);
		// 更新获取storage的数据
		getAndUpdateLoacalstorage();
		
		recommendText = '【AI 提示】';
		if (isIcePoint()) {
			recommendText += 'Fire the hole! 冰点出现! 冰点出现! ';
			recommendText += getSZEnv();
			speecher.speak(recommendText, false);
		} else {
			recommendText += getSZEnv();
			recommendText += getEmotions(); 
			recommendText += isBandInCharge() ? getBandtickets() : getTickits();
		}		
		saveLoacalstorage(dataStorage);
		
		var tatics = getTaticsTxt();
		if(Configure.isPreBidding()) {
			speecher.speak(tatics, false);
		}
		
		var displayColor = Configure.cangMap.get(dataStorage.emotion).context == '博弈' ? 'blue' :
					Configure.cangMap.get(dataStorage.emotion).context == '主升' ? 'red' : 'green';
		return {color: displayColor, txt: recommendText, tatics: tatics};
	};
	
	var drawEmotionCycle = function(){
		canvas.drawEmotionCycle(dataStorage.emotion);
	};
	
	var init = function() {
		// 清理storage过期的数据 LocalStore_history_period
		Object.keys(LocalStore.getAll()).forEach((key)=>{
			if(key.includes(storeNamePrefix)) {
				var dateStr = key.substr(key.indexOf(storeNamePrefix) + storeNamePrefix.length);
				if(dateStr.length == 8) {
					dateStr = dateStr.substr(0,4) + '/' + dateStr.substr(4,2) + '/' + dateStr.substr(6,2);
					if (Configure.getDaysBetween(new Date(dateStr), new Date()) > 
								Configure.LocalStore_history_period) {
						LocalStore.remove(key);
					}
				}
			}
		});
	};
	
	return {
		init:init,
		getRecommend:getRecommend,
		isBandTicket:isBandTicket,
		isBoardsTicket:isBoardsTicket,
		isBandInCharge:isBandInCharge,
		drawEmotionCycle:drawEmotionCycle,
	}
})();