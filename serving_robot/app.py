import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from sim import Simulation
from intent import infer


def main():
    p=argparse.ArgumentParser(); p.add_argument('--backend',choices=['mock','ollama'],default='mock'); p.add_argument('--model'); p.add_argument('--port',type=int,default=8765); a=p.parse_args()
    sim=Simulation(); lock=threading.Lock(); last={'backend':a.backend,'model':a.model,'message':'行先を入力してください。' + ('mock は AI 推論ではありません。' if a.backend=='mock' else 'このMacのローカルAIで解釈します。')}
    def loop():
        while True:
            with lock: sim.step()
            time.sleep(.01)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_GET(self):
            if self.path=='/':
                data=Path(__file__).with_name('index.html').read_bytes(); content='text/html; charset=utf-8'
            elif self.path=='/state':
                with lock: data=json.dumps(dict(sim.state(),intent=last)).encode()
                content='application/json'
            else: self.send_error(404); return
            self.send_response(200); self.send_header('Content-Type',content); self.end_headers(); self.wfile.write(data)
        def do_POST(self):
            if self.path not in ['/command','/stop']: self.send_error(404); return
            if self.headers.get('Origin') not in [None,f'http://127.0.0.1:{a.port}',f'http://localhost:{a.port}']: self.send_error(403); return
            size=int(self.headers.get('Content-Length','0'))
            if not 0<=size<=4096: self.send_error(413); return
            try:
                text=json.loads(self.rfile.read(size)).get('text','')
                if not isinstance(text,str): raise ValueError('text must be a string')
            except Exception: self.send_error(400); return
            # Every new utterance cancels the previous path BEFORE potentially slow inference.
            # Epoch guards ensure an in-flight reply can never undo a newer stop/command.
            with lock:
                sim.stop(); last['epoch']=last.get('epoch',0)+1; epoch=last['epoch']; last['message']='解釈中：停止しています'
            started=time.perf_counter()
            try:
                value={'action':'stop','goal':None} if self.path=='/stop' else infer(text,a.backend,a.model)
                with lock:
                    if epoch==last['epoch']:
                        if value['action']=='move': sim.go(value['goal'])
                        elif value['action']=='clarify': sim.status='clarify'
                        last.update(value,latency_seconds=time.perf_counter()-started,message='行先を一つ、明確に指定してください' if value['action']=='clarify' else value['action'])
            except Exception as e:
                with lock:
                    if epoch==last['epoch']: sim.stop(); last['latency_seconds']=time.perf_counter()-started; last['message']='推論または計画エラー：停止しました ('+type(e).__name__+')'
            self.send_response(200); self.end_headers(); self.wfile.write(b'{}')
    server=ThreadingHTTPServer(('127.0.0.1',a.port),Handler)
    threading.Thread(target=loop,daemon=True).start()
    print(f'http://127.0.0.1:{a.port} backend={a.backend}',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
if __name__=='__main__': main()
