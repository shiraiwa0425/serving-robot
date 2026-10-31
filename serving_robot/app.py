import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from session import Session,Conflict

def make_server(session,port):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def reply(self,status,payload):
            data=json.dumps(payload,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
        def do_GET(self):
            if self.path=='/state':self.reply(200,session.state());return
            if self.path!='/':self.send_error(404);return
            self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(Path(__file__).with_name('index.html').read_bytes())
        def do_POST(self):
            if self.path not in ['/command','/stop','/confirm','/cancel']:self.send_error(404);return
            origin=self.headers.get('Origin')
            if origin not in [None,f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}']:self.send_error(403);return
            try:
                size=int(self.headers.get('Content-Length','0'))
                if size<0 or size>4096:raise ValueError('入力が長すぎます')
                body=json.loads(self.rfile.read(size))
                if not isinstance(body,dict):raise ValueError('JSON object required')
                if self.path=='/command':
                    text=body.get('text')
                    if not isinstance(text,str) or len(text)>500:raise ValueError('指示は500文字以内にしてください')
                    session.command(text)
                elif self.path=='/stop':session.stop()
                else:
                    token=body.get('candidate_id')
                    if not isinstance(token,str):raise ValueError('候補IDが必要です')
                    (session.confirm if self.path=='/confirm' else session.cancel)(token)
            except Conflict as exc:self.reply(409,dict(error=str(exc)));return
            except (ValueError,TypeError) as exc:self.reply(400,dict(error=str(exc)));return
            self.reply(200,dict(ok=True))
    return ThreadingHTTPServer(('127.0.0.1',port),Handler)

def main():
    p=argparse.ArgumentParser();p.add_argument('--backend',choices=['mock','ollama'],default='mock');p.add_argument('--model');p.add_argument('--port',type=int,default=8767);a=p.parse_args()
    session=Session(a.backend,a.model);server=make_server(session,a.port);shutdown=threading.Event()
    def loop():
        while not shutdown.is_set():session.step();shutdown.wait(.01)
    worker=threading.Thread(target=loop,daemon=True);worker.start()
    print(f'http://127.0.0.1:{server.server_port} backend={a.backend}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:shutdown.set();server.server_close();worker.join(timeout=1)
if __name__=='__main__':main()
