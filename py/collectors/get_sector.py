# coding=utf-8
"""板块数据采集。行业板块+概念板块。动态追加跟踪方向。"""
import requests, json, time, os, re, glob
from datetime import datetime

def get_output_path(filename):
    data_dir = os.path.join(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"), '..', 'data')
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, filename)

def _get_tracking_keys():
    """从最新策略文件提取纯中文跟踪方向（避免特殊符号）"""
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
    root = os.path.join(base, '..', '..')
    files = glob.glob(os.path.join(root, 'strategy_*.md'))
    if not files:
        return []
    latest = max(files, key=os.path.getmtime)
    with open(latest, 'r', encoding='utf-8') as f:
        text = f.read()
    keys = set()
    for line in text.split('\n'):
        if '锚点' in line or '候选' in line:
            matches = re.findall(r'[\u4e00-\u9fff]{2,}', line)
            for m in matches:
                if m not in ('正式锚点','并行锚点','预置锚点','候选池','窗口期','阶段标记','主线候选','方向名','仓','阶段'):
                    keys.add(m)
    return list(keys)

def fetch_concept_sectors():
    url = ("https://push2.eastmoney.com/api/qt/clist/get?"
           "cb=cb&fid=f62&po=1&pz=10000&pn=1&np=1&fltt=2&invt=2"
           "&ut=8dec03ba335b81bf4ebdf7b29ec27d15"
           "&fs=m:90+t:3"
           "&fields=f12,f14,f2,f3,f4,f6,f62,f128,f104,f105")
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://quote.eastmoney.com/'}
    for _ in range(5):
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.encoding = 'utf-8'
            text = resp.text
            if '(' in text and ')' in text:
                text = text[text.index('(')+1:text.rindex(')')]
            data = json.loads(text)
            if data.get('data') and data['data'].get('diff'):
                return data['data']['diff']
            time.sleep(2)
        except Exception as e:
            print(f"[概念错误] {e}")
            time.sleep(2)
    return []

def fetch_industry_sectors():
    url = ("https://push2.eastmoney.com/api/qt/clist/get?"
           "np=1&fltt=1&invt=2&cb=cb"
           "&fs=m:90+t:2+f:!50"
           "&fields=f12,f14,f2,f3,f4,f6,f20,f104,f105,f128,f140,f62"
           "&fid=f3&pn=1&pz=10000&po=1&dect=1"
           "&ut=fa5fd1943c7b386f172d6893dbfba10b")
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://quote.eastmoney.com/'}
    for _ in range(5):
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.encoding = 'utf-8'
            text = resp.text
            if '(' in text and ')' in text:
                text = text[text.index('(')+1:text.rindex(')')]
            data = json.loads(text)
            if data.get('data') and data['data'].get('diff'):
                return data['data']['diff']
            time.sleep(2)
        except Exception as e:
            print(f"[行业错误] {e}")
            time.sleep(2)
    return []

def append_tracking_sectors(filename, industry_list, concept_list):
    keys = _get_tracking_keys()
    if not keys:
        return
    track_con = [it for it in concept_list if any(k in it.get('f14','') for k in keys)]
    track_ind = [it for it in industry_list if any(k in it.get('f14','') for k in keys)]
    if not track_con and not track_ind:
        return
    with open(filename, 'a', encoding='utf-8') as f:
        if track_con:
            f.write("\n=== 跟踪方向概念板块 ===\n")
            for it in track_con:
                nm = it.get('f14',''); ch = float(it.get('f3',0))
                amt = float(it.get('f6',0))/1e8 if it.get('f6','')!='' else 0
                ld = it.get('f128',''); uc = it.get('f104','?'); dc = it.get('f105','?')
                net = float(it.get('f62',0) or 0)/1e8
                f.write(f"{nm}: {ch:+.2f}% 成交{amt:.1f}亿 涨{uc}/跌{dc} 主力净流入{net:.2f}亿 领涨:{ld}\n")
        if track_ind:
            f.write("\n=== 跟踪方向行业板块 ===\n")
            for it in track_ind:
                nm = it.get('f14',''); ch = float(it.get('f3',0))
                amt = float(it.get('f6',0))/1e8 if it.get('f6','')!='' else 0
                ld = it.get('f128',''); uc = it.get('f104','?'); dc = it.get('f105','?')
                net = float(it.get('f62',0) or 0)/1e8
                f.write(f"{nm}: {ch:+.2f}% 成交{amt:.1f}亿 涨{uc}/跌{dc} 主力净流入{net:.2f}亿 领涨:{ld}\n")

if __name__ == '__main__':
    date_str = datetime.now().strftime('%Y%m%d')
    print("获取行业板块...")
    industry_list = fetch_industry_sectors()
    print(f"行业板块数量: {len(industry_list)}")
    time.sleep(1)
    print("获取概念板块...")
    concept_list = fetch_concept_sectors()
    print(f"概念板块数量: {len(concept_list)}")

    filename = get_output_path(f'sector_data_{date_str}.txt')
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"日期: {date_str}\n")
        f.write("\n=== 行业板块涨幅前15 ===\n")
        for item in sorted(industry_list, key=lambda x: float(x.get('f3',0)), reverse=True)[:15]:
            nm = item.get('f14',''); ch = float(item.get('f3',0))
            amt = float(item.get('f6',0))/1e8 if item.get('f6','')!='' else 0
            ld = item.get('f128',''); uc = item.get('f104','?'); dc = item.get('f105','?')
            net = float(item.get('f62',0) or 0)/1e8
            f.write(f"{nm}: {ch:+.2f}% 成交{amt:.1f}亿 涨{uc}/跌{dc} 主力净流入{net:.2f}亿 领涨:{ld}\n")
        f.write("\n=== 概念板块涨幅前20 ===\n")
        for item in sorted(concept_list, key=lambda x: float(x.get('f3',0)), reverse=True)[:20]:
            nm = item.get('f14',''); ch = float(item.get('f3',0))
            amt = float(item.get('f6',0))/1e8 if item.get('f6','')!='' else 0
            ld = item.get('f128',''); uc = item.get('f104','?'); dc = item.get('f105','?')
            net = float(item.get('f62',0) or 0)/1e8
            f.write(f"{nm}: {ch:+.2f}% 成交{amt:.1f}亿 涨{uc}/跌{dc} 主力净流入{net:.2f}亿 领涨:{ld}\n")

    print(f"数据已保存至 {filename}")
    append_tracking_sectors(filename, industry_list, concept_list)
    print("完成。")
