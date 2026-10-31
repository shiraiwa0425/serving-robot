"""Explicit live AI/local physics integration, separate from fast unit tests."""
import concurrent.futures,json,math,time,urllib.request
from pathlib import Path
BASE='http://127.0.0.1:8766'
def get():
    with urllib.request.urlopen(BASE+'/state',timeout=5) as r:return json.load(r)
def post(path,text=''):
    t=time.perf_counter();req=urllib.request.Request(BASE+path,data=json.dumps({'text':text}).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=60) as r:r.read()
    return time.perf_counter()-t

def main():
    out=Path('artifacts/live-ai-integration.json')
    if out.exists():raise ValueError('preserve previous run before repeating')
    evidence=[]
    try:
        s=get();assert s['intent']['backend']=='ollama'
        t=post('/command','二番のテーブルまでお願い');s=get();assert s['target']=='table2' and s['status']=='moving',s
        start=s;time.sleep(1);s=get();assert math.dist((s['x'],s['y']),(start['x'],start['y']))>.05,s
        evidence.append(dict(case='AI paraphrase starts physical motion',latency=t,state=s))
        t=post('/command','動くのをやめて');time.sleep(.5);s=get();assert s['status']=='stopped' and s['speed']<.01,s
        evidence.append(dict(case='AI text stop',latency=t,state=s))
        post('/command','1番テーブルへ運んで');time.sleep(.5)
        t=post('/command','1番か2番へ運んで');time.sleep(.5);s=get();assert s['status']=='clarify' and s['speed']<.01,s
        evidence.append(dict(case='AI ambiguity stops and clarifies',latency=t,state=s))
        with concurrent.futures.ThreadPoolExecutor() as pool:
            pending=pool.submit(post,'/command','3番に向かって');time.sleep(.1)
            t=post('/stop');pending.result()
        time.sleep(.5);s=get();assert s['status']=='stopped' and s['target'] is None and s['speed']<.01,s
        evidence.append(dict(case='newer direct stop defeats stale AI result',latency=t,state=s))
        report=dict(success=True,evidence=evidence)
    except Exception as e:
        report=dict(success=False,error=repr(e),evidence=evidence)
        raise
    finally:out.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(dict(success=True,cases=len(evidence)),ensure_ascii=False))
if __name__=='__main__':main()
