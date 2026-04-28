 'use strict';
(function(exports){	
	var storageName = 'rtGaiData';
	var storeVer = 1;
	
	var updateStoreVersion = function(storeData) {
		if(storeData) {
			if(!storeData.version || storeData.version != storeVer){  //should update
				if(storeVer == 1) {
					storeData.version = storeVer;
					storeData.topEchelons = [];
				}
			} 
		} else {                 // 初始化
			storeData = {
				version:storeVer,
				eDate: new Date(),
				topEchelons:[],            // 记录RT_canvas_record_days_num天内的最高ehelon
				echelons:[],				// 记录当天的echelons
				data: [],
			};
			
			for (var i = 0; i < 240; i ++) {
				storeData.data.push({
					index: 0,
					gaiRank:[],
					date: new Date(),
					paramExt:{},
				})
			}
		}
		return storeData;
	};

	let rtGaiData = function () {
		var storeData = LocalStore.get(storageName);
		
		this.gRankData = updateStoreVersion(storeData);
		//如果eDate不是今天并且今天不是周末， 数据清理
		var today = new Date();
		if(!Configure.datesAreOnSameDay(new Date(this.gRankData.eDate), today) && !Configure.isWeekend(today)) {
			this.gRankData.eDate = JSON.stringify(today).replace(/\"/g, '');
			if(this.gRankData.topEchelons.length >= Math.floor(Configure.RT_echelons_max_num/4)) {
				this.gRankData.topEchelons.splice(0,this.gRankData.topEchelons.length - 
						Math.floor(Configure.RT_echelons_max_num/4) + 1);
			}
			var eIdx = this.gRankData.echelons.findIndex((e)=>{
				return Configure.gaiBlackList_verbose.indexOf(e.name) == -1 &&
						Configure.gaiBlackList_verbose.indexOf(e.name.substr(1)) == -1 && 
						this.gRankData.topEchelons.findIndex((topE)=> {
							return topE.name == e.name;
						}) == -1;
			});
			this.gRankData.topEchelons = 
					this.gRankData.topEchelons.concat(this.gRankData.echelons.slice(eIdx,eIdx + 1));
			this.gRankData.echelons = [];
			var start = Configure.RT_data_length / Configure.RT_canvas_record_days_num;
			this.gRankData.data = this.gRankData.data.slice(start, Configure.RT_data_length);
			for(var i = 0; i < start; i ++) {    
				this.gRankData.data.push({
					date: new Date(),
					index: 0,
					gaiRank:[],
					paramExt:{},
				});
			}
		}
	};
	rtGaiData.prototype.getIndexFromDate = function(d = new Date()) {
		var date = d;
		var hour = date.getHours();
		var minute = date.getMinutes();
		var base = Configure.RT_data_length * (Configure.RT_canvas_record_days_num - 1)/ 
							Configure.RT_canvas_record_days_num;
		var offset = Configure.RT_canvas_record_days_num * 240 / Configure.RT_data_length;
		var index = -1;
		if (hour == 9 && minute >= 15) {
			minute >= 30 ? 
				index = (minute - 30) / offset : index = 0;
		} else if(hour == 10) {
			index = (minute + 30) /offset;
		}else if(hour == 11 && minute < 30) {
			index = (minute + 90) /offset;
		}
		else if(hour == 13) {
			index = (minute + 120) /offset;
		}else if(hour == 14) {
			index = (minute + 180) /offset;
		}else {
			index = 240/offset;
		}
		return base + Math.floor(index);
	}
	
	rtGaiData.prototype.getRankData = function() {
		return this.gRankData;
	};
	rtGaiData.prototype.getOriginalDataFromDateStr = function(dateStr) {
		return this.gRankData;
	}
	rtGaiData.prototype.getLastRankData = function() {
		var index = this.getIndexFromDate(new Date(this.gRankData.eDate));
		return this.gRankData.data[index] ? this.gRankData.data[index].gaiRank : [];
	};
	rtGaiData.prototype.getTopEchelons = function() {
		return  this.gRankData.topEchelons.slice();
	};
	rtGaiData.prototype.getEchelons = function() {
		var retEchelons = this.gRankData.topEchelons.slice();
		var sortFunc = (a, b) => {
			return parseFloat(b.score) - parseFloat(a.score);
		}
		this.gRankData.echelons.sort(sortFunc);
		this.gRankData.echelons.forEach((e)=>{
			var fEhelon = retEchelons.find((topE)=>{
				return topE.name == e.name;
			});
			if(!fEhelon) {
				retEchelons.push(e);
			}
		});
		retEchelons.sort(sortFunc);
		return retEchelons;
	};	

	rtGaiData.prototype.setRankDataFromNow = function(dArr, echelonArr, paramExt) {
		var d = new Date();
		var index = this.getIndexFromDate(d);
		var base = Configure.RT_data_length * (Configure.RT_canvas_record_days_num - 1)/ 
							Configure.RT_canvas_record_days_num;
		if(Configure.isBidding()) {   // 竞价阶段的echelons需要清空
			this.gRankData.echelons = [];
		};
		if (index >= base && index < Configure.RT_data_length && !Configure.isWeekend(d)) {
			this.gRankData.eDate = d;
			this.gRankData.data[index].gaiRank = dArr;
			this.gRankData.data[index].date = Configure.getDateStr(d, '/');
			this.gRankData.data[index].paramExt = paramExt;
			this.gRankData.data[index].index = index - base;
			echelonArr.forEach((newE)=>{
				var idx = this.gRankData.echelons.findIndex((e)=>{
					return e.name == newE.name;
				});
				if(idx == -1) {
					this.gRankData.echelons.push(newE);
				} else {
					if(parseFloat(this.gRankData.echelons[idx].score) < parseFloat(newE.score)) {
						this.gRankData.echelons[idx].score = newE.score;
					}
				}
			})
			// 保存到storage避免数据丢失
			if(rtDataManager.checkIfRtDataUpdated()) {
				LocalStore.set(storageName, this.gRankData);
			}
		} else {
			// debug 数据
		/*	for(var i = 4; i < 240; i ++) {
				this.gRankData.data[i].gaiRank = dArr;
			}
			LocalStore.set(storageName, this.gRankData);  */
		}
	};
	
	exports.GaiData = rtGaiData;	
}(window));
