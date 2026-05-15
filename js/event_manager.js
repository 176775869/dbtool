// js/event_manager.js —— 全局事件统一管理 (v2.1)
var EventManager = (function() {
    'use strict';

    // ----- 快捷键注册表 -----
    var hotkeys = {};
    var isHotkeysSuspended = false;
    var boundHotkeyHandler = null;

    // ----- 背景冻结状态 -----
    var isFrozen = false;
    var freezeEvents = ['mousedown','mouseup','click','dblclick','contextmenu',
                        'wheel','mousewheel','DOMMouseScroll',
                        'touchstart','touchmove','touchend'];
    var activePanel = null;
    var boundFreezeHandler = null;

    // 面板相关的全局监听器引用（用于清理）
    var globalKeyFilter = null;
    var panelWheelHandler = null;

    function init() {
        if (boundHotkeyHandler) return;

        // 全局快捷键分发
        boundHotkeyHandler = function(e) {
            if (isHotkeysSuspended) return;
            var fns = hotkeys[e.key];
            if (fns && fns.length > 0) {
                for (var i = 0; i < fns.length; i++) {
                    fns[i](e);
                }
            }
        };
        document.addEventListener('keydown', boundHotkeyHandler);

        // 背景冻结拦截器
        boundFreezeHandler = function(e) {
            if (!isFrozen) return;
            if (activePanel && activePanel.contains(e.target)) return;
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
        };
        freezeEvents.forEach(function(type) {
            var opts = (type === 'wheel' || type === 'mousewheel' || type === 'DOMMouseScroll' || 
                        type === 'touchstart' || type === 'touchmove') 
                       ? { capture: true, passive: false } 
                       : { capture: true };
            document.addEventListener(type, boundFreezeHandler, opts);
        });
    }

    // =================== 公共接口 ===================

    function register(key, fn) {
        if (!boundHotkeyHandler) init();
        if (!hotkeys[key]) hotkeys[key] = [];
        hotkeys[key].push(fn);
    }

    function suspendHotkeys() {
        isHotkeysSuspended = true;
    }

    function resumeHotkeys() {
        isHotkeysSuspended = false;
    }

    function activatePanel(panelEl) {
        if (!boundFreezeHandler) init();
        activePanel = panelEl;
        isFrozen = true;
        suspendHotkeys();

        // ===== 全局键盘过滤器（绑定在 document 上确保生效） =====
        globalKeyFilter = function(e) {
            var tag = (e.target.tagName || '').toLowerCase();

            // Esc 关闭面板
            if (e.key === 'Escape') {
                if (typeof DoubaoWorkbench !== 'undefined' && DoubaoWorkbench.hide) {
                    DoubaoWorkbench.hide();
                }
                e.stopPropagation();
                e.preventDefault();
                return;
            }

            // Tab 切换面板标签（焦点不在输入框时）
            if (e.key === 'Tab') {
                if (tag === 'input' || tag === 'textarea' || tag === 'select') return;
                e.preventDefault();
                var tabs = panelEl.querySelectorAll('.wb-tab');
                if (tabs.length === 0) return;
                var active = panelEl.querySelector('.wb-tab.active') || tabs[0];
                var idx = Array.prototype.indexOf.call(tabs, active);
                var nextIdx = (idx + 1) % tabs.length;
                tabs[nextIdx].click();
                return;
            }

            // 输入控件完全放行
            if (tag === 'input' || tag === 'textarea' || tag === 'select') return;

            // F 键和所有功能键（F1-F12）放行
            if (e.key && (e.key === 'F' || e.key === 'f' || /^F\d{1,2}$/.test(e.key)) && !e.ctrlKey && !e.altKey && !e.metaKey) {
                return;
            }

            // 其余按键阻止冒泡，避免触发背景快捷键
            e.stopPropagation();
        };
        document.addEventListener('keydown', globalKeyFilter, true);

        // ===== 面板滚轮拦截 =====
        panelWheelHandler = function(e) {
            e.stopPropagation();
        };
        panelEl.addEventListener('wheel', panelWheelHandler, { passive: true });
    }

    function deactivatePanel() {
        isFrozen = false;
        resumeHotkeys();

        if (globalKeyFilter) {
            document.removeEventListener('keydown', globalKeyFilter, true);
            globalKeyFilter = null;
        }
        if (activePanel && panelWheelHandler) {
            activePanel.removeEventListener('wheel', panelWheelHandler);
            panelWheelHandler = null;
        }
        activePanel = null;
    }

    init();

    return {
        register: register,
        suspendHotkeys: suspendHotkeys,
        resumeHotkeys: resumeHotkeys,
        activatePanel: activatePanel,
        deactivatePanel: deactivatePanel
    };
})();