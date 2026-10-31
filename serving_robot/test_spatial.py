import math,threading,unittest
from unittest.mock import patch
from spatial_intent import evidence,validate,checked_model
from spatial_map import candidate
from session import Session,Conflict
from sim import Simulation,GOALS,free,plan
class SpatialTests(unittest.TestCase):
    def test_relation_evidence(self):
        for text,r,refs,c in [('2番テーブルと3番テーブルの間へ','between',['table2','table3'],'none'),('三番と二番の間に行って','between',['table2','table3'],'none'),('一番テーブルの近くへ','near',['table1'],'none'),('部屋の右上へ','corner',[],'top_right'),('部屋の左下の角へ','corner',[],'bottom_left'),('キッチンに戻って','landmark',['kitchen'],'none')]:
            with self.subTest(text=text):self.assertEqual(evidence(text),dict(action='move',relation=r,landmarks=refs,corner=c))
    def test_ambiguity_unknown_negation(self):
        for text in ['2番と3万の間','12番の近く','四番テーブルの近く','部屋の角へ','右上か左下へ','1番と1番の間','1番と2番と3番の間','2番か3番の間','1番の右隣へ','厨房と2番の間','2番の近くと右上','1番には行かないで','座標(2,3)へ','1番と2番の間の近く','3番に行ったら厨房へ']:
            with self.subTest(text=text):self.assertEqual(evidence(text)['action'],'clarify')
    def test_stop_priority(self):
        for text in ['2番と3番の間へ、いや停止して','右上はキャンセル','そのまま止まって']:self.assertEqual(evidence(text)['action'],'stop')
        self.assertEqual(evidence('停止しないで1番へ')['action'],'clarify')
    def test_invalid_structure(self):
        for value in [{},dict(action='move',relation='corner',landmarks=['table1'],corner='top_left'),dict(action='move',relation='between',landmarks=['table2','table2'],corner='none'),dict(action='stop',relation='near',landmarks=[],corner='none')]:
            with self.assertRaises(ValueError):validate(value)
    def test_model_veto_and_malformed_fallback(self):
        for text,payload in [('2番と3万の間へ',dict(action='move',relation='between',landmarks=['table2','table3'],corner='none')),('部屋の角へ',dict(action='move',relation='corner',landmarks=[],corner='none')),('12番へ',dict(action='move',relation='landmark',landmarks=['table2'],corner='none'))]:
            self.assertEqual(checked_model(text,payload)['final']['action'],'clarify')
    def test_map_midpoint_and_near(self):
        c=candidate(evidence('2番と3番の間へ'),GOALS['kitchen']);self.assertLess(math.dist(c['point'],(4.025,4.225)),.1)
        for n in ['1','2','3']:
            c=candidate(evidence(n+'番の近くへ'),GOALS['kitchen']);self.assertTrue(free(*c['point']));self.assertTrue(c['path'])
    def test_spatial_physics_routes(self):
        for text in ['右上へ','左上へ','右下へ','左下へ','2番と3番の間へ','3番の近くへ']:
            with self.subTest(text=text):
                s=Simulation();c=candidate(evidence(text),GOALS['kitchen']);self.assertTrue(free(*c['point']));s.go_point(c['point'],c['label'])
                for _ in range(15000):
                    s.step();self.assertTrue(free(*s.data.qpos[:2],margin=.245))
                    if s.status=='arrived' and math.hypot(*s.data.qvel[:2])<.005:break
                self.assertEqual(s.status,'arrived');self.assertLess(math.dist(s.data.qpos[:2],c['point']),.07);self.assertEqual(s.contacts,0)
    def test_blocked_and_unreachable(self):
        for setting in [patch('spatial_map.free',return_value=False),patch('spatial_map.plan',side_effect=ValueError('blocked'))]:
            with setting:
                s=Session();s.command('2番と3番の間へ');self.assertIsNone(s.pending);self.assertEqual(s.sim.status,'clarify');self.assertFalse(s.sim.path)
    def test_actual_search_rejects_disconnected_map(self):
        original=free
        def barrier(x,y,margin=.32):return original(x,y,margin) and not 2.0<x<2.5
        with patch('sim.free',side_effect=barrier):
            with self.assertRaises(ValueError):plan(GOALS['kitchen'],GOALS['table1'])
            s=Session();s.command('2番と3番の間へ');self.assertIsNone(s.pending);self.assertFalse(s.sim.path);self.assertEqual(s.sim.status,'clarify')
    def test_unsafe_endpoints(self):
        for point in [(2.6,2.6),(0,0),(5.45,1)]:
            with self.assertRaises(ValueError):plan(GOALS['kitchen'],point)
    def test_confirmation_cancel_duplicate(self):
        s=Session();s.command('2番と3番の間へ');p=s.pending;self.assertEqual(s.sim.status,'awaiting_confirmation');self.assertFalse(s.sim.path)
        for _ in range(100):s.step()
        self.assertLess(math.dist(s.sim.data.qpos[:2],GOALS['kitchen']),.001);s.confirm(p['id']);self.assertEqual(s.sim.status,'moving')
        with self.assertRaises(Conflict):s.confirm(p['id'])
        s.stop();s.command('右上へ');p=s.pending;s.cancel(p['id']);self.assertIsNone(s.pending);self.assertFalse(s.sim.path)
        with self.assertRaises(Conflict):s.confirm(p['id'])
    def test_new_instruction_invalidates_candidate(self):
        s=Session();s.command('右上へ');old=s.pending['id'];s.command('1番の近くへ')
        with self.assertRaises(Conflict):s.confirm(old)
        with self.assertRaises(Conflict):s.cancel(old)
        self.assertEqual(s.pending['relation'],'near');s.command('存在しない行先へ');self.assertIsNone(s.pending);self.assertFalse(s.sim.path)
    def test_confirm_rechecks_pose(self):
        s=Session();s.command('左上へ');token=s.pending['id'];s.sim.data.qpos[:2]=[2.6,2.6]
        with self.assertRaises(Conflict):s.confirm(token)
        self.assertIsNone(s.pending);self.assertFalse(s.sim.path)
    def test_inflight_stop_and_new_instruction(self):
        entered=threading.Event();release=threading.Event()
        def slow(text):
            if text=='右上へ':entered.set();release.wait(3)
            return dict(final=evidence(text),raw=None)
        for next_text in [None,'1番の近くへ']:
            entered.clear();release.clear();s=Session(interpreter=slow);t=threading.Thread(target=s.command,args=('右上へ',));t.start();self.assertTrue(entered.wait(1))
            if next_text:s.command(next_text)
            else:s.stop()
            release.set();t.join(3);self.assertFalse(t.is_alive())
            if next_text:self.assertEqual(s.pending['relation'],'near')
            else:self.assertIsNone(s.pending);self.assertEqual(s.sim.status,'stopped')
    def test_concurrent_confirm(self):
        s=Session();s.command('左上へ');token=s.pending['id'];results=[]
        def confirm():
            try:s.confirm(token);results.append('ok')
            except Conflict:results.append('conflict')
        ts=[threading.Thread(target=confirm) for _ in range(6)]
        for t in ts:t.start()
        for t in ts:t.join()
        self.assertEqual(results.count('ok'),1);self.assertEqual(results.count('conflict'),5)
if __name__=='__main__':unittest.main(verbosity=2)
