import os, sys, json, time, requests
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
os.makedirs(DATA_DIR, exist_ok=True)

URL = "https://www.cls.cn/nodeapi/updateTelegraphList"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.cls.cn/telegraph'
}

def fetch():
    # 关键修复：hasFirstVipArticle=1，表示已看过VIP，接口才会返回普通电报
    now = int(time.time())
    params = {
        'app': 'CailianpressWeb',
        'hasFirstVipArticle': '1',          # 必须为 1
        'lastTime': str(now - 3600),        # 拉取最近1小时
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
        
        # 普通电报
        roll = data.get('data', {}).get('roll_data', [])
        print(f"[TELEGRAPH] roll_data count: {len(roll)}")
        for item in roll:
            t = item.get('title', '') or item.get('brief', '') or item.get('content', '')[:80]
            if t:
                titles.append(t)
        
        # VIP
        vip = data.get('vipData', [])
        print(f"[TELEGRAPH] vipData count: {len(vip)}")
        for item in vip:
            t = item.get('title', '') or item.get('brief', '')
            if t:
                titles.append(t)
        
        # 全球VIP
        gvip = data.get('vipGlobal', [])
        print(f"[TELEGRAPH] vipGlobal count: {len(gvip)}")
        seen = set(titles)
        for item in gvip:
            t = item.get('title', '') or item.get('brief', '')
            if t and t not in seen:
                titles.append(t)
                seen.add(t)
        
        print(f"[TELEGRAPH] total after merge: {len(titles)}")
        return titles
    except Exception as e:
        print(f"[TELEGRAPH] fetch error: {e}")
        return []

def main():
    today = datetime.now().strftime('%Y%m%d')
    items = fetch()
    unique = list(dict.fromkeys(items))
    
    lines = [f"日期: {today}", "", "=== 产业催化电报（全量） ==="]
    if unique:
        for i, t in enumerate(unique, 1):
            lines.append(f"{i}. {t}")
    else:
        lines.append("今日暂无电报。")
    lines.append("")
    
    out = os.path.join(DATA_DIR, f'market_context_{today}.txt')
    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"[TELEGRAPH] saved to {out}")

if __name__ == '__main__':
    main()