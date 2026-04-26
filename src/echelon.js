'use strict';

(function(exports){	
	var handOverBar_w = 8;
	var handOverBar_h = 20;
	
	let Echelon = function (canvas, e, rect) {
		this.canvas = canvas;
		this.echelon = e;
		this.rect = rect;
		
		this.points1 = [[1/2, 2/12],[1/8, 3/12],[7/8, 3/12],[1/4,3/12],[3/4, 3/12]];
		this.points2 = [[3/8, 5/12], [5/8, 5/12],[1/8, 5/12],  [7/8, 5/12],[3/4, 3/12],[1/4, 7/12], [7/8, 3/12],[3/4, 7/12],];
		this.points3 = [[3/8, 9/12],[5/8, 9/12],[1/8, 9/12], [1/2, 7/12],[1/4, 7/12], [3/4, 7/12], [7/8, 9/12],
						[3/4, 11/12], [1/2,11/12], [1/4, 11/12]];
		
		this.dateArr = workbook.getDateArr((a,b)=>{
			return b - a;
		});

		this.tickets = this.obtainCacheTickets();   // cache 重复collect很耗时
		if(this.tickets.length == 0) {
			this.collectTickets();
			// 检查断板
			this.tickets.forEach((ticket)=>{
				ticket.startDate = this.dateArr[this.getBoardDateIndex(ticket, ticket.selectDate)];
			});
			this.filterTickets();
		}
		this.cutTickets();
	};
	
	Echelon.prototype.get_tickit_period = function() {
		return Configure.Echelons_tickit_period;
	};
	Echelon.prototype.obtainCacheTickets = function() {
		return [];
	};
	
	Echelon.prototype.collectTickets = function() {
		for (var i = 0; i < this.get_tickit_period(); i ++ ) {
			var param = {
				hotpointArr: [],
				type:0,
				sort:1
			}
			var tArr = parser.getTickets(this.dateArr[i],param);
			tArr = tArr.filter((t1)=>{
				var isSelect = true;
				this.tickets.forEach((t2)=> {
					if(t2[Configure.title.code] == t1[Configure.title.code]){
						isSelect = false;
					}
				})
				
				if(isSelect) {
					t1.selectDate = this.dateArr[i];
				}
				return isSelect;
			});
			
			this.tickets = this.tickets.concat(tArr);
		};
	};
	
	Echelon.prototype.filterTickets = function() {
		// 过滤掉首板和背离率大于3的
		this.tickets = this.tickets.filter((t)=>{
			var isSelect = true;
			// echelon股票
			var isInEchelon = false;
			this.echelon.hotPoints.forEach((g)=> {
				if(t[Configure.replaceTitleDate(Configure.title.reason, t.selectDate)].indexOf(g) != -1){
						isInEchelon = true;
				}
			});
			isSelect = isInEchelon;
			//首板
			var dayNumber = t[Configure.replaceTitleDate(Configure.title.dayNumber, t.selectDate)];
			if (dayNumber == 1 &&   
				parseInt(this.dateArr.indexOf(t.startDate)) - 
				this.dateArr.indexOf(t.selectDate) < this.get_tickit_period()) {
				isSelect = false;
			} 
			
			// 背离率大于3， 断板大于6的
			if ((parseInt(this.dateArr.indexOf(t.startDate)) - 
				this.dateArr.indexOf(t.selectDate) > this.get_tickit_period() 
			)) {
				if (t[Configure.title.totalDivergence] > 6) {
					isSelect = false;
				}
				
			} else if(t[Configure.title.totalDivergence] > 3){
				isSelect = false;
			}
			return isSelect;
		});  
	};
	
	Echelon.prototype.cutTickets = function() {
		// 按得分排序，减除多余的
		this.tickets.sort((a, b)=> {
			return b[Configure.title.score] - a[Configure.title.score];
		});
		this.tickets = this.tickets.slice(0,Configure.Echelons_ticket_NUM);
	};
	
	Echelon.prototype.getBoardDateIndex = function (ticket, selectDate) {
		var dayNumber = parseInt(ticket[Configure.replaceTitleDate(Configure.title.dayNumber, selectDate)]);
		dayNumber = dayNumber > 0 ? dayNumber : 1;  // check valid 
		var startIndex = this.dateArr.indexOf(selectDate) + dayNumber - 1;
		
		var obj = {};
		for (var i = 1; i <= Configure.Echelons_miss_tickit_period; i ++ ) {
			var param = {sheetName:this.dateArr[startIndex + i],
				ticketCode:ticket[Configure.title.code]};
			obj.tkt = workbook.getValue(param);
			if(obj.tkt && Configure.isFloorOrFailed(obj.tkt, this.dateArr[startIndex + i])) {
				obj.date = this.dateArr[startIndex + i];
				break;
			}
		}
		if (obj.tkt && Configure.isFloorOrFailed(obj.tkt, this.dateArr[startIndex + i])) {
			startIndex = this.getBoardDateIndex(obj.tkt, obj.date);
		}
		return startIndex;
	};
	
	Echelon.prototype.getSitePoint = function (ticket) {
		var ticketBoardNum = this.dateArr.indexOf(ticket.startDate);
		var retP;
		if (ticketBoardNum >= 6) {
			retP = this.points1[0];
			this.points1 = this.points1.slice(1);
		} else if (ticketBoardNum >= 3) {
			retP = this.points2[0];
			this.points2 = this.points2.slice(1);
		} else {
			retP = this.points3[0];
			this.points3 = this.points3.slice(1);
		}
		return retP;
	};
	Echelon.prototype.calBarRect = function(startPoint, drawLenth, index) {
		return {x: startPoint.x + (drawLenth - 1 - index) * handOverBar_w,
							y: startPoint.y,
							width: handOverBar_w,
							height: handOverBar_h};
	};
	Echelon.prototype.drawBar = function(rect, realHandoverPer, boardStrength) {
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
			ctx.fillStyle= 'rgba(128,128,128,0.2)';
			ctx.fillRect(rect.x, rect.y, rect.width * 0.9, rect.height);	
		}
	};
	Echelon.prototype.drawTicket = function (ticket, startPoint) {
		// 获取其他日期的换手率
		var index = parseInt(this.dateArr.indexOf(ticket.selectDate));
		var drawLenth = parseInt(this.dateArr.indexOf(ticket.startDate)) + 1;
				
		for (var i = drawLenth -1 ; i >= 0; i --) {
			var param = {sheetName:this.dateArr[i],
					ticketCode:ticket[Configure.title.code]};
			var tkt = workbook.getValue(param);
			var /*realHandoverPer = -1 ,*/ turnOver = -1;
			var boardStrength = '';
			if (tkt && tkt[Configure.replaceTitleDate(Configure.title.dayNumber,this.dateArr[i])] != 0) {
				//realHandoverPer = parseFloat(parseFloat(tkt[Configure.replaceTitleDate(Configure.title.handoverPercent, this.dateArr[i])]) 
				//						/ ((100 - tkt[Configure.title.orgProportion])/100)).toFixed(2) + '  ';
				turnOver = tkt[Configure.title.turnOver] / 100000000;
				boardStrength = Configure.getBoardStrength(tkt[Configure.title.boardType], 
									tkt[Configure.replaceTitleDate(Configure.title.boardPercent, this.dateArr[i])]).description;
									
				//当最后一天该股票的涨停原因为空或者其他情况，index需要重新更新，显示名字颜色
				index = i;
				/////
			}
			
			var barRect = this.calBarRect(startPoint, drawLenth, i);
			this.drawBar(barRect, turnOver, boardStrength);
		}
		// 名字
		var ctx = this.canvas.getContext("2d");		
		ctx.beginPath();
		ctx.lineWidth="3";
		ctx.font="16px 楷体";
		if (index != 0) {
			ctx.fillStyle = 'green';
		} else {
			ctx.fillStyle = 'red';
		}
		ctx.fillText(ticket[Configure.title.name], startPoint.x, startPoint.y - 3);
	};
	Echelon.prototype.drawTitle = function() {
		var ctx = this.canvas.getContext("2d");	
		ctx.lineWidth="2";
		ctx.font="16px 楷体";
		ctx.fillStyle = 'orange';
		ctx.fillText(this.echelon.name, this.rect.x + 5, this.rect.y + 15);
		
		ctx.font="14px 楷体";
		ctx.fillStyle = 'orange';
		ctx.fillText('<' + Configure.Echelons_miss_tickit_period + '天连板>', this.rect.x + 5, this.rect.y + 30);
	};
	Echelon.prototype.draw = function () {
		window.performance.mark("Echelon:draw");
		var ctx = this.canvas.getContext("2d");	
		ctx.clearRect(this.rect.x, this.rect.y, this.rect.width, this.rect.height);
		ctx.beginPath();
		ctx.lineWidth="2";
		ctx.strokeStyle = "rgba(0, 0, 255, 0.5)";
	//	ctx.strokeRect(this.rect.x, this.rect.y, this.rect.width, this.rect.height);	
		this.drawTitle();
		this.tickets.forEach((t)=>{
			var p = this.getSitePoint(t);
	//		Configure.Debug(p);
			if(p) {
				this.drawTicket(t, {x : this.rect.x + this.rect.width * p[0] - 15,
								y : this.rect.y + this.rect.height * p[1]});
			} else {
				console.error('No enough point site to set ' + t[Configure.title.name]);
			}
			
		});
		window.performance.mark("Echelon:drawDone");
			Configure.Debug('Echelon draw duration:' 
				+ window.performance.measure("Echelon", "Echelon:draw", "Echelon:drawDone").duration + 'ms');
	};
	
	Echelon.prototype.getTickets = function() {
		return this.tickets;
	}
	exports.Echelon = Echelon;
}(window));
