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

	var highlightTichets;
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
			if (i == 0) {
				highlightTichets = e1.getTickets();
			}
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
		table.createTable(d, param, highlightTichets);
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

		var keyBoardEvent = function(event) {
			Configure.Debug('Keydown:', event.key);
			switch(event.key) {
				case '1': case '2': case '3':
					document.getElementById('form1').gtype[event.key - 1].click(); break;
				case 's': document.getElementById('form1').sort[0].click(); break;
				case 'h': document.getElementById('form1').sort[1].click(); break;
				case 'r': document.getElementById('form1').sort[2].click(); break;
				case 'ArrowDown': nextOption('rtShowdays'); event.preventDefault(); break;
				case 'ArrowUp': nextOption('rtShowdays', true); event.preventDefault(); break;
				case 'ArrowRight': document.getElementById('next').click(); event.preventDefault(); break;
				case 'ArrowLeft': document.getElementById('pre').click(); event.preventDefault(); break;
				case 'Escape': document.getElementById('last').click(); break;
				case 'Enter': nextOption('indecator'); event.preventDefault(); break;
				case 'Tab': nextOption('showdays'); event.preventDefault(); break;
				case 'F1': document.getElementById('cailianshe').click(); event.preventDefault(); break;
				case 'F2': document.getElementById('jiuyan').click(); event.preventDefault(); break;
				case 'F3': document.getElementById('taogu').click(); event.preventDefault(); break;
			}
		}

		$('#date').change(dateChange);
		$('#pre').click(dateOnclick);
		$('#next').click(dateOnclick);
		$('#last').click(dateOnclick);
		document.addEventListener('keydown', keyBoardEvent);
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