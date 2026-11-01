// UI state/interaction regression in Node; this is not visual browser verification.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const html=fs.readFileSync(new URL('./index.html',import.meta.url),'utf8');
// The stop label changes without hiding, disabling, or restyling the control.
assert.ok(html.includes('<button class="stop" id="stop">走行中の停止</button>'));
// Keep native input-history suggestions disabled without changing text entry.
assert.match(html, /<form\b[^>]*\bid="form"[^>]*\bautocomplete="off"/);
assert.match(html, /<input\b[^>]*\bid="text"[^>]*\bautocomplete="off"/);
for (const n of [1,2,3]) assert.ok(html.includes(`table${n}:'${n}番テーブル'`));
assert.ok(html.includes('「一番テーブル」「一番卓」'));
assert.match(html, /<p id="error" role="status" aria-live="polite" aria-atomic="true">/);
assert.ok(html.indexOf('id="error"')>html.indexOf('</form>')&&html.indexOf('id="error"')<html.indexOf('id="proposal"'));
const elements=new Map();const element=id=>{if(!elements.has(id))elements.set(id,{disabled:false,hidden:true,textContent:'',innerHTML:'',value:''});return elements.get(id);};
const timers=[],posts=[];let holdCommand=false,releaseCommand=null,nextPostError=null,holdState=false,rejectState=null;
let current={epoch:1,x:.7,y:.7,speed:0,status:'awaiting_confirmation',time:1,path:[],goals:{kitchen:[.7,.7]},boxes:[],intent:{backend:'mock',message:'candidate'},candidate:{id:'A',label:'2番テーブルと3番テーブルの間',point:[4,4.2],path:[],explanation:'安全な候補'}};
const response=(error=null)=>({ok:!error,json:async()=>error?{error}:{ok:true}});
const context=vm.createContext({document:{getElementById:element},setTimeout:fn=>timers.push(fn),fetch:async(path,options)=>{
 if(path==='/state'&&holdState){holdState=false;return new Promise((resolve,reject)=>rejectState=reject);}
 if(path==='/state')return {json:async()=>structuredClone(current)};
 posts.push({path,body:JSON.parse(options.body)});
 if(path==='/command'&&holdCommand)return new Promise(resolve=>releaseCommand=(error=null)=>resolve(response(error)));
 const error=nextPostError;nextPostError=null;return response(error);
}});
vm.runInContext(html.split('<script>')[1].split('</script>')[0],context);
const flush=()=>new Promise(resolve=>setImmediate(resolve));await flush();
assert.equal(element('proposal').hidden,false);assert.equal(element('confirm').disabled,false);assert.match(element('candidate-label').textContent,/2番テーブル/);
element('confirm').onclick();element('confirm').onclick();await flush();
assert.equal(posts.filter(x=>x.path==='/confirm').length,1);assert.equal(posts[0].body.candidate_id,'A');
holdCommand=true;element('text').value='右上へ';element('form').onsubmit({preventDefault(){}});
assert.equal(posts.at(-1).path,'/command');assert.equal(posts.at(-1).body.text,'右上へ');
assert.equal(element('confirm').disabled,true);await timers.shift()();await flush();
assert.equal(element('confirm').disabled,true);assert.equal(element('proposal').hidden,true);
current={...current,epoch:2,candidate:{...current.candidate,id:'B',label:'右上の角付近'}};releaseCommand();await flush();await timers.shift()();await flush();
assert.equal(element('confirm').disabled,false);assert.equal(element('candidate-label').textContent,'右上の角付近');
element('cancel').onclick();await flush();assert.equal(posts.at(-1).path,'/cancel');assert.equal(posts.at(-1).body.candidate_id,'B');
element('stop').onclick();await flush();assert.equal(posts.at(-1).path,'/stop');assert.equal(element('confirm').disabled,true);
console.log('PASS: candidate display, explicit confirmation, double click, pending-command stale poll suppression, fresh candidate, cancel, stop');

// Interpretation feedback is visible, text-only, and clears on recovery.
holdCommand=false;
current={...current,epoch:3,status:'clarify',candidate:null,intent:{backend:'mock',action:'clarify',message:'1〜3番テーブルを指定してください。<img src=x onerror=alert(1)>'}};
await vm.runInContext('draw()',context);
assert.equal(element('error').textContent,current.intent.message);assert.equal(element('error').innerHTML,'');
assert.equal(element('proposal').hidden,true);
element('text').value='一番卓へ';element('form').onsubmit({preventDefault(){}});await flush();
assert.equal(element('error').textContent,'');
current={...current,epoch:4,status:'awaiting_confirmation',candidate:{id:'C',label:'1番テーブル',point:[4.7,1],path:[],explanation:'候補'},intent:{backend:'mock',action:'candidate',message:'候補を確認してください。'}};
await vm.runInContext('draw()',context);assert.equal(element('error').textContent,'');
// HTTP validation failures persist across unchanged state and clear on a new state.
nextPostError='指示は500文字以内にしてください';element('form').onsubmit({preventDefault(){}});await flush();
assert.equal(element('error').textContent,'指示は500文字以内にしてください');
await vm.runInContext('draw()',context);assert.equal(element('error').textContent,'指示は500文字以内にしてください');
current={...current,epoch:5};await vm.runInContext('draw()',context);assert.equal(element('error').textContent,'');
// An older command error cannot overwrite a newer stop/cancel operation.
for(const action of ['stop','cancel']){
 holdCommand=true;element('form').onsubmit({preventDefault(){}});await flush();
 if(action==='stop')element('stop').onclick();else vm.runInContext("send('/cancel',{candidate_id:'C'})",context);
 await flush();releaseCommand('古い指示のエラー');await flush();
 assert.equal(element('error').textContent,'');holdCommand=false;
}
// A late polling failure cannot overwrite feedback from a newer operation.
holdState=true;const oldPoll=vm.runInContext('draw()',context);
nextPostError='新しい操作のエラー';element('stop').onclick();await flush();
rejectState(new Error('old poll'));await oldPoll;
assert.equal(element('error').textContent,'新しい操作のエラー');
element('stop').onclick();await flush();assert.equal(element('error').textContent,'');
console.log('PASS: accessible inline clarify, text-only messages, recovery, HTTP errors, new-state clearing, stale command/poll errors after stop/cancel');

// Deferred fetches expose the UI while requests (and response bodies) are pending.
const pendingMessage='指示を解釈して候補を作成中です…';
assert.match(html, /#error\.pending\{color:#b9cadb\}/);
async function pendingHarness(){
 const nodes=new Map(),requests=[],polls=[];
 const node=id=>{if(!nodes.has(id))nodes.set(id,{disabled:false,hidden:true,textContent:'',innerHTML:'',className:'',value:''});return nodes.get(id);};
 const state={epoch:1,x:.7,y:.7,speed:0,status:'clarify',time:1,path:[],goals:{},boxes:[],candidate:null,intent:{backend:'mock',action:'clarify',message:'以前の確認メッセージ'}};
 let deferPoll=false;
 const ctx=vm.createContext({document:{getElementById:node},setTimeout:()=>{},fetch:(path,options)=>{
  if(path==='/state'&&!deferPoll)return Promise.resolve({json:async()=>structuredClone(state)});
  return new Promise((resolve,reject)=>(path==='/state'?polls:requests).push({path,options,resolve,reject}));
 }});
 vm.runInContext(html.split('<script>')[1].split('</script>')[0],ctx);await flush();
 return {node,requests,polls,state,submit(){node('text').value='一番卓へ';node('form').onsubmit({preventDefault(){}});return requests.at(-1);},
  poll(){return vm.runInContext('draw()',ctx);},deferPoll(){deferPoll=true;},
  cancel(){return vm.runInContext("send('/cancel',{candidate_id:'old'})",ctx);}};
}
const expectPending=h=>{assert.equal(h.node('error').textContent,pendingMessage);assert.equal(h.node('error').className,'pending');assert.equal(h.node('proposal').hidden,true);assert.equal(h.node('confirm').disabled,true);assert.equal(h.node('stop').disabled,false);};
const expectClear=h=>{assert.equal(h.node('error').textContent,'');assert.equal(h.node('error').className,'');};
{
 const h=await pendingHarness(),request=h.submit();expectPending(h);
 await h.poll();expectPending(h); // Unchanged/clarify state must not erase pending feedback.
 let resolveBody;request.resolve({ok:true,json:()=>new Promise(resolve=>resolveBody=resolve)});await flush();expectPending(h);
 resolveBody({ok:true});await flush();expectClear(h);
 h.state.epoch++;h.state.status='awaiting_confirmation';h.state.intent={backend:'mock',action:'candidate',message:'確認してください'};
 h.state.candidate={id:'fresh',point:[1,1],label:'1番テーブル',path:[],explanation:'候補'};
 await h.poll();expectClear(h);assert.equal(h.node('proposal').hidden,false);assert.equal(h.node('confirm').disabled,false);
}
for(const failure of ['http','network','json']){
 const h=await pendingHarness(),request=h.submit();expectPending(h);
 if(failure==='http')request.resolve(response('入力を確認してください'));
 if(failure==='network')request.reject(new Error('offline'));
 if(failure==='json')request.resolve({ok:true,json:async()=>{throw new Error('invalid JSON');}});
 await flush();assert.notEqual(h.node('error').textContent,pendingMessage);assert.ok(h.node('error').textContent);assert.equal(h.node('error').className,'');
 const retry=h.submit();expectPending(h);retry.resolve(response());await flush();expectClear(h);
}
for(const action of ['stop','cancel'])for(const lateResult of ['success','http','network']){
 const h=await pendingHarness(),old=h.submit();expectPending(h);
 // Cancel is hidden during a command; exercise the shared mutation path without
 // changing that safety behavior. Stop remains a directly available UI action.
 if(action==='stop')h.node('stop').onclick();else h.cancel();
 expectClear(h);h.requests.at(-1).resolve(response());await flush();expectClear(h);
 if(lateResult==='network')old.reject(new Error('old failure'));else old.resolve(response(lateResult==='http'?'old error':null));
 await flush();expectClear(h);
}
for(const olderFinishesFirst of [true,false])for(const oldFails of [true,false]){
 const h=await pendingHarness(),old=h.submit(),latest=h.submit();expectPending(h);
 if(olderFinishesFirst){old.resolve(response(oldFails?'old error':null));await flush();expectPending(h);latest.resolve(response());}
 else{latest.resolve(response());await flush();expectClear(h);old.resolve(response(oldFails?'old error':null));}
 await flush();expectClear(h);
}
for(const pollFails of [true,false]){
 const h=await pendingHarness();h.deferPoll();const oldPoll=h.poll(),request=h.submit();expectPending(h);
 if(pollFails)h.polls[0].reject(new Error('stale poll'));else h.polls[0].resolve({json:async()=>h.state});
 await oldPoll;expectPending(h);
 const duringPoll=h.poll();request.resolve(response());await flush();expectClear(h);
 h.node('stop').onclick();h.requests.at(-1).resolve(response());await flush();expectClear(h);
 // Even a response that began during the command cannot restore old feedback
 // after the newer stop has settled.
 if(pollFails)h.polls[1].reject(new Error('stale poll'));else h.polls[1].resolve({json:async()=>h.state});
 await duringPoll;expectClear(h);
}
console.log('PASS: immediate neutral pending feedback, deferred body, success, HTTP/network/JSON failure, retry, stop/cancel, out-of-order commands and stale poll success/failure');

// A poll begun during a command is stale even if it arrives after that command.
for(const pollFails of [true,false]){
 const h=await pendingHarness(),request=h.submit();h.deferPoll();const poll=h.poll();
 request.resolve(response());await flush();expectClear(h);
 if(pollFails)h.polls[0].reject(new Error('poll started while pending'));
 else h.polls[0].resolve({json:async()=>h.state});
 await poll;expectClear(h);assert.equal(h.node('proposal').hidden,true);
}
console.log('PASS: polls begun during mutation cannot restore obsolete feedback after settlement');
// An older completion also cannot erase the newest request's failure.
{
 const h=await pendingHarness(),old=h.submit(),latest=h.submit();
 latest.resolve(response('最新の入力エラー'));await flush();
 old.resolve(response());await flush();
 assert.equal(h.node('error').textContent,'最新の入力エラー');assert.equal(h.node('error').className,'');
}
console.log('PASS: older success cannot erase the latest command error');
