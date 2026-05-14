import os, sys, json, time, requests
import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
DATA_DIR = os.path.join(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"), '..', 'data')
os.makedirs(DATA_DIR, exist_ok=True)

URL = "https://www.cls.cn/nodeapi/updateTelegraphList"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.cls.cn/telegraph'
}

# 产业相关关键词
KEYWORDS = [
    '芯片', '半导体', '锂电', '新能源', '光伏', '储能', 'AI', '人工智能',
    '算力', 'CPO', '光模块', '军工', '航天', '卫星', '稀土', '碳酸锂',
    '涨价', '突破', '量产', '订单', '中标', '特高压', '机器人', '自动驾驶',
    '人形机器人', '低空经济', '商业航天', '固态电池', '钠离子', '量子',
    '核聚变', '国防', '政策', '部委', '国务院', '发改委', '工信部',
    '华为', '苹果', '特斯拉', '出口管制', '制裁', '关税', 'A股', '大盘',
    '指数', '板块', '涨停', '跌停', '成交', '主力', '北向', '央行', '降息',
    '降准', 'LPR', 'MLF', '社融', 'CPI', 'PPI', 'PMI',
    '监管', '问询', '重组', '借壳', '年报', '一季报', '半年报',
    '通威', '宁德', '比亚迪', '5G', '6G', '数据中心', '服务器', '液冷',
    '光刻', 'EDA', 'IP', 'FPGA', '碳化硅', 'IGBT', 'MCU', 'MOSFET',
    '风电', '光伏组件', 'BIPV', 'HJT', 'TOPCon', '钙钛矿', '储能变流器',
    '氢能', '燃料电池', '电解槽', '充电桩', '换电', '铜箔', '铝箔',
    '薄膜', '聚丙烯', '锂电隔膜', '电解液', '负极材料', '正极材料',
    '磷酸铁锂', '三元锂', '钠电池', '半固态', '全固态',
    '减速器', '伺服电机', '控制器', '机器视觉', '激光雷达',
    '航天发动机', '导弹', '隐身', '雷达', '电子对抗'
]

# 外围市场、期货、宏观关键词
OUTER_MARKET_KW = [
    '美股', '道指', '纳指', '标普', '道琼斯', '纳斯达克', '罗素',
    '欧股', '德国DAX', '法国CAC', '富时100', '日经', '恒生', '恒指',
    'A50', '富时A50', '上证', '深证', '创业板', '科创50',
    '期货', '原油', 'WTI', '布伦特', '黄金', '白银', '铜', '铝', '锌',
    '汇率', '美元', '人民币', '离岸', '在岸', '欧元', '日元', '英镑',
    '美债', '收益率', '美联储', '加息', '降息', '欧央行', '日央行',
    'GDP', 'CPI', 'PPI', 'PMI', '非农', '失业金', '零售销售',
    'Vix', '恐慌指数', '地缘', '冲突', '制裁', '关税',
]
KEYWORDS.extend(OUTER_MARKET_KW)


def is_relevant(title):
    """判断电报是否与A股主线或宏观环境相关"""
    for kw in KEYWORDS:
        if kw in title:
            return True
    return False


def get_start_timestamp():
    """
    根据当前时间动态计算 lastTime 参数的时间戳：
    - 如果当前是上午（0:00 - 11:59），则返回前一个自然日的下午3点整的时间戳
    - 如果当前是下午（12:00 - 23:59），则返回当天凌晨0点整的时间戳
    这样做可以保证上午采集时覆盖昨日收盘后的所有电报，下午采集时覆盖今日所有电报。
    """
    now = datetime.datetime.now()
    if now.hour < 12:  # 上午
        # 前一天的 15:00:00
        target = now - datetime.timedelta(days=1)
        target = target.replace(hour=15, minute=0, second=0, microsecond=0)
    else:  # 下午
        # 当天的 00:00:00
        target = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(target.timestamp())


def fetch(skip_filter=False):
    """
    获取财联社电报列表
    skip_filter=True: 返回所有电报，不过滤关键词
    skip_filter=False: 只返回与关键词相关的电报
    """
    last_time = str(get_start_timestamp())
    params = {
        'app': 'CailianpressWeb',
        'hasFirstVipArticle': '1',
        'lastTime': last_time,
        'os': 'web',
        'rn': '80',
        'subscribedColumnIds': '',
        'sv': '8.4.6'
    }
    try:
        resp = requests.get(URL, params=params, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"[TELEGRAPH] HTTP error {resp.status_code}")
            return []
        data = resp.json()
        titles = []

        # 普通电报
        roll = data.get('data', {}).get('roll_data', [])
        kept = 0
        for item in roll:
            t = item.get('title', '') or item.get('brief', '') or item.get('content', '')[:80]
            if t:
                if skip_filter or is_relevant(t):
                    titles.append(t)
                    kept += 1
        if skip_filter:
            print(f"[TELEGRAPH] roll_data: {kept} kept (full mode)")
        else:
            print(f"[TELEGRAPH] roll_data: {kept} kept (filtered)")

        # VIP电报
        vip = data.get('vipData', [])
        for item in vip:
            t = item.get('title', '') or item.get('brief', '')
            if t:
                if skip_filter or is_relevant(t):
                    titles.append(f"[VIP] {t}")

        # 全球VIP电报
        gvip = data.get('vipGlobal', [])
        seen = set(titles)
        for item in gvip:
            t = item.get('title', '') or item.get('brief', '')
            if t:
                label = f"[全球] {t}"
                if label not in seen:
                    if skip_filter or is_relevant(t):
                        titles.append(label)
                        seen.add(label)

        print(f"[TELEGRAPH] total: {len(titles)}")
        return titles
    except Exception as e:
        print(f"[TELEGRAPH] error: {e}")
        return []


def save_to_file(items, filename):
    now_str = datetime.datetime.now().strftime('%Y%m%d')
    lines = [f"日期: {now_str}", "", "=== 产业催化电报 ==="]
    if items:
        for i, t in enumerate(items, 1):
            lines.append(f"{i}. {t}")
    else:
        lines.append("今日暂无相关电报。")
    lines.append("")
    out = os.path.join(DATA_DIR, filename)
    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"[TELEGRAPH] saved to {out}")


def main():
    today_str = datetime.datetime.now().strftime('%Y%m%d')

    # 保存过滤版（仅包含相关关键词）
    items_filtered = fetch(skip_filter=False)
    unique_filtered = list(dict.fromkeys(items_filtered))
    save_to_file(unique_filtered, f'market_context_{today_str}.txt')

    # 保存全量版（无过滤，可了解市场整体氛围）
    items_full = fetch(skip_filter=True)
    unique_full = list(dict.fromkeys(items_full))
    save_to_file(unique_full, f'market_context_full_{today_str}.txt')


if __name__ == '__main__':
    main()