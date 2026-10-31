"""Explicit integration against the isolated real-AI preview, never the old app."""
import concurrent.futures,json,math,time,urllib.request,urllib.error
from pathlib import Path
BASE='http://127.0.0.1:8767'
def state():
    with urllib.request.urlopen(BASE+'/state',timeout=5) as r:return json.load(r)
def post(path,data=None):
    req=urllib.request.Request(BASE+path,data=json.dumps(data or {}).encode(),headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=60) as r:return r.status
    except urllib.error.HTTPError as e:return e.code

def main():
    out=Path(__file__).parent/'artifacts/spatial-live-v1.json'
    if out.exists():raise ValueError('do not overwrite previous evidence')
    evidence=[];success=False
    try:
        assert state()['intent']['backend']=='ollama'
        assert post('/command',{'text':'2番テーブルと3番テーブルの間へ'})==200
        s=state();c=s['candidate'];assert c and s['status']=='awaiting_confirmation' and not s['path'];before=(s['x'],s['y']);time.sleep(.6);s=state();assert math.dist(before,(s['x'],s['y']))<.01
        evidence.append(dict(case='AI between candidate, stationary until confirmation',state=s))
        assert post('/confirm',{'candidate_id':c['id']})==200;assert post('/confirm',{'candidate_id':c['id']})==409
        time.sleep(1);s=state();assert s['status']=='moving' and math.dist(before,(s['x'],s['y']))>.05;evidence.append(dict(case='confirmed actual physics movement and duplicate rejected',state=s))
        post('/stop');time.sleep(.6);s=state();assert s['status']=='stopped' and s['speed']<.01
        assert post('/command',{'text':'1番の近くへ'})==200;s=state();assert s['candidate']['relation']=='near';assert post('/cancel',{'candidate_id':s['candidate']['id']})==200;assert state()['candidate'] is None
        evidence.append(dict(case='near and cancellation',state=state()))
        post('/command',{'text':'部屋の右下へ'});s=state();assert s['candidate']['corner']=='bottom_right';assert s['candidate']['adjustment_m']>.1;evidence.append(dict(case='corner adjusted around table obstacle',state=s))
        old=s['candidate']['id'];post('/command',{'text':'2番と3万の間へ'});s=state();assert s['candidate'] is None and s['status']=='clarify';assert post('/confirm',{'candidate_id':old})==409
        evidence.append(dict(case='typo not guessed; old candidate invalid',state=s))
        with concurrent.futures.ThreadPoolExecutor() as pool:
            pending=pool.submit(post,'/command',{'text':'左上の角へ'});time.sleep(.08);post('/stop');pending.result()
        s=state();assert s['status']=='stopped' and s['candidate'] is None;evidence.append(dict(case='stop wins over in-flight real AI',state=s));success=True
    finally:
        post('/stop');out.write_text(json.dumps(dict(success=success,evidence=evidence),ensure_ascii=False,indent=2))
    print(json.dumps(dict(success=success,cases=len(evidence))))
if __name__=='__main__':main()
