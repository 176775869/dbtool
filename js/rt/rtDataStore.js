
var rtDataStore = (function(){
	var indexDBName = 'rtData';
	var dataStoreName = 'ticketslist';
	var indexDBver = 1;
	
	var storeId = 'rtDataStore_storeDate';
	var storeDate = LocalStore.get(storeId);
	
	var historyRtTicketsArray = [];
	
	var onupgradeneeded = function(event) {
		// 数据库创建或升级的时候会触发
		Configure.Debug("onupgradeneeded");
		db = event.target.result; // 数据库对象
		var objectStore;
		// 创建存储库
		objectStore = db.createObjectStore(dataStoreName, {
			keyPath: "ID", // 这是主键
			//autoIncrement: true // 实现自增
		});
		// 创建索引，在后面查询数据的时候可以根据索引查
		objectStore.createIndex("ID", "ID", { unique: false });
		objectStore.createIndex("Data", "Data", { unique: false });
	};
	
	var storeToday = function(rtTickets) {
		if((!storeDate || !Configure.datesAreOnSameDay(new Date(storeDate), new Date())) && 
				Configure.isAfterTrading()) {
			var todayStr = Configure.getDateStr(new Date());
			IndexDB.openDB(indexDBName, onupgradeneeded, indexDBver).then((db)=>{
				IndexDB.getDataByKey(db, dataStoreName, todayStr).then((result)=>{
					if(!result) {
						IndexDB.addData(db, dataStoreName, {ID:todayStr , Data:rtTickets});
					}
					IndexDB.closeDB(db);
				});
			});	
			storeDate = new Date();
			LocalStore.set(storeId, storeDate);
		}
	};
	
	var updateRtTicketsToDB = function(rtticketsArray) {
		IndexDB.openDB(indexDBName, onupgradeneeded, indexDBver).then((db)=>{
			rtticketsArray.forEach((d)=>{
				IndexDB.deleteDB(db, dataStoreName, d.ID);
				IndexDB.addData(db, dataStoreName, d);
			});
			IndexDB.closeDB(db);
		});
	};
	
	var getAllRtTicketsFromDB = function() {
		return IndexDB.openDB(indexDBName, onupgradeneeded, indexDBver).then((db)=>{
			var promise = IndexDB.cursorGetData(db, dataStoreName);
			IndexDB.closeDB(db);
			return promise;
		});
	};
	
	var getRtTicketsFromDates = function(startDate, endDate) {
		return IndexDB.openDB(indexDBName, onupgradeneeded, indexDBver).then((db)=>{
			var promise = IndexDB.cursorGetDataByIndexRange(db, dataStoreName, 'ID', startDate, endDate);
			IndexDB.closeDB(db);
			return promise;
		});
	};
	
	var init = function(dateArr){
		return new Promise((resolve, reject) => {
			if(!historyRtTicketsArray || !historyRtTicketsArray.length) {
				window.performance.mark("IndexDB:readAll");
				getRtTicketsFromDates(dateArr[0], dateArr[dateArr.length - 1]).then((list)=>{
					window.performance.mark("IndexDB:readAllDone");
					Configure.Debug('Load db duration:' 
						+ window.performance.measure("IndexDB", "IndexDB:readAll", "IndexDB:readAllDone").duration + 'ms');
					historyRtTicketsArray = list;
					resolve();
				});
			}
		});
	};
	var getHistoryFromDatestr = function(dateStr){
		var historyData = historyRtTicketsArray.find((rt) => {
			return rt['ID'] == dateStr;
		});
		return historyData ? historyData['Data']  : [];
	};
	return {
		init:init,
		updateRtTicketsToDB:updateRtTicketsToDB,
		getAllRtTicketsFromDB:getAllRtTicketsFromDB,
		storeToday:storeToday,
		getHistoryFromDatestr:getHistoryFromDatestr,
	};
})();