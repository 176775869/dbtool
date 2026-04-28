# coding=utf-8
"""
豆包模式 · 买点检测引擎 v1.0
支持：C类型A/B、D1、D2、D3、B 五种买点
"""
from datetime import datetime

def detect_buy_signals(main_lines, data, anchor):
    """
    检测所有符合条件的买点，返回执行清单列表。
    每个元素为 {'type': 'C-A', 'name': '板块名', 'stocks': [...], 'condition': '触发条件', 'cangwei': 3}
    """
    today = data.get('date', datetime.now().strftime('%Y%m%d'))
    signals = []

    for ml in main_lines:
        stage = ml.get('stage', '')
        roles = ml.get('roles', {})
        direction_name = ml.get('name', '')

        if ml.get('type') != 'main':
            continue

        # ---- C类型A：启动日 ----
        if stage == 'C':
            signals.append(detect_c_type_a(direction_name, roles, data))

        # ---- C类型B：确认日 ----
        elif stage in ('1G-1',):
            signals.append(detect_c_type_b(direction_name, roles, data, anchor))

        # ---- D1：开板回封 ----
        elif stage in ('1D-1', '2D-1'):
            signals.append(detect_d1(direction_name, roles, data))

        # ---- D2：换手活口 ----
        elif stage in ('1D-2', '2D-2'):
            signals.append(detect_d2(direction_name, roles, data))

        # ---- D3：中军低吸 ----
        elif 'D' in stage:
            signals.append(detect_d3(direction_name, roles, data))

        # ---- B：冰点套利 ----
        elif stage == 'E':
            signals.append(detect_b(direction_name, roles, data))

    return [s for s in signals if s is not None]  # 过滤空信号


def detect_c_type_a(direction_name, roles, data):
    """C类型A：启动日买点"""
    lianban = roles.get('lianban_pioneer')
    elastic = roles.get('elastic_pioneer')
    stocks = []
    conditions = []

    if lianban:
        stocks.append(f"{lianban['name']}({lianban.get('code','')})")
        conditions.append(f"板块涨停≥10家且中军大涨→打板/回封最先换手板{lianban['name']}")
    if elastic:
        stocks.append(f"{elastic['name']}({elastic.get('code','')})")
        conditions.append(f"若先锋买不到→低吸弹性套利标的{elastic['name']}")

    if not stocks:
        return None

    return {
        'type': 'C-A',
        'name': direction_name,
        'stocks': stocks,
        'condition': '；'.join(conditions),
        'cangwei': '仓3-仓4',
        'timing': '早盘10:30前确认'
    }


def detect_c_type_b(direction_name, roles, data, anchor):
    """C类型B：确认日买点"""
    lianban = roles.get('lianban_pioneer')
    elastic = roles.get('elastic_pioneer')
    stocks = []
    conditions = []

    # 确认条件
    conditions.append("隔日核心封单加大≥50%且>3亿")
    conditions.append("早盘新增涨停≥2家")
    conditions.append("板块指数继续>2%")

    if lianban:
        stocks.append(f"{lianban['name']}({lianban.get('code','')})")
        conditions.append(f"弱转强确认→跟随买入连板先锋{lianban['name']}")
    if elastic:
        stocks.append(f"{elastic['name']}({elastic.get('code','')})")
        conditions.append(f"若先锋买不到→低吸弹性套利标的{elastic['name']}")

    if not stocks:
        return None

    return {
        'type': 'C-B',
        'name': direction_name,
        'stocks': stocks,
        'condition': '；'.join(conditions),
        'cangwei': '仓3-仓4',
        'timing': '早盘10:30前确认'
    }


def detect_d1(direction_name, roles, data):
    """D1：开板回封（当日买点）"""
    lianban = roles.get('lianban_pioneer')
    if not lianban:
        return None

    return {
        'type': 'D1',
        'name': direction_name,
        'stocks': [f"{lianban['name']}({lianban.get('code','')})"],
        'condition': f"开板后午盘前回封，封单额/成交>1.5→打板买入",
        'cangwei': '仓4',
        'timing': '午盘前确认'
    }


def detect_d2(direction_name, roles, data):
    """D2：换手活口分离（隔日买点）"""
    lianban = roles.get('lianban_pioneer')
    trend = roles.get('trend_pioneer')
    stocks = []
    conditions = []

    conditions.append("昨日活口已筛选，次日竞价高开3-7%且竞价放量>30%")
    conditions.append("开盘15分钟内快速拉升翻红，分时站稳均线")

    if lianban:
        stocks.append(f"{lianban['name']}({lianban.get('code','')})")
    if trend:
        stocks.append(f"{trend['name']}({trend.get('code','')})")

    if not stocks:
        return None

    return {
        'type': 'D2',
        'name': direction_name,
        'stocks': stocks,
        'condition': '；'.join(conditions),
        'cangwei': '仓2-仓3',
        'timing': '次日早盘确认'
    }


def detect_d3(direction_name, roles, data):
    """D3：中军低吸（隔日买点）"""
    mid_cap = roles.get('mid_cap', [])
    if not mid_cap:
        return None

    stocks = [f"{m['name']}({m.get('code','')})" for m in mid_cap[:2]]

    return {
        'type': 'D3',
        'name': direction_name,
        'stocks': stocks,
        'condition': "中军回踩5/10日线缩量企稳→次日尾盘或早盘不创新低时低吸",
        'cangwei': '仓2-仓3',
        'timing': '尾盘14:50或次日早盘'
    }


def detect_b(direction_name, roles, data):
    """B：冰点套利"""
    mid_cap = roles.get('mid_cap', [])
    if not mid_cap:
        return None

    stocks = [f"{m['name']}({m.get('code','')})" for m in mid_cap[:1]]

    return {
        'type': 'B',
        'name': direction_name,
        'stocks': stocks,
        'condition': "连续2日下跌>3000家+核心个股缩量止跌→尾盘或次日轻仓低吸",
        'cangwei': '仓1',
        'timing': '尾盘14:50或次日早盘'
    }