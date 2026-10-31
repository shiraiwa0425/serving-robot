import json,math,unittest
import mujoco
from pathlib import Path
from sim import Simulation,GOALS,plan,free
from intent import infer,validate,guard_move
class RobotTests(unittest.TestCase):
    def test_routes(self):
        evidence=[]
        for goal in GOALS:
            sim=Simulation();sim.go(goal)
            for _ in range(14000):
                sim.step()
                self.assertTrue(free(*sim.data.qpos[:2],margin=.245))
                if sim.status=='arrived' and math.hypot(*sim.data.qvel[:2])<.005:break
            self.assertEqual(sim.status,'arrived');self.assertLess(math.dist(sim.data.qpos[:2],GOALS[goal]),.07)
            self.assertLessEqual(sim.max_speed,.36);self.assertEqual(sim.contacts,0)
            evidence.append(dict(goal=goal,seconds=sim.data.time,position=sim.data.qpos[:2].tolist(),max_speed=sim.max_speed,contacts=sim.contacts))
        Path('artifacts/routes.json').write_text(json.dumps(evidence,indent=2))
    def test_physical_contact(self):
        sim=Simulation();sim.data.qpos[:2]=[4.6,1];sim.data.ctrl[:]=[.5,0]
        contact=False
        for _ in range(500):
            mujoco.mj_step(sim.model,sim.data);contact=contact or sim.data.ncon>0
        self.assertTrue(contact)
        self.assertLess(sim.data.qpos[0],4.9)  # obstacle face 5.1 minus radius .22
    def test_stop(self):
        sim=Simulation();sim.go('table1')
        for _ in range(250):sim.step()
        before=sim.data.qpos[:2].copy();sim.stop()
        for _ in range(100):sim.step()
        self.assertLess(math.dist(before,sim.data.qpos[:2]),.05);self.assertLess(math.hypot(*sim.data.qvel[:2]),.001)
    def test_all_pairs(self):
        for start in GOALS.values():
            for end in GOALS.values():self.assertTrue(all(free(*point) for point in plan(start,end)))
    def test_safety_envelope(self):
        sim=Simulation();sim.go('table1');sim.data.qpos[:2]=[.24,1];sim.step();self.assertEqual(sim.status,'safety_stop')
    def test_guard_vetoes_unsupported_ai_moves(self):
        for text,value in [('1番へ',dict(action='move',goal='kitchen')),('いつもの席へ',dict(action='move',goal='table1')),('1番か2番へ',dict(action='move',goal='table2')),('3番には行かないで',dict(action='move',goal='table3'))]:
            final,reason=guard_move(text,value);self.assertEqual(final['action'],'clarify');self.assertIsNotNone(reason)
        value=dict(action='move',goal='table2');self.assertEqual(guard_move('二番のテーブルまでお願い',value),(value,None))
    def test_intents(self):
        for text in ['1番か2番へ運んで','1番と三番へ運んで','1番のあと2番','1番、2番','1番以外に運んで']:
            self.assertEqual(infer(text)['action'],'clarify')
        self.assertEqual(infer('3番には行かないで')['action'],'clarify')
        for value in [None,{},dict(action='move',goal='table9'),dict(action='stop',goal='table1'),dict(action='move',goal='table1',extra=1)]:
            with self.assertRaises(ValueError):validate(value)
if __name__=='__main__':unittest.main(verbosity=2)
