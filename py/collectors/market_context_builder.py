import os, sys, json, time, requests
from datetime import datetime

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
    '关税', '监管', '问询', '重组', '借壳', '年报', '一季报', '半年报',
    '通威', '宁德', '比亚迪', '5G', '6G', '数据中心', '服务器', '液冷',
    '光刻', 'EDA', 'IP', 'FPGA', '碳化硅', 'IGBT', 'MCU', 'MOSFET',
    '风电', '光伏组件', 'BIPV', 'HJT', 'TOPCon', '钙钛矿', '储能变流器',
    '氢能', '燃料电池', '电解槽', '充电桩', '换电', '铜箔', '铝箔',
    '薄膜', '聚丙烯', '锂电隔膜', '电解液', '负极材料', '正极材料',
    '磷酸铁锂', '三元锂', '钠电池', '半固态', '全固态',
    '减速器', '伺服电机', '控制器', '机器视觉', '激光雷达',
    '航天发动机', '导弹', '隐身', '雷达', '电子对抗'
]

def is_relevant(title):
    """判断电报是否与A股主线相关"""
    for kw in KEYWORDS:
        if kw in title:
            return True
    return False

def fetch():
    now = int(time.time())
    params = {
        'app': 'CailianpressWeb',
        'hasFirstVipArticle': '1',
        'lastTime': str(now - 3600),
        'os': 'web',
        'rn': '60',
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
        
        # 普通电报：过滤不相关的
        roll = data.get('data', {}).get('roll_data', [])
        print(f"[TELEGRAPH] roll_data: {len(roll)} raw")
        kept = 0
        for item in roll:
            t = item.get('title', '') or item.get('brief', '') or item.get('content', '')[:80]
            if t and is_relevant(t):
                titles.append(t)
                kept += 1
        print(f"[TELEGRAPH] roll_data: {kept} kept (filtered)")
        
        # VIP：全部保留，加标记
        vip = data.get('vipData', [])
        print(f"[TELEGRAPH] vipData: {len(vip)} raw")
        for item in vip:
            t = item.get('title', '') or item.get('brief', '')
            if t:
                titles.append(f"[VIP] {t}")
        
        # 全球VIP：去重后保留
        gvip = data.get('vipGlobal', [])
        print(f"[TELEGRAPH] vipGlobal: {len(gvip)} raw")
        seen = set(titles)
        for item in gvip:
            t = item.get('title', '') or item.get('brief', '')
            if t and f"[VIP] {t}" not in seen:
                titles.append(f"[全球] {t}")
                seen.add(f"[全球] {t}")
        
        print(f"[TELEGRAPH] total: {len(titles)}")
        return titles
    except Exception as e:
        print(f"[TELEGRAPH] error: {e}")
        return []

def main():
    today = datetime.now().strftime('%Y%m%d')
    items = fetch()
    unique = list(dict.fromkeys(items))
    
    lines = [f"日期: {today}", "", "=== 产业催化电报 ==="]
    if unique:
        for i, t in enumerate(unique, 1):
            lines.append(f"{i}. {t}")
    else:
        lines.append("今日暂无相关电报。")
    lines.append("")
    
    out = os.path.join(DATA_DIR, f'market_context_{today}.txt')
    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"[TELEGRAPH] saved to {out}")

if __name__ == '__main__':
    main()
