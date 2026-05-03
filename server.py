# coding=utf-8
import os, sys, json, glob, subprocess, logging, time, re
from http.server import HTTPServer, SimpleHTTPRequestHandler
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests as req

load_dotenv()

logging.basicConfig(filename='server.log', level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s')

HOST = '0.0.0.0'; PORT = 8080
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 路径准备
sys.path.insert(0, os.path.join(BASE_DIR, 'py', 'core'))
from prompt_builder import build_prompt
from memory_manager import call_with_memory  # 共享记忆调用

CONFIG_PATH = os.path.join(BASE_DIR, 'py', 'config', 'feed_config.json')
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    CONFIG = json.load(f)

_last_collect_time = {}
DATA_DIRS = ['py/data', 'py/collectors']

FILE_COLLECTOR_MAP = {
    'index_data_*.txt': 'get_index_only.py',
    'limit_up_*.txt': 'get_limit_up.py',
    'sector_ma_*.txt': 'get_sector_ma.py',
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
    for d in DATA_DIRS:
        if glob.glob(os.path.join(BASE_DIR, d, pattern)):
            return True
    return False

def run_collector(script_name, force=False):
    interval = CONFIG.get('collectors', {}).get(script_name, 0)
    now = time.time()
    last = _last_collect_time.get(script_name, 0)
    if not force and interval > 0 and (now - last) < interval:
        return True
    path = os.path.join(BASE_DIR, 'py', 'collectors', script_name)
    if not os.path.exists(path):
        return False
    try:
        result = subprocess.run(['python', path], cwd=BASE_DIR, capture_output=True, encoding='utf-8', timeout=60)
        _last_collect_time[script_name] = time.time()
        if result.returncode != 0:
            logging.error(f'{script_name} 失败: {result.stderr.strip()}')
            return False
        logging.info(f'采集完成: {script_name}')
        return True
    except Exception as e:
        logging.error(f'{script_name} 异常: {e}')
        return False

def ensure_data_files():
    """检查 replay 所需文件，缺失则运行对应采集脚本"""
    missing = []
    for fr in CONFIG.get('replay', {}).get('files', []):
        if fr.startswith('AUTO_LATEST:'):
            pat = fr[len('AUTO_LATEST:'):]
            if not any_file_exists(pat):
                missing.append(pat)
    if not missing:
        return
    print(f"需要生成: {missing}")
    for pat in missing:
        script = FILE_COLLECTOR_MAP.get(pat)
        if not script:
            continue
        for attempt in range(3):
            if run_collector(script, force=True):
                time.sleep(1)
                if any_file_exists(pat):
                    break
            time.sleep(2)
        if not any_file_exists(pat):
            raise RuntimeError(f'无法生成 {pat}')

# ---------- HTTP 服务 ----------
class ReplayHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/.well-known/'):
            self.send_error(404)
            return
        if self.path == '/api/workbook':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({}, ensure_ascii=False).encode('utf-8'))
            return
        super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        try:
            data = json.loads(body) if body else {}
        except:
            data = {}

        # ========== 聊天（使用共享记忆） ==========
        if self.path == '/api/chat':
            msg = data.get('message', '').strip()
            if not msg:
                self.send_json(400, {'error': '消息为空'})
                return
            # 获取聊天场景的 system_prompt（豆包规则）
            try:
                chat_system = build_prompt('chat')
            except:
                chat_system = "你是一个精通豆包模式交易系统的助手。"
            reply = call_with_memory('chat', msg, temperature=0.7, max_tokens=2000,
                          use_memory=CONFIG.get('chat', {}).get('use_shared_memory', True),
                          max_memory_items=CONFIG.get('chat', {}).get('max_memory_items', 40),
                          memory_content=msg,
                          system_prompt=chat_system)
            print(f"[Token] 聊天 | 用户 {len(msg)}字符 | 预估token ~{len(msg)//2}")
            self.send_json(200, {'reply': reply})
            return

        # ========== 策略生成 ==========
        if self.path == '/api/generate':
            force = data.get('force', False)
            cp = data.get('custom_prompt', None)

            # 缓存逻辑
            if not force and not cp:
                sf = glob.glob('strategy_*.md')
                if sf:
                    latest = max(sf, key=os.path.getctime)
                    with open(latest, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self.send_json(200, {'file': latest, 'content': content, 'cached': True})
                    return

            try:
                ensure_data_files()
            except Exception as e:
                self.send_json(500, {'error': str(e)})
                return

            # 构建并发送 Prompt
            user_prompt = build_prompt('replay', extra_note=cp)
            ai_reply = call_with_memory('replay', user_prompt, temperature=0.1, max_tokens=8192,
                          use_memory=CONFIG.get('replay', {}).get('use_shared_memory', True),
                          max_memory_items=CONFIG.get('replay', {}).get('max_memory_items', 40),
                          memory_content=cp if cp else '自动复盘')
            print(f"[Token] 复盘 | 用户 {len(user_prompt)}字符 | 预估token ~{len(user_prompt)//2}")

            # 保存策略文件
            today = datetime.now().strftime('%Y%m%d')
            next_date = (datetime.strptime(today, '%Y%m%d') + timedelta(days=1)).strftime('%Y%m%d')
            out_file = os.path.join(BASE_DIR, f'strategy_{next_date}.md')
            with open(out_file, 'w', encoding='utf-8') as f:
                f.write(ai_reply)

            self.send_json(200, {'file': out_file, 'content': ai_reply, 'cached': False})
            return

        # ========== 监控 ==========
        if self.path == '/api/monitor':
            try:
                run_collector('get_index_only.py')
                run_collector('get_subscription_data.py')
                user_prompt = build_prompt('monitor')
                ai_reply = call_with_memory('monitor', user_prompt, temperature=0.1, max_tokens=2048,
                              use_memory=CONFIG.get('monitor', {}).get('use_shared_memory', True),
                              max_memory_items=CONFIG.get('monitor', {}).get('max_memory_items', 40),
                              memory_content='定时监控（无特殊指令）')
                print(f"[Token] 监控 | 用户 {len(user_prompt)}字符 | 预估token ~{len(user_prompt)//2}")
                # 解析 JSON 结果
                try:
                    match = re.search(r'\{.*\}', ai_reply, re.DOTALL)
                    if match:
                        parsed = json.loads(match.group())
                        parsed['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        self.send_json(200, parsed)
                    else:
                        self.send_json(200, {"signals": [], "summary": ai_reply[:200]})
                except:
                    self.send_json(200, {"signals": [], "summary": ai_reply[:200]})
            except Exception as e:
                logging.error(f"监控错误: {e}")
                self.send_json(500, {'error': str(e)})
            return

        # ========== 手动全量采集 ==========
        if self.path == '/api/collect':
            try:
                for s in CONFIG.get('collectors', {}):
                    run_collector(s, force=True)
                self.send_json(200, {'message': '采集完成'})
            except Exception as e:
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
    print(f"服务启动: http://0.0.0.0:{PORT}/tool.html")
    HTTPServer((HOST, PORT), ReplayHandler).serve_forever()