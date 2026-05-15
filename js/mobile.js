

var mobile = (function(){
	function init() {
		if(isMobilePortrait()) {
			Configure.WinXFactor = 1;
		}
	}
	
	function isPortrait() {
		return window.innerHeight > window.innerWidth;
	}
	
	function isMobilePortrait() {
	  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) && 
				isPortrait();
	}
	
	return {
		init:init,
		isMobilePortrait:isMobilePortrait,
	}
})();

mobile.init();