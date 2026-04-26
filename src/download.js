var Downloader = (function() {
	var storeId = 'backup';
	var backupDate = LocalStore.get(storeId);
	
	var aoa = [
		['主要信息', null, null, '其它信息'], // 特别注意合并的地方后面预留2个null
		['姓名', '性别', '年龄', '注册时间'],
		['张三', '男', 18, new Date()],
		['李四', '女', 22, new Date()]
	];
	
	var sheet = XLSX.utils.aoa_to_sheet(aoa);
	sheet['!merges'] = [
		// 设置A1-C1的单元格合并
		{s: {r: 0, c: 0}, e: {r: 0, c: 2}}
	];
	
	// 将一个sheet转成最终的excel文件的blob对象，然后利用URL.createObjectURL下载
	var sheet2blob = function(sheet, sheetName) {
		sheetName = sheetName || 'sheet1';
		var workbook = {
			SheetNames: [sheetName],
			Sheets: {}
		};
		workbook.Sheets[sheetName] = sheet;
		// 生成excel的配置项
		var wopts = {
			bookType: 'xlsx', // 要生成的文件类型
			bookSST: false, // 是否生成Shared String Table，官方解释是，如果开启生成速度会下降，但在低版本IOS设备上有更好的兼容性
			type: 'binary'
			};
		var wbout = XLSX.write(workbook, wopts);
		var blob = new Blob([s2ab(wbout)], {type:"application/octet-stream"});
		// 字符串转ArrayBuffer
		function s2ab(s) {
			var buf = new ArrayBuffer(s.length);
			var view = new Uint8Array(buf);
			for (var i=0; i!=s.length; ++i) view[i] = s.charCodeAt(i) & 0xFF;
			return buf;
		}
		return blob;
	}

	var arrayDataToBlob = function(data){
		var jsonStr = JSON.stringify(data); //  把 JSON 对象转换为字符串
		return new Blob([jsonStr]); //  创建 blob 对象
	}
	
	/**
	* 通用的打开下载对话框方法，没有测试过具体兼容性
	* @param url 下载地址，也可以是一个blob对象，必选
	* @param saveName 保存文件名，可选
	*/
	var  openDownloadDialog = function(url, saveName)
	{
		if(typeof url == 'object' && url instanceof Blob)
		{
			url = URL.createObjectURL(url); // 创建blob地址
		}
		var aLink = document.createElement('a');
		aLink.href = url;
		aLink.download = saveName || ''; // HTML5新增的属性，指定保存文件名，可以不要后缀，注意，file:///模式下不会生效
		var event;
		if(window.MouseEvent) event = new MouseEvent('click');
		else
		{
			event = document.createEvent('MouseEvents');
			event.initMouseEvent('click', true, false, window, 0, 0, 0, 0, 0, false, false, false, false, 0, null);
		}
			aLink.dispatchEvent(event);
	}

	var upload = function(data, index) {
		Configure.Debug('upload index:' + index + ',data:' + data);
		rtDataStore.updateRtTicketsToDB(JSON.parse(data));
	}
	var download = function(saveName, backupMonth) {
		if(!backupDate || new Date(backupDate).getMonth() != new Date().getMonth()) {   // 时间到下一个月
			rtDataStore.getAllRtTicketsFromDB().then((data)=>{
				if(data && data.length) {
					var backupData = data.filter((d)=>{
							return d.ID.substr(0,6) == backupMonth;
						});
					var  url = saveName.includes('xlsx') ?  
										sheet2blob(XLSX.utils.aoa_to_sheet(backupData)) :
										arrayDataToBlob(backupData);
					openDownloadDialog(url, saveName);
				}
				backupDate = new Date();
				LocalStore.set(storeId, backupDate);
			});	
		}
	}

	return {
		download:download,
		upload:upload,
	}
	
})();	
