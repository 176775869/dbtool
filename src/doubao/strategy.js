var DoubaoWorkbench = (function() {
    var panel = null;
    var visible = false;

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
                <p>盘中监控功能开发中...</p>
              </div>
            </div>
            <div id="wb-resize-handle"></div>
          </div>
        `;
        $('body').append(html);
        panel = document.getElementById('doubao-workbench');

        $(panel).find('.wb-tab').on('click', function() {
            var tab = $(this).data('tab');
            $(panel).find('.wb-tab').removeClass('active');
            $(this).addClass('active');
            $(panel).find('.wb-panel').removeClass('active');
            $('#tab-' + tab).addClass('active');
        });

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
        document.addEventListener('mouseup', function() {
            isResizing = false;
        });

        $('#btn-generate-strategy').on('click', function() { generateStrategy(); });
        $('#btn-load-cached').on('click', loadStrategy);

        $('#chat-send-btn').on('click', sendChat);
        $('#chat-input').on('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); }
        });
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
