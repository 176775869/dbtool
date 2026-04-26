var table = (function(){
	
	//var tableHeadDone = false;
	var tbl = document.getElementById('tbl');
	var tBody = tbl.tBodies[0];
	var tHead = tbl.tHead;
	var tHeadtds;
	
	var datetoload;   // load date
	var param;        // load param
	var highlightTichets;  // highlight
	
	var btn_loadMore = document.getElementById('load-all-btn');
	var load_item_num = 20;
	
	var updateForm = function() {
		var fr = document.getElementById('form2');
		var checkNameArr = [];
		while(fr.hasChildNodes()) {
			if (fr.lastChild.checked) {
				checkNameArr.push(fr.lastChild.dataset.titleName);   // 记录checked input
			};
			fr.removeChild(fr.lastChild);
		};
		
		var t = document.createTextNode('概念：');
		fr.appendChild(t);	
		// all
		var oAll = document.createTextNode('全部\xa0\xa0\xa0\xa0');
		var inputAll = document.createElement('input');
		var oOther = document.createTextNode('其他\xa0\xa0\xa0\xa0');
		var inputOther = document.createElement('input');
		inputAll.type = 'checkbox';
		inputAll.name = 'all';
		inputAll.dataset.titleName = 'all';
		inputAll.checked = checkNameArr.indexOf(inputAll.dataset.titleName) != -1;
		inputAll.onchange = function(e){
			if (e.target.checked) {
				if (fr.gainian && fr.gainian.length > 1) {
					Array.from(fr.gainian).forEach((input)=>{
						input.checked = false;
						inputOther.checked = false;
					})
				} else if(fr.gainian){
					fr.gainian.checked = false;
					inputOther.checked = false;
				}
			}
		};
		fr.appendChild(inputAll);	
		fr.appendChild(oAll);		
		// other
		inputOther.type = 'checkbox';
		inputOther.name = 'all';
		inputOther.dataset.titleName = 'other';
		inputOther.checked = checkNameArr.indexOf(inputOther.dataset.titleName) != -1;
		inputOther.onchange = function(e){
			if (e.target.checked) {
				if (fr.gainian && fr.gainian.length > 1) {
					Array.from(fr.gainian).forEach((input)=>{
						input.checked = false;
						inputAll.checked = false;
					})
				} else if(fr.gainian){
					fr.gainian.checked = false;
					inputAll.checked = false;
				}
			}
		};
			
		
		var d = $('#date')[0].value.replace(/\-/g, '');	
		var echelonArr = Configure.getMode() == Configure.modeType.DP ? 
									parserRT.getRTEchelons() : parser.getEchelons(d);
		echelonArr.forEach((g)=>{
			//if (g.score >= Configure.Echelons_show_min_score) {
				var oTxt = document.createTextNode(g.name + '(' + g.score + ')\xa0\xa0\xa0\xa0');
				var input = document.createElement('input');
				input.type = 'checkbox';
				input.name = 'gainian';
				input.dataset.titleProp = g.hotPoints;
				input.dataset.titleName = g.name;
				input.checked = checkNameArr.indexOf(input.dataset.titleName) != -1;
				input.onchange = function(e){
					if(e.target.checked) {
						inputAll.checked = false;
						inputOther.checked = false;
					}
				}
				Tip.show(input, g.hotPoints.toString().replace(/\,/g, '、<br>'));
					
				fr.appendChild(input);	
				fr.appendChild(oTxt);	
			//}
		
		});
		
		fr.appendChild(inputOther);	
		fr.appendChild(oOther);	

	};
	
	var createTableHead = function() {
		//remove all tr
		while(tHead.hasChildNodes()) {
			tHead.removeChild(tHead.lastChild);
		};
		
		var tr = document.createElement('tr');
		if (false) {  // for Debug
			for (var prop in Configure.title) {
				var td = document.createElement('td');
				td.innerHTML = Configure.title[prop];
				td.dataset.titleProp = prop;
				tr.appendChild(td);
			}
		} else {
			var titleArr = document.getElementById('form1').gtype[2].checked ?  Configure.rankShowInTableTitile :
						document.getElementById('form1').gtype[1].checked ? 
						Configure.bandShowInTableTitile : Configure.showInTableTitile;
			titleArr.forEach((t)=> {
				var td = document.createElement('td');
				if (t == 'reason') {
					td.innerHTML = '涨停原因';
				} else if (t == 'dayNumber') {
					td.innerHTML = '连板数';
				}else if (t == 'boardTime') {
					td.innerHTML = '最终涨停时间';
				} else {
					td.innerHTML =  Configure.title[t];
				}
				td.dataset.titleProp = t;
				tr.appendChild(td);
			});
		}
		tr.className = 'bold';
		tHead.appendChild(tr);
		tHeadtds = Array.from(tHead.getElementsByTagName('td'));
	}
	var addDetailAndDelete = function(tr, ticket) {
			//添加详细超链接
		var tDetail = document.createElement('td');
		tDetail.innerHTML = '<a href="javascript:;" >详细</a>';
		var oD = tDetail.children[0];
		oD.onclick = function(){
			var url = "http://quote.eastmoney.com/" + ticket[Configure.title.code] + ".html#fullScreenChart"
			window.open(url);
		};
		//添加删除超链接
		var tDel = document.createElement('td');
		tDel.innerHTML = '<a href="javascript:;">删除</a>';
		//执行删除表格行操作
		var oA = tDel.children[0];
		oA.onclick = function(){
		//	if(confirm("确定删除吗？")){
				tBody.removeChild(this.parentNode.parentNode);
		//	}
			};
		tr.appendChild(tDetail);
		tr.appendChild(tDel);
		tBody.appendChild(tr);
	}
	var createTicketRow = function() {
		//remove all tr
		while(tBody.hasChildNodes()) {
			tBody.removeChild(tBody.lastChild);
		};
		
		var tks = parser.getTickets(datetoload,param);
		var dateArr = workbook.getDateArr((a,b)=>{
			return b - a;
		});
		tks.forEach((ticket)=> {
			var tr = document.createElement('tr');
			tr.dataset.ticketCode = ticket[Configure.title.code];
			tHeadtds.forEach((t)=> {
				var td = document.createElement('td');
				td.dataset.prop = t.dataset.titleProp;
				td.innerHTML =ticket.selectDate ? 
								ticket[Configure.replaceTitleDate(Configure.title[t.dataset.titleProp],ticket.selectDate)] :
									ticket[Configure.title[t.dataset.titleProp]];
				switch (t.dataset.titleProp) {
					case 'name':
						if(ticket[Configure.title.code]) {
							if( Configure.isChungTicket(ticket[Configure.title.code])) {
								td.innerHTML += '(创)';
							} else if (Configure.isKeTicket(ticket[Configure.title.code])) {
								td.innerHTML += '(科)';
							} else if (Configure.isBJTicket(ticket[Configure.title.code])) {
									td.innerHTML += '(京)';		
									tr.className = 'grey';
							} else if(Configure.isSHTicket(ticket[Configure.title.code])){
									td.innerHTML += '(SH)';
							};
						};
						break;
					case 'realValue':
						let v = parseFloat(ticket[t.innerHTML]/100000000);
						if (v > 100) {
							td.className = 'red';
						} 
						td.innerHTML = v.toFixed(2);
						Tip.show(td, '流通市值：' + parseFloat(ticket[Configure.title.value]/100000000).toFixed(2) + '<br>' +
								'机构持股比例合计: ' + ticket[Configure.title.orgProportion] + '%<br>');
						break;
					case 'boardStrength':
						td.innerHTML = ticket[Configure.title.boardStrength].description;
						if (ticket[Configure.title.boardStrength].description == '很强') {
							td.className = 'red';
						} 
						Tip.show(td, '封板类型：' + ticket[Configure.title.boardType] + '<br>' +
								'封成比: ' + ticket[Configure.title.boardPercent] + '%');
						break;
					case 'dayNumber':
						if(parseInt(ticket[Configure.title.boardAndDay]) > 196611){  // 196611 三连扳
							Tip.show(td, '板：' + ticket[Configure.title.boardAndDay] + '<br>');
						};
						break;
					case 'boardAndDay':
						var db = Configure.getDayBoard(ticket[Configure.title.boardAndDay]);
						var txt = db.d == db.b ? db.b : db.d + '/' + db.b  + 
							'/' + Configure.replaceTitleDate(ticket[Configure.title.dayNumber], datetoload);
						td.innerHTML = txt ? txt : ticket[Configure.title.boardAndDay];
						
						break;
					case 'totalDivergence':
						Tip.show(td, '价格：' + ticket[Configure.title.price] + '<br>' +
								(ticket[Configure.title.profitProportion] ? 
								'筹码: ' + ticket[Configure.title.profitProportion] : ''));
						if (ticket[Configure.title.totalDivergence] > 18) {
							td.className = 'grey';
						} else if(ticket[Configure.title.totalDivergence] > 3){
							td.className = 'green';
						}
						break;
					case 'realHandoverPercent':
						var dayNum = parseInt(Configure.replaceTitleDate(ticket[Configure.title.dayNumber]));
						var txtshow = dayNum > 1 ? '前' + (dayNum - 1) +  '天实际换手率：' : '';
						for(var i = dayNum - 1; i > 0 ; i --){
							var param = {sheetName:dateArr[i],
								ticketCode:ticket[Configure.title.code]};
							var tkt = workbook.getValue(param);
							if (tkt) {
								txtshow += parseFloat(tkt[Configure.replaceTitleDate(Configure.title.handoverPercent, dateArr[i])] 
										/ ((100 - tkt[Configure.title.orgProportion])/100)).toFixed(2) + '  ';
							}
						}
						if(txtshow && txtshow != '') {
							Tip.show(td, txtshow);
						}
						if (ticket[Configure.title.realHandoverPercent] > Configure.Dead_Handover) {
							td.className = 'green';
						}
						break;
					case 'turnOver' : 
						td.innerHTML = parseFloat(ticket[Configure.title.turnOver] / 100000000).toFixed(2);
						break;
					case 'reason':
						Tip.show(t, parser.getHotpointstxt(datetoload));
						break;
					case 'selectDate':
						td.innerHTML = ticket.selectDate.slice(0,4) + '-' + 
										ticket.selectDate.slice(4,6) + '-' + 
										ticket.selectDate.slice(6);
						break;
					case 'price' : 
						td.innerHTML = '&nbsp;&nbsp;&nbsp;' + td.innerHTML + '&nbsp;&nbsp;&nbsp;';
						break;
					case 'increaseRate':
						td.innerHTML = ticket.increaseRate == '' ? '' : parseFloat(ticket.increaseRate * 100).toFixed(2);
						var num = dateArr.indexOf(ticket.startDate) - dateArr.indexOf(ticket.selectDate);
						var txt = '' + ticket.startDate + '-' + ticket.selectDate +' ' + num + '天';
						Tip.show(td, txt);
					default:
						break;
					} 
					
				if(highlightTichets) {
					highlightTichets.forEach((t)=>{
						if(t[Configure.title.code] == ticket[Configure.title.code]) {
							tr.className = 'highlight';
						}
					})
				}
				tr.appendChild(td);
			});
			addDetailAndDelete(tr, ticket);
		});
	};
	
	var createRankRow = function() {
		//remove all tr
		while(tBody.hasChildNodes()) {
			tBody.removeChild(tBody.lastChild);
		};
		var rankTickets = parserRT.getRankTickets(datetoload,param);
		var findIndexWithNum = function(str,cha,num){
			var x=str.indexOf(cha);
			for(var i=0;i<num;i++){
				x=str.indexOf(cha,x+1);
			}
			return x;
		}
		function createRow(ticket) {
			var tr = document.createElement('tr');
			tr.dataset.ticketCode = ticket[Configure.title.code];
			tHeadtds.forEach((t)=> {
				var td = document.createElement('td');
				td.dataset.prop = t.dataset.titleProp;
				var value = ticket[Configure.title[t.dataset.titleProp]];
				td.innerHTML = value;
				
				switch (t.dataset.titleProp) {
					case 'name':
						if(ticket[Configure.title.code]) {
							if( Configure.isChungTicket(ticket[Configure.title.code])) {
								td.innerHTML += '(创)';
							} else if (Configure.isKeTicket(ticket[Configure.title.code])) {
								td.innerHTML += '(科)';
							} else if (Configure.isBJTicket(ticket[Configure.title.code])) {
								td.innerHTML += '(京)';		
							} else if(Configure.isSHTicket(ticket[Configure.title.code])){
								td.innerHTML += '(SH)';
							} 
						};
						if(Configure.isNew(ticket[Configure.title.time])) {
							td.innerHTML += '(新)';
							td.className = 'grey';
						} else if(AI.isBandTicket(ticket[Configure.title.code])) {
							td.className = 'blue';
						} else if(AI.isBoardsTicket(ticket[Configure.title.code])) {
							td.className = 'lightRed';
						};
						if (ticket[Configure.title.dragonTag]) {
							td.innerHTML += '  (' + ticket[Configure.title.dragonTag].tagDes.substr(0,2) + ')';
							tr.className = ticket[Configure.title.dragonTag].style;
							Tip.show(td, ticket[Configure.title.dragonTag].tagDes);
						}
						break
					case 'price':
						if(Configure.isSuspend(td.innerHTML)) {
							tr.className = 'grey';
						}
					case 'time':
						if(Configure.isNew(value)) {
							td.className = 'grey';
						}
						break;
					case 'increaseRate':
						Tip.show(td, '5日涨幅：' + parseFloat(ticket[Configure.title.rise_5]).toFixed(2) + '<br>' +
									'10日涨幅：' + parseFloat(ticket[Configure.title.rise_10]).toFixed(2) + '<br>' +
									'20日涨幅：' + parseFloat(ticket[Configure.title.rise_20]).toFixed(2) + '<br>');
						break;
					case 'rise_1':				
						td.innerHTML = value.toString().replace(/\%/g, '');
						if(parseFloat(value) >= 0) {
							td.className = 'fontRed';
						} else {
							td.className = 'fontGreen';
						} 
						if (!Configure.isNew(ticket[Configure.title.time], 1) &&
							Configure.isNew(ticket[Configure.title.time]) && 
							value > 20) {
								td.className = 'highlight';
							}
						break;
					case 'rise_5':	
						if(Configure.getMode() == Configure.modeType.FP) {
							// check is new for this week;
							if(!parserRT.getRankTicketFromCode(ticket[Configure.title.code], true) &&
							   td.innerHTML != '--') {
								td.className = 'highlight';
							} 
						}
						
					case 'rise_10':
					case 'rise_20':
						if(td.innerHTML == '--') {
							var min = t.dataset.titleProp == 'rise_5' ? 10 : 
									t.dataset.titleProp == 'rise_10' ? 25 : 40;
							td.innerHTML = '<' + min;
						}
						break;
					case 'value':
						td.innerHTML = parseFloat(ticket[t.innerHTML]/100000000).toFixed(2);
						break;
					case 'gainianDragon':
						td.innerHTML = td.innerHTML.substr(0,findIndexWithNum(td.innerHTML, '】', 2)+1);
						if(td.innerHTML.length > 20) {  //大于20个字符，截取两个概念显示
							td.innerHTML = td.innerHTML.substr(0,findIndexWithNum(td.innerHTML, '】', 1)+1);
						}
						if(Configure.getMode() == Configure.modeType.FP){
							if(td.innerHTML == 'undefined' || td.innerHTML == ''){
								var txt = '';
								var arr = ticket[Configure.title.gainian].split(',');
								if (arr.length <= 1) arr = ticket[Configure.title.gainian].split(';');   //兼容';'
								for(var i = arr.length - 1; i >= 0; i --) {
									if(Configure.gaiBlackList_critical.indexOf(arr[i]) == -1 &&
										Configure.gaiBlackList_verbose.indexOf(arr[i]) == -1) {
										txt += '【';
										txt += arr[i] + '】';
									}
									if (txt.length > 20) break;
								};
								td.innerHTML = td.innerHTML != '' ? td.innerHTML : txt;
							}
						}
						value == '--' ? Tip.show(td, ticket[Configure.title.gainian]) 
										: Tip.show(td,  value);
						Tip.show(t, parserRT.getEchelonsTxt());
						break;
					default :
						break;
				}
				td.innerHTML = td.innerHTML == 'undefined'  ?  '' : td.innerHTML;
				tr.appendChild(td);
			});
			addDetailAndDelete(tr, ticket);
		}
		
		if(rankTickets.length > load_item_num && load_item_num > 0) {
			btn_loadMore.hidden = false;
		} else if(rankTickets.length > 0){
			load_item_num = rankTickets.length;
			btn_loadMore.hidden = true;
		}
		for(var j = 0; j < load_item_num; j ++ ) {
			if(rankTickets[j]) {
				createRow(rankTickets[j]);
			}
		}
	};
	var updateRow = function() {
		if(param.type == 2) {
			createRankRow();
		} else {
			btn_loadMore.hidden = true;
		}
		updateTd();
		updateForm();
	};
	
	var createTable = function (d, p, h) {
		datetoload = d;
		param = p;
		highlightTichets = h;
		
		createTableHead();
		
		btn_loadMore.addEventListener('click', () => {  
			load_item_num = -1;
			btn_loadMore.hidden = true;
			updateRow();
		});

		param.type == 2 ? createRankRow() : createTicketRow(); 
		updateRow();
	};
	
	var updateTd = function() {
		Array.from(tBody.childNodes).forEach((tr)=>{
			tHeadtds.forEach((t)=>{
				var td = Array.from(tr.childNodes).find((td)=>{
							return td.dataset.prop == t.dataset.titleProp;
						})
				var dataT = rtDataManager.getRTTicketFromCode(tr.dataset.ticketCode);
				switch (t.dataset.titleProp) {
					case 'f3' :
					case 'f8':
					case 'f2':
						td.innerHTML = dataT && dataT[t.dataset.titleProp] != '-' ? 
									parseFloat(dataT[t.dataset.titleProp]/100).toFixed(2) : '-';
						if(dataT && parseFloat(dataT['f3']/100) > 0) {
							td.className = 'fontRed';
						} else if (dataT){
							td.className = 'fontGreen';
						} else {
							// default is black
						}
						if(t.dataset.titleProp == 'f3') {
							if(Configure.isBoardDone(dataT)) {
								td.className = 'yellow';
							} else {
								td.className += ' bold';
							}
						}
						if (dataT && !Configure.isNew(dataT['f26'], 1) &&
							Configure.isNew(dataT['f26']) && 
							parseFloat(dataT['f3']/100) > 25) {
								td.className += ' highlight';
						}
						break;
					case 'f6':
						td.innerHTML = dataT && dataT[t.dataset.titleProp] != '-' ? 
									parseFloat(dataT[t.dataset.titleProp]/100000000).toFixed(2) : '-';
						break;
					case 'f109': 
					case 'f110': 
					case 'f160':
						td.innerHTML = dataT && dataT[t.dataset.titleProp] != '-' ? 
									parseFloat(dataT[t.dataset.titleProp]/100).toFixed(2) : '-';
						break;
					case 'gainianDragon':
						// 显示最后三个概念
						if(dataT && dataT['f101']) {
							var txt = dataT['f101'] + ' ';
							var arr = dataT['f103'].split(',');
							for(i = arr.length - 1; i >= 0; i --) {
								if(Configure.gaiBlackList_critical.indexOf(arr[i]) == -1 &&
									Configure.gaiBlackList_verbose.indexOf(arr[i]) == -1) {
									txt += '【';
									txt += arr[i] + '】';
								}
								if (txt.length > 20) break;
							};
							td.innerHTML = td.innerHTML != '' ? td.innerHTML : txt;
							Tip.show(td,  '【' + dataT['f100'] + '】<br>' + dataT['f103']);
						}
					default:
						break;
				}
			});
		});
	};
	
	return {
		createTable:createTable,
		updateForm:updateForm,
		updateTd:updateTd,
		updateRow:updateRow,
	}
})();
