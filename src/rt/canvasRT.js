var canvasRT = (function() {
	var drawing;
	var rect;
	var width = 0;
	var height = 0;
	var width_factor = 0.90;
	var height_factor = 0.8;
	var siteX;
	var siteY;
	var siteHeight;
	var siteWidth;
	var cellWidth, cellNum;
	var cell_factor = 1;
	var site_weight_max = Configure.RT_GAI_show_weight_maxOffset + 
							Configure.RT_GAI_show_weight_min;
	var site_score_max = 3000;
	var rtShowDays_num = Configure.RT_canvas_show_days_num;	

	var POINT_PIXEL = 8;
	
	var clear = function()  {
		drawing.getContext("2d").clearRect(rect.x, rect.y, rect.width, rect.height);
	};
	var drawSite = function() {
		//画线
		var ctx = drawing.getContext("2d");		
		ctx.beginPath();
		ctx.lineWidth="0.5";
		ctx.strokeStyle = 'grey';
		ctx.moveTo(siteX,siteY);
		ctx.lineTo(siteX ,siteY + siteHeight);
		ctx.lineTo(siteX + siteWidth, siteY + siteHeight);
		ctx.lineTo(siteX + siteWidth, siteY);
		ctx.lineTo(siteX,siteY);
		
		// 画内部网格
		for(var i = 1; i <= 3; i ++) {
			ctx.moveTo(siteX  + siteWidth * i / 4,siteY);
			ctx.lineTo(siteX + siteWidth * i / 4,siteY + siteHeight);	
			if(i == 2) {
				ctx.moveTo(siteX,siteY + siteHeight * i / 4);
				ctx.lineTo(siteX + siteWidth ,siteY + siteHeight * i / 4);
				ctx.stroke(); 
			}
		}
		ctx.stroke(); 
		///
		var offset = rtShowDays_num * 240 / Configure.RT_data_length;
		ctx.fillStyle = 'red';
		ctx.font="14px 楷体";
		ctx.fillText(Configure.RT_GAI_show_weight_min, siteX + siteWidth + 4, siteY + siteHeight);
		ctx.fillText(site_weight_max, siteX + siteWidth + 4, siteY + 12);
		ctx.fillText(site_score_max, siteX + siteWidth, siteY);
		
		ctx.fillStyle = Configure.site_color;
		ctx.font="14px 楷体";
		ctx.fillText('09:30', siteX - 10, siteY + siteHeight + 15);
		ctx.fillText('15:00',  siteX + siteWidth/offset - 30, siteY + siteHeight + 15);
		ctx.fillText( Configure.getDateStr(new Date(parserRT.getGaiRankData().getRankData().eDate), '-'), 
						siteX + siteWidth * (rtShowDays_num - 1)/
						rtShowDays_num, 
						siteY - 10);
		ctx.stroke(); 
		
		// 画涨跌个数
		ctx.beginPath();
		ctx.lineWidth="4";
		ctx.strokeStyle = 'red';
		ctx.fillStyle = 'red';
		ctx.font="bold 16px";
		var up = rtDataManager.getRTTickets().filter((rtData)=>{
			return rtData['f3'] > 0;
		}).length;
		var down = rtDataManager.getRTTickets().length - up;
		ctx.fillText( up, siteX + siteWidth * (rtShowDays_num - 1)/ rtShowDays_num + 80, siteY - 10);
		ctx.moveTo(siteX,siteY);
		ctx.lineTo(siteX + siteWidth * (up / (down + up)),siteY);
		ctx.stroke(); 
		ctx.beginPath();
		ctx.fillStyle = 'green';
		ctx.strokeStyle = 'green';
		ctx.fillText( down, siteX + siteWidth * (rtShowDays_num - 1)/ rtShowDays_num + 110, siteY - 10);
		ctx.moveTo(siteX + siteWidth * (up / (down + up)),siteY);
		ctx.lineTo(siteX + siteWidth,siteY);
		ctx.stroke(); 
	};
	
	var ColorReverse = function(OldColorValue){
		var OldColorValue = "0x"+OldColorValue.replace(/#/g,"");
		var str="000000"+(0xFFFFFF-OldColorValue).toString(16);
		return '#' + str.substring(str.length-6,str.length);
	}

	var drawEchelonLine = function(echelon, color, eIndex, num, needReverse = false) {
		var ctx = drawing.getContext("2d");		
		ctx.beginPath();
		ctx.fillStyle= color;
		var rtRankData = parserRT.getGaiRankData();   // getRankData() -> {eDate:,data: []};
		// 从数据中取要显示的第一天index 
		var index = Configure.RT_data_length * 
						(Configure.RT_canvas_record_days_num - rtShowDays_num) / 
							Configure.RT_canvas_record_days_num;
		var eFirst; 	// 记录第一个点，数据不连贯，连线难看
		var offsetX = cellWidth * eIndex/ num;  // 错位显示不同Echelon的cell
		for(i = 0; i < cellNum; i ++, index ++) {
			var e = parserRT.getEchelonByIndex(echelon, index);
			if(e&& e.score!=0) {
				var pointH = siteHeight * 
					(parseFloat(e.score) - Configure.RT_GAI_show_weight_min)/
						(site_weight_max - Configure.RT_GAI_show_weight_min);
				var szPoint = {x: siteX + cellWidth  * i + offsetX,
					y: siteY + siteHeight - pointH};
				
				if(!eFirst ) {
					eFirst = parserRT.getEchelonByIndex(echelon, index); 
					//ctx.fillRect(szPoint.x - POINT_PIXEL / 2, szPoint.y - POINT_PIXEL / 2, 
					//		POINT_PIXEL, POINT_PIXEL);   // 画第一个点
					ctx.font="14px 楷体";
					ctx.fillText('<' + e.name.substr(0,2) + '>',siteX + siteWidth - 5, 
					szPoint.y);
					ctx.stroke();
				}
				if(eFirst && eFirst.score != 0) {
					ctx.beginPath();
					var pointFirstH = needReverse ?  siteHeight  * (parseFloat(eFirst.score) - Configure.RT_GAI_show_weight_min)/
								(site_weight_max - Configure.RT_GAI_show_weight_min) : 0;
					var szpointFirst = {x:siteX + cellWidth  * i + offsetX,
											y: siteY + siteHeight - pointFirstH};
					ctx.lineWidth= cellWidth / Configure.RT_canvas_show_echelons_num;
					ctx.strokeStyle = szPoint.y > szpointFirst.y && needReverse ?
										ColorReverse(color) : color;
					ctx.moveTo(szPoint.x, szPoint.y);
					ctx.lineTo(szpointFirst.x, szpointFirst.y);
					ctx.stroke();
				}
				ctx.stroke();
			}
		}
	};
	
	var drawEchelons = function(nameArr) {
		var displayIndex = 0;
		Array.from(parserRT.getRTEchelons()).forEach((e) => {
			var color = Configure.echelon_color[displayIndex%Configure.echelon_color.length];
			var topEchelons = parserRT.getGaiRankData().getTopEchelons();
			var idx = topEchelons.findIndex((tEchelon)=>{
				return tEchelon.name == e.name;
			})
			if(!nameArr || nameArr.length == 0) {   // 默认显示top echelons
				if(idx >= 0) {
					drawEchelonLine(e, color, displayIndex, topEchelons.length, true);
					displayIndex ++;
				}
			} else {
				if(nameArr.includes(e.name) && 
					displayIndex <= Configure.RT_canvas_show_echelons_num){
					drawEchelonLine(e, color, displayIndex, nameArr.length, idx >= 0);
					displayIndex ++;
				};
			}
		});
	};
	var drawEmotion = function(isShowMA) {
		var ctx = drawing.getContext("2d");		
		var rtRankData = parserRT.getGaiRankData();   // getRankData() -> {eDate:,data: []};
		// 从数据中取要显示的第一天index 和最后一天 indexLast
		var index = Configure.RT_data_length * 
						(Configure.RT_canvas_record_days_num - rtShowDays_num) / 
							Configure.RT_canvas_record_days_num;
		var indexLast = rtRankData.getIndexFromDate(new Date(rtRankData.getRankData().eDate));
		indexLast = indexLast > Configure.RT_data_length ? Configure.RT_data_length : indexLast;
		var drawLength = indexLast - index;
		var score = 0, scoreNext = 0;
		for(i = 0; i < cellNum; i ++, index ++) {
			function drawLine(score, scoreNext) {
				if(score!=0) {
					var pointH = siteHeight * 
						(parseFloat(score) - 0)/ site_score_max;
					var point = {x: siteX + cellWidth  * i,
						y: siteY + siteHeight - pointH};
					if (i * Configure.RT_canvas_record_days_num % Configure.RT_data_length == 0) {   // 每天的首个
						ctx.fillRect(point.x - POINT_PIXEL / 2, point.y - POINT_PIXEL / 2, 
											POINT_PIXEL + 2, POINT_PIXEL + 2);
					}
					if (i < drawLength - 1) {   // 不是最后一天
						
						var pointNextH = siteHeight * (parseFloat(scoreNext) - 0)/ site_score_max;
						var pointNext = {x: siteX + cellWidth  * (i + 1),
									y: siteY + siteHeight - pointNextH};
						ctx.moveTo(point.x, point.y);
						ctx.lineTo(pointNext.x, pointNext.y);
					} 
				}
			}
			
			ctx.beginPath();
			var grd=ctx.createLinearGradient(siteX, siteY + siteHeight, siteX, siteY);
			grd.addColorStop(0,"green");
			grd.addColorStop(0.6,"orange");
			grd.addColorStop(1,Configure.line_color);  
			ctx.lineWidth="3";
			ctx.fillStyle = grd;
			ctx.strokeStyle = grd;
			score = parserRT.getScoreTotalByIndex(index);
			score = score == 0 ? scoreNext : score;
			scoreNext = parserRT.getScoreTotalByIndex(index + 1);
			scoreNext = scoreNext == 0 ? score : scoreNext;
			drawLine(score, scoreNext);
			ctx.stroke();
			
			//  画均线
			if (isShowMA && index >= 3 * Configure.RT_data_length / Configure.RT_canvas_record_days_num) {
				ctx.beginPath();
				ctx.lineWidth="2";
				ctx.fillStyle = 'black';
				ctx.strokeStyle = 'black';
				var ma3 = parserRT.getScoreMAByIndex(index);
				var ma3Next = parserRT.getScoreMAByIndex(index + 1);
				ma3 = ma3 == 0 ? ma3Next : ma3;
				ma3Next = ma3Next == 0 ? ma3 : ma3Next;
				drawLine(ma3, ma3Next);
				ctx.stroke();
			} 
		}
	};
	
	var drawLine = function(type, zero, maxoffset, color) {
		var ctx = drawing.getContext("2d");		
		ctx.beginPath();
		ctx.lineWidth="1";
		ctx.strokeStyle = color;
		
		var rtRankData = parserRT.getGaiRankData();   // getRankData() -> {eDate:,data: []};
		// 从数据中取要显示的第一天index 和最后一天 indexLast
		var index = Configure.RT_data_length * 
						(Configure.RT_canvas_record_days_num - rtShowDays_num) / 
							Configure.RT_canvas_record_days_num;
		var indexLast = rtRankData.getIndexFromDate(new Date(rtRankData.getRankData().eDate));
		indexLast = indexLast > Configure.RT_data_length ? Configure.RT_data_length : indexLast;
		var drawLength = indexLast - index;
		var score = 0, scoreNext = 0;
		for(i = 0; i < cellNum; i ++, index ++) {
			score = rtRankData.getRankData().data[index].paramExt[type];
			score = !score || score == 0 ? scoreNext : score;
			if(score!=0) {
				var pointH = siteHeight * 
					(parseFloat(score) - zero)/ maxoffset;
				var point = {x: siteX + cellWidth  * i,
					y: siteY + siteHeight - pointH};
				if (i * Configure.RT_canvas_record_days_num % Configure.RT_data_length == 0) {   // 每天的首个
					ctx.fillStyle= color;
					ctx.fillRect(point.x - POINT_PIXEL / 2, point.y - POINT_PIXEL / 2, 
										POINT_PIXEL, POINT_PIXEL);
				}
				if (i < drawLength - 1) {   // 不是最后一天
					scoreNext = rtRankData.getRankData().data[index + 1].paramExt[type];
					scoreNext = !scoreNext || scoreNext == 0 ? score : scoreNext;
					var pointNextH = siteHeight * (parseFloat(scoreNext) - zero)/ maxoffset;
					var pointNext = {x: siteX + cellWidth  * (i + 1),
								y: siteY + siteHeight - pointNextH};
					ctx.moveTo(point.x, point.y);
					ctx.lineTo(pointNext.x, pointNext.y);
				} else if(i == drawLength - 1){
					// 前一天此时得分
				//	var bscore =rtRankData.getRankData().data[index - Configure.RT_data_length / 
				//			Configure.RT_canvas_record_days_num].paramExt[type];
				//	if(bscore > 0) {
				//		ctx.fillStyle= score > bscore ? 'rgba(255,0,0,0.5)' : 'rgba(0,255,120,0.5)';
				//		ctx.fillText(type + score + '(' + (score - bscore) + ')', point.x - 20, point.y - 15);
				//	} else {
						ctx.fillStyle= color;  //'rgba(255,0,0,0.5)';
						var o = Configure.isAfterTrading() ? -30 : 10;
						ctx.fillText(type + score, point.x + o, point.y < siteY ? siteY : point.y - 5);
				//	}
				}
				ctx.stroke();
			}
		}
	};
	
	var reload = function() {
		cellNum = Configure.RT_data_length * rtShowDays_num / 
							Configure.RT_canvas_record_days_num;
		cellWidth = siteWidth/ cellNum  * cell_factor;
	};
	var reDraw = function(nameArr, rtShowD) {
		clear();
		site_weight_max = Math.ceil(parserRT.getMaxScoreWithDaynum(rtShowD, 'echelon'));
		site_weight_max = site_weight_max > 10 ? site_weight_max : 10;
		site_score_max = Math.ceil(parserRT.getMaxScoreWithDaynum(rtShowD, 'total') / 1000) * 1000;
		site_score_max = site_score_max > 4000 ? site_score_max : 4000;
		rtShowDays_num = rtShowD;
		var sitefloorMax = rtDataManager.getRTTickets().filter(rtDataManager.floorFilter).length;
		sitefloorMax = sitefloorMax > 100 ?  Math.ceil(sitefloorMax/200)*200 :
						sitefloorMax > 20 ?  Math.ceil(sitefloorMax/20)*20 : 20;
		var siteboardMax = rtDataManager.getRTTickets().filter(rtDataManager.boardFilter).length;
		siteboardMax = siteboardMax > 100 ?  Math.ceil(siteboardMax/100)*100 :
						siteboardMax > 60 ?  Math.ceil(siteboardMax/10)*10 : 60;
		var siteboardFailMax = rtDataManager.getRTTickets().filter((data)=>{
			return rtDataManager.boardedFilter(data) && !rtDataManager.boardFilter(data);
		}).length;
		siteboardFailMax = siteboardFailMax > 100 ?  Math.ceil(siteboardFailMax/100)*100 :
						siteboardFailMax > 30 ?  Math.ceil(siteboardFailMax/10)*10 : 30;
		
		reload();
		drawSite();
		drawEchelons(nameArr);

		if(!nameArr || nameArr.length == 0) {	
		//	drawLine('赚钱效应', -3, 10, 'blue');
			drawLine('涨停', 0, siteboardMax, 'red');
			drawLine('跌停', -sitefloorMax, sitefloorMax, 'green');
			if (rtShowD < 2) {
				drawLine('上涨', 0, 5500, '#FFC0CB');
				drawLine('炸板', -siteboardFailMax, siteboardFailMax, 'DarkSeaGreen');
			}
		}
		drawEmotion(nameArr.length != 0 || rtShowD <= 2);
	}
	var draw = function(c, r, nameArr, rtShowD) {
		if (c.getContext){
			window.performance.mark("CanvasRT:draw");
			drawing = c;
			rect = r;
			
			width = rect.width;
			height = rect.height;
			siteX = rect.x + 10;
			siteY = rect.y + height * (1 - height_factor)/2;
			siteWidth = width * width_factor;
			siteHeight = height * height_factor;
			Configure.Debug('RT canvas width:' + width + 
					' height:' + height + 
					' siteX' + siteX +
					' siteY:' + siteY +
					' siteWidth:' + siteWidth + 
					' siteHeight:' + siteHeight);		
			reDraw(nameArr, rtShowD);
			window.performance.mark("CanvasRT:drawDone");
			Configure.Debug('CanvasRT draw duration:' 
				+ window.performance.measure("CanvasRT", "CanvasRT:draw", "CanvasRT:drawDone").duration + 'ms');
		}
	};
	return {
		draw:draw,
		reDraw:reDraw,
	}
})();