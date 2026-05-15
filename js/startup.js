var startup = (function(text) {
	var startTime;
	var isOnline = window.location.protocol !== 'file:';   // 新增

	var displayAI = function (recommend) {
		var oDiv = document.getElementById("AI");
		while(oDiv.hasChildNodes()) {
			oDiv.removeChild(oDiv.lastChild);
		}
		oDiv.style.color = oDiv.style.borderColor = recommend.color;
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

	var drawCanvasRight = function(){
		var elCanvas = document.getElementById("drawing");
		var rtCanvasFactor = 0;
		if(Configure.getMode() == Configure.modeType.DP) {
			rtCanvasFactor = Configure.WinRTfactor;
			var rect = {x: elCanvas.width * Configure.WinXFactor + 30, y:0,
						width: elCanvas.width * rtCanvasFactor - 30, height:elCanvas.height};
			canvasRT.draw(elCanvas, rect, getParamEchelons(), document.getElementById('rtShowdays').value);
		}

		var dateArr = workbook.getDateArr((a,b)=> b - a);
		var echelonNames = getParamEchelons();
		var type = document.getElementById('form1').gtype[1].checked ? 1 : 0;
		var echelons = echelonNames.length ?
						[(parser.getCombinedEchelon(dateArr[0], echelonNames))] : [];
		echelons = echelons.concat([(parser.getCombinedEchelon(dateArr[0]))]);
		echelons = echelons.concat(parser.getEchelons(dateArr[0]));
		for (var i = 0; i < Configure.Echelons_Draw_NUM; i++) {
			var rect = {x: elCanvas.width * (Configure.WinXFactor + rtCanvasFactor) +
								i * elCanvas.width * (1-Configure.WinXFactor)/Configure.Echelons_Draw_NUM,
							y:0,
							width:elCanvas.width * (1-Configure.WinXFactor-rtCanvasFactor)/Configure.Echelons_Draw_NUM,
							height:elCanvas.height};
			let e1;
			if(type == 0) {
				e1 = new window.Echelon(elCanvas, echelons[i], rect);
			} else {
				e1 = new window.bandEchelon(elCanvas, echelons[i], rect);
			}
			e1.draw();
			if (workbook.getBandTickets().length == 0) {
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
					paramGainian = paramGainian.concat(input.dataset.titleProp.split(','));
				} else {
					paramGainianForOther = paramGainianForOther.concat(input.dataset.titleProp.split(','));
				}
			});
		} else if(fr2.gainian){
			if (fr2.gainian.checked) {
				paramGainian = paramGainian.concat(fr2.gainian.dataset.titleProp.split(','));
			} else {
				paramGainianForOther = paramGainianForOther.concat(fr2.gainian.dataset.titleProp.split(','));
			}
		}
		var isOther = fr2.all[1].checked;
		var param = {
			hotpointArr: isOther ? paramGainianForOther : paramGainian,
			type: fr.gtype[2].checked ? 2 : fr.gtype[0].checked ? 0 : 1,
			sort: fr.sort[2].checked ? 2 : fr.sort[0].checked ? 0 : 1,
			other: fr2.all[1].checked,
			sector:(fr3.sector[0].checked << 0) | (fr3.sector[1].checked << 1) | (fr3.sector[2].checked << 2)
		};
		table.createTable(d, param);
	};

	var init = function() {
		var dateArr = workbook.getDateArr(()=> {}, '-');
		$('#date').val(dateArr[dateArr.length - 1]);
		document.getElementById('date').min = dateArr[0];
		document.getElementById('mode').disabled = true;
		if(Configure.getMode() == Configure.modeType.DP) {
			document.getElementById('pre').disabled = true;
			document.getElementById('date').disabled = true;
			document.getElementById('next').disabled = true;
			document.getElementById('last').disabled = true;
			document.getElementById('excel-file').disabled = true;
			document.getElementById('showdays').disabled = true;
		}
		parser.loadConfFromExl();
		AI.init();
		dragons.init();
		Configure.Debug("rtDataManager.init: " + (window.performance.now() - startTime) + "ms");
		return rtDataManager.init(workbook.getDateArr(()=>{}));
	};

	var startRequests = function() {
		if(Configure.getMode() == Configure.modeType.DP) {
			requests.stop();
			requests.start(()=>{
				parserRT.parseAndStoreRTData();
				table.updateRow();
				if (document.getElementById('showdays').value < 120) {
					canvasRT.reDraw(getParamEchelons(), document.getElementById('rtShowdays').value);
				}
			});
			Timer.start(Configure.Request_interval);
			rtSpirit.init();
		}
	};

	var addEvent = function() {
		var formUpdate = function() {
			drawCanvasLeft();
			if (document.getElementById('showdays').value < 120) {
				drawCanvasRight();
			}
			fillTicketsTable();
			AI.drawEmotionCycle();
		};

		var showDaysUpdate = function() {
			if (document.getElementById('showdays').value >= 120) {
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
			canvas.reload();
			table.updateForm();
			formUpdate();
			displayAI(AI.getRecommend());
		}

		var dateOnclick = function(e) {
			var dateStr = $('#date')[0].value.replace(/\-/g, '');
			var retDatestr = e.currentTarget.id == 'last' ? workbook.getLastDate('-') :
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

		EventManager.register('1', function() { document.getElementById('form1').gtype[0].click(); });
		EventManager.register('2', function() { document.getElementById('form1').gtype[1].click(); });
		EventManager.register('3', function() { document.getElementById('form1').gtype[2].click(); });
		EventManager.register('s', function() { document.getElementById('form1').sort[0].click(); });
		EventManager.register('h', function() { document.getElementById('form1').sort[1].click(); });
		EventManager.register('r', function() { document.getElementById('form1').sort[2].click(); });
		EventManager.register('ArrowDown', function() { nextOption('rtShowdays'); });
		EventManager.register('ArrowUp', function() { nextOption('rtShowdays', true); });
		EventManager.register('ArrowRight', function() { document.getElementById('next').click(); });
		EventManager.register('ArrowLeft', function() { document.getElementById('pre').click(); });
		EventManager.register('Escape', function() { document.getElementById('last').click(); });
		EventManager.register('Enter', function() { nextOption('indecator'); });
		EventManager.register('Tab', function() { nextOption('showdays'); });
		EventManager.register('F1', function(e) { document.getElementById('cailianshe').click(); e.preventDefault(); });
		EventManager.register('F2', function(e) { document.getElementById('jiuyan').click(); e.preventDefault(); });
		EventManager.register('F3', function(e) { document.getElementById('taogu').click(); e.preventDefault(); });
		EventManager.register('F4', function(e) { document.getElementById('wb-toggle-btn').click(); e.preventDefault(); });

		$('#date').change(dateChange);
		$('#pre').click(dateOnclick);
		$('#next').click(dateOnclick);
		$('#last').click(dateOnclick);
		$('#jiuyan').click((e)=>{
			e.preventDefault();
			var url = "https://www.jiuyangongshe.com/action/" + Configure.getDateStr(Configure.date, '-');
			window.open(url);
		});
	};

	var loadExcelDone = function(data) {
		window.performance.mark("XLSX:read");
		try {
			workbook.Book(XLSX.read(data, { type: 'binary' }));
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
			startRequests();
			Configure.Debug("Init done: " + (window.performance.now() - startTime) + "ms");
			document.querySelector('.loader-container').style.display = 'none';
			updateTitle(Configure.getMode() == 0 ? 'fp' : 'dp');

			// 在线模式下，表格和表单初始隐藏，Excel加载后显示
			if (isOnline) {
				$('#tbl, #form1, #form2, #form3').show();
			}
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
					Downloader.upload(data, ev.target.index);
				} else {
					if(ev.target.index == 0) {
						var name = ev.target.file.name;
						updateTitle(name.slice(name.indexOf('20'), name.indexOf('20') + 4));
						loadExcelDone(data);
					}
				}
			};
			fileReader.readAsBinaryString(file);
		})
    });

	var updateTitle = function(str) {
		document.title = document.title + '.' + str;
	};

	var start = function() {
		window.performance.mark("startup:start");
		window.addEventListener('beforeunload', () => {
			requests.stop();
		});

		window.onload = function(){
			// 在线模式自动从服务端加载 Excel 文件
			if (isOnline) {
				console.log('[WORKBOOK] 在线模式，开始自动加载 Excel...');
				document.querySelector('.loader-container').style.display = 'block';
				fetch('/api/workbook')
					.then(function(resp) {
						console.log('[WORKBOOK] 收到响应, status:', resp.status, 'content-length:', resp.headers.get('content-length'));
						if (!resp.ok) throw new Error('HTTP ' + resp.status);
						return resp.arrayBuffer();
					})
					.then(function(buffer) {
						console.log('[WORKBOOK] buffer 大小:', buffer.byteLength, '字节');
						startTime = window.performance.now();
						var data = new Uint8Array(buffer);
						var arr = [];
						for (var i = 0; i < data.length; i++) {
							arr.push(String.fromCharCode(data[i]));
						}
						var binaryStr = arr.join('');
						console.log('[WORKBOOK] 转二进制字符串长度:', binaryStr.length);
						console.log('[WORKBOOK] 前20字符:', binaryStr.substring(0, 20));
						updateTitle('auto');
						loadExcelDone(binaryStr);
					})
					.catch(function(err) {
						console.log('[WORKBOOK] 自动加载失败:', err.message);
						document.querySelector('.loader-container').style.display = 'none';
					});
			}
			updateTitle(Configure.version);
			$('#date').val(Configure.getDateStr(Configure.date, '-'));
			$('#rtShowdays').val(Configure.RT_canvas_show_days_num/2);

			// 在线模式：初始隐藏表格和表单，等待Excel加载后显示
			if (isOnline) {
				$('#tbl, #form1, #form2, #form3').hide();
                var excelInput = document.getElementById('excel-file');
                if (excelInput) {
                    excelInput.disabled = true;
                    excelInput.title = '在线模式，文件自动加载';
                }
			}
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
			Configure.setMode(mobile.isMobilePortrait() ? Configure.modeType.MP : $('#mode')[0].value);
			$('#mode').change((e)=>{
				Configure.setMode(mobile.isMobilePortrait() ? Configure.modeType.MP : $('#mode')[0].value);
				updateIndicator();
			});

			const canvas = document.getElementById('drawing');
			canvas.width = window.innerWidth;
			const ctx = canvas.getContext('2d');
			const img = new Image();
			img.src = 'js/img/情绪周期.png';
			img.onload = function() {
				var w = img.width * canvas.height/img.height,
					h = canvas.height;
				ctx.drawImage(img, (canvas.width - w)/2, 0, w, h);
			};

			updateIndicator();

			function getLastMonth() {
				var date = new Date();
				var year = date.getFullYear();
				var month = date.getMonth();
				if (month == 0) {
					year -= 1;
					month = 12;
				}
				month = month < 10 ? ('0' + month) : month;
				return '' + year + month;
			};
			var backUpMonth = getLastMonth();
			Downloader.download('备份数据' + backUpMonth + '.backup', backUpMonth);
			window.performance.mark("startup:start done");
			Configure.Debug('startup:start duration:'
				+ window.performance.measure("startup", "startup:start", "startup:start done").duration + 'ms');
		};
	};

	return { start:start };
})();

startup.start();