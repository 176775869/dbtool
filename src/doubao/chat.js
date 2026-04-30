/**
 * 豆包 AI 聊天面板
 * 依赖：无
 */
(function() {
    let chatHistory = [];

    // ============ 打开面板 ============
    window.openChat = function() {
        document.getElementById('ai-chat-panel').style.display = 'flex';
        document.getElementById('chat-toggle-btn').style.display = 'none';
    };

    // ============ 关闭面板（保留记录） ============
    window.closeChat = function() {
        document.getElementById('ai-chat-panel').style.display = 'none';
        document.getElementById('chat-toggle-btn').style.display = 'block';
    };

    // ============ 发送消息 ============
    window.sendChatMessage = async function() {
        const input = document.getElementById('chat-input');
        const msgText = input.value.trim();
        if (!msgText) return;

        appendMessage('user', msgText);
        chatHistory.push({role: 'user', content: msgText});
        input.value = '';

        appendMessage('assistant', '思考中...');

        try {
            const recentHistory = chatHistory.slice(-5, -1);
            const resp = await fetch('/api/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({message: msgText, history: recentHistory})
            });
            const data = await resp.json();

            const container = document.getElementById('chat-messages');
            const lastMsg = container.lastChild;
            const reply = data.reply || data.error || '未知错误';
            lastMsg.innerHTML = '<strong style="color:#e67e22;">AI：</strong>' + escapeHtml(reply);
            
            if (data.reply) {
                chatHistory.push({role: 'assistant', content: data.reply});
            }
        } catch (e) {
            const container = document.getElementById('chat-messages');
            const lastMsg = container.lastChild;
            lastMsg.innerHTML = '<strong style="color:#e67e22;">AI：</strong>请求失败：' + escapeHtml(e.message);
        }
    };

    function appendMessage(role, text) {
        const container = document.getElementById('chat-messages');
        const div = document.createElement('div');
        div.style.marginBottom = '8px';
        if (role === 'user') {
            div.innerHTML = '<strong style="color:#4a90d8;">你：</strong>' + escapeHtml(text);
        } else {
            div.innerHTML = '<strong style="color:#e67e22;">AI：</strong>' + text;
        }
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }

    function escapeHtml(str) {
        const temp = document.createElement('div');
        temp.textContent = str;
        return temp.innerHTML;
    }

    // ============ 拖拽移动（标题栏拖动整个面板） ============
    function initDrag() {
        const header = document.getElementById('chat-header');
        const panel = document.getElementById('ai-chat-panel');
        let isDragging = false, offsetX, offsetY;

        header.addEventListener('mousedown', function(e) {
            if (e.target.tagName === 'BUTTON') return;
            isDragging = true;
            const rect = panel.getBoundingClientRect();
            offsetX = e.clientX - rect.left;
            offsetY = e.clientY - rect.top;
            panel.style.transition = 'none';
            document.body.style.userSelect = 'none';
        });

        document.addEventListener('mousemove', function(e) {
            if (!isDragging) return;
            panel.style.left = (e.clientX - offsetX) + 'px';
            panel.style.top = (e.clientY - offsetY) + 'px';
            panel.style.right = 'auto';
            panel.style.bottom = 'auto';
        });

        document.addEventListener('mouseup', function() {
            if (isDragging) {
                isDragging = false;
                document.body.style.userSelect = '';
            }
        });
    }

    // ============ 拖拽缩放 ============
    function initResize() {
        const handle = document.getElementById('resize-handle');
        const panel = document.getElementById('ai-chat-panel');
        let isResizing = false, startX, startY, startWidth, startHeight;

        handle.addEventListener('mousedown', function(e) {
            isResizing = true;
            startX = e.clientX;
            startY = e.clientY;
            startWidth = panel.offsetWidth;
            startHeight = panel.offsetHeight;
            e.preventDefault();
            e.stopPropagation();
            document.body.style.userSelect = 'none';
        });

        document.addEventListener('mousemove', function(e) {
            if (!isResizing) return;
            panel.style.width = Math.max(300, startWidth + (e.clientX - startX)) + 'px';
            panel.style.height = Math.max(250, startHeight + (e.clientY - startY)) + 'px';
        });

        document.addEventListener('mouseup', function() {
            if (isResizing) {
                isResizing = false;
                document.body.style.userSelect = '';
            }
        });
    }

    // 初始化拖拽和缩放
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            initDrag();
            initResize();
        });
    } else {
        initDrag();
        initResize();
    }

})();