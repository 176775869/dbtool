# coding=utf-8
import os, sys, json, glob, subprocess, logging, time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from datetime import datetime
from dotenv import load_dotenv
import requests as req

load_dotenv()

# 日志配置（UTF-8 编码）
logging.basicConfig(
    filename='server.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    encoding='utf-8'
)

HOST = '0.0.0.0'; PORT = 8080
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 路径准备
sys.path.insert(0, os.path.join(BASE_DIR, 'py', 'core'))
from prompt_builder import resolve_file, build_prompt, DATA_SEARCH_DIRS

CONFIG_PATH = os.path.join(BASE_DIR, 'py', 'config', 'feed_config.json')
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    CONFIG = json.load(f)

_last_collect_time = {}

# 精确的文件名映射（完整路径前缀匹配，避免歧义）
FILE_COLLECTOR_MAP = {
    'index_data_*.txt': 'get_index_only.py',
    'limit_up_*.txt': 'get_limit_up.py',
    'sector_ma_*.txt': 'get_sector_ma.py',   # 必须在 sector_*.txt 之前
    'sector_*.txt': 'get_sector.py',
    'top_amount_*.txt': 'get_top_amount.py',
    'mid_cap_*.txt': 'get_mid_cap.py',
    'zhaban_*.txt': 'get_zhaban.py',
    'limit_down_*.txt': 'get_limit_down.py',
    'qs_pool_*.txt': 'get_qs_pool.py',
    'market_context_*.txt': 'market_context_builder.py',
    'subscription_*.txt': 'get_subscription_data.py',
    'replay_full_*.txt': 'merge_replay.py',
}

def any_file_exists(pattern):
    for d in DATA_SEARCH_DIRS:
        if glob.glob(os.path.join(BASE_DIR, d, pattern)):
            return True
    return False

def run_collector(script_name, force=False):
    interval = CONFIG.get('collectors', {}).get(script_name, 0)
    now = time.time()
    last = _last_collect_time.get(script_name, 0)
    if not force and interval > 0 and (now - last) < interval:
        return True, '跳过 (时间锁)'

    path = os.path.join(BASE_DIR, 'py', 'collectors', script_name)
    if not os.path.exists(path):
        return False, f'脚本不存在: {script_name}'

    try:
        result = subprocess.run(
            ['python', path],
            cwd=BASE_DIR,
            capture_output=True,
            encoding='utf-8',
            timeout=60
        )
        _last_collect_time[script_name] = time.time()
        if result.returncode != 0:
            return False, result.stderr.strip()
        logging.info(f'采集完成: {script_name}')
        return True, ''
    except Exception as e:
        return False, str(e)

def ensure_data_files():
    """检查 replay 所需文件，缺失则运行对应采集脚本"""
    replay_cfg = CONFIG.get('replay', {})
    missing_patterns = []

    for file_ref in replay_cfg.get('files', []):
        if not file_ref.startswith('AUTO_LATEST:'):
            continue
        pattern = file_ref[len('AUTO_LATEST:'):]
        if not any_file_exists(pattern):
            missing_patterns.append(pattern)

    if not missing_patterns:
        return

    print(f"[采集] 需要生成: {missing_patterns}")
    for pattern in missing_patterns:
        script = FILE_COLLECTOR_MAP.get(pattern)
        if not script:
            logging.warning(f'未找到对应脚本: {pattern}')
            continue

        for attempt in range(1, 4):
            print(f"  运行 {script} (第 {attempt}/3 次)")
            success, msg = run_collector(script, force=True)
            if success:
                time.sleep(1)
                if any_file_exists(pattern):
                    print(f"    文件已生成")
                    break
                else:
                    print(f"    脚本成功但未找到文件，等待...")
            else:
                logging.error(f'{script} 失败: {msg}')
            time.sleep(2)
        else:
            raise RuntimeError(f'无法生成 {pattern}，脚本 {script} 多次失败')

class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body) if body else {}
        except:
            data = {}

        if self.path == '/api/collect':
            try:
                for s in CONFIG.get('collectors', {}):
                    run_collector(s, force=True)
                self.send_json(200, {'message': '采集完成'})
            except Exception as e:
                self.send_json(500, {'error': str(e)})
            return

        if self.path == '/api/chat':
            msg = data.get('message', '').strip()
            history = data.get('history', [])
            if not msg: self.send_json(400, {'error': '消息为空'}); return
            if not DEEPSEEK_API_KEY: self.send_json(500, {'error': '无API KEY'}); return
            try:
                sys_prompt = build_prompt('chat')
            except:
                sys_prompt = "助手"
            msgs = [{'role':'system','content':sys_prompt}]
            for h in history[-6:]:
                msgs.append({'role':h.get('role','user'), 'content':h.get('content','')})
            msgs.append({'role':'user','content':msg})
            try:
                r = req.post('https://api.deepseek.com/chat/completions',
                    headers={'Authorization':f'Bearer {DEEPSEEK_API_KEY}','Content-Type':'application/json'},
                    json={'model':'deepseek-chat','messages':msgs,'temperature':0.7,'max_tokens':2000},
                    timeout=60)
                if r.status_code != 200:
                    self.send_json(500, {'error': r.text[:200]}); return
                rep = r.json()['choices'][0]['message']['content']
                self.send_json(200, {'reply': rep})
            except Exception as e:
                logging.error(f"聊天失败: {e}")
                self.send_json(500, {'error': str(e)})
            return

        if self.path == '/api/generate':
            force = data.get('force', False)
            cp = data.get('custom_prompt', None)

            if not force and not cp:
                sf = glob.glob('strategy_*.md')
                if sf:
                    latest = max(sf, key=os.path.getctime)
                    with open(latest, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self.send_json(200, {'file':latest, 'content':content, 'cached':True})
                    return

            try:
                ensure_data_files()
            except Exception as e:
                logging.error(f"数据采集失败: {e}")
                self.send_json(500, {'error': str(e)})
                return

            try:
                env = os.environ.copy()
                if cp: env['CUSTOM_PROMPT'] = cp
                r = subprocess.run(['python', 'py/core/generate_strategy.py'],
                                   cwd=BASE_DIR, capture_output=True, encoding='utf-8', env=env)
                if r.returncode != 0:
                    self.send_json(500, {'error': r.stderr.strip()}); return
                sf = glob.glob('strategy_*.md')
                if not sf: self.send_json(500, {'error':'未找到策略文件'}); return
                latest = max(sf, key=os.path.getctime)
                with open(latest, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.send_json(200, {'file':latest, 'content':content, 'cached':False})
            except Exception as e:
                self.send_json(500, {'error': str(e)})
            return

        if self.path == '/api/monitor':
            try:
                run_collector('get_index_only.py')
                run_collector('get_subscription_data.py')
                from py.core.monitor import check_signals
                self.send_json(200, check_signals())
            except Exception as e:
                logging.error(f"监控失败: {e}")
                self.send_json(500, {'error': str(e)})
            return

        self.send_error(404)

    def send_json(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    os.chdir(BASE_DIR)
    print(f"服务已启动: http://0.0.0.0:{PORT}/tool.html")
    HTTPServer((HOST, PORT), Handler).serve_forever()
