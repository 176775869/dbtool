/**
 * 豆包 AI 聊天面板
 * 默认关闭，点击浮动按钮打开
 */
var chatVisible = false;

function openChat() {
    document.getElementById('ai-chat-panel').style.display = 'flex';
    document.getElementById('chat-toggle-btn').style.display = 'none';
    chatVisible = true;
}

function closeChat() {
    document.getElementById('ai-chat-panel').style.display = 'none';
    document.getElementById('chat-toggle-btn').style.display = 'flex';
    chatVisible = false;
}

function toggleChat() {
    if (chatVisible) {
        closeChat();
    } else {
        openChat();
    }
}

function sendChatMessage() {
    var input = document.getElementById('chat-input');
    var messagesDiv = document.getElementById('chat-messages');
    var message = input.value.trim();

    if (!message) return;

    // 显示用户消息
    var userDiv = document.createElement('div');
    userDiv.className = 'chat-message user-message';
    userDiv.textContent = message;
    messagesDiv.appendChild(userDiv);

    input.value = '';
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    // 显示加载中
    var loadingDiv = document.createElement('div');
    loadingDiv.className = 'chat-message ai-message';
    loadingDiv.textContent = '思考中...';
    loadingDiv.id = 'loading-message';
    messagesDiv.appendChild(loadingDiv);

    // 获取历史消息
    var history = [];
    var allMessages = messagesDiv.querySelectorAll('.chat-message');
    allMessages.forEach(function(msg) {
        if (msg.id !== 'loading-message') {
            var role = msg.classList.contains('user-message') ? 'user' : 'assistant';
            history.push({ role: role, content: msg.textContent });
        }
    });

    // 调用 API
    fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: message, history: history.slice(-6) })
    })
    .then(function(resp) { return resp.json(); })
    .then(function(data) {
        // 移除加载提示
        var loading = document.getElementById('loading-message');
        if (loading) loading.remove();

        // 显示 AI 回复
        var aiDiv = document.createElement('div');
        aiDiv.className = 'chat-message ai-message';
        aiDiv.textContent = data.reply || data.error || '无响应';
        messagesDiv.appendChild(aiDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    })
    .catch(function(err) {
        var loading = document.getElementById('loading-message');
        if (loading) loading.remove();
        var errDiv = document.createElement('div');
        errDiv.className = 'chat-message ai-message';
        errDiv.textContent = '请求失败: ' + err.message;
        messagesDiv.appendChild(errDiv);
    });
}

// 回车发送
document.addEventListener('DOMContentLoaded', function() {
    var chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendChatMessage();
            }
        });
    }

    // 初始化拖拽调整大小
    var panel = document.getElementById('ai-chat-panel');
    var resizeHandle = document.getElementById('resize-handle');
    if (panel && resizeHandle) {
        var isResizing = false;
        var startX, startY, startWidth, startHeight;

        resizeHandle.addEventListener('mousedown', function(e) {
            isResizing = true;
            startX = e.clientX;
            startY = e.clientY;
            startWidth = panel.offsetWidth;
            startHeight = panel.offsetHeight;
            e.preventDefault();
        });

        document.addEventListener('mousemove', function(e) {
            if (!isResizing) return;
            var newWidth = Math.max(300, Math.min(800, startWidth - (e.clientX - startX)));
            var newHeight = Math.max(200, Math.min(700, startHeight + (e.clientY - startY)));
            panel.style.width = newWidth + 'px';
            panel.style.height = newHeight + 'px';
        });

        document.addEventListener('mouseup', function() {
            isResizing = false;
        });
    }

    // 默认关闭聊天面板
    var chatPanel = document.getElementById('ai-chat-panel');
    var chatToggleBtn = document.getElementById('chat-toggle-btn');
    if (chatPanel && chatToggleBtn) {
        chatPanel.style.display = 'none';
        chatToggleBtn.style.display = 'flex';
        chatVisible = false;
    }
});