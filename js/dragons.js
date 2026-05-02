
var dragons = (function() {
	var dragons;
	
	var title = {
		name: '名称',
		secBPrice: '二板价格',
		tickitsNumber:'流通股本',
		orgProportion:'机构持股占流通股比例%',
	//	realCirculateValue:'二板实际流通市值', 	  
		profitProportion:'二板筹码获利%' 
	};
	
	var dragon = {};
	
	var init = function () {
		dragons = workbook.getSheet('连扳龙头');
		dragon = getAverageValue();
	};
	
	var average = function(arr){
		var num = parseInt(arr.length / 7);
		arr.sort((a, b)=> {
			return b - a;
		});
		var retArr = arr.slice(num, arr.length - num);
		var sum = 0;
		retArr.forEach((r)=>{
			sum += r;
		})
		
		return sum/retArr.length;
	};
	
	var getAverageValue = function() {
		var priceArr = [];
		var realCirculateValueArr = [];
		var profitProportionArr = [];
		dragons.forEach((d)=>{
			priceArr.push(parseFloat(d[title.secBPrice]));
			realCirculateValueArr.push(parseInt(d[title.secBPrice]* d[title.tickitsNumber] * 
						(100 - d[title.orgProportion])/100));
			profitProportionArr.push(parseFloat(d[title.profitProportion]));
		});
		
		return {
			price: average(priceArr),
			realCirculateValue: average(realCirculateValueArr),
			profitProportion: average(profitProportionArr)
		}
	} ;
	
	var getDragonStandard = function(boardNum, code) {
		var f = Configure.isKechuangTicket(code) ? 1.2 : 1.1;
		return {
			price : parseFloat(dragon.price * Math.pow(f, boardNum -2)).toFixed(2),
			realCirculateValue : parseInt(dragon.realCirculateValue * Math.pow(f, boardNum -2)),
			profitProportion : parseInt(dragon.profitProportion)
		}
	};
	
	return {
		init : init,
		getDragonStandard : getDragonStandard
	}
})();