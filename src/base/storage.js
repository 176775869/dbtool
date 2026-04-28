
//判断数据类型的方法（对typeof的增强，9种常用类型的判断，返回小写字符串）
function Type(obj) {
    var arr = ['null', 'undefined', 'number', 'string', 'boolean', 'nan', 'array', 'object', 'function'];
    if (obj === null) {
        return 'null';
    }
    if (obj !== obj) {
        return 'nan';
    }
    if (typeof Array.isArray === 'function') {
        if (Array.isArray(obj)) { //浏览器支持则使用isArray()方法
            return 'array';
        }
    } else { //否则使用toString方法
        if (Object.prototype.toString.call(obj) === '[object Array]') {
            return 'array';
        }
    }
    return (typeof obj).toLowerCase();
}
 
//创建Store对象(增强localStorage或sessionStorage，直接存取对象或者数组)
var Store = function () {
    this.name = 'Store';
};
 
Store.prototype = {
    init: function (type) {
        this.store = window[type];
        return this;
    },
    set: function (key, value) {
        var type = Type(value);
 
        switch (type) {
            case 'object':
            case 'array':
                this.store.setItem(key, JSON.stringify(value));
                break;
            default:
                this.store.setItem(key, value);
        }
 
    },
    get: function (key) {
        var value = this.store.getItem(key);
 
        try {
            value = Type(+value) == 'number' ? value : JSON.parse(value);
        } catch (e) {}
 
        return value;
    },
    getAll: function () {
        var store = JSON.parse(JSON.stringify(this.store));
        var json = {};
        var value = '';
 
        for (var attr in store) {
            try {
                value = store[attr];
                value = Type(+value) == 'number' ? value : JSON.parse(value);
            } catch (e) {}
            json[attr] = value;
        }
        return json;
    },
    remove: function (key) {
        this.store.removeItem(key);
    },
    clear: function () {
        this.store.clear();
    },
};
 
//localStorage操作
var LocalStore = new Store().init('localStorage');
 
//sessionStorage操作
var SessionStore = new Store().init('sessionStorage');