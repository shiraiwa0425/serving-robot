"""MuJoCo planar omnidirectional base; SI units, actual force/velocity dynamics."""
import heapq
import math
import mujoco

GOALS = {'kitchen': (0.7, 0.7), 'table1': (4.7, 1.0), 'table2': (4.7, 3.0), 'table3': (2.6, 4.7)}
BOXES = [(5.45,1,.35,.5),(5.45,3,.35,.5),(2.6,5.45,.5,.35),(2.6,2.6,.5,.55)]
RADIUS = .22
XML = '''<mujoco><option timestep="0.01" gravity="0 0 -9.81"/><worldbody>
<light pos="3 3 8"/><geom type="plane" size="6 6 .1" rgba=".9 .9 .9 1"/>
<geom type="box" pos="3 -.1 .3" size="3.1 .1 .3"/>
<geom type="box" pos="3 6.1 .3" size="3.1 .1 .3"/>
<geom type="box" pos="-.1 3 .3" size=".1 3 .3"/>
<geom type="box" pos="6.1 3 .3" size=".1 3 .3"/>
%s
<body name="robot" pos="0 0 .23"><joint name="x" type="slide" axis="1 0 0" damping="2"/><joint name="y" type="slide" axis="0 1 0" damping="2"/><joint name="yaw" type="hinge" axis="0 0 1" damping="1"/>
<geom name="base" type="cylinder" size=".22 .2" mass="8" rgba=".1 .55 .8 1"/>
<geom type="box" pos=".15 0 .22" size=".06 .04 .02" mass=".1" rgba="1 .7 .1 1"/></body></worldbody>
<actuator><velocity joint="x" kv="80" ctrllimited="true" ctrlrange="-.5 .5" forcelimited="true" forcerange="-20 20"/><velocity joint="y" kv="80" ctrllimited="true" ctrlrange="-.5 .5" forcelimited="true" forcerange="-20 20"/></actuator></mujoco>''' % ''.join('<geom type="box" pos="%s %s .4" size="%s %s .4"/>' % b for b in BOXES)

def free(x,y, margin=.32):
    return margin <= x <= 6-margin and margin <= y <= 6-margin and all(abs(x-a)>w+margin or abs(y-b)>h+margin for a,b,w,h in BOXES)

def segment_free(start,target):
    steps=max(1,math.ceil(math.dist(start,target)/.02))
    return all(free(*(start[j]+(target[j]-start[j])*i/steps for j in range(2))) for i in range(steps+1))

def plan(start, target):
    if not free(*start) or not free(*target):raise ValueError('出発点または目的地が安全領域外です')
    scale=10
    s=tuple(round(v*scale) for v in start); g=tuple(round(v*scale) for v in target)
    if not segment_free(start,tuple(v/scale for v in s)) or not segment_free(tuple(v/scale for v in g),target):raise ValueError('グリッド接続が安全ではありません')
    q=[(0,s)]; cost={s:0}; prev={}
    while q:
        _,n=heapq.heappop(q)
        if n==g:
            path=[target]
            while n!=s:
                n=prev[n]; path.append(tuple(v/scale for v in n))
            return list(reversed(path))
        for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            m=n[0]+dx,n[1]+dy
            if free(m[0]/scale,m[1]/scale) and cost[n]+1<cost.get(m,1e9):
                cost[m]=cost[n]+1; prev[m]=n
                heapq.heappush(q,(cost[m]+abs(m[0]-g[0])+abs(m[1]-g[1]),m))
    raise ValueError('安全な経路がありません')

class Simulation:
    def __init__(self):
        self.model=mujoco.MjModel.from_xml_string(XML); self.data=mujoco.MjData(self.model)
        self.data.qpos[:2]=GOALS['kitchen']; mujoco.mj_forward(self.model,self.data)
        self.path=[]; self.status='idle'; self.target=None; self.max_speed=0.; self.contacts=0
    def stop(self):
        self.path=[]; self.data.ctrl[:]=0; self.status='stopped'; self.target=None
    def go(self,goal):
        self.go_point(GOALS[goal],goal)
    def go_point(self,point,label):
        route=plan(self.data.qpos[:2],point)
        self.path=route; self.target=label; self.status='moving'
    def step(self):
        x,y=self.data.qpos[:2]; vx,vy=self.data.qvel[:2]
        # Fail-safe envelope includes braking distance (v^2 / 2a) and extra margin.
        speed=math.hypot(vx,vy)
        if not free(x,y,RADIUS+.025+speed*speed/2):
            self.stop(); self.status='safety_stop'
        while self.path and math.dist((x,y),self.path[0])<.045: self.path.pop(0)
        if self.path:
            dx,dy=self.path[0][0]-x,self.path[0][1]-y; d=math.hypot(dx,dy)
            self.data.ctrl[:]=[dx/d*min(.35,3*d),dy/d*min(.35,3*d)]
        else:
            self.data.ctrl[:]=0
            if self.status=='moving': self.status='arrived'
        mujoco.mj_step(self.model,self.data)
        self.max_speed=max(self.max_speed,math.hypot(*self.data.qvel[:2]))
        self.contacts+=self.data.ncon
    def state(self):
        return dict(x=float(self.data.qpos[0]),y=float(self.data.qpos[1]),status=self.status,target=self.target,
                    time=float(self.data.time),speed=math.hypot(*self.data.qvel[:2]),path=self.path,goals=GOALS,boxes=BOXES)
