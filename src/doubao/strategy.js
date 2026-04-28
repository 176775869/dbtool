/**
 * 豆包模式策略生成器
 * 依赖：jQuery（页面已加载）
 */
var DoubaoStrategy = (function() {
    var panelVisible = false;
    var panel = null;

    function createPanel() {
        var html = `
            <div id="doubao-panel" style="display:none;">
                <div id="doubao-header">
                    <span>📊 豆包模式策略生成器</span>
                    <button class="btn-close" onclick="DoubaoStrategy.hide()">✕</button>
                </div>
                <div id="doubao-body">
                    <button class="btn-generate" onclick="DoubaoStrategy.generate()">
                        ⚡ 一键生成策略
                    </button>
                    <div id="doubao-status"></div>
                    <div id="doubao-strategy"></div>
                </div>
            </div>
        `;
        $('body').append(html);
        panel = document.getElementById('doubao-panel');

        // 拖拽功能
        var header = document.getElementById('doubao-header');
        var isDragging = false;
        var offsetX, offsetY;

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
        panelVisible = true;
    }

    function hide() {
        if (panel) panel.style.display = 'none';
        panelVisible = false;
    }

    function toggle() {
        if (panelVisible) hide();
        else show();
    }

    async function generate() {
        var btn = document.querySelector('#doubao-body .btn-generate');
        var status = document.getElementById('doubao-status');
        var output = document.getElementById('doubao-strategy');

        btn.disabled = true;
        btn.textContent = '⏳ 生成中...';
        status.textContent = '正在采集数据并生成策略，请稍候...';
        output.style.display = 'none';

        try {
            var resp = await fetch('/api/generate', { method: 'POST' });
            var data = await resp.json();

            if (resp.ok) {
                status.textContent = '✅ 生成成功！文件：' + data.file;
                output.innerHTML = data.content
                    .replace(/^# (.*)/gm, '<h1>$1</h1>')
                    .replace(/^## (.*)/gm, '<h2>$1</h2>')
                    .replace(/^### (.*)/gm, '<h3>$1</h3>')
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/^- (.*)/gm, '• $1')
                    .replace(/\n/g, '<br>');
                output.style.display = 'block';
            } else {
                status.textContent = '❌ 生成失败：' + data.error;
            }
        } catch (e) {
            status.textContent = '❌ 请求失败：' + e.message;
        }

        btn.disabled = false;
        btn.textContent = '⚡ 一键生成策略';
    }

    // 初始化：在页面上添加一个打开按钮
    function init() {
        var openBtn = document.createElement('button');
        openBtn.className = 'btn-open-doubao';
        openBtn.textContent = '📊 策略';
        openBtn.onclick = toggle;
        document.body.appendChild(openBtn);
        createPanel();
    }

    return {
        init: init,
        show: show,
        hide: hide,
        toggle: toggle,
        generate: generate
    };
})();

// 页面加载完成后初始化
$(function() {
    DoubaoStrategy.init();
});