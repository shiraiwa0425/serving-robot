import json,threading,unittest,urllib.request,urllib.error
from app import make_server
from session import Session
from spatial_intent import evidence
class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.session=Session();self.server=make_server(self.session,0);self.thread=threading.Thread(target=self.server.serve_forever);self.thread.start();self.base='http://127.0.0.1:'+str(self.server.server_port)
    def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join(2)
    def post(self,path,data,origin=None):
        headers={'Content-Type':'application/json'}
        if origin:headers['Origin']=origin
        req=urllib.request.Request(self.base+path,data=json.dumps(data).encode(),headers=headers)
        try:
            with urllib.request.urlopen(req,timeout=5) as r:return r.status,json.load(r)
        except urllib.error.HTTPError as e:
            return e.code,None
    def state(self):
        with urllib.request.urlopen(self.base+'/state') as r:return json.load(r)
    def test_preview_confirm_once_and_no_client_coordinates(self):
        self.assertEqual(self.post('/command',{'text':'2番と3番の間へ'})[0],200);s=self.state();p=s['candidate'];self.assertTrue(p);self.assertFalse(s['path']);self.assertEqual(s['status'],'awaiting_confirmation')
        self.assertEqual(self.post('/confirm',{'candidate_id':p['id'],'point':[0,0]})[0],200)
        s=self.state();self.assertEqual(s['status'],'moving');self.assertEqual(list(s['path'][-1]),p['point'])
        self.assertEqual(self.post('/confirm',{'candidate_id':p['id']})[0],409)
        self.assertEqual(self.post('/stop',{})[0],200);self.assertFalse(self.state()['path'])
    def test_table_aliases_preview_and_invalid_names(self):
        for name in ['一番テーブル','一番卓','1番テーブル','1番卓']:
            self.assertEqual(self.post('/command',{'text':name+'へ'})[0],200)
            state=self.state()
            self.assertEqual(state['candidate']['landmarks'],['table1'])
            self.assertEqual(state['candidate']['label'],'1番テーブル')
            self.assertEqual(state['status'],'awaiting_confirmation');self.assertFalse(state['path'])
        for text in ['一番卓と三万テーブルの間へ','四番卓へ','テーブルへ']:
            self.post('/command',{'text':text});state=self.state()
            self.assertIsNone(state['candidate']);self.assertFalse(state['path']);self.assertEqual(state['status'],'clarify');self.assertIn('1〜3番テーブル',state['intent']['message'])
    def test_cancel_new_command_and_stale_ids(self):
        self.post('/command',{'text':'右上へ'});old=self.state()['candidate']['id'];self.post('/command',{'text':'3番の近くへ'});new=self.state()['candidate']['id']
        self.assertNotEqual(old,new);self.assertEqual(self.post('/cancel',{'candidate_id':old})[0],409);self.assertEqual(self.post('/confirm',{'candidate_id':old})[0],409)
        self.assertEqual(self.state()['candidate']['id'],new);self.assertEqual(self.post('/cancel',{'candidate_id':new})[0],200);self.assertIsNone(self.state()['candidate'])
    def test_request_validation(self):
        self.assertEqual(self.post('/command',{'text':'1番へ'},'https://example.com')[0],403)
        for data in [[],{},dict(text=3),dict(text='a'*501)]:self.assertEqual(self.post('/command',data)[0],400)
        self.assertEqual(self.post('/confirm',{})[0],400)
        with urllib.request.urlopen(self.base+'/') as r:
            html=r.read().decode();self.assertIn('この候補へ移動',html);self.assertIn('候補を取り消す',html)
    def test_stop_during_http_inference(self):
        entered=threading.Event();release=threading.Event()
        def slow(text):entered.set();release.wait(3);return dict(final=evidence(text),raw=None)
        self.session.interpreter=slow;thread=threading.Thread(target=self.post,args=('/command',{'text':'右上へ'}));thread.start();self.assertTrue(entered.wait(1));self.assertEqual(self.post('/stop',{})[0],200);release.set();thread.join(3);self.assertFalse(thread.is_alive());s=self.state();self.assertIsNone(s['candidate']);self.assertEqual(s['status'],'stopped')
if __name__=='__main__':unittest.main(verbosity=2)
