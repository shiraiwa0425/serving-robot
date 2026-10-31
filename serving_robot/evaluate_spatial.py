"""Spatial development set, deliberately separate from historical 20+15 cases."""
import argparse,hashlib,json,time,statistics
from pathlib import Path
from spatial_intent import interpret,evidence,PROMPT
CASES=[('2番テーブルと3番テーブルの間へ','between',['table2','table3'],'none'),('1番と2番の間へ','between',['table1','table2'],'none'),('三番と一番の間へ','between',['table1','table3'],'none'),('1番の近くへ','near',['table1'],'none'),('二番のそばに来て','near',['table2'],'none'),('三番の付近までお願い','near',['table3'],'none'),('部屋の右上へ','corner',[],'top_right'),('左上の角へ','corner',[],'top_left'),('右下の角に行こう','corner',[],'bottom_right'),('部屋の左下へ','corner',[],'bottom_left'),('一番へ配膳して','landmark',['table1'],'none'),('2番テーブルへ運んで','landmark',['table2'],'none'),('三番卓に届けて','landmark',['table3'],'none'),('厨房へ戻って','landmark',['kitchen'],'none')]
AMBIGUOUS=['2番と3万の間へ','12番の近くへ','どこかの角へ','右上か左下へ','1番の右隣へ','1番と2番と3番の間へ','2番には行かないで','座標(2,3)に向かって']
def main():
    p=argparse.ArgumentParser();p.add_argument('--run',default='v1');a=p.parse_args()
    if a.run not in ['v1','v2']:raise ValueError('explicit run label required')
    root=Path(__file__).parent/'artifacts';out=root/f'spatial-ai-{a.run}.json'
    if out.exists():raise ValueError('preserve previous result')
    cases=[dict(text=t,expected=dict(action='move',relation=r,landmarks=refs,corner=c)) for t,r,refs,c in CASES]
    cases += [dict(text=t,expected=dict(action='clarify',relation='none',landmarks=[],corner='none')) for t in AMBIGUOUS]
    manifest=root/'spatial-cases-fixed.json'
    if not manifest.exists():manifest.write_text(json.dumps(cases,ensure_ascii=False,indent=2))
    if json.loads(manifest.read_text())!=cases:raise ValueError('fixed cases changed')
    rows=[]
    for case in cases:
        start=time.perf_counter();error=None
        try:detail=interpret(case['text'],'ollama','qwen3:1.7b')
        except Exception as exc:error=type(exc).__name__;detail=dict(final=None,raw=None)
        rows.append(dict(case,details=detail,error=error,seconds=time.perf_counter()-start,final_correct=detail['final']==case['expected'],raw_correct=detail['raw']==case['expected']))
        print(json.dumps(rows[-1],ensure_ascii=False),flush=True)
    report=dict(run=a.run,model='qwen3:1.7b',count=len(rows),final_correct=sum(x['final_correct'] for x in rows),raw_correct=sum(x['raw_correct'] for x in rows),unsafe_moves=sum(x['details']['final'] is not None and x['details']['final']['action']=='move' and not x['final_correct'] for x in rows),errors=sum(x['error'] is not None for x in rows),median_seconds=statistics.median(x['seconds'] for x in rows),max_seconds=max(x['seconds'] for x in rows),prompt_sha256=hashlib.sha256(PROMPT.encode()).hexdigest(),cases_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),rows=rows)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='rows'},ensure_ascii=False))
if __name__=='__main__':main()
