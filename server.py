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

sys.path.insert(0, os.path.join(BASE_DIR, 'py', 'core'))
from prompt_builder import build_prompt
from memory_manager import call_with_memory
from collector_scheduler import should_collect

CONFIG_PATH = os.path.join(BASE_DIR, 'py', 'config', 'feed_config.json')
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    CONFIG = json.load(f)

# 调度由 collector_scheduler.should_collect 统一管理

def run_collector(script_name, force=False):
    """运行采集脚本，调度决策由 collector_scheduler.should_collect 控制"""
    path = os.path.join(BASE_DIR, 'py', 'collectors', script_name)
    if not os.path.exists(path):
        return False
    try:
        result = subprocess.run(['python', path], cwd=BASE_DIR, capture_output=True, encoding='utf-8', timeout=60)
        if result.returncode != 0:
            logging.error(f'{script_name} 失败: {result.stderr.strip()}')
            return False
        logging.info(f'采集完成: {script_name}')
        return True
    except Exception as e:
        logging.error(f'{script_name} 异常: {e}')
        return False

# ensure_data_files 已废弃，采集调度由 collector_scheduler.should_collect 接管

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

        # ========== 聊天 ==========
        if self.path == '/api/chat':
            msg = data.get('message', '').strip()
            if not msg:
                self.send_json(400, {'error': '消息为空'})
                return

            # build_prompt 返回 (system_prompt, user_prompt) 元组
            prompt_tuple = build_prompt('chat')
            # 把元组作为 user_content 传给 call_with_memory
            reply = call_with_memory('chat', prompt_tuple,
                          use_memory=CONFIG.get('chat', {}).get('use_shared_memory', True),
                          max_memory_items=CONFIG.get('chat', {}).get('max_memory_items', 40),
                          memory_content=msg)
            print(f"[Token] 聊天 | 用户 {len(msg)}字符 | 预估token ~{len(msg)//2}")
            self.send_json(200, {'reply': reply})
            return

        # ========== 策略生成 ==========
        if self.path == '/api/generate':
            force = data.get('force', False)
            cp = data.get('custom_prompt', None)
            if not force and not cp:
                sf = glob.glob('strategy_*.md')
                if sf:
                    latest = max(sf, key=os.path.getctime)
                    with open(latest, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self.send_json(200, {'file': latest, 'content': content, 'cached': True})
                    return

            # 复盘前强制全量采集
            for s, interval in CONFIG.get('collectors', {}).items():
                if should_collect(s, interval, force=True):
                    run_collector(s, force=True)
            # build_prompt 返回 (system_prompt, user_prompt) 元组
            prompt_tuple = build_prompt('replay', extra_note=cp)
            reply = call_with_memory('replay', prompt_tuple,
                          use_memory=CONFIG.get('replay', {}).get('use_shared_memory', True),
                          max_memory_items=CONFIG.get('replay', {}).get('max_memory_items', 40),
                          memory_content=cp if cp else '自动复盘')
            print(f"[Token] 复盘 | 用户 {len(prompt_tuple[1]) if isinstance(prompt_tuple, tuple) else len(prompt_tuple)}字符")

            today = datetime.now().strftime('%Y%m%d')
            next_date = (datetime.strptime(today, '%Y%m%d') + timedelta(days=1)).strftime('%Y%m%d')
            out_file = os.path.join(BASE_DIR, f'strategy_{next_date}.md')
            with open(out_file, 'w', encoding='utf-8') as f:
                f.write(reply)
            self.send_json(200, {'file': out_file, 'content': reply, 'cached': False})
            return

        # ========== 监控 ==========
        if self.path == '/api/monitor':
            print("[MONITOR] 收到前端监控请求")
            try:
                for s, interval in CONFIG.get('collectors', {}).items():
                    if should_collect(s, interval, force=False):
                        run_collector(s, force=True)
                prompt_tuple = build_prompt('monitor')
                reply = call_with_memory('monitor', prompt_tuple,
                          use_memory=False,
                          max_memory_items=0,
                          memory_content=None)
                user_len = len(prompt_tuple[1]) if isinstance(prompt_tuple, tuple) else len(prompt_tuple)
                print(f"[Token] 监控 | 用户 {user_len}字符 | 预估token ~{user_len//2}")
                try:
                    match = re.search(r'\{.*\}', reply, re.DOTALL)
                    if match:
                        parsed = json.loads(match.group())
                        parsed['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        self.send_json(200, parsed)
                    else:
                        self.send_json(200, {"reply": reply})
                except:
                    self.send_json(200, {"reply": reply})
            except Exception as e:
                logging.error(f"监控错误: {e}")
                self.send_json(500, {'error': str(e)})
            return

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