/**
 * 豆包模式策略生成器
 * 依赖：jQuery（页面已加载）
 */
var DoubaoStrategy = (function() {
    var panel = null;
    var isPanelVisible = false;

    function createPanel() {
        var html = `
            <div id="doubao-panel" style="display:none;">
                <div id="doubao-header">
                    <span>📊 策略生成器</span>
                    <button class="btn-close" onclick="DoubaoStrategy.hide()">✕</button>
                </div>
                <div id="doubao-body">
                    <div class="doubao-actions">
                        <button class="btn-generate" id="btn-generate-strategy" title="执行完整数据采集+AI生成">
                            ⚡生成
                        </button>
                        <button class="btn-generate" id="btn-load-cached" title="查看已生成的策略">
                            📄加载
                        </button>
                        <button class="btn-generate" id="btn-force-generate" title="忽略缓存强制重新生成">
                            🔁新生成
                        </button>
                    </div>
                    <div id="doubao-status"></div>
                    <div id="doubao-strategy"></div>
                </div>
            </div>
        `;
        $('body').append(html);
        panel = document.getElementById('doubao-panel');

        // 绑定事件
        $('#btn-generate-strategy').on('click', function() { generateStrategy(false); });
        $('#btn-load-cached').on('click', function() { loadLatestCached(); });
        $('#btn-force-generate').on('click', function() { generateStrategy(true); });

        // 拖拽功能
        var header = document.getElementById('doubao-header');
        var isDragging = false, offsetX, offsetY;

        header.addEventListener('mousedown', function(e) {
            isDragging = true;
            offsetX = e.clientX - panel.offsetLeft;
            offsetY = e.clientY - panel.offsetTop;
        });

        document.addEventListener('mousemove', function(e) {
            if (!isDragging) return;
            panel.style.left = (e.clientX - offsetX) + 'px';
            panel.style.top = (e.clientY - offsetY) + 'px';
            panel.style.right = 'auto';
        });

        document.addEventListener('mouseup', function() {
            isDragging = false;
        });
    }

    function show() {
        if (!panel) createPanel();
        panel.style.display = 'flex';
        isPanelVisible = true;
    }

    function hide() {
        if (panel) panel.style.display = 'none';
        isPanelVisible = false;
    }

    function toggle() {
        if (isPanelVisible) hide(); else show();
    }

    // 加载缓存的最新策略（不重新生成）
    async function loadLatestCached() {
        var status = document.getElementById('doubao-status');
        var output = document.getElementById('doubao-strategy');
        status.innerHTML = '⏳ 读取最新策略...';
        output.style.display = 'none';

        try {
            var resp = await fetch('/api/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ force: false })
            });
            var data = await resp.json();
            if (resp.ok) {
                displayStrategy(data);
            } else {
                status.innerHTML = '❌ 错误：' + data.error;
            }
        } catch (e) {
            status.innerHTML = '❌ 请求失败：' + e.message;
        }
    }

    // 生成策略（可选择强制）
    async function generateStrategy(force) {
        var status = document.getElementById('doubao-status');
        var output = document.getElementById('doubao-strategy');
        status.innerHTML = force ? '⏳ 强制重新生成中...' : '⏳ 正在生成策略...';
        output.style.display = 'none';

        var btns = document.querySelectorAll('#doubao-body .btn-generate');
        btns.forEach(function(b) { b.disabled = true; });

        try {
            var resp = await fetch('/api/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ force: force })
            });
            var data = await resp.json();
            if (resp.ok) {
                displayStrategy(data);
            } else {
                status.innerHTML = '❌ 生成失败：' + data.error;
            }
        } catch (e) {
            status.innerHTML = '❌ 请求失败：' + e.message;
        }

        btns.forEach(function(b) { b.disabled = false; });
    }

    function displayStrategy(data) {
        var status = document.getElementById('doubao-status');
        var output = document.getElementById('doubao-strategy');
        status.innerHTML = '✅ ' + (data.cached ? '加载缓存' : '生成成功') + '：' + data.file;
        
        // 简单的 Markdown 转 HTML（保留原有逻辑）
        var html = data.content
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/^# (.*$)/gim, '<h1>$1</h1>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/^\- (.*)/gm, '• $1')
            .replace(/```json\n([\s\S]*?)\n```/g, '<pre><code>$1</code></pre>')
            .replace(/\n/g, '<br>');

        output.innerHTML = html;
        output.style.display = 'block';
    }

    // 初始化：添加浮动按钮
    function init() {
        var openBtn = document.createElement('button');
        openBtn.className = 'btn-open-doubao';
        openBtn.textContent = '📊';
        openBtn.onclick = toggle;
        openBtn.title = '策略生成器';
        openBtn.style.cssText = 'position:fixed; right:20px; bottom:160px; z-index:9999; width:44px; height:44px; background:#2c3e50; color:white; border:none; border-radius:50%; cursor:pointer; font-size:20px; box-shadow:0 2px 10px rgba(0,0,0,0.3); display:flex; align-items:center; justify-content:center;';
        document.body.appendChild(openBtn);
        createPanel();
    }

    return {
        init: init,
        show: show,
        hide: hide,
        toggle: toggle,
        generate: generateStrategy
    };
})();

// 页面加载完成后初始化
$(function() {
    DoubaoStrategy.init();
});