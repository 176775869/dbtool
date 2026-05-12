

var mobile = (function(){
	function init() {
		if(isMobile()) {
			Configure.WinXFactor = 1;
		}
	}
	
	function isMobile() {
	  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
	}
	
	return {
		init:init,
		isMobile:isMobile,
	}
})();

mobile.init();