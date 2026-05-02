var DoubaoWorkbench = (function() {
    var panel = null;
    var visible = false;
    var monitorTimer = null;
    var monitorRunning = false;

    function createPanel() {
        var html = `
          <div id="doubao-workbench" style="display:none;">
            <div id="wb-header">
              <div class="wb-tabs">
                <button class="wb-tab active" data-tab="strategy">📈 复盘</button>
                <button class="wb-tab" data-tab="chat">💬 聊天</button>
                <button class="wb-tab" data-tab="monitor">🔔 监控</button>
              </div>
              <button class="wb-close" onclick="DoubaoWorkbench.hide()">✕</button>
            </div>
            <div id="wb-content">
              <div id="tab-strategy" class="wb-panel active">
                <div class="doubao-actions">
                    <input type="text" id="custom-prompt-input" placeholder="输入额外指令（如：以今日数据为准，推翻旧结论）" style="flex:1; padding:6px; margin-right:6px; border:1px solid #ccc; border-radius:4px;">
                    <button class="btn-generate" id="btn-generate-strategy">⚡ 生成</button>
                    <button class="btn-generate" id="btn-load-cached">📄 加载</button>
                </div>
                <div id="doubao-status"></div>
                <div id="doubao-strategy"></div>
              </div>
              <div id="tab-chat" class="wb-panel">
                <div id="chat-messages"></div>
                <div id="chat-input-area">
                  <textarea id="chat-input" placeholder="输入消息..."></textarea>
                  <button id="chat-send-btn">发送</button>
                </div>
              </div>
              <div id="tab-monitor" class="wb-panel">
                <div class="doubao-actions">
                  <button class="btn-generate" id="btn-toggle-monitor" style="background:#27ae60;">🔴 开始监控</button>
                  <select id="monitor-interval" style="margin-left:6px; padding:6px; border-radius:4px; border:1px solid #ccc;">
                    <option value="30000">30秒</option>
                    <option value="60000" selected>1分钟</option>
                    <option value="120000">2分钟</option>
                    <option value="300000">5分钟</option>
                  </select>
                  <span id="monitor-timestamp" style="margin-left:10px; font-size:12px; color:#555;"></span>
                </div>
                <div id="monitor-status" style="margin-bottom:10px; font-size:13px;"></div>
                <div id="monitor-results" style="overflow-y:auto; max-height:400px;">
                  <p>点击"开始监控"按钮，定期检查买卖点信号。</p>
                </div>
              </div>
            </div>
            <div id="wb-resize-handle"></div>
          </div>
        `;
        $('body').append(html);
        panel = document.getElementById('doubao-workbench');

        // 标签切换
        $(panel).find('.wb-tab').on('click', function() {
            var tab = $(this).data('tab');
            $(panel).find('.wb-tab').removeClass('active');
            $(this).addClass('active');
            $(panel).find('.wb-panel').removeClass('active');
            $('#tab-' + tab).addClass('active');
        });

        // 拖拽移动
        var header = document.getElementById('wb-header');
        var isDragging = false, offsetX, offsetY;
        header.addEventListener('mousedown', function(e) {
            isDragging = true;
            offsetX = e.clientX - panel.offsetLeft;
            offsetY = e.clientY - panel.offsetTop;
            e.preventDefault();
        });
        document.addEventListener('mousemove', function(e) {
            if (!isDragging) return;
            panel.style.left = (e.clientX - offsetX) + 'px';
            panel.style.top = (e.clientY - offsetY) + 'px';
        });
        document.addEventListener('mouseup', function() { isDragging = false; });

        // 拖拽改变大小
        var resizeHandle = document.getElementById('wb-resize-handle');
        var isResizing = false;
        var startX, startY, startW, startH;
        resizeHandle.addEventListener('mousedown', function(e) {
            isResizing = true;
            startX = e.clientX;
            startY = e.clientY;
            startW = panel.offsetWidth;
            startH = panel.offsetHeight;
            e.preventDefault();
            e.stopPropagation();
        });
        document.addEventListener('mousemove', function(e) {
            if (!isResizing) return;
            var newW = Math.max(400, startW + (e.clientX - startX));
            var newH = Math.max(300, startH + (e.clientY - startY));
            panel.style.width = newW + 'px';
            panel.style.height = newH + 'px';
        });
        document.addEventListener('mouseup', function() { isResizing = false; });

        // 策略按钮事件
        $('#btn-generate-strategy').on('click', function() { generateStrategy(); });
        $('#btn-load-cached').on('click', loadStrategy);

        // 聊天发送事件
        $('#chat-send-btn').on('click', sendChat);
        $('#chat-input').on('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); }
        });

        // 监控按钮事件
        $('#btn-toggle-monitor').on('click', toggleMonitor);
    }

    function show() { if (!panel) createPanel(); panel.style.display = 'flex'; visible = true; }
    function hide() { if (panel) panel.style.display = 'none'; visible = false; }
    function toggle() { if (visible) hide(); else show(); }

    async function loadStrategy() {
        var status = document.getElementById('doubao-status');
        var output = document.getElementById('doubao-strategy');
        status.innerHTML = '⏳ 加载...';
        output.style.display = 'none';
        try {
            var resp = await fetch('/api/generate', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({force:false}) });
            var data = await resp.json();
            if (resp.ok) {
                status.innerHTML = '✅ ' + (data.cached ? '缓存' : '最新') + '：' + data.file;
                displayMarkdown(output, data.content);
            } else {
                status.innerHTML = '❌ ' + data.error;
            }
        } catch(e) { status.innerHTML = '❌ 请求失败'; }
    }

    async function generateStrategy() {
        var status = document.getElementById('doubao-status');
        var output = document.getElementById('doubao-strategy');
        var customPrompt = document.getElementById('custom-prompt-input').value.trim();

        status.innerHTML = '⏳ 正在生成策略...';
        output.style.display = 'none';

        var requestBody = { force: true };
        if (customPrompt) {
            requestBody.custom_prompt = customPrompt;
        }

        try {
            var resp = await fetch('/api/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });
            var data = await resp.json();
            if (resp.ok) {
                status.innerHTML = '✅ 生成成功：' + data.file;
                displayMarkdown(output, data.content);
            } else {
                status.innerHTML = '❌ ' + data.error;
            }
        } catch(e) {
            status.innerHTML = '❌ 请求失败';
        }
    }

    function displayMarkdown(container, mdText) {
        if (typeof marked !== 'undefined') {
            container.innerHTML = marked.parse(mdText);
        } else {
            container.innerHTML = mdText.replace(/\n/g, '<br>');
        }
        container.style.display = 'block';
    }

    var chatHistory = [];
    async function sendChat() {
        var input = document.getElementById('chat-input');
        var msg = input.value.trim();
        if (!msg) return;
        var messagesDiv = document.getElementById('chat-messages');
        messagesDiv.innerHTML += '<div class="chat-message user">' + msg + '</div>';
        input.value = '';
        chatHistory.push({role:'user', content:msg});
        try {
            var resp = await fetch('/api/chat', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:msg, history:chatHistory.slice(-6)}) });
            var data = await resp.json();
            var reply = data.reply || '无响应';
            messagesDiv.innerHTML += '<div class="chat-message ai">' + (typeof marked !== 'undefined' ? marked.parse(reply) : reply) + '</div>';
            chatHistory.push({role:'assistant', content:reply});
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        } catch(e) {
            messagesDiv.innerHTML += '<div class="chat-message ai">❌ 出错</div>';
        }
    }

    // --- 盘中监控相关函数（手动控制版） ---
    function toggleMonitor() {
        if (monitorRunning) {
            stopMonitor();
        } else {
            startMonitor();
        }
    }

    function startMonitor() {
        if (monitorTimer) return;
        monitorRunning = true;
        var btn = document.getElementById('btn-toggle-monitor');
        if (btn) {
            btn.innerHTML = '🟢 停止监控';
            btn.style.background = '#c0392b';
        }
        checkMonitor();
        var interval = parseInt(document.getElementById('monitor-interval').value) || 60000;
        monitorTimer = setInterval(checkMonitor, interval);
        console.log('[监控] 已启动，间隔 ' + (interval/1000) + ' 秒');
    }

    function stopMonitor() {
        if (monitorTimer) {
            clearInterval(monitorTimer);
            monitorTimer = null;
        }
        monitorRunning = false;
        var btn = document.getElementById('btn-toggle-monitor');
        if (btn) {
            btn.innerHTML = '🔴 开始监控';
            btn.style.background = '#27ae60';
        }
        console.log('[监控] 已停止');
    }

    async function checkMonitor() {
        var status = document.getElementById('monitor-status');
        var results = document.getElementById('monitor-results');
        var timestamp = document.getElementById('monitor-timestamp');

        if (status) status.innerHTML = '⏳ 查询中...';
        try {
            var resp = await fetch('/api/monitor', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });
            var data = await resp.json();
            if (resp.ok) {
                if (status) status.innerHTML = '✅ 检查完成';
                if (timestamp) timestamp.innerText = data.timestamp || '';
                displayMonitorResults(results, data);
            } else {
                if (status) status.innerHTML = '❌ ' + (data.error || '请求失败');
            }
        } catch(e) {
            if (status) status.innerHTML = '❌ 网络错误';
        }
    }

    function displayMonitorResults(container, data) {
        if (!container) return;
        var html = '';
        var signals = (data && data.signals) ? data.signals : [];
        var summary = (data && data.summary) ? data.summary : '';

        if (!summary && (!signals || signals.length === 0)) {
            html = '<p>暂无触发买卖点，继续观察。</p>';
            if (data && data.error) {
                html += '<p style="color: #e74c3c; font-size: 12px;">错误: ' + data.error + '</p>';
            }
        } else {
            if (summary) {
                html += '<div style="margin-bottom:12px; padding:10px; background:#f8f9fa; border-left:4px solid #2c3e50; font-size:13px;">' +
                       summary.replace(/\n/g, '<br>') + '</div>';
            }
            if (signals && signals.length > 0) {
                html += '<table style="width:100%; border-collapse:collapse; font-size:13px;">';
                html += '<tr style="background:#2c3e50; color:white;"><th>信号</th><th>标的</th><th>状态</th><th>建议</th></tr>';
                signals.forEach(function(s) {
                    var color = s.status === 'triggered' ? '#27ae60' : (s.status === 'pending' ? '#f39c12' : '#999');
                    html += '<tr style="border-bottom:1px solid #ddd; color:' + color + ';">';
                    html += '<td style="padding:4px;">' + (s.type || '') + '</td>';
                    html += '<td>' + (s.name || '') + ' ' + (s.code || '') + '</td>';
                    html += '<td>' + (s.status || '') + '</td>';
                    html += '<td>' + (s.suggestion || '') + '</td>';
                    html += '</tr>';
                });
                html += '</table>';
            }
        }
        container.innerHTML = html;
    }

    function init() {
        if (window.location.protocol === 'file:') return;
        var btn = document.createElement('button');
        btn.id = 'wb-toggle-btn';
        btn.innerHTML = '⚡';
        btn.title = '豆包工作台';
        btn.style.cssText = 'position:fixed; top:20px; right:20px; z-index:9999; width:44px; height:44px; background:#2c3e50; color:white; border:none; border-radius:50%; font-size:20px; cursor:pointer;';
        btn.onclick = toggle;
        document.body.appendChild(btn);
        createPanel();
    }

    return { init, show, hide, toggle };
})();
$(function() { DoubaoWorkbench.init(); });
