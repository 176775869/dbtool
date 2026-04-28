(function($) {
	var box;
	$.fn.clear=(function() {
		if(box && box.hide) box.hide(0,function(){$(this).remove();});
	});
    $.fn.tip=(function(options) {
        var _this = $(this);
        var _param = {message:'',position:'bottom center',color:'red',bgColor:'#fffce7',bdColor:'#f8cc7e',hideEvent:'mouseout',fontSize:'16px',hideTime:0,top:0,left:0};
        $.extend(_param,options);
        if(typeof(options) != 'object') _param.message = options;
        if(!_param.message) return false;
		if(box && box.hide) box.hide(_param.hideTime,function(){$(this).remove();});
        box = $('<div></div>').css({'color':_param.color,'background':_param.bgColor,border:'1px solid '+_param.bdColor,'position':'absolute','padding':'5px 10px','font-size':_param.fontSize}).html('<div id="tip_message">'+_param.message+'</div>').appendTo($('body'));
        var _point = $('<div>◆</div>').css({width:16,height:16,'position':'absolute','color':_param.bdColor,'font-size':'14px','line-height':'14px'}).appendTo(box);
        var _point_shade = _point.clone().css('color',_param.bgColor).appendTo(box);
        var _position = _param.position.split(' ');
        _position[1] = _position[1] ? _position[1] : 'center';
        var _top,_left;
        switch (_position[0]) {
            case 'bottom':
                _top = -7;
                _left = (_position[1]=='center') ? (box.outerWidth()-16)/2 : _position[1];
                _point.css({top:_top,left:_left}); _point_shade.css({top:_top+1,left:_left});
                box.css({top:_this.offset().top+_this.outerHeight()+8+_param.top,left:_this.offset().left+_param.left});
                break;
            case 'top':
                _top = box.outerHeight()-7;
                _left = (_position[1]=='center') ? (box.outerWidth()-16)/2 : _position[1];
                _point.css({top:_top,left:_left}); _point_shade.css({top:_top-1,left:_left});
                box.css({top:_this.offset().top-box.outerHeight()-8+_param.top,left:_this.offset().left+_param.left});
                break;
            case 'left':
                _top = (_position[1]=='center') ? (box.outerHeight()-16)/2 : _position[1];
                _left = box.outerWidth()-8;
                _point.css({top:_top,left:_left}); _point_shade.css({top:_top,left:_left-1});
                box.css({top:_this.offset().top,left:_this.offset().left-box.outerWidth()-8});
                break;
            case 'right':
                _top = (_position[1]=='center') ? (box.outerHeight()-16)/2 : _position[1];
                _left = -7;
                _point.css({top:_top,left:_left}); _point_shade.css({top:_top,left:_left+1});
                box.css({top:_this.offset().top,left:_this.offset().left+_this.outerWidth()+8});
                break;
            default:
                _top = -7;
                _left = (_position[1]=='center') ? (box.outerWidth()-16)/2 : _position[1];
                _point.css({top:_top,left:_left}); _point_shade.css({top:_top+1,left:_left});
                box.css({top:_this.offset().top+_this.outerHeight()+8+_param.top,left:_this.offset().left+_param.left});
                break;
        }
        _this.bind(_param.hideEvent,function(){box.hide(_param.hideTime,function(){$(this).remove();});});
		//_this.bind('DOMNodeRemoved',function(){box.hide(_param.hideTime,function(){$(this).remove();});});
    });
})(jQuery);

var Tip = (function () {
	var show = function(el, txt) {
		el.onmouseover  = function() {
			$(this).tip(txt);
		};
	};

	return {
		show:show
	}
})();