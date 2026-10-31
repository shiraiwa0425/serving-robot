"""Known-map geometry; no coordinates from a model or a browser request."""
import math
from sim import GOALS,BOXES,free,plan

TABLES={name:BOXES[i] for i,name in enumerate(['table1','table2','table3'])}
CORNER_ANCHORS={'top_left':(.5,5.5),'top_right':(5.5,5.5),'bottom_left':(.5,.5),'bottom_right':(5.5,.5)}
LABELS={'kitchen':'厨房','table1':'1番卓','table2':'2番卓','table3':'3番卓', 'top_left':'左上','top_right':'右上','bottom_left':'左下','bottom_right':'右下'}

def candidate(spec,start):
    relation=spec['relation'];refs=spec['landmarks'];adjustment=0.
    if relation=='landmark':
        points=[GOALS[refs[0]]];anchor=points[0];label=LABELS[refs[0]]
    elif relation=='between':
        a,b=(TABLES[n] for n in refs);anchor=((a[0]+b[0])/2,(a[1]+b[1])/2)
        # Only the geometric midpoint and <=0.3m local adjustment qualify as "between".
        points=[(round(anchor[0]*10)/10+dx/10,round(anchor[1]*10)/10+dy/10) for dx in range(-3,4) for dy in range(-3,4) if math.hypot(dx,dy)<=3]
        label='と'.join(LABELS[n] for n in refs)+'の間'
    elif relation=='near':
        x,y,w,h=TABLES[refs[0]];anchor=(x,y)
        points=[(x-w-.5,y),(x+w+.5,y),(x,y-h-.5),(x,y+h+.5), (x-w-.4,y-h-.4),(x+w+.4,y-h-.4),(x-w-.4,y+h+.4),(x+w+.4,y+h+.4)]
        points=[tuple(round(v*10)/10 for v in p) for p in points];label=LABELS[refs[0]]+'の近く'
    elif relation=='corner':
        anchor=CORNER_ANCHORS[spec['corner']]
        points=[(anchor[0]+dx/10,anchor[1]+dy/10) for dx in range(-10,11) for dy in range(-10,11) if dx*dx+dy*dy<=100]
        label='画面'+LABELS[spec['corner']]+'の角付近'
    else:raise ValueError('移動先を特定できません')
    feasible=[]
    for point in sorted(set(points),key=lambda p:(math.dist(p,anchor),p)):
        if feasible and relation!='near' and math.dist(point,anchor)>feasible[0][0][0]+1e-8:break
        if not free(*point):continue
        try:route=plan(start,point)
        except ValueError:continue
        distance=sum(math.dist(a,b) for a,b in zip(route,route[1:]))
        score=(distance,point) if relation=='near' else (math.dist(point,anchor),distance,point)
        feasible.append((score,point,route))
        if relation in ['landmark','between','corner'] and math.dist(point,anchor)<.06:break
    if not feasible:raise ValueError('指定した関係の範囲に、安全で到達可能な候補がありません')
    _,point,route=min(feasible,key=lambda item:item[0]);adjustment=math.dist(point,anchor)
    return dict(label=label,point=list(point),path=route,relation=relation,landmarks=refs,corner=spec['corner'],anchor=list(anchor),adjustment_m=round(adjustment,3),explanation='既知の地図から算出。壁・障害物の余白と経路を確認済み。'+(' 障害物から離した位置です。' if adjustment>.15 and relation!='near' else '')+(' 安全な周辺候補のうち経路が短い位置です。' if relation=='near' else ''))
