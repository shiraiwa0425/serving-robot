// UI state/interaction regression in Node; this is not visual browser verification.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const html=fs.readFileSync(new URL('./index.html',import.meta.url),'utf8');
const elements=new Map();const element=id=>{if(!elements.has(id))elements.set(id,{disabled:false,hidden:true,textContent:'',innerHTML:'',value:''});return elements.get(id);};
const timers=[],posts=[];let holdCommand=false,releaseCommand=null;
let current={epoch:1,x:.7,y:.7,speed:0,status:'awaiting_confirmation',time:1,path:[],goals:{kitchen:[.7,.7]},boxes:[],intent:{backend:'mock',message:'candidate'},candidate:{id:'A',label:'2番卓と3番卓の間',point:[4,4.2],path:[],explanation:'安全な候補'}};
const response=()=>({ok:true,json:async()=>({ok:true})});
const context=vm.createContext({document:{getElementById:element},setTimeout:fn=>timers.push(fn),fetch:async(path,options)=>{
 if(path==='/state')return {json:async()=>structuredClone(current)};
 posts.push({path,body:JSON.parse(options.body)});
 if(path==='/command'&&holdCommand)return new Promise(resolve=>releaseCommand=()=>resolve(response()));
 return response();
}});
vm.runInContext(html.split('<script>')[1].split('</script>')[0],context);
const flush=()=>new Promise(resolve=>setImmediate(resolve));await flush();
assert.equal(element('proposal').hidden,false);assert.equal(element('confirm').disabled,false);assert.match(element('candidate-label').textContent,/2番卓/);
element('confirm').onclick();element('confirm').onclick();await flush();
assert.equal(posts.filter(x=>x.path==='/confirm').length,1);assert.equal(posts[0].body.candidate_id,'A');
holdCommand=true;element('text').value='右上へ';element('form').onsubmit({preventDefault(){}});
assert.equal(element('confirm').disabled,true);await timers.shift()();await flush();
assert.equal(element('confirm').disabled,true);assert.equal(element('proposal').hidden,true);
current={...current,epoch:2,candidate:{...current.candidate,id:'B',label:'右上の角付近'}};releaseCommand();await flush();await timers.shift()();await flush();
assert.equal(element('confirm').disabled,false);assert.equal(element('candidate-label').textContent,'右上の角付近');
element('cancel').onclick();await flush();assert.equal(posts.at(-1).path,'/cancel');assert.equal(posts.at(-1).body.candidate_id,'B');
element('stop').onclick();await flush();assert.equal(posts.at(-1).path,'/stop');assert.equal(element('confirm').disabled,true);
console.log('PASS: candidate display, explicit confirmation, double click, pending-command stale poll suppression, fresh candidate, cancel, stop');
