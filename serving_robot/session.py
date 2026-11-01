"""Confirmation transaction and stop priority, shared by HTTP and deterministic tests."""
import threading
import time
import uuid
from sim import Simulation,plan
from spatial_intent import interpret,stop_requested
from spatial_map import candidate

class Conflict(ValueError):pass

class Session:
    def __init__(self,backend='mock',model=None,interpreter=None):
        self.sim=Simulation();self.lock=threading.RLock();self.epoch=0;self.pending=None
        self.interpreter=interpreter or (lambda text:interpret(text,backend,model))
        self.last=dict(backend=backend,model=model,message='目的地の候補を作成し、確認してから移動します。')
    def _invalidate(self):
        self.epoch+=1;self.pending=None;self.sim.stop()
    def stop(self):
        with self.lock:
            self._invalidate();self.last.update(action='stop',message='停止しました。候補も取り消しました。')
    def command(self,text):
        with self.lock:
            self._invalidate();epoch=self.epoch;start=tuple(self.sim.data.qpos[:2]);self.last.update(message='解釈中：停止しています',action='interpreting')
        if stop_requested(text):self.stop();return
        started=time.perf_counter()
        try:
            result=self.interpreter(text);spec=result['final']
            proposal=candidate(spec,start) if spec['action']=='move' else None
            with self.lock:
                if epoch!=self.epoch:return
                self.last.update(interpretation=spec,raw_model=result.get('raw'),reason=result.get('reason'),latency_seconds=time.perf_counter()-started)
                if proposal:
                    proposal['id']=uuid.uuid4().hex;self.pending=proposal;self.sim.status='awaiting_confirmation'
                    self.last.update(action='candidate',message=proposal['label']+'：候補を確認してください。まだ移動していません。')
                elif spec['action']=='stop':self.sim.stop();self.last.update(action='stop',message='停止しました。')
                else:self.sim.status='clarify';self.last.update(action='clarify',message='行先・関係を確認できません。1〜3番テーブルを指定してください（例：一番卓へ／1番と2番の間へ／3番の近くへ）。厨房や画面の右上なども指定できます。誤記や複数の行先は一つの指示に直してください。')
        except Exception as exc:
            with self.lock:
                if epoch!=self.epoch:return
                self.sim.stop();self.sim.status='clarify'
                self.last.update(action='clarify',message=str(exc) if isinstance(exc,ValueError) else '推論に失敗しました。停止したまま指示を確認してください。',latency_seconds=time.perf_counter()-started)
    def confirm(self,token):
        with self.lock:
            if not self.pending or self.pending['id']!=token:raise Conflict('この候補は無効です。新しい候補を確認してください。')
            proposal=self.pending
            if sum(v*v for v in self.sim.data.qvel[:2])>.0001:raise Conflict('減速中です。停止後に確認してください。')
            # Fresh reachability check; coordinates are from server-side pending state only.
            try:self.sim.go_point(proposal['point'],proposal['label'])
            except ValueError:
                self._invalidate();self.sim.status='clarify';self.last.update(message='確認時に安全な経路が得られませんでした。停止しています。');raise Conflict(self.last['message'])
            self.pending=None;self.epoch+=1;self.last.update(action='move',message=proposal['label']+'へ移動します。')
    def cancel(self,token):
        with self.lock:
            if not self.pending or self.pending['id']!=token:raise Conflict('取り消す候補は既に無効です。')
            self._invalidate();self.last.update(action='stop',message='候補を取り消しました。')
    def step(self):
        with self.lock:
            self.sim.step()
            if self.sim.status=='safety_stop' and self.pending:
                self.pending=None;self.epoch+=1;self.last.update(message='安全停止：候補を取り消しました。')
    def state(self):
        with self.lock:return dict(self.sim.state(),intent=dict(self.last),candidate=self.pending,epoch=self.epoch)
