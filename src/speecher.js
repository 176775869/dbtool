var speecher = (function() {
	var storeId = 'speecker';
	var speeckerEL = document.getElementById("speecker");
	var textContainer = []; 
	var showText = function (t) {
		var d = new Date();
		var h = d.getHours();
		var m = d.getMinutes();
		var s = d.getSeconds();
		speeckerEL.innerHTML = (h < 10 ? '0' + h : h) + ':' + 
									(m < 10 ? '0' + m : m) + ':' + 
									(s < 10 ? '0'+ s : s)+ ' ' + t;
		/涨|流入|打开跌停/g.test(t) ? speeckerEL.className = ("speak fontRed") : 
				/跌|流出|炸板/g.test(t) ? speeckerEL.className = ("speak fontGreen") : speeckerEL.className = ("speak fontBlue");
		textContainer.unshift({date: d, txt:speeckerEL.innerHTML});
		if(textContainer.length > 2000) {
			textContainer.pop();
		} 
		LocalStore.set(storeId, textContainer);
		var textshow = '';
		textContainer.forEach((obj)=>{
			textshow += obj.txt + '<br>';
			if(textshow.length > 700) return;
		});
		Tip.show(speeckerEL, textshow);
	};
	var speak = function(text, show = true) {
		if (show) {
			showText(text);
		}
		// 创建一个SpeechSynthesisUtterance对象  
		var utterance = new SpeechSynthesisUtterance();
		// 设置语音合成的语速  
		utterance.rate = 0.8; // 0.5表示正常语速，可以设置为0.1到10之间的值 
		// 设置语音合成的音调  
		utterance.pitch = 2; // 1表示正常音调，可以设置为0到2之间的值  
		// 设置语音合成的音量  
		utterance.volume = 1; // 1表示正常音量，可以设置为0到1之间的值  
		utterance.text = text;  
		window.speechSynthesis.speak(utterance);
	};
	
	var init = function() {
		var txt = Configure.apothegms[Math.round(Math.random() * Configure.apothegms.length)];
		speeckerEL.innerHTML = txt ? txt : Configure.apothegms[0];
		
		textContainer = LocalStore.get(storeId);
		if(textContainer &&  textContainer.length >0) {
			var today = new Date();
			if(!Configure.datesAreOnSameDay(new Date(textContainer[0].date), today) && !Configure.isWeekend(today)) {
				textContainer =  [];
			}
		} else {
			textContainer =  [];
		};
	};
	
	return {
		init:init,
		speak:speak,
	}
})();

speecher.init();