import io,json,math,threading,unittest
from unittest.mock import patch
from spatial_intent import evidence,validate,checked_model,interpret,canonical_table_names,empty
from spatial_map import candidate
from session import Session,Conflict
from sim import Simulation,GOALS,free,plan
class SpatialTests(unittest.TestCase):
    def assert_refused_candidate(self,text,guessed):
        self.assertEqual(evidence(text),empty())
        self.assertEqual(checked_model(text,guessed)['final'],empty())
        self.assertEqual(checked_model(text,empty())['final'],empty())
        session=Session();session.command(text)
        self.assertIsNone(session.pending);self.assertFalse(session.sim.path)
    def test_review_common_prohibitions(self):
        guessed=dict(action='move',relation='landmark',landmarks=['table1'],corner='none')
        for text in ['1番へ行ってはいけません','1番へ行くべきではありません',
                     '1番へは行きません','1番へ行かぬように','1番へ行かずに待って',
                     '1番へ行くことは認めません','1番へ行ってはだめです']:
            with self.subTest(text=text):self.assert_refused_candidate(text,guessed)
    def test_review_numeric_expressions_are_not_table_suffixes(self):
        guessed=dict(action='move',relation='landmark',landmarks=['table2'],corner='none')
        for text in ['1,2番へ','1、2番へ','1 / 2番へ','1/2番へ','１／２番へ',
                     '½番へ','二分の一番へ','テーブル1,2へ','テーブル1/2へ',
                     '1,2番と3番の間へ','1/2番の近くへ',
                     '1・2番へ','1〜2番へ','1~2番へ','1と2番へ']:
            with self.subTest(text=text):self.assert_refused_candidate(text,guessed)
    def test_review_unsupported_spatial_modifiers(self):
        cases=[('1番の右側の近くへ','near',['table1'],'none'),
               ('1番の右隣の近くへ','near',['table1'],'none'),
               ('1番の北側の近くへ','near',['table1'],'none'),
               ('1番の前方の近くへ','near',['table1'],'none'),
               ('1番の後ろの近くへ','near',['table1'],'none'),
               ('1番の正面の近くへ','near',['table1'],'none'),
               ('1番から2m離れた近くへ','near',['table1'],'none'),
               ('1番と2番の間の右側へ','between',['table1','table2'],'none'),
               ('1番と2番の間から30cm奥へ','between',['table1','table2'],'none'),
               ('左上の角から1m右へ','corner',[],'top_left'),
               ('左上の角から1メートルへ','corner',[],'top_left'),
               ('右上の角の隣へ','corner',[],'top_right'),
               ('右上から二歩へ','corner',[],'top_right')]
        for text,relation,refs,corner in cases:
            guessed=dict(action='move',relation=relation,landmarks=refs,corner=corner)
            with self.subTest(text=text):self.assert_refused_candidate(text,guessed)
    def test_review_preserves_supported_relations_and_stop_priority(self):
        for text in ['一番卓へ','1番へ必ず運んで','2番テーブルと三番卓の間へ',
                     '三番卓の近くへ','左上の角へ','右下へ','厨房に戻って',
                     '1番の近くへ行って下さい','1番と2番の間へ行って下さい',
                     '右上へ行って下さい']:
            with self.subTest(text=text):
                spec=evidence(text);self.assertEqual(spec['action'],'move')
                self.assertEqual(checked_model(text,spec)['final'],spec)
                self.assertEqual(checked_model(text,empty())['final'],empty())
        for text in ['1,2番へ、いや停止して','1番の右側の近くへ、キャンセル',
                     '1番へ行ってはいけません、停止して']:
            self.assertEqual(evidence(text),empty('stop'))
    def test_relation_evidence(self):
        for text,r,refs,c in [('2番テーブルと3番テーブルの間へ','between',['table2','table3'],'none'),('三番と二番の間に行って','between',['table2','table3'],'none'),('一番テーブルの近くへ','near',['table1'],'none'),('部屋の右上へ','corner',[],'top_right'),('部屋の左下の角へ','corner',[],'bottom_left'),('キッチンに戻って','landmark',['kitchen'],'none')]:
            with self.subTest(text=text):self.assertEqual(evidence(text),dict(action='move',relation=r,landmarks=refs,corner=c))
    def test_table_aliases_and_model_guard(self):
        # Model payloads are fixtures, not evidence of real LLM accuracy.
        for n,kanji in [('1','一'),('2','二'),('3','三')]:
            for number in [n,kanji,chr(ord('１')+int(n)-1)]:
                for suffix in ['番テーブル','番卓','番のテーブル','番の卓','番']:
                    name=number+suffix
                    for tail,relation in [('へ運んで','landmark'),('の近くへ','near')]:
                        text=name+tail
                        expected=dict(action='move',relation=relation,landmarks=['table'+n],corner='none')
                        with self.subTest(text=text):
                            self.assertEqual(evidence(text),expected)
                            self.assertEqual(canonical_table_names(text),n+'番テーブル'+tail)
                            self.assertEqual(checked_model(text,expected)['final'],expected)
                            self.assertEqual(checked_model(text,empty())['final'],empty())
        for left in ['一番テーブル','一番卓','1番テーブル','1番卓']:
            for right in ['二番テーブル','二番卓','2番テーブル','2番卓']:
                expected=dict(action='move',relation='between',landmarks=['table1','table2'],corner='none')
                self.assertEqual(evidence(left+'と'+right+'の間へ'),expected)
                self.assertEqual(checked_model(left+'と'+right+'の間へ',expected)['final'],expected)
    def test_incomplete_and_malformed_table_names(self):
        for text in ['テーブルへ','卓へ','番テーブルへ','一テーブルへ','一卓へ',
                     '0番卓へ','4番テーブルへ','四番卓へ','12番卓へ','十一番卓へ',
                     '百一番卓へ','零一番卓へ','-1番卓へ','1.2番卓へ','01番卓へ',
                     '.1番卓へ','1.2.3番卓へ','−1番卓へ','A1番卓へ',
                     '1番番卓へ','1番テーブル2へ','1番卓Xへ','3万テーブルへ',
                     '一番卓と三万テーブルの間へ','一番卓とテーブルの間へ',
                     '一番卓と名前不明の卓の近くへ','右上とテーブルへ',
                     '一番テーブルか二番テーブルの間へ','一番卓か一番テーブルの近くへ']:
            with self.subTest(text=text):
                self.assertEqual(evidence(text),empty())
                guessed=dict(action='move',relation='landmark',landmarks=['table1'],corner='none')
                self.assertEqual(checked_model(text,guessed)['final'],empty())
    def test_model_request_uses_canonical_name_but_keeps_guard(self):
        expected=evidence('一番卓の近くへ')
        response=io.BytesIO(json.dumps({'message':{'content':json.dumps(expected)}}).encode())
        with patch('spatial_intent.urllib.request.urlopen',return_value=response) as request:
            result=interpret('一番卓の近くへ','ollama','fixture-only')
        body=json.loads(request.call_args.args[0].data)
        self.assertEqual(body['messages'][-1]['content'],'1番テーブルの近くへ')
        self.assertEqual(result['final'],expected)
        original='一番卓と3万テーブルの間へ'
        guessed=dict(action='move',relation='between',landmarks=['table1','table3'],corner='none')
        response=io.BytesIO(json.dumps({'message':{'content':json.dumps(guessed)}}).encode())
        with patch('spatial_intent.urllib.request.urlopen',return_value=response) as request:
            result=interpret(original,'ollama','fixture-only')
        self.assertEqual(json.loads(request.call_args.args[0].data)['messages'][-1]['content'],original)
        self.assertEqual(result['final'],empty());self.assertEqual(result['reason'],'text_evidence_disagrees')
        with patch('spatial_intent.urllib.request.urlopen') as request:
            self.assertEqual(interpret('三万テーブルへ、いや停止して','ollama','fixture-only')['final'],empty('stop'))
            request.assert_not_called()
    def test_alias_candidate_requires_confirmation(self):
        s=Session();s.command('一番卓へ');self.assertEqual(s.sim.status,'awaiting_confirmation')
        self.assertEqual(s.pending['label'],'1番テーブル');self.assertFalse(s.sim.path)
        s.command('一番テーブルと二番卓の間へ')
        self.assertEqual(s.pending['label'],'1番テーブルと2番テーブルの間');self.assertFalse(s.sim.path)
        s.command('一番卓と三万テーブルの間へ');self.assertIsNone(s.pending);self.assertFalse(s.sim.path)
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
