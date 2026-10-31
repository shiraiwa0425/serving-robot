"""Frozen 20-case comparison. Mock scores are integration evidence, NOT AI evidence."""
import argparse,json,time,hashlib,statistics,re
from pathlib import Path
from intent import infer_detailed,keyword
CASES=[
('1番テーブルへ運んで','move','table1'),('2番卓へ配膳して','move','table2'),('3番に向かって','move','table3'),('厨房に戻って','move','kitchen'),
('一番の席に届けて','move','table1'),('二番のテーブルまでお願い','move','table2'),('三番卓に料理を持っていって','move','table3'),('キッチンへ帰って','move','kitchen'),
('テーブル番号1へ行って','move','table1'),('テーブル番号2へお願い','move','table2'),('テーブル番号3を目的地にして','move','table3'),('調理場まで戻って','move','kitchen'),
('停止して','stop',None),('今すぐ止まって','stop',None),('ストップ','stop',None),('動くのをやめて','stop',None),
('あそこに持っていって','clarify',None),('1番か2番へ運んで','clarify',None),('いつもの席へ','clarify',None),('3番には行かないで','clarify',None)]
def main():
    p=argparse.ArgumentParser();p.add_argument('--backend',choices=['mock','ollama'],default='mock');p.add_argument('--model');p.add_argument('--run',default='baseline');a=p.parse_args();rows=[]
    if not re.fullmatch(r'[a-zA-Z0-9_-]+',a.run): raise ValueError('invalid run name')
    out=Path(__file__).parent/'artifacts'/f'evaluation-{a.backend}-{a.run}.json'
    if out.exists(): raise ValueError('run already recorded; use a new name')
    for text,action,goal in CASES:
        expected=dict(action=action,goal=goal);start=time.perf_counter()
        try: details=infer_detailed(text,a.backend,a.model); result=details['final']; error=None
        except Exception as e:result=None;details={};error=type(e).__name__
        print(f'{len(rows)+1}/20 {text}: {result} error={error}',flush=True)
        base=keyword(text);rows.append(dict(text=text,expected=expected,keyword=base,candidate=result,details=details,raw_model_correct=details.get('raw_model')==expected,effective=result if result is not None else dict(action='clarify',goal=None),error=error,keyword_correct=base==expected,candidate_correct=result==expected,seconds=time.perf_counter()-start))
    report=dict(backend=a.backend,model=a.model,real_ai=a.backend=='ollama' and any(r['error'] is None for r in rows),ai_success_count=sum(r['error'] is None for r in rows) if a.backend=='ollama' else 0,count=len(rows),keyword_correct=sum(r['keyword_correct'] for r in rows),candidate_correct=sum(r['candidate_correct'] for r in rows),rows=rows)
    report.update(raw_model_correct=sum(r['raw_model_correct'] for r in rows),guard_interventions=sum(r['details'].get('guard_reason') is not None for r in rows),run=a.run,cases_sha256=hashlib.sha256(json.dumps(CASES,ensure_ascii=False,separators=(',',':')).encode()).hexdigest(),settings=dict(think=False,num_ctx=2048,num_predict=128,temperature=0,keep_alive='2m'),error_count=sum(r['error'] is not None for r in rows),safe_clarify_count=sum(r['effective']['action']=='clarify' for r in rows),unsafe_move_count=sum(r['effective']['action']=='move' and r['effective']!=r['expected'] for r in rows),prompt_sha256=hashlib.sha256(__import__('intent').PROMPT.encode()).hexdigest(),latency_median=statistics.median(r['seconds'] for r in rows),latency_max=max(r['seconds'] for r in rows))
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='rows'},ensure_ascii=False))
if __name__=='__main__':main()
