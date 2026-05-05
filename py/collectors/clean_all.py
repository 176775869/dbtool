"""清理 py/data/ 下过时的临时/中间文件，保留最新必要数据"""
import os, glob, time

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
now = time.time()
# 保留最近 12 小时的 replay_full，其余删除
for f in glob.glob(os.path.join(DATA_DIR, 'replay_full_*.txt')):
    if os.path.getmtime(f) < now - 43200:
        os.remove(f)
        print(f'[clean] 已删除旧 replay: {os.path.basename(f)}')

# 删除所有 feed_ 和 result_ 文件
for pat in ['feed_*.txt', 'result_*.txt', 'subscription_*.txt']:
    for f in glob.glob(os.path.join(DATA_DIR, pat)):
        os.remove(f)
        print(f'[clean] 已删除 {os.path.basename(f)}')

# 删除 2 天前的旧 sector、limit 等数据文件（保留最新即可）
for pat in ['sector_data_*.txt', 'limit_up_data_*.txt', 'zhaban_data_*.txt', 'limit_down_data_*.txt']:
    for f in glob.glob(os.path.join(DATA_DIR, pat)):
        if os.path.getmtime(f) < now - 172800:
            os.remove(f)
            print(f'[clean] 已删除旧数据: {os.path.basename(f)}')

print('[clean] 清理完成')
