 'use strict';

(function(exports){	

	var handOverBar_w = 6;
	var handOverBar_h = 30;
	
		// 根据 题材、排名涨速算最后的得分    
	var GetBandFinalScroe = function(t, scoreFactor = Configure.AI_Default_Band_Factor) {
		var ticket = parserRT.getRankTicketFromCode(t[Configure.title.code]);
		var sum = 0;
		if(ticket) {
			sum += !!parseFloat(ticket[Configure.title.rise_5]) ? parseFloat(ticket[Configure.title.rise_5]) : 0;
			sum += !!parseFloat(ticket[Configure.title.rise_10]) ? parseFloat(ticket[Configure.title.rise_10]) : 0;
			sum += !!parseFloat(ticket[Configure.title.rise_20]) ? parseFloat(ticket[Configure.title.rise_20]) : 0;
		}
	//	Configure.Debug('getRankTicketFromCode code ' + t[Configure.title.code] + '  t score:' + 
	//				t[Configure.title.score] + '  sum:' + sum + '  factor:' + scoreFactor);
		return parseInt(t[Configure.title.score] + scoreFactor * sum);
	};

	let bandEchelon = function (canvas, e, rect) {
		window.performance.mark("bandEchelon:constructor");
		Echelon.call(this, canvas, e, rect);

		this.points = [[1/2, 1/12],
						[1/4,3/12],[3/8, 5/12], 
						[3/4, 3/12],[5/8, 5/12],[3/8, 9/12], 
									[1/8, 5/12],[5/8, 9/12],[1/4, 7/12], 
												[1/8, 9/12],[3/4, 7/12],[3/4, 11/12],
															[1/2, 7/12],[1/2,11/12],
																		[1/4, 11/12]];
																		
		window.performance.mark("bandEchelon:constructor End");
			Configure.Debug('bandEchelon constructor duration:' 
				+ window.performance.measure("bandEchelon", "bandEchelon:constructor", "bandEchelon:constructor End").duration + 'ms');
	};			
	
	function F() {
	}
	// 把F的原型指向Student.prototype:
	F.prototype = Echelon.prototype;
	bandEchelon.prototype = new F();
	bandEchelon.prototype.constructor = bandEchelon;
	bandEchelon.prototype.obtainCacheTickets = function() {
		return workbook.getBandTickets();
	};
	bandEchelon.prototype.getBoardDateIndex = function(ticket, selectDate) {
		var dayNumber = parseInt(ticket[Configure.replaceTitleDate(Configure.title.dayNumber, selectDate)]);
		dayNumber = dayNumber > 0 ? dayNumber : 1;  // check valid 
		var startIndex = this.dateArr.indexOf(selectDate) + dayNumber - 1;
		
		var obj = {};
		for (var i = 1; i <= Configure.Band_miss_tickit_period ; i ++ ) {
			var param = {sheetName:this.dateArr[startIndex + i],
				ticketCode:ticket[Configure.title.code]};
			obj.tkt = workbook.getValue(param);
			if(obj.tkt) {
				obj.date = this.dateArr[startIndex + i];
				break;
			}
		}
		if (obj.tkt && this.dateArr.indexOf(obj.date) < Configure.Band_Max_LENGTH) {
			startIndex = this.getBoardDateIndex(obj.tkt, obj.date);
		}
		return startIndex;
	};
	
	bandEchelon.prototype.calBarRect = function(startPoint, drawLenth, index) {
		return {x: startPoint.x + (drawLenth - 1 - index) * handOverBar_w,
							y: startPoint.y,
							width: handOverBar_w,
							height: handOverBar_h};
	};
	/*bandEchelon.prototype.drawBar = function(rect, realHandoverPer, boardStrength) {
		var ctx = this.canvas.getContext("2d");		
		ctx.beginPath();
		ctx.lineWidth="2";

		if(parseFloat(realHandoverPer) < 100 && parseFloat(realHandoverPer) > 0) {
			if(boardStrength == '很强') {
				ctx.fillStyle= 'red';
			} else if (boardStrength == '强'){
				ctx.fillStyle= 'orange';
			} else if (boardStrength == '一般') {
				ctx.fillStyle= '#E0E080';
			} else if (boardStrength == '弱'){
				ctx.fillStyle= 'green';
			}
			
			var barHeight = rect.height * parseFloat(realHandoverPer)/100 * Configure.Echelons_handover_factor;
			ctx.fillRect(rect.x, rect.y + rect.height - barHeight, rect.width * 0.9, barHeight);
	//		ctx.fillStyle= 'black';			
	//		ctx.fillText(realHandoverPer, rect.x + 100, rect.y + rect.height - barHeight);
		} else {
			ctx.fillStyle= 'grey';
			ctx.fillRect(rect.x, rect.y, rect.width * 0.9, rect.height);	
		}
	}; */
	
	bandEchelon.prototype.drawTitle = function () {
		var ctx = this.canvas.getContext("2d");	
		ctx.lineWidth="2";
		ctx.font="16px 楷体";
		ctx.fillStyle = 'Orange';
		ctx.fillText(this.echelon.name , this.rect.x + 5, this.rect.y + 15);
		
		ctx.font="14px 楷体";
		ctx.fillStyle = 'Orange';
		ctx.fillText('<' + Configure.Band_miss_tickit_period + '天趋势>', this.rect.x + 5, this.rect.y + 30);
	};
	
	bandEchelon.prototype.getSitePoint = function (ticket) {
		var retP = this.points[0];
		this.points = this.points.slice(1);
		return retP;
	};
	
	bandEchelon.prototype.get_tickit_period = function() {
		return Configure.Band_tickit_period;
	};

	bandEchelon.prototype.filterTickets = function() {
		window.performance.mark("bandEchelon:filterTickets");
		this.tickets = this.tickets.filter((t, index)=>{
			var isSelect = true;
			//首板
			var dayNumber = t[Configure.replaceTitleDate(Configure.title.dayNumber, t.selectDate)];
			if (dayNumber > 1 || this.dateArr.indexOf(t.startDate) - this.dateArr.indexOf(t.selectDate)
					< Configure.Band_tickit_filter_period ) {
				isSelect = false;
			} 
			//市值 && 没有进入排名
			if(t[Configure.title.value] < Configure.Band_Min_Value && 
				!parserRT.getRankTicketFromCode(t[Configure.title.code])) {
				isSelect = false;
			}
			return isSelect;
		});  
		workbook.setBandTickets(this.tickets);   // 剔除之前记录
		window.performance.mark("bandEchelon:filterTickets End");
			Configure.Debug('bandEchelon filterTickets duration:' 
				+ window.performance.measure("bandEchelon", "bandEchelon:filterTickets", "bandEchelon:filterTickets End").duration + 'ms');
	};
	
	bandEchelon.prototype.cutTickets = function() {
		window.performance.mark("bandEchelon:cutTickets");
		// 计算涨速
		this.tickets.forEach((ticket)=>{
			var param = {
				sheetName: ticket.startDate,
				ticketCode:ticket[Configure.title.code]
			}
			
			var tktStart = workbook.getValue(param);
			var priceStart = tktStart ? tktStart[Configure.title.price] : 0;
			var dayNum = this.dateArr.indexOf(ticket.startDate) - this.dateArr.indexOf(ticket.selectDate);
			ticket.increaseRate = (!priceStart || priceStart == 0 || dayNum == 0) ? 0 : 
				parseFloat((parseFloat(ticket[Configure.title.price]) - priceStart) / (priceStart * dayNum)).toFixed(4);
		});
		// echelon股票
		this.tickets = this.tickets.filter((t) => {
			var isSelect = false;
			this.echelon.hotPoints.forEach((g)=> {
				if(t[Configure.replaceTitleDate(Configure.title.reason, t.selectDate)].indexOf(g) != -1){
						isSelect = true;
				}
			});
			return isSelect;
		})
		
		// 按得分排序，减除多余的
		this.tickets.sort((a, b)=> {
			return GetBandFinalScroe(b) - GetBandFinalScroe(a);
		});
		this.tickets = this.tickets.slice(0,Configure.Echelons_ticket_NUM);
		window.performance.mark("bandEchelon:cutTickets End");
			Configure.Debug('bandEchelon cutTickets duration:' 
				+ window.performance.measure("bandEchelon", "bandEchelon:cutTickets", "bandEchelon:cutTickets End").duration + 'ms');
	};
	
	exports.bandEchelon = bandEchelon;
	exports.GetBandFinalScroe = GetBandFinalScroe;
}(window));
