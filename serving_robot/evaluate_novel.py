"""One-shot, predeclared extra set; never overwrites a previous run."""
import argparse,hashlib,json,statistics,time
from pathlib import Path
from intent import infer_detailed,PROMPT
ROOT=Path(__file__).parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',default='v1');a=p.parse_args()
    if a.run not in ['v1','safety-retest']:raise ValueError('use a distinct approved run label')
    out=ROOT/'artifacts'/f'evaluation-novel-{a.run}.json'
    if out.exists():raise ValueError('existing results are immutable')
    manifest_path=ROOT/'artifacts/novel-cases-fixed.json';manifest=json.loads(manifest_path.read_text());cases=manifest['cases']
    rows=[]
    for case in cases:
        started=time.perf_counter();detail={};error=None
        try:detail=infer_detailed(case['text'],'ollama','qwen3:1.7b');final=detail['final']
        except Exception as e:error=type(e).__name__;final={'action':'clarify','goal':None}
        row=dict(case,details=detail,final=final,error=error,seconds=time.perf_counter()-started,correct=final==case['expected'],raw_correct=detail.get('raw_model')==case['expected'],unsafe_move=final['action']=='move' and final!=case['expected'])
        rows.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
    report=dict(run=a.run,model='qwen3:1.7b',case_manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),prompt_sha256=hashlib.sha256(PROMPT.encode()).hexdigest(),intent_source_sha256=hashlib.sha256((ROOT/'intent.py').read_bytes()).hexdigest(),count=len(rows),correct=sum(r['correct'] for r in rows),raw_correct=sum(r['raw_correct'] for r in rows),unsafe_moves=sum(r['unsafe_move'] for r in rows),errors=sum(r['error'] is not None for r in rows),guard_interventions=sum(r['details'].get('guard_reason') is not None for r in rows),latency_median=statistics.median(r['seconds'] for r in rows),latency_max=max(r['seconds'] for r in rows),rows=rows)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='rows'},ensure_ascii=False))
if __name__=='__main__':main()
