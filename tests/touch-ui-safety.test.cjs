const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'app/assets/touch-ui.js'), 'utf8').replace(/\r\n/g,'\n');

function harness(state) {
  const nodes = new Map();
  const context = {
    st: structuredClone(state), window: {}, localStorage: {getItem: () => null},
    document: {getElementById: id => {if(!nodes.has(id)) nodes.set(id, {hidden:true,textContent:'',addEventListener:()=>{}}); return nodes.get(id);}, body:{classList:{add:()=>{},remove:()=>{}}}},
    setTimeout: () => 1, clearTimeout: () => {}, console,
    save: () => {context.saved++;}, renderAll: () => {}, haptic: () => {},
    showToast: message => {context.message=message;}, saved:0
  };
  const isolated = source.replace('  init();\n})();', '  window.testUndo=undoLastAction;\n})();');
  vm.runInNewContext(isolated, context);
  return context;
}
function base() {
  return {balances:{conta:{label:'Conta',amount:1000},vale1:{label:'VA',amount:100}},tx:[],credit:{used:200,reserved:70,tx:[]},investments:{total:500,history:[]},debtors:[{id:'preserved-debtor',amount:100}],myDebts:[{id:'preserved-debt',amount:40}],goals:[{id:'preserved-goal',saved:50}],customField:{preserve:true}};
}
function recordWallet(c) {
  const before=c.window.WEEDVERSO_TOUCH_UI.captureQuick('out','conta');
  c.st.balances.conta.amount-=20;
  c.st.tx.unshift({id:'new',account:'conta',type:'out',value:20,note:'Teste'});
  c.window.WEEDVERSO_TOUCH_UI.offerQuickUndo(before);
}

test('HTML inline JavaScript and UI module parse without dependencies', () => {
  const html=fs.readFileSync(path.join(root,'app/index.html'),'utf8');
  for(const match of html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)) new vm.Script(match[1]);
  new vm.Script(source);
  assert.match(html,/const KEY='rotina_prime_v2'/);
  assert.match(html,/assets\/touch-ui\.js\?v=1/);
  for(const file of ['index.html','assets/touch-ui.js','assets/touch-ui.css']) {
    assert.equal(fs.readFileSync(path.join(root,file),'utf8'),fs.readFileSync(path.join(root,'app',file),'utf8'),`Both entry points must serve the same ${file}`);
  }
});
test('undo reverses only the new wallet entry and preserves other state', () => {
  const initial=base(), c=harness(initial);
  recordWallet(c); c.window.testUndo();
  assert.deepEqual(c.st,initial); assert.equal(c.saved,1);
});
test('undo refuses a remotely changed balance without writing', () => {
  const c=harness(base()); recordWallet(c); c.st.balances.conta.amount=812;
  const current=structuredClone(c.st); c.window.testUndo();
  assert.deepEqual(c.st,current); assert.equal(c.saved,0);
});
test('undo refuses an edited transaction without writing', () => {
  const c=harness(base()); recordWallet(c); c.st.tx[0].note='Editado em outro aparelho';
  const current=structuredClone(c.st); c.window.testUndo();
  assert.deepEqual(c.st,current); assert.equal(c.saved,0);
});
test('undo preserves concurrent entries in another wallet', () => {
  const c=harness(base()); recordWallet(c);
  c.st.tx.unshift({id:'other',account:'vale1',type:'in',value:10}); c.st.balances.vale1.amount+=10;
  c.window.testUndo();
  assert.equal(c.st.balances.conta.amount,1000); assert.equal(c.st.balances.vale1.amount,110);
  assert.deepEqual(c.st.tx,[{id:'other',account:'vale1',type:'in',value:10}]);
});
test('undo refuses later operations even when their net effect is zero', () => {
  const c=harness(base()); recordWallet(c);
  c.st.tx.unshift({id:'later-in',account:'conta',value:5},{id:'later-out',account:'conta',value:5});
  const current=structuredClone(c.st); c.window.testUndo(); assert.deepEqual(c.st,current); assert.equal(c.saved,0);
});
test('credit undo leaves reserve, wallets and existing credit history intact', () => {
  const initial=base(), c=harness(initial);
  const before=c.window.WEEDVERSO_TOUCH_UI.captureQuick('card','conta');
  c.st.credit.used+=30; c.st.credit.tx.unshift({id:'new-card',type:'expense',value:30});
  c.window.WEEDVERSO_TOUCH_UI.offerQuickUndo(before); c.window.testUndo();
  assert.deepEqual(c.st,initial);
});
test('investment adjustment undo restores its exact preceding total', () => {
  const initial=base(), c=harness(initial);
  const before=c.window.WEEDVERSO_TOUCH_UI.captureInvestment(500);
  c.st.investments.total=900; c.st.investments.history.push({type:'set',value:900,balanceAfter:900});
  c.window.WEEDVERSO_TOUCH_UI.offerInvestmentUndo(before); c.window.testUndo();
  assert.deepEqual(c.st,initial);
});
test('investment undo refuses any later investment operation', () => {
  const c=harness(base()), before=c.window.WEEDVERSO_TOUCH_UI.captureInvestment(500);
  c.st.investments.total=600; c.st.investments.history.push({type:'add',value:100});
  c.window.WEEDVERSO_TOUCH_UI.offerInvestmentUndo(before);
  c.st.investments.total=650; c.st.investments.history.push({type:'add',value:50});
  const current=structuredClone(c.st); c.window.testUndo(); assert.deepEqual(c.st,current); assert.equal(c.saved,0);
});

function syncHarness() {
  const html=fs.readFileSync(path.join(root,'app/index.html'),'utf8');
  const start=html.indexOf('async function pullServerState(){');
  const end=html.indexOf('function flushStateOnly(){',start);
  const pending=[];
  const c={API_BASE:'http://preview',serverSync:{initialized:true,pushing:false,timer:null,lastSnapshot:''},value:'initial',st:{},writes:[],renders:0,
    snapshotState:()=>c.value, setTimeout:()=>42, clearTimeout:()=>{},
    requestApi:(route,opts)=>{if(opts)c.writes.push(opts.body); return new Promise(resolve=>pending.push(resolve));},
    normalizeLoadedState:value=>value,rotateDay:()=>{},writeStoredState:()=>{},renderAll:()=>c.renders++,hydrateShareInfo:()=>Promise.resolve()};
  vm.runInNewContext(html.slice(start,end),c);
  return {c,pending};
}
test('rapid saves queue the latest snapshot until the active write finishes', async () => {
  const {c,pending}=syncHarness();
  const first=c.pushServerState();
  c.value='undo'; await c.pushServerState();
  assert.deepEqual(c.writes,['initial']); assert.equal(c.serverSync.pendingPush,true);
  pending.shift()({ok:true}); await new Promise(resolve=>setImmediate(resolve));
  assert.deepEqual(c.writes,['initial','undo']);
  pending.shift()({ok:true}); await first;
  assert.equal(c.serverSync.lastSnapshot,'undo'); assert.equal(c.serverSync.pushing,false);
});
test('an older server response cannot replace a newer local operation', async () => {
  const {c,pending}=syncHarness();
  const pull=c.pullServerState(); c.value='local-newer'; pending.shift()({value:'server-older'});
  await pull; assert.equal(c.renders,0); assert.deepEqual(c.st,{});
});

function gistHarness() {
  const html=fs.readFileSync(path.join(root,'app/index.html'),'utf8');
  const start=html.indexOf('const GIST_SYNC={');
  const end=html.indexOf('\n};',start)+4;
  const pending=[],timers=[];
  const c={window:{},st:{value:'initial'},console,el:{},
    localStorage:{getItem:()=> 'test-token'},snapshotState:()=>JSON.stringify(c.st),
    setTimeout:callback=>{timers.push(callback);return 42;},clearTimeout:()=>{},
    fetch:(url,options)=>{c.requests.push(options);return new Promise(resolve=>pending.push(resolve));},requests:[],
    normalizeLoadedState:value=>value,rotateDay:()=>{},writeStoredState:()=>{},renderAll:()=>{c.renders++;},renders:0};
  vm.runInNewContext(html.slice(start,end)+'\nwindow.gist=GIST_SYNC;',c);
  c.window.gist.updateStatus=()=>{};
  return {c,pending,timers};
}
test('Gist queues a later operation while the previous snapshot is uploading', async () => {
  const {c,pending,timers}=gistHarness();
  const first=c.window.gist.push(); c.st={value:'undo'}; await c.window.gist.push();
  pending.shift()({ok:true}); await first;
  assert.equal(timers.length,1); timers.shift()();
  const payload=JSON.parse(c.requests[1].body).files['weedverso_state.json'].content;
  assert.equal(JSON.parse(payload).value,'undo'); pending.shift()({ok:true});
});
test('Gist never replaces a local operation with an older in-flight download', async () => {
  const {c,pending}=gistHarness();
  const pull=c.window.gist.pull(true); c.st={value:'local-newer'};
  pending.shift()({ok:true,json:async()=>({files:{'weedverso_state.json':{content:JSON.stringify({value:'older'})}}})});
  await pull; assert.equal(c.st.value,'local-newer'); assert.equal(c.renders,0);
});
