 var workbook = (function() {
	var Book;
	
	// 生成动作很耗时 cache一下
	var BandTicketsCache = [];
	var SheetCache = {};  // 存储要使用的表
		
	var Book = function(b){
		Book = b
	};
	var sheetExist = function(name) {
		return Book.Sheets.hasOwnProperty(name) || 
				//兼容老版本不完整得日期表格
				Book.Sheets.hasOwnProperty(name.substr(-6)) ||   
				Book.Sheets.hasOwnProperty(name.substr(-4));
				// 兼容老版本不完整得日期表格 end 
	};
	
	var getSheet = function(name) {
		if (SheetCache[name]) {
			return SheetCache[name].slice();
		}
		// 表格的表格范围，可用于判断表头是否数量是否正确
        var fromTo = '';
		SheetCache[name] = [];  // 存储要使用的表
		if(sheetExist(name)) {
			SheetCache[name] = SheetCache[name].concat(XLSX.utils.sheet_to_json(Book.Sheets[name]));
			 //兼容老版本不完整得日期表格
			if(!SheetCache[name].length) {   
				SheetCache[name] = SheetCache[name].concat(XLSX.utils.sheet_to_json(Book.Sheets[name.substr(-6)]));
				if(!SheetCache[name].length) {
					SheetCache[name] = SheetCache[name].concat(XLSX.utils.sheet_to_json(Book.Sheets[name.substr(-4)]));
				}
			}
			// 兼容老版本不完整得日期表格 end 
		}
        // 遍历每张表读取
   /*     for (var sheet in Book.Sheets) {
            if (Book.Sheets.hasOwnProperty(sheet) && name && name.substr(-4) == (sheet)) {
				fromTo = Book.Sheets[sheet]['!ref'];
                SheetCache[name] = SheetCache[name].concat(XLSX.utils.sheet_to_json(Book.Sheets[sheet]));
                //  break; // 如果只取第一张表，就取消注释这行
            }
        } */
		return SheetCache[name].slice();
	};

	var setBandTickets = function(ticketArr) {
		BandTicketsCache = ticketArr.slice(0);
	};
	
	var getBandTickets = function() {
		return BandTicketsCache;
	};
	
	var getEmotionalCycles = function(dateStr) {
		var sheet = getSheet('情绪');
		sheet.reverse();
		var index = sheet.findIndex((e)=>{
				var d = Configure.formatExcelDate(e[Configure.titleCycles.date]);
				if (d != '' && dateStr >= d) return true;
			});
		var retCycle = {};
		for(var i = index; i < sheet.length; i ++) {
			if(sheet[i][Configure.titleCycles.cycles]) {
				retCycle.cycles = sheet[i][Configure.titleCycles.cycles];
				retCycle.hotpoint = sheet[i][Configure.titleCycles.hotpoint];
				retCycle.isTurning = false;
				if (dateStr == Configure.formatExcelDate(sheet[i][Configure.titleCycles.date])) {
					retCycle.isTurning = true;
				}
				break;
			}
		}
		return retCycle;
	};
	var getTactics = function(t) {
		var sheet = getSheet('交易模式');
		return sheet.find((item)=> {
			return item[Configure.titleTactics.tractic] && 
					item[Configure.titleTactics.tractic].includes(t);
		});
	};
	var getEchelonsFromExcel = function() {
		return getSheet('题材配置');
	};
	var getContext = function(contextStr) {
		var sheet = getSheet('交易模式');
		return sheet.find((item)=> {
			return item[Configure.titleTactics.context] && 
					contextStr.includes(item[Configure.titleTactics.context]);
		});
	};
	var getContextTypeAndParam = function(contextStr) {
		var item = getContext(contextStr);
		var ret = item && item[Configure.titleTactics.contextType] ? 
				{type:item[Configure.titleTactics.contextType], param:item[Configure.titleTactics.param]}  
					: null;
		return  ret;
	};
	
	var getDatesSheet= function() {
		var sheet = getSheet('周期');
		var start = sheet.length > Configure.Days_Max_lengh ? 
						sheet.length - Configure.Days_Max_lengh : 0;
		var lastDate = Configure.getDateStr(Configure.date, '-');
		var end = sheet.findIndex((d)=>{
			return Configure.formatExcelDate(d[Configure.title2.date]) > lastDate;
		});
		return  end > start ? sheet.slice(start, end) : sheet.slice(start);
	};
	
	var getDateArr = function(sort, separator = '') {
		var sheet = getDatesSheet();
		var retArr = [];
		sheet.forEach((d)=>{
			 retArr.push(Configure.formatExcelDate(d[Configure.title2.date], separator));
		});
		return retArr.sort(sort);
	};
	var getPreDate = function(dateStr, separator = '') {
		var dateArr = getDateArr(()=>{});
		var index = dateArr.findIndex((d)=>{
			return d >= dateStr
		});
		index = index > 0 ? index - 1 : 0;
		if(separator) {
			dateArr = getDateArr(()=>{}, separator);
		}
		return dateArr[index];
	};
	var getNextDate = function(dateStr, separator = '') {
		var sheet = getSheet('周期').reverse();    //获取原始的表
		var index = sheet.findIndex((d)=>{
			return Configure.formatExcelDate(d[Configure.title2.date], '') <= dateStr
		});
		index = index > 0 ?
					index - 1 : 0;
		return Configure.formatExcelDate(sheet[index][Configure.title2.date], separator);
	};
	var getLastDate = function(separator = '') {
		var sheet = getSheet('周期').reverse();    //获取原始的表
		return  Configure.formatExcelDate(sheet[0][Configure.title2.date], separator);
	};
		
	var getDisplayLastDate = function() {
		return getDateArr((a,b)=>{
			return b - a;
		})[0];
	};
	
	// A :5日涨幅大于20%或者10日涨幅大于30%或者20日涨幅大于40%
	var getRankTickets = function(preWeek = false) {
		var weeknum = Configure.getWeek(Configure.date);
		if(preWeek) weeknum --;
		while(!sheetExist('W' + weeknum) && weeknum > 0){
			weeknum --;
		}
		return getSheet('W' + weeknum);
	};

	// param = {sheetName: '0707',ticketCode:'SZ002527'}}
	// A : 今日非ST涨停板或者今日涨停过或者今日跌停或者今日跌停过 上市时间超过30天
	var getValue = function(param) {
		var s = getSheet(param.sheetName);
		var ret ;
		s.forEach((t)=>{
			if(t[Configure.title.code] == param.ticketCode) {
				ret = t;
			}
		})
		return ret;
	};
	return {
		Book:Book,
		getSheet:getSheet,
		sheetExist:sheetExist,
		getDateArr:getDateArr,
		getDatesSheet:getDatesSheet,
		getValue:getValue,
		getEmotionalCycles:getEmotionalCycles,
		getTactics:getTactics,
		getEchelonsFromExcel:getEchelonsFromExcel,
		getContext:getContext,
		getContextTypeAndParam:getContextTypeAndParam,
		getDisplayLastDate:getDisplayLastDate,
		getPreDate:getPreDate,
		getNextDate:getNextDate,
		getLastDate:getLastDate,
		setBandTickets:setBandTickets,
		getBandTickets:getBandTickets,
		getRankTickets:getRankTickets,
	}
 })();