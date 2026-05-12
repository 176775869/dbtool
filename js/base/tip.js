/*!
 * jquery.tip.js (v2.0) – 自动清理版
 * 兼容原有 Tip.show() 用法 & 解决元素移除后气泡残留问题
 */
(function ($, window, document) {
    'use strict';

    // 当前所有活动 tip 的引用（支持多个）
    var activeTips = [];

    /**
     * 关闭所有活动 tip
     */
    function closeAllTips() {
        for (var i = activeTips.length - 1; i >= 0; i--) {
            var t = activeTips[i];
            if (t.box && t.box.stop) {
                t.box.stop(true, true).remove();
            }
        }
        activeTips = [];
    }

    /**
     * 关闭指定元素绑定的 tip
     * @param {HTMLElement} el
     */
    function closeTip(el) {
        for (var i = activeTips.length - 1; i >= 0; i--) {
            if (activeTips[i].el === el) {
                if (activeTips[i].box) {
                    activeTips[i].box.stop(true, true).remove();
                }
                if (activeTips[i].observer) {
                    activeTips[i].observer.disconnect();
                }
                activeTips.splice(i, 1);
                break;
            }
        }
    }

    // ---------- 全局清除（兼容旧 $.fn.clear） ----------
    $.fn.clear = function () {
        closeAllTips();
    };

    // ---------- 清除所有提示的静态接口 ----------
    $.clearAllTips = function () {
        closeAllTips();
    };

    // ---------- 核心 tip 方法 ----------
    $.fn.tip = function (options) {
        var _this = this;
        // 参数处理
        var _param = {
            message: '',
            position: 'bottom center',
            color: 'red',
            bgColor: '#fffce7',
            bdColor: '#f8cc7e',
            hideEvent: 'mouseout',
            fontSize: '16px',
            hideTime: 0,
            top: 0,
            left: 0
        };
        $.extend(_param, options);
        if (typeof options !== 'object') _param.message = options;
        if (!_param.message) return false;

        // 若该元素已有提示，先关闭旧的
        closeTip(this[0]);

        // 创建 DOM
        var box = $('<div></div>').css({
            color: _param.color,
            background: _param.bgColor,
            border: '1px solid ' + _param.bdColor,
            position: 'absolute',
            padding: '5px 10px',
            'font-size': _param.fontSize,
            'z-index': 99999
        }).html('<div class="tip_message">' + _param.message + '</div>').appendTo($('body'));

        // 箭头
        var _point = $('<div>◆</div>').css({
            width: 16,
            height: 16,
            position: 'absolute',
            color: _param.bdColor,
            'font-size': '14px',
            'line-height': '14px'
        }).appendTo(box);
        var _point_shade = _point.clone().css('color', _param.bgColor).appendTo(box);

        // 定位
        var _position = _param.position.split(' ');
        _position[1] = _position[1] ? _position[1] : 'center';
        var _top, _left;
        var BOX_W = box.outerWidth();
        var BOX_H = box.outerHeight();
        var EL_W = _this.outerWidth();
        var EL_H = _this.outerHeight();
        var EL_OFFSET = _this.offset();

        switch (_position[0]) {
            case 'bottom':
                _top = -7;
                _left = (_position[1] === 'center') ? (BOX_W - 16) / 2 : _position[1];
                _point.css({ top: _top, left: _left }); _point_shade.css({ top: _top + 1, left: _left });
                box.css({ top: EL_OFFSET.top + EL_H + 8 + _param.top, left: EL_OFFSET.left + _param.left });
                break;
            case 'top':
                _top = BOX_H - 7;
                _left = (_position[1] === 'center') ? (BOX_W - 16) / 2 : _position[1];
                _point.css({ top: _top, left: _left }); _point_shade.css({ top: _top - 1, left: _left });
                box.css({ top: EL_OFFSET.top - BOX_H - 8 + _param.top, left: EL_OFFSET.left + _param.left });
                break;
            case 'left':
                _top = (_position[1] === 'center') ? (BOX_H - 16) / 2 : _position[1];
                _left = BOX_W - 8;
                _point.css({ top: _top, left: _left }); _point_shade.css({ top: _top, left: _left - 1 });
                box.css({ top: EL_OFFSET.top + _param.top, left: EL_OFFSET.left - BOX_W - 8 + _param.left });
                break;
            case 'right':
                _top = (_position[1] === 'center') ? (BOX_H - 16) / 2 : _position[1];
                _left = -7;
                _point.css({ top: _top, left: _left }); _point_shade.css({ top: _top, left: _left + 1 });
                box.css({ top: EL_OFFSET.top + _param.top, left: EL_OFFSET.left + EL_W + 8 + _param.left });
                break;
            default: // 默认 bottom center
                _top = -7;
                _left = (BOX_W - 16) / 2;
                _point.css({ top: _top, left: _left }); _point_shade.css({ top: _top + 1, left: _left });
                box.css({ top: EL_OFFSET.top + EL_H + 8 + _param.top, left: EL_OFFSET.left + _param.left });
        }

        // 隐藏事件
        _this.bind(_param.hideEvent, function () {
            closeTip(_this[0]);
        });

        // ---------- 元素移除自动清理 ----------
        var targetEl = _this[0];
        var observer = null;
        if (window.MutationObserver) {
            observer = new MutationObserver(function () {
                if (!document.body.contains(targetEl)) {
                    // 目标元素已不在 DOM 中，清除这个 tip
                    closeTip(targetEl);
                }
            });
            observer.observe(document.body, { childList: true, subtree: true });
        }

        // 保存活动提示信息
        activeTips.push({
            el: targetEl,
            box: box,
            observer: observer
        });

        // 自动消失（如果设置了 hideTime > 0）
        if (_param.hideTime > 0) {
            setTimeout(function () {
                closeTip(targetEl);
            }, _param.hideTime);
        }

        return box;
    };

    // ---------- 原有的 Tip 静态对象（兼容） ----------
    window.Tip = {
        show: function (el, txt) {
            el.onmouseover = function () {
                $(this).tip(txt);
            };
        }
    };

})(jQuery, window, document);