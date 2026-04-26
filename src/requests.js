var requests = (function(){

	/**
	*  数据请求放在后台线程
	*/
	const workerCode = `
	// worker.js
	let interval = 1000; // 默认间隔 1 秒
	let timerId = null;
	var urlH = 'http://23.push2.eastmoney.com/api/qt/clist/get?cb=jQuery112403461296577881501_1600744555568';
	var param = {
		pn:1,
		pz:200,
		po:0,
		np:1,
		ut:'bd1d9ddb04089700cf9c27f6f74262812&invt=2&fid=f12&fs=m:0+t:6,m:0+t:13,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048',
		_:1600744555569,
		fields:'f12,f14,f2,f3,f6,f8,f15,f16,f18,f20,f21,f100,f101,f103,f109,f160,f110,f26',
	};

	var reqPageNumberIndex = 1;
	var pageSize = 100;   // 平台限制最大100
	
	let consecutiveFailures = 0; //失败计数与封禁状态
	const MAX_CONSECUTIVE_FAILURES = 3;
	let isBlocked = false;
	
	function gernerateURL(){
		var url = urlH;
		for(let prop in param) {
			if (prop == 'pn') {
				url += '&' + prop + '=' + reqPageNumberIndex;
			} else if (prop == 'pz') {
				url += '&' + prop + '=' + pageSize;
			} else {
				url += '&' + prop + '=' + param[prop];
			}
		}
		return url;
	}

	// 接收主线程的消息
	self.onmessage = function(e) {
	  const { action, data } = e.data;
	  // 启动/停止定时器
	  if (action === 'start') {
		startTimer(data);
	  } else if (action === 'stop') {
		stopTimer();
	  }
	  // 调整间隔
	  if (action === 'setInterval' && data?.interval) {
		interval = data.interval;
		restartTimer();
	  }
	  if (action === 'resume') {
		if (isBlocked) {
			console.log('[Worker] 收到恢复指令，重置封禁状态，继续请求');
			isBlocked = false;
			consecutiveFailures = 0;
			// 注意：不重置页码，从当前页继续
			startTimer({ interval: interval, pageSize: pageSize });
		}
	  }
	};

	// 启动定时器
	function startTimer(data) {
	  if (data && data.interval) interval = data.interval;
	  if (data && data.pageSize) pageSize = data.pageSize;
	  // 可选：是否重置页码（由外部传入，但这里保持原有逻辑：只有首次启动才重置）
	  // 为了兼容原逻辑，不在此处重置页码。
	  stopTimer(); // 确保先清除旧定时器
	  timerId = setInterval(() => {
		fetchData();
	  }, interval);
	}

	// 停止定时器
	function stopTimer() {
	  if (timerId) {
		clearInterval(timerId);
		timerId = null;
	  }
	}

	// 重启定时器
	function restartTimer() {
	  stopTimer();
	  startTimer();
	}

	// 发送请求
	function fetchData() {
	  // === 新增：封禁中则不发起请求 ===
	  if (isBlocked) {
		console.log('[Worker] 当前处于封禁暂停，等待恢复指令...');
		return;
	  }
	  
	  let url = gernerateURL();
	  console.log('[Worker] Fetch pagenum ' + reqPageNumberIndex +' pageSize ' + pageSize + ' -> ' + url);
	  fetch(url)
		.then(response => {
		  if (!response.ok) throw new Error('请求失败');
		  return response.text();
		})
		.then(data => {
			// === 请求成功，重置失败计数 ===
			consecutiveFailures = 0;
			
			var s = data.indexOf('(') + 1; 
			var json_str = data.substr(s, data.length - s - 2);
			if(JSON.parse(json_str)['data'] != null) {
			   var retObj = {data:json_str, reqPageNumberIndex:reqPageNumberIndex, pageSize:pageSize};
			   self.postMessage({ type: 'data', data: JSON.stringify(retObj)});
			   reqPageNumberIndex++;
		   } else {
			   reqPageNumberIndex = 1;
		   }
		})
		.catch(error => {
		  consecutiveFailures++;
		  console.error('[Worker] 请求失败 (连续失败 ' + consecutiveFailures + '/' + MAX_CONSECUTIVE_FAILURES + '):', error.message);
		  
		  if (consecutiveFailures >= MAX_CONSECUTIVE_FAILURES) {
			// 达到阈值，判定为IP被封，停止定时器，通知主线程
			console.error('[Worker] 检测到IP封禁，暂停请求');
			isBlocked = true;
			stopTimer();
			self.postMessage({ type: 'ipBlocked' });
		  }
		});
	}
	`;
	
	var worker;
	var startWorker = function(callback) {
		if (window.Worker) {
			var reqNum = 0;
			const blob = new Blob([workerCode], { type: 'application/javascript' });
			worker = new Worker(URL.createObjectURL(blob));

			// 监听 Worker 消息
			worker.onmessage = function(e) {
				const { type, data, error } = e.data;
				var suspendRequest = function() {
					if(Configure.Request_suspend_duration > 0) {
						Configure.Debug('Request suspend ' +  Configure.Request_suspend_duration + 's.');
						worker.postMessage({ action: 'stop', data: {}});
						setTimeout(()=>{
							worker.postMessage({ action: 'setInterval', data: { interval: Configure.Request_interval} });
						}, Configure.Request_suspend_duration);
					};
				};
			  if (type === 'data') {
				var resObj = JSON.parse(data);
				const json_str = resObj.data;
				const reqPageNumberIndex = resObj.reqPageNumberIndex;
				const pageSize = resObj.pageSize;
				Configure.Debug('Request Page number ' + reqPageNumberIndex);
				Configure.Debug(JSON.parse(json_str));
				var maxTicketNum = parseInt(JSON.parse(json_str)['data']['total']);
				var maxPage = Math.ceil(maxTicketNum / pageSize);
				rtDataManager.setRTTickets(JSON.parse(json_str)['data']['diff'], 
											maxTicketNum, reqPageNumberIndex, maxPage, pageSize);
				if (reqPageNumberIndex >= maxPage) {
					if(typeof callback === 'function') {
						callback();
					};
					suspendRequest();
				} 
				Configure.Debug('Debug --- request num = ' + reqNum++ );
				} else if (type === 'ipBlocked') {
				console.warn('IP 已被限制，暂停请求');
				speecher.speak('IP 已被限制，请更换 IP 后点击确定', false);
				if (confirm('IP 已被限制，是否已更换 IP？\n点击“确定”继续请求，点击“取消”保持暂停。')) {
					if (worker) {
						worker.postMessage({ action: 'resume' });
					}
				} else {
					console.log('用户取消恢复，保持暂停');
				}
			  }
			};
			worker.postMessage({ action: 'start', data: { interval: Configure.Request_interval, 
														pageSize:Configure.Request_pagesize} });
		 } else {
			console.error('浏览器不支持 Web Workers!');
		 }
	}
	
	var stopWorker = function() {
		if (worker) {
			worker.postMessage({ action: 'stop' });
			worker.terminate(); // 强制终止 Worker
		}
	}

	return {
		start:startWorker,
		stop:stopWorker,
	}
})();