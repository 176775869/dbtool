# coding=utf-8
"""
豆包模式精简复盘数据整合脚本 v2
涨停板数据改用 ulist 接口批量拉取，避免 JSONP 解析失败
"""
import sys
import os
import requests
import json
import pandas as pd
from datetime import datetime
import time

# ==================== 核心中军池 ====================
CORE_STOCKS = {
    'CPO': ['300308','300502','300394'],
    '光纤/光通信': ['601869','600487','600522'],
    '算力': ['002230','000977','603019'],
    '商业航天': ['600118','000547','002025'],
    '固态电池': ['300750','002074','002709'],
    '锂电池': ['300750','002074','002460'],
    '机器人': ['300124','002527','300024'],
}

ALL_CODES = list(set(code for codes in CORE_STOCKS.values() for code in codes))

# ==================== 通用 ulist 请求函数 ====================
def fetch_stocks_by_ulist(code_list, extra_fields=''):
    """
    通过 ulist 接口一次性拉取指定股票列表的行情
    extra_fields: 额外的字段，如 'f250,f251,f136' 用于获取连板数和封单额
    """
    if not code_list:
        return pd.DataFrame()

    secids = []
    for code in code_list:
        prefix = '1.' if code.startswith('6') else '0.'
        secids.append(f'{prefix}{code}')
    secids_str = ','.join(secids)

    fields = 'f2,f3,f4,f5,f6,f7,f8,f12,f14,f15,f16,f17,f18'
    if extra_fields:
        fields += ',' + extra_fields

    url = (
        f"http://push2.eastmoney.com/api/qt/ulist.np/get?"
        f"fltt=2&secids={secids_str}&fields={fields}&"
        f"ut=bd1d9ddb04089700cf9c27f6f7426281"
    )

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.79 Safari/537.36',
        'Referer': 'https://quote.eastmoney.com/'
    }

    for attempt in range(5):
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.encoding = 'utf-8'
            data = json.loads(resp.text)
            if data.get('data') and data['data'].get('diff'):
                df = pd.DataFrame(data['data']['diff'])
                rename_map = {
                    'f2': 'close', 'f3': 'zhangfu', 'f4': 'zhangdie',
                    'f5': 'volume', 'f6': 'amount', 'f7': 'zhenfu',
                    'f8': 'hs_l', 'f12': 'code', 'f14': 'name',
                    'f15': 'high', 'f16': 'low', 'f17': 'open', 'f18': 'pre_close'
                }
                # 额外字段
                if 'f250' in df.columns:
                    rename_map['f250'] = 'limit_times'
                if 'f251' in df.columns:
                    rename_map['f251'] = 'first_time'
                if 'f136' in df.columns:
                    rename_map['f136'] = 'seal_amount'
                df = df.rename(columns=rename_map)
                for col in ['close','zhangfu','amount','high','low','limit_times','seal_amount']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                return df
        except Exception as e:
            print(f"ulist请求失败，重试... {str(e)[:40]}")
            time.sleep(2)
    return pd.DataFrame()


# ==================== 主程序 ====================
if __name__ == '__main__':
    date_str = datetime.now().strftime('%Y%m%d')

    # 1. 检查已有文件
    index_file = f'index_data_{date_str}.txt'
    sector_file = f'sector_data_{date_str}.txt'
    for f in [index_file, sector_file]:
        if not os.path.exists(f):
            print(f"缺少文件 {f}")
            sys.exit(1)

    with open(index_file, 'r', encoding='utf-8') as f:
        index_content = f.read()
    with open(sector_file, 'r', encoding='utf-8') as f:
        sector_content = f.read()

    # 2. 获取核心中军数据（不含连板字段，因为中军不是连板股）
    print("正在获取核心中军数据...")
    midcap_df = fetch_stocks_by_ulist(ALL_CODES)
    print(f"获取到 {len(midcap_df)} 只中军数据")

    # 3. 从中军数据里找出涨停的，再从板块领涨股里挑几个涨停的，一起查询连板信息
    # 3.1 中军里的涨停股
    limit_codes_from_mid = midcap_df[midcap_df['zhangfu'] >= 9.8]['code'].tolist()

    # 3.2 从板块领涨股里提取代码（领涨股大概率是涨停的）
    leader_codes = []
    for line in sector_content.split('\n'):
        if '领涨:' in line:
            # 尝试提取股票代码
            parts = line.split('领涨:')
            if len(parts) > 1:
                name = parts[1].strip()
                # 从板块数据无法直接拿到代码，跳过，只用中军里的涨停股
                pass

    # 3.3 合并所有需要查询连板信息的涨停股代码
    all_limit_codes = list(set(limit_codes_from_mid))

    # 3.4 用 ulist 获取这些涨停股的连板数据
    limit_df = pd.DataFrame()
    if all_limit_codes:
        print(f"正在获取 {len(all_limit_codes)} 只涨停股的连板数据...")
        limit_df = fetch_stocks_by_ulist(all_limit_codes, extra_fields='f250,f251,f136')
        # 只保留真正涨停的（涨幅>=9.8%）
        if not limit_df.empty:
            limit_df = limit_df[limit_df['zhangfu'] >= 9.8]
            print(f"确认涨停股: {len(limit_df)} 只")
    else:
        print("未从中军中找到涨停股")

    # 4. 输出完整复盘数据包
    output_file = f'replay_full_{date_str}.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(index_content)
        f.write("\n\n")

        # 涨停板概览
        f.write("=" * 50 + "\n")
        f.write(f"【涨停板概览】从中军/领涨股中识别到 {len(limit_df)} 只涨停\n")
        if not limit_df.empty:
            max_limit = limit_df['limit_times'].max() if 'limit_times' in limit_df else 0
            if max_limit > 0:
                max_row = limit_df[limit_df['limit_times'] == max_limit].iloc[0]
                f.write(f"最高连板: {max_row['name']}({max_row['code']}) {int(max_limit)}连板\n")
            f.write("\n涨停详情:\n")
            for _, row in limit_df.iterrows():
                seal = row.get('seal_amount', 0)
                seal_str = f"封单{seal/1e8:.2f}亿" if seal and not pd.isna(seal) and seal > 0 else ""
                first = row.get('first_time', '--')
                lt = int(row.get('limit_times', 0)) if not pd.isna(row.get('limit_times', 0)) else 0
                f.write(f"  {row['name']}({row['code']}) {row['zhangfu']:.1f}% "
                        f"连板{lt}天 首封{first} {seal_str}\n")
        f.write("\n")

        # 板块数据
        f.write("=" * 50 + "\n")
        f.write(sector_content)
        f.write("\n")

        # 核心中军表现
        f.write("=" * 50 + "\n")
        f.write("【核心中军表现】\n")
        for category, codes in CORE_STOCKS.items():
            f.write(f"\n{category}:\n")
            for code in codes:
                row = midcap_df[midcap_df['code'] == code]
                if not row.empty:
                    r = row.iloc[0]
                    direction = "+" if r['zhangfu'] > 0 else ""
                    f.write(f"  {r['name']}({code}): {r['close']:.2f} "
                            f"{direction}{r['zhangfu']:.2f}% 成交{r['amount']/1e8:.2f}亿\n")
                else:
                    f.write(f"  {code}: 未获取到数据\n")

    print(f"\n完整复盘数据包已保存至 {output_file}")
    print("内容预览：")
    with open(output_file, 'r', encoding='utf-8') as f:
        print(f.read()[:800])