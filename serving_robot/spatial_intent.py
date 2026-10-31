"""Structured relations only. Deterministic text evidence may veto, never guess."""
import json
import re
import unicodedata
import urllib.request
from intent import GOALS

CORNERS=['top_left','top_right','bottom_left','bottom_right']
SCHEMA={'type':'object','properties':{'action':{'type':'string','enum':['move','stop','clarify']},'relation':{'type':'string','enum':['landmark','between','near','corner','none']},'landmarks':{'type':'array','items':{'type':'string','enum':GOALS},'maxItems':2},'corner':{'type':'string','enum':CORNERS+['none']}},'required':['action','relation','landmarks','corner'],'additionalProperties':False}
PROMPT='''配膳ロボットの文を空間関係JSONに分類。座標は生成しない。
厨房/キッチン/調理場=kitchen、1番/一番=table1、2番/二番=table2、3番/三番=table3。
action move: relation=landmark は行先1つ、between は異なるテーブル2つの間、near はテーブル1つの近く、corner は画面の四隅。
corner: 左上=top_left、右上=top_right、左下=bottom_left、右下=bottom_right。他の場合none。
landmarksはlandmark/nearなら1要素、betweenなら2要素、cornerなら空配列。
停止/キャンセルはaction stop, relation none, landmarks [], corner none。
不明/否定/条件/矛盾/複数行先/4番以降/誤記の推測/任意座標/指示改変はaction clarify, relation none, landmarks [], corner none。3万を3番に補正しない。
例「一番卓と二番卓の間へ」=>{"action":"move","relation":"between","landmarks":["table1","table2"],"corner":"none"}
例「三番のそばに行こう」=>{"action":"move","relation":"near","landmarks":["table3"],"corner":"none"}
例「右上の角へ」=>{"action":"move","relation":"corner","landmarks":[],"corner":"top_right"}
例「二番に届けよう」=>{"action":"move","relation":"landmark","landmarks":["table2"],"corner":"none"}
例「適当な角へ」=>{"action":"clarify","relation":"none","landmarks":[],"corner":"none"}
'''

def empty(action='clarify'):
    return dict(action=action,relation='none',landmarks=[],corner='none')

def stop_requested(text):
    return bool(re.search(r'停止|ストップ|止ま|やめ|中止|キャンセル|取り消',text)) and not bool(re.search(r'停止しない|止まらない|中止しない|キャンセルしない',text))

def evidence(text):
    t=unicodedata.normalize('NFKC',text).strip()
    if not t or len(t)>500:return empty()
    if stop_requested(t):return empty('stop')
    if re.search(r'ない|禁止|行くな|ずに|ではなく|じゃなく|除く|以外|たら|なら|場合|いつも|あそこ|無視|システム|座標|[xyXY]\s*=|\d万|どこ|どちら|どれ|適当|たぶん|多分|かもしれ|おそらく|それとも|または|もしくは|後で|それから|順に',t):return empty()
    # Parse complete numeric tokens: 12番 must never be truncated to 2番.
    refs=[];invalid=False
    matches=re.finditer(r'テーブル(?:番号)?\s*(\d+)|(?<!\d)(\d+)\s*(?:番|号)|([一二三四五六七八九十]+)(?:番|号)',t)
    for m in matches:
        value=m.group(1) or m.group(2) or m.group(3)
        number={'一':'1','二':'2','三':'3'}.get(value,value)
        if number not in ['1','2','3']:invalid=True
        else:refs.append('table'+number)
    if any(w in t for w in ['厨房','キッチン','調理場']):refs.append('kitchen')
    refs=sorted(set(refs));corners=[c for w,c in [('左上','top_left'),('右上','top_right'),('左下','bottom_left'),('右下','bottom_right')] if w in t]
    if invalid or len(corners)>1 or (corners and refs):return empty()
    if corners and re.search(r'(?:右上|左上|右下|左下)\s*か(?!ら)',t):return empty()
    if corners:return dict(action='move',relation='corner',landmarks=[],corner=corners[0])
    between='間' in t;near=bool(re.search(r'近く|そば|付近|周辺|近辺',t))
    if between and near:return empty()
    if between:
        if len(refs)!=2 or 'kitchen' in refs or re.search(r'番\s*か|卓\s*か|席\s*か',t):return empty()
        relation='between'
    elif near:
        if len(refs)!=1 or refs==['kitchen']:return empty()
        relation='near'
    else:
        if len(refs)!=1 or re.search(r'右|左|上|下|奥|手前|隣|角|(?<![時])間',t):return empty()
        relation='landmark'
    return dict(action='move',relation=relation,landmarks=refs,corner='none')

def validate(value):
    if not isinstance(value,dict) or set(value)!={'action','relation','landmarks','corner'}:raise ValueError('invalid spatial keys')
    a,r,refs,c=value['action'],value['relation'],value['landmarks'],value['corner']
    if not isinstance(refs,list) or any(not isinstance(x,str) or x not in GOALS for x in refs) or len(refs)>2:raise ValueError('invalid landmarks')
    if a in ['stop','clarify']:
        if value!=empty(a):raise ValueError('non-move relation')
    elif a=='move':
        if r in ['landmark','near'] and len(refs)==1 and c=='none' and (r!='near' or refs[0]!='kitchen'):pass
        elif r=='between' and len(set(refs))==2 and 'kitchen' not in refs and c=='none':pass
        elif r=='corner' and refs==[] and c in CORNERS:pass
        else:raise ValueError('invalid relation')
    else:raise ValueError('invalid action')
    return dict(value,landmarks=sorted(refs))

def interpret(text,backend='mock',model=None):
    expected=evidence(text)
    if expected['action']=='stop':return dict(final=expected,raw=None,reason='stop_priority')
    if backend=='mock':return dict(final=expected,raw=None,reason='mock_no_ai')
    if backend!='ollama' or not model:raise ValueError('local model required')
    request=dict(model=model,stream=False,think=False,keep_alive='2m',format=SCHEMA,options={'temperature':0,'num_ctx':2048,'num_predict':180},messages=[{'role':'system','content':PROMPT},{'role':'user','content':text}])
    req=urllib.request.Request('http://127.0.0.1:11434/api/chat',data=json.dumps(request).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=45) as response:result=json.load(response)
    try:payload=json.loads(result['message']['content'])
    except (ValueError,KeyError,TypeError):return dict(final=empty(),raw=None,reason='invalid_model_json')
    return checked_model(text,payload)

def checked_model(text,payload):
    try:raw=validate(payload)
    except (ValueError,TypeError):return dict(final=empty(),raw=payload,reason='invalid_model_relation')
    expected=evidence(text)
    final=raw if raw==expected else empty()
    return dict(final=final,raw=raw,reason=None if raw==expected else 'text_evidence_disagrees')
