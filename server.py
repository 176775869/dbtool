# coding=utf-8
import os, sys, json, glob, subprocess, logging
from http.server import HTTPServer, SimpleHTTPRequestHandler
from datetime import datetime
from dotenv import load_dotenv
import requests as req

load_dotenv()

logging.basicConfig(filename='server.log', level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s')

HOST = '0.0.0.0'
PORT = 8080
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
WORKBOOK_DATA = None

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'py', 'core'))
from prompt_builder import get_auto_collect

def run_collectors():
    base = os.path.dirname(os.path.abspath(__file__))
    collectors_dir = os.path.join(base, 'py', 'collectors')
    scripts = [
        'get_index_only.py','get_sector.py','get_sector_ma.py',
        'get_qs_pool.py','get_limit_up.py','get_zhaban.py',
        'get_limit_down.py','get_top_amount.py','get_mid_cap.py',
        'get_history.py','merge_replay.py','market_context_builder.py',
        'get_subscription_data.py'
    ]
    for s in scripts:
        path = os.path.join(collectors_dir, s)
        if os.path.exists(path):
            subprocess.run(['python', path], cwd=base, capture_output=True, encoding='utf-8')
            logging.info(f'Collected: {s}')

def preload_workbook():
    global WORKBOOK_DATA
    # 保留原逻辑，此处省略

class ReplayHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/workbook':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(WORKBOOK_DATA if WORKBOOK_DATA else {}, ensure_ascii=False).encode('utf-8'))
            return
        super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        try:
            data = json.loads(body) if body else {}
        except:
            data = {}

        if self.path == '/api/collect':
            try:
                run_collectors()
                self.send_json(200, {'message': '采集完成'})
            except Exception as e:
                self.send_json(500, {'error': str(e)})
            return

        if self.path == '/api/chat':
            # ... 略，保持原有逻辑
            pass

        if self.path == '/api/generate':
            force = data.get('force', False)
            custom_prompt = data.get('custom_prompt', None)
            if get_auto_collect() and not force:
                replay_files = glob.glob('py/data/replay_full_*.txt')
                if replay_files:
                    latest = max(replay_files, key=os.path.getmtime)
                    mtime = datetime.fromtimestamp(os.path.getmtime(latest))
                    if mtime.date() != datetime.now().date():
                        logging.info('自动采集数据...')
                        run_collectors()
            if custom_prompt:
                force = True
            if not force:
                strategy_files = glob.glob('strategy_*.md')
                if strategy_files:
                    latest = max(strategy_files, key=os.path.getctime)
                    with open(latest, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self.send_json(200, {'file': latest, 'content': content, 'cached': True})
                    return
            try:
                subprocess.run(['python', 'py/collectors/merge_replay.py'],
                               cwd=os.path.dirname(os.path.abspath(__file__)),
                               capture_output=True, encoding='utf-8')
                env = os.environ.copy()
                if custom_prompt:
                    env['CUSTOM_PROMPT'] = custom_prompt
                result = subprocess.run(['python', 'py/core/generate_strategy.py'],
                                        cwd=os.path.dirname(os.path.abspath(__file__)),
                                        capture_output=True, encoding='utf-8', env=env)
                if result.returncode != 0:
                    error_msg = result.stderr.strip() if result.stderr else "未知错误"
                    self.send_json(500, {'error': error_msg})
                    return
                strategy_files = glob.glob('strategy_*.md')
                if not strategy_files:
                    self.send_json(500, {'error': '未找到策略文件'})
                    return
                latest = max(strategy_files, key=os.path.getctime)
                with open(latest, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.send_json(200, {'file': latest, 'content': content, 'cached': False})
            except Exception as e:
                self.send_json(500, {'error': str(e)})
            return

        if self.path == '/api/monitor':
            try:
                if get_auto_collect():
                    replay_files = glob.glob('py/data/replay_full_*.txt')
                    if replay_files:
                        latest = max(replay_files, key=os.path.getmtime)
                        mtime = datetime.fromtimestamp(os.path.getmtime(latest))
                        if mtime.date() != datetime.now().date():
                            logging.info('监控前自动采集...')
                            run_collectors()
                from monitor import check_signals
                result = check_signals()
                self.send_json(200, result)
            except Exception as e:
                logging.error(f"Monitor error: {e}")
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
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    preload_workbook()
    print(f"Server starting on http://0.0.0.0:{PORT}/tool.html")
    HTTPServer((HOST, PORT), ReplayHandler).serve_forever()
