var Timer = (function(){
	var timerId;
	
	var callbackArray = [];
	var start = function(timerDuration = 1000) {
		timerId = setInterval(function () {
			callbackArray.forEach((f) => {
				f();
			});
		}, timerDuration)
	};
	
	var addTimerCallback = function(callback) {
		callbackArray.push(callback);
	};
	
	var stop = function() {
		callbackArray = [];
		clearInterval(timerId);
	};
	
	return {
		start:start,
		stop:stop,
		addTimerCallback:addTimerCallback,
	}
})();