var startup = (function(text) {
	var startTime;   // 记录启动时间 优化

	var displayAI = function (recommend) {
		var oDiv = document.getElementById("AI");
		//remove child
		while(oDiv.hasChildNodes()) {
			oDiv.removeChild(oDiv.lastChild);
		};
		
		oDiv.style.color = oDiv.style.borderColor  = recommend.color;
        var oStrong = document.createElement("div");
        var oTxt = document.createTextNode(recommend.txt);
		Tip.show(oDiv, recommend.tatics);
		oDiv.addEventListener('click', function(event){
			Configure.Debug('click');
			speecher.speak(recommend.tatics, false);
		});
		
		oStrong.appendChild(oTxt);
		oDiv.appendChild(oStrong);
	};
	
	var getParamEchelons = function() {
		var fr2 = document.getElementById('form2');
		var paramEchelons = [];
		if (fr2.gainian && fr2.gainian.length > 1) {
			Array.from(fr2.gainian).forEach((input)=> {
				if(input.checked) {
					paramEchelons = paramEchelons.concat(input.dataset.titleName);
				} 
			});
		} else if(fr2.gainian){
			if(fr2.gainian.checked) {
				paramEchelons = paramEchelons.concat(fr2.gainian.dataset.titleName);
			} 
		}
		return paramEchelons;
	};
	
	var drawCanvasLeft = function() {
		canvas.draw(getParamEchelons(), document.getElementById('indecator').value, 
				document.getElementById('showdays').value);
	};
	
	
	var highlightTichets;
	var drawCanvasRight = function(){
		var elCanvas = document.getElementById("drawing");
		var rtCanvasFactor = 0;
		// RT canvas
		if(Configure.getMode() == Configure.modeType.DP) {
			rtCanvasFactor = Configure.WinRTfactor;
			var rect = {x: elCanvas.width * Configure.WinXFactor  + 30, y:0,
						width: elCanvas.width * rtCanvasFactor - 30, height:elCanvas.height};
			canvasRT.draw(elCanvas, rect, getParamEchelons(), document.getElementById('rtShowdays').value);
		} 
				
		// 梯队
		var dateArr = workbook.getDateArr((a,b)=>{
				return b - a;
			});
		var echelonNames = getParamEchelons();
		var type = document.getElementById('form1').gtype[1].checked ? 
							1 : 0;   // type = 0 画连扳， 1画趋势 
							
		var echelons = echelonNames.length ?  
						[(parser.getCombinedEchelon(dateArr[0], echelonNames))] : [];
		echelons = echelons.concat([(parser.getCombinedEchelon(dateArr[0]))]);
		echelons = echelons.concat(parser.getEchelons(dateArr[0]));
		for (var i = 0; i < Configure.Echelons_Draw_NUM; i ++) {
			var rect = {x: elCanvas.width * (Configure.WinXFactor + rtCanvasFactor) +
								i * elCanvas.width * (1-Configure.WinXFactor)/Configure.Echelons_Draw_NUM, 
							y:0,
							width:elCanvas.width * (1-Configure.WinXFactor-rtCanvasFactor)/
															Configure.Echelons_Draw_NUM,
							height:elCanvas.height};
			let e1;
			if(type == 0) {
				e1 = new window.Echelon(elCanvas, echelons[i], rect);      //连板
			} else {  // type = 1
				e1 = new window.bandEchelon(elCanvas, echelons[i], rect);   // 趋势，首板断板
			}
			e1.draw();
			
			if (i == 0) {
				highlightTichets = e1.getTickets();     // 记录需要highlight的票
			}
			if (workbook.getBandTickets().length == 0) {
				// 初始化一下趋势数据 AI需要使用
				new window.bandEchelon(elCanvas, echelons[i], rect);   
			}
		}	
	};
	
	var fillTicketsTable = function() {
		var d = $('#date')[0].value.replace(/\-/g, '');	
		
		var fr = document.getElementById('form1');
		var fr2 = document.getElementById('form2');
		var fr3 = document.getElementById('form3');
		
		var paramGainian = [];
		var paramGainianForOther = [];
		if (fr2.gainian && fr2.gainian.length > 1) {
			Array.from(fr2.gainian).forEach((input)=> {
				if(input.checked) {
					paramGainian =paramGainian.concat(input.dataset.titleProp.split(','));
				} else {
					paramGainianForOther= paramGainianForOther.concat(input.dataset.titleProp.split(','));
				}
			});
		} else if(fr2.gainian){
			if (fr2.gainian.checked) {
				paramGainian =paramGainian.concat(fr2.gainian.dataset.titleProp.split(','));
			} else {
				paramGainianForOther= paramGainianForOther.concat(fr2.gainian.dataset.titleProp.split(','));
			}
		}

	//	var gainian = fr.gainian;
		var isOther = fr2.all[1].checked;  // other 选项
		var param = {
			hotpointArr: isOther ? paramGainianForOther : paramGainian,
			type: fr.gtype[2].checked ? 2 : 
				fr.gtype[0].checked ? 0 : 1,   
			sort: fr.sort[2].checked ? 2 :
				fr.sort[0].checked ? 0 : 1,
			other: fr2.all[1].checked,
			sector:(fr3.sector[0].checked << 0) | (fr3.sector[1].checked << 1) | (fr3.sector[2].checked << 2)
		};
		table.createTable(d, param, highlightTichets);
	};
	
	var init = function() {
		var dateArr = workbook.getDateArr(()=>{}, '-');
		$('#date').val(dateArr[dateArr.length - 1]);
		document.getElementById('date').min = dateArr[0];
	//	document.getElementById('date').max = dateArr[dateArr.length - 1];
		document.getElementById('mode').disabled = true;
		if(Configure.getMode() == Configure.modeType.DP) {
			document.getElementById('pre').disabled = true;
			document.getElementById('date').disabled = true;
			document.getElementById('next').disabled = true;
			document.getElementById('last').disabled = true;
			document.getElementById('excel-file').disabled = true;
			document.getElementById('showdays').disabled = true;
		}
		parser.loadConfFromExl();  // 加载题材配置
		AI.init();
		dragons.init();
		Configure.Debug("rtDataManager.init: " + (window.performance.now() - startTime) + "ms");
		return rtDataManager.init(workbook.getDateArr(()=>{}));   // 读数据库，异步
	};
	
	var startRequests = function() {
		if(Configure.getMode() == Configure.modeType.DP) {
			requests.stop();
			requests.start(()=>{
				parserRT.parseAndStoreRTData();
				table.updateRow();
				if (document.getElementById('showdays').value < 120 ) { //canvas显示大于等于120天时不显示right
					canvasRT.reDraw(getParamEchelons(), document.getElementById('rtShowdays').value);
				}
			});
			Timer.start(Configure.Request_interval);
			// 初始化精灵
			rtSpirit.init();
		}
	}; 
	
	var addEvent = function() {
		var formUpdate = function() {
			// canvas update
			drawCanvasLeft();
			
			if (document.getElementById('showdays').value < 120 ) { //canvas显示大于等于120天时不显示right
				drawCanvasRight();
			}
			
			// table update
			fillTicketsTable();
			
			AI.drawEmotionCycle();
		};
		
		var showDaysUpdate = function() {
			if (document.getElementById('showdays').value >= 120 ) {  // canvas显示大于等于120天时resize宽度
				canvas.resize(document.getElementById("drawing"), 1);
				drawCanvasLeft();
			} else {
				canvas.resize(document.getElementById("drawing"), Configure.WinXFactor);
				formUpdate();
			}
		};		
		$('#form1').change(formUpdate);
		$('#form2').change(formUpdate);
		$('#form3').change(formUpdate);
		$('#indecator').change(formUpdate);
		$('#showdays').change(showDaysUpdate);
		$('#rtShowdays').change(()=>{
			canvasRT.reDraw(getParamEchelons(), document.getElementById('rtShowdays').value);
		});
		
		var dateChange = function(e) {
			Configure.date = new Date($('#date')[0].value);
	//		if (document.getElementById('showdays').value < 120 ) {  // canvas显示大于等于120天时不reload
				canvas.reload();
	//		}
			table.updateForm();
			formUpdate();
			displayAI(AI.getRecommend());
		}
		
		var dateOnclick = function(e) {
			var dateStr = $('#date')[0].value.replace(/\-/g, '');
			var retDatestr = e.currentTarget.id ==  'last' ? workbook.getLastDate('-') :
								e.currentTarget.id == 'next' ? workbook.getNextDate(dateStr, '-') : 
																workbook.getPreDate(dateStr, '-');
			$('#date').val(retDatestr);
			dateChange();
		};
		var nextOption = function(elementID, reverse = false) {  
			var selectElement = document.getElementById(elementID);  
			var currentIndex = selectElement.selectedIndex;  
			var optionsCount = selectElement.options.length;  
			if (reverse) {
				if (currentIndex > 0) {  
					selectElement.selectedIndex = currentIndex - 1;  
				} else {  
					selectElement.selectedIndex = optionsCount - 1;
				} 
			} else {
				if (currentIndex < optionsCount - 1) {  
					selectElement.selectedIndex = currentIndex + 1;  
				} else {  
					selectElement.selectedIndex = 0;
				} 
			}
			 
			var event = new Event('change', { bubbles: true });  
			selectElement.dispatchEvent(event);  
		};
		
		var keyBoardEvent = function(event) {
			Configure.Debug('Keydown:', event.key);  
			switch(event.key) {
				case '1':
				case '2':
				case '3':
					document.getElementById('form1').gtype[event.key - 1].click();
					break;
				case 's': 
					document.getElementById('form1').sort[0].click();
					break;
				case 'h': 
					document.getElementById('form1').sort[1].click();
					break;
				case 'r': 
					document.getElementById('form1').sort[2].click();
					break;
				case 'ArrowDown': 
					nextOption('rtShowdays');
					event.stopPropagation(); 
					event.preventDefault();
					break;
				case 'ArrowUp': 
					nextOption('rtShowdays', true);
					event.stopPropagation(); 
					event.preventDefault();
					break;
				case 'ArrowRight': 
					document.getElementById('next').click();
					event.stopPropagation(); 
					event.preventDefault();
					break;
				case 'ArrowLeft': 
					document.getElementById('pre').click();
					event.stopPropagation(); 
					event.preventDefault();
					break;
				case 'Escape': 
					document.getElementById('last').click();
					break;
				case 'Enter': 
					nextOption('indecator');
					event.stopPropagation(); 
					event.preventDefault();
					break;
				case 'Tab': 
					nextOption('showdays');
					event.stopPropagation(); 
					event.preventDefault();
					break;
				case 'F1': 
					document.getElementById('cailianshe').click();
					event.stopPropagation(); 
					event.preventDefault();
					break;
				case 'F2': 
					document.getElementById('jiuyan').click();
					event.stopPropagation(); 
					event.preventDefault();
					break;
				case 'F3': 
					document.getElementById('taogu').click();
					event.stopPropagation(); 
					event.preventDefault();
					break;
			}
		}
		
		$('#date').change(dateChange);
		$('#pre').click(dateOnclick);
		$('#next').click(dateOnclick);
		$('#last').click(dateOnclick);
		
		document.addEventListener('keydown', keyBoardEvent);
		
		// link
		$('#jiuyan').click((e)=>{
			e.preventDefault();  
			var url = "https://www.jiuyangongshe.com/action/" + Configure.getDateStr(Configure.date, '-');
			window.open(url);
		});
	};
	
	var loadExcelDone = function(data) {
		window.performance.mark("XLSX:read");
		try {
			workbook.Book(XLSX.read(data, {
				type: 'binary'
			})); // 以二进制流方式读取得到整份excel表格对象
		} catch (e) {
			Configure.Debug('文件类型不正确');
			return;
		}
		window.performance.mark("XLSX:readDone");
				Configure.Debug('XLSX read data duration:' 
					+ window.performance.measure("XLSX", "XLSX:read", "XLSX:readDone").duration + 'ms');
		Configure.Debug("Startup:init " + (window.performance.now() - startTime) + "ms");
		init().then(()=>{							
			Configure.Debug("Draw canvas: " + (window.performance.now() - startTime) + "ms");
			const c = document.getElementById('drawing');
			const ctx = c.getContext('2d');
			ctx.clearRect(0, 0, c.width, c.height);
			
			table.updateForm();
			canvas.init(document.getElementById("drawing"), Configure.WinXFactor);
		
			drawCanvasLeft();
			drawCanvasRight();
			fillTicketsTable();
			Configure.Debug("Draw canvas done: " + (window.performance.now() - startTime) + "ms");
			displayAI(AI.getRecommend());
			AI.drawEmotionCycle();
			
			addEvent();
					
			//start requests
			startRequests();
			Configure.Debug("Init done: " + (window.performance.now() - startTime) + "ms");
			document.querySelector('.loader-container').style.display = 'none';
			updateTitle(Configure.getMode() == 0 ? 'fp' : 'dp');
		});
	};

    $('#excel-file').change(function(e) {
		startTime = window.performance.now();  
		document.querySelector('.loader-container').style.display = 'block';
        var files = e.target.files;
		Array.from(files).forEach((file, index)=>{
			var fileReader = new FileReader();
			fileReader.file = file;
			fileReader.index = index;
			fileReader.onload = function(ev) {
				
				var data = ev.target.result
				if(ev.target.file.type == 'application/json') {
					Downloader.upload(data, ev.target.index);   // 恢复数据库
				} else {
					if(ev.target.index == 0) {  // excel只加载第一个
						var name =ev.target.file.name;
						updateTitle(name.slice(name.indexOf('20'), name.indexOf('20') + 4));
						loadExcelDone(data);   
					}
				}
			};
			// 以二进制方式打开文件
			fileReader.readAsBinaryString(file);
		})
    });
	
	var updateTitle = function(str) {
		document.title = document.title + '.' +  str;
	};
	var start = function() {
		window.performance.mark("startup:start");
		
		// 停止 Worker（页面卸载时清理）
		window.addEventListener('beforeunload', () => {
			requests.stop();
		});
		
		window.onload = function(){
			updateTitle(Configure.version);
			$('#date').val(Configure.getDateStr(Configure.date, '-'));
			$('#rtShowdays').val(Configure.RT_canvas_show_days_num/2);

			var fp = function() {
				document.getElementById('form1').gtype[0].checked = true;
				document.getElementById('form1').sort[2].checked = true;
				document.getElementById('showdays').value = 60;
				document.getElementById('rtShowdays').hidden = true;
			};
			var dp = function() {
				document.getElementById('form1').gtype[2].checked = true;
				document.getElementById('form1').sort[0].checked = true;
				document.getElementById('showdays').value = 30;
				document.getElementById('rtShowdays').hidden = false;
			};
			
			var updateIndicator = function() {
				var indecator = document.getElementById('indecator');
				var options = indecator.getElementsByTagName("option");
				for(var i = 0; i < options.length; i++) {
					indecator.removeChild(options[i]);
					i--;
				}
				for(var i = 0; i < Configure.selectIndicators.length; i++) {
					var option1 = document.createElement("option");
					var text1 = document.createTextNode(Configure.selectIndicators[i].name);
					option1.appendChild(text1);
					indecator.appendChild(option1);
				}
			};
			if(Configure.isAfterTrading() || Configure.isWeekend()){
				fp()
			} else {
				dp();
			}
			Configure.setMode($('#mode')[0].value);
			$('#mode').change((e)=>{
				Configure.setMode($('#mode')[0].value);
				Configure.getMode() == Configure.modeType.DP ? dp() : fp();
				updateIndicator();
			});

			const canvas = document.getElementById('drawing');
			canvas.width = window.innerWidth;
			const ctx = canvas.getContext('2d');
			const img = new Image();
			img.src = 'img/情绪周期.png';
			img.onload = function() {
				var w = img.width  * canvas.height/img.height, 
					h = canvas.height;
				ctx.drawImage(img, (canvas.width - w)/2, 0, w, h);
			};
			
			updateIndicator();
			
			// 当月备份上一个月的数据
			function getLastMonth() {
				var date = new Date();
				var year = date.getFullYear();   //当前年：四位数字
				var month = date.getMonth();     //当前月：0-11
				if (month == 0) {   //如果是0，则说明是1月份，上一个月就是去年的12月
					year -= 1;
					month = 12;
				}
				month = month < 10 ? ('0' + month) : month;   //月份格式化：月份小于10则追加个0
				let lastYearMonth = '' + year + month;
				return lastYearMonth;
			};
			var backUpMonth = getLastMonth();
			Downloader.download('备份数据' + backUpMonth + '.backup', backUpMonth);
			window.performance.mark("startup:start done");
				Configure.Debug('startup:start duration:' 
					+ window.performance.measure("startup", "startup:start", "startup:start done").duration + 'ms');
		};
	};
	
	return {
		start:start,
	}
})();

startup.start();