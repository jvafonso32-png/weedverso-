
// Higienização de URL: mantém a URL sempre limpa e idêntica
try{
  if(window.location.search && !window.location.search.includes('code=')){
    var cleanUrl=window.location.origin+window.location.pathname+(window.location.hash||'');
    window.history.replaceState(null,'',cleanUrl);
  }
}catch(e){}

const KEY='rotina_prime_v2', PRIVACY_KEY=`${KEY}:privacy`, XP_H=40;
const MONTH_SHORT_LABELS=['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
const IS_REMOTE_APP=Boolean(window.location && /^https?:$/i.test(window.location.protocol));
const DESKTOP_BACKUP_SUPPORTED=!IS_REMOTE_APP||/Windows/i.test(String(navigator.userAgent||''));
const API_BASE=(function(){
  if(window.WEEDVERSO_API_BASE) return window.WEEDVERSO_API_BASE;
  if(IS_REMOTE_APP) return '';
  return 'http://127.0.0.1:8765';
})();
const STORAGE=(function(){
  try{
    return window.localStorage;
  }catch(err){
    try{ return window.sessionStorage; }catch(e){ return null; }
  }
})();
const DEF={
  appName:'weedverso',userName:'',xp:40,streak:0,routineDone:false,lastDate:'2026-10-03',
  habits:[
    {id:'qfp42sybsajcf',name:'Academia',goal:'',done:false,date:'2026-09-11',lastDoneAt:'2026-09-12T02:46:51.164Z',skillTag:'treinar'}
  ],
  balances:{
    conta:{label:'Saldo em Conta',amount:569.06},
    vale1:{label:'Alelo Alimentação',amount:594.69},
    vale2:{label:'Alelo Refeição',amount:421.01}
  },
  tx:[],
  credit:{
    name:'AMEX',
    used:3684,
    reserved:860,
    tx:[
      {id:'mia2fr322yblk',type:'expense',value:1400,desc:'',category:'Sem Categoria',categoryKey:'sem categoria',at:'2026-09-18T14:55:03.992Z'},
      {id:'lyyw631r2xxun',type:'reserve-in',value:700,desc:'Reserva cartão',category:'Reserva Cartao',categoryKey:'reserva cartao',at:'2026-09-18T14:54:46.175Z'},
      {id:'qnrueho6x12ei',type:'reserve-in',value:160,desc:'Reserva cartão',category:'Reserva Cartao',categoryKey:'reserva cartao',at:'2026-09-10T02:36:00.234Z'},
      {id:'09x2q0i4x0qeh',type:'expense',value:4383,desc:'Gasto no cartão',category:'Sem Categoria',categoryKey:'sem categoria',at:'2026-09-10T02:35:44.681Z'}
    ]
  },
  debtors:[
    {id:'kler0dqobgw3r',name:'André',amount:282,note:'',payDate:'',paid:false,paidAt:'',at:'2026-09-15T23:42:22.599Z'},
    {id:'1glozn8ex2nu3',name:'Lucas',amount:267,note:'',payDate:'2026-09-29',paid:true,paidAt:'2026-09-29T16:48:02.214Z',at:'2026-09-10T02:37:14.667Z'},
    {id:'h0zpcvijx1zkz',name:'Dilson',amount:366,note:'',payDate:'',paid:false,paidAt:'',at:'2026-09-10T02:36:43.235Z'},
    {id:'lndsa4olx1r0s',name:'Pai',amount:1200,note:'',payDate:'2026-10-01',paid:false,paidAt:'',at:'2026-09-10T02:36:32.140Z'}
  ],
  myDebts:[],
  routineLog:[],
  skills:{estudar:0,treinar:25,trabalhar:0},
  goals:[],
  dailyStats:{'2026-09-09':{done:0,total:0,percent:0},'2026-09-10':{done:0,total:0,percent:0}},
  focusSession:{habitId:'qfp42sybsajcf',secondsLeft:1500,running:false}
};
var focusTick=null;
var st=load();
const ui={page:'home',privacy:readPrivacyMode(),financePeriod:'7d',accountFlowPeriod:'month',debtsView:(function(){try{return localStorage.getItem('weedverso_debts_view')||'debtors';}catch(e){return 'debtors';}})(),statementFilter:'all',statementSearch:'',balances:{conta:false,vale1:false,vale2:false},credit:false,creditChartMonth:'',debtors:{},myDebts:{},goals:{},statement:{wallet:false,food:false,credit:false,five:false,goal:false},statementEditor:null};
const serverSync={initialized:false,available:false,timer:null,poller:null,pushing:false,lastSnapshot:''};
const SERVER_POLL_ACTIVE_MS=1000;
const SERVER_POLL_BACKGROUND_MS=3000;
const publishSync={busy:false,version:0,updatedAt:'',reason:'',links:{preferred:'',local:'',public:''},notifications:{telegram:'idle',discord:'idle'},lastError:''};
const codeBackupSync={launching:false,poller:null,pollDeadline:0,status:'idle',message:'',startedAt:'',finishedAt:'',lastRunAt:'',branch:'',commit:'',remote:'',changedFiles:0,lastError:'',lastSeenAt:''};

function haptic(type='light'){
  try{
    if(!navigator.vibrate) return;
    if(type==='light') navigator.vibrate(12);
    else if(type==='medium') navigator.vibrate(25);
    else if(type==='success') navigator.vibrate([15, 30, 20]);
    else if(type==='error') navigator.vibrate([35, 40, 35]);
  }catch(e){}
}

function showToast(message, type='ok', duration=3200){
  const container=document.getElementById('toastContainer');
  if(!container) return;
  const t=document.createElement('div');
  t.className=`toast toast-${type}`;
  const icon=type==='error'?'⚠️':type==='warn'?'🔔':'✓';
  t.innerHTML=`<span style="font-size:1rem;line-height:1">${icon}</span><span>${esc(message)}</span>`;
  container.appendChild(t);
  setTimeout(()=>{
    t.classList.add('toast-out');
    setTimeout(()=>t.remove(),260);
  },duration);
}

function evaluateMathExpression(str){
  if(!str) return null;
  const clean=String(str).trim().replace(/,/g,'.');
  if(!/^[\d\s\+\-\*\/\.\(\)]+$/.test(clean)) return null;
  try{
    const tokens=clean.match(/(\d+(?:\.\d+)?|[\+\-\*\/\(\)])/g);
    if(!tokens) return null;
    let pos=0;
    function parsePrimary(){
      const t=tokens[pos++];
      if(t==='('){
        const val=parseAddSub();
        if(tokens[pos++]!==')') throw new Error();
        return val;
      }
      if(t==='-') return -parsePrimary();
      if(t==='+') return parsePrimary();
      const num=parseFloat(t);
      if(isNaN(num)) throw new Error();
      return num;
    }
    function parseMulDiv(){
      let val=parsePrimary();
      while(pos<tokens.length && (tokens[pos]==='*' || tokens[pos]==='/')){
        const op=tokens[pos++];
        const right=parsePrimary();
        if(op==='*') val *= right;
        else{
          if(right===0) throw new Error();
          val /= right;
        }
      }
      return val;
    }
    function parseAddSub(){
      let val=parseMulDiv();
      while(pos<tokens.length && (tokens[pos]==='+' || tokens[pos]==='-')){
        const op=tokens[pos++];
        const right=parseMulDiv();
        if(op==='+') val += right;
        else val -= right;
      }
      return val;
    }
    const result=parseAddSub();
    if(pos<tokens.length) return null;
    return Number.isFinite(result)?result:null;
  }catch(e){
    return null;
  }
}

function triggerConfetti(){
  const canvas=document.getElementById('confettiCanvas');
  if(!canvas) return;
  const ctx=canvas.getContext('2d');
  if(!ctx) return;
  canvas.width=window.innerWidth;
  canvas.height=window.innerHeight;
  canvas.style.display='block';
  const colors=['#39ff8f','#00f5ff','#ff3366','#ffd056','#a78bfa','#ffffff'];
  const particles=[];
  for(let i=0;i<75;i++){
    particles.push({
      x:canvas.width*0.5+(Math.random()-0.5)*120,
      y:canvas.height*0.35+(Math.random()-0.5)*100,
      vx:(Math.random()-0.5)*14,
      vy:(Math.random()-1.2)*15,
      size:Math.random()*8+4,
      color:colors[Math.floor(Math.random()*colors.length)],
      alpha:1,
      decay:Math.random()*0.015+0.012,
      rotation:Math.random()*360,
      rotSpeed:(Math.random()-0.5)*12
    });
  }
  let animId=null;
  function animate(){
    ctx.clearRect(0,0,canvas.width,canvas.height);
    let alive=false;
    for(let p of particles){
      if(p.alpha>0){
        alive=true;
        p.x+=p.vx;
        p.y+=p.vy;
        p.vy+=0.38;
        p.vx*=0.98;
        p.rotation+=p.rotSpeed;
        p.alpha=Math.max(0,p.alpha-p.decay);
        ctx.save();
        ctx.globalAlpha=p.alpha;
        ctx.fillStyle=p.color;
        ctx.translate(p.x,p.y);
        ctx.rotate((p.rotation*Math.PI)/180);
        ctx.fillRect(-p.size/2,-p.size/2,p.size,p.size*0.6);
        ctx.restore();
      }
    }
    if(alive){
      animId=requestAnimationFrame(animate);
    }else{
      cancelAnimationFrame(animId);
      canvas.style.display='none';
      ctx.clearRect(0,0,canvas.width,canvas.height);
    }
  }
  animate();
}

function getUserLevelInfo(){
  const xp=Number(st.xp)||0;
  const streak=Number(st.streak)||0;
  if(xp>=700 || streak>=14){
    return {level:4, name:'Mestre weedverso', icon:'👑'};
  }else if(xp>=300 || streak>=7){
    return {level:3, name:'Implacável', icon:'🔥'};
  }else if(xp>=100 || streak>=3){
    return {level:2, name:'Focado', icon:'⚡'};
  }
  return {level:1, name:'Aspirante', icon:'🌱'};
}

function renderAchievements(){
  const lvl=getUserLevelInfo();
  const badgeEl=document.getElementById('userLevelBadge');
  if(badgeEl){
    badgeEl.innerHTML=`${lvl.icon} Nv. ${lvl.level} · ${safe(lvl.name)}`;
  }
  const achRow=document.getElementById('achievementsRow');
  if(!achRow) return;
  const list=[
    {id:'first_habit', label:'Primeiro Passo', icon:'🎯', unlocked:(st.habits||[]).some(h=>h.done)},
    {id:'streak_3', label:'Streak 3d', icon:'🔥', unlocked:(Number(st.streak)||0)>=3},
    {id:'reserve_ready', label:'Reserva Ativa', icon:'🛡️', unlocked:(st.credit && Number(st.credit.reserved)>0)},
    {id:'perfect_day', label:'Dia 100%', icon:'👑', unlocked:(st.habits||[]).length>0 && (st.habits||[]).every(h=>h.done)}
  ];
  achRow.innerHTML=list.map(a=>`
    <div class="trophyPill ${a.unlocked?'unlocked':'locked'}" title="${a.unlocked?'Conquista desbloqueada!':'Bloqueado: cumpra o objetivo para liberar'}">
      <span>${a.icon}</span>
      <span>${safe(a.label)}</span>
      <span>${a.unlocked?'✓':'🔒'}</span>
    </div>
  `).join('');
}

function debtorDueTag(d){
  if(d.paid || !d.payDate) return '';
  const todayStr=new Date().toISOString().slice(0,10);
  const d1=new Date(todayStr), d2=new Date(d.payDate);
  const diff=Math.round((d2 - d1)/(1000*60*60*24));
  if(diff < 0) return `<span class="tag danger" style="background:rgba(255,95,112,.18);color:#ff7d8d;border-color:rgba(255,95,112,.4);">🚨 Atrasado ${Math.abs(diff)}d</span>`;
  if(diff === 0) return `<span class="tag warn" style="background:rgba(255,184,0,.18);color:#ffd056;border-color:rgba(255,184,0,.4);">🔔 Vence hoje!</span>`;
  if(diff <= 3) return `<span class="tag warn" style="background:rgba(255,184,0,.15);color:#ffd056;border-color:rgba(255,184,0,.35);">⚠️ Vence em ${diff}d</span>`;
  return `<span class="tag month" style="color:#9fb3a8;">⏳ Vence em ${diff}d</span>`;
}

function openZenMode(){
  const overlay=document.getElementById('zenFocusOverlay');
  if(!overlay) return;
  overlay.style.display='flex';
  overlay.setAttribute('aria-hidden','false');
  updateZenDisplay();
  if(!st.focusSession.running){
    startFocusSession();
  }
}
function closeZenMode(){
  const overlay=document.getElementById('zenFocusOverlay');
  if(!overlay) return;
  overlay.style.display='none';
  overlay.setAttribute('aria-hidden','true');
}
function updateZenDisplay(){
  const overlay=document.getElementById('zenFocusOverlay');
  if(!overlay || overlay.style.display==='none') return;
  const sec=Math.max(0,parseInt(st.focusSession.secondsLeft||0,10));
  const mm=String(Math.floor(sec/60)).padStart(2,'0');
  const ss=String(sec%60).padStart(2,'0');
  const clock=document.getElementById('zenTimerDisplay');
  if(clock) clock.textContent=`${mm}:${ss}`;
  const habit=(st.habits||[]).find(h=>h.id===st.focusSession.habitId);
  const title=document.getElementById('zenHabitTitle');
  if(title) title.textContent=habit?habit.name:'Foco Total';
  const status=document.getElementById('zenStatusLabel');
  if(status) status.textContent=st.focusSession.running?'⚡ Foco Ativo':'⏸ Pausado';
  const pauseBtn=document.getElementById('zenPauseBtn');
  if(pauseBtn) pauseBtn.textContent=st.focusSession.running?'Pausar':'Continuar';
}

function setupPullToRefresh(){
  const indicator=document.getElementById('pullIndicator');
  if(!indicator) return;
  let startY=0;
  let pulling=false;
  let dist=0;
  const threshold=70;
  window.addEventListener('touchstart',e=>{
    if(window.scrollY<=0 && e.touches.length===1){
      startY=e.touches[0].clientY;
      pulling=true;
      dist=0;
    }else{
      pulling=false;
    }
  },{passive:true});
  window.addEventListener('touchmove',e=>{
    if(!pulling) return;
    const y=e.touches[0].clientY;
    dist=y-startY;
    if(dist>15 && window.scrollY<=0){
      indicator.style.display='flex';
      const translateY=Math.min(dist*0.42, 55);
      indicator.style.transform=`translateY(${translateY}px)`;
      if(dist>=threshold){
        indicator.textContent='↑ Solte para sincronizar';
        indicator.classList.add('ready');
      }else{
        indicator.textContent='↓ Puxe para sincronizar';
        indicator.classList.remove('ready');
      }
    }else{
      indicator.style.display='none';
    }
  },{passive:true});
  window.addEventListener('touchend',()=>{
    if(!pulling) return;
    pulling=false;
    if(dist>=threshold){
      indicator.textContent='🔄 Sincronizando...';
      indicator.style.transform='translateY(50px)';
      const doneSync=()=>{
        setTimeout(()=>{
          indicator.style.display='none';
          indicator.style.transform='';
          showToast('✓ Sincronizado!','ok');
        },550);
      };
      if(typeof GIST_SYNC!=='undefined' && GIST_SYNC.hasToken()){
        GIST_SYNC.pull(true).finally(doneSync);
      }else if(API_BASE){
        pullServerState().finally(doneSync);
      }else{
        doneSync();
      }
    }else{
      indicator.style.display='none';
      indicator.style.transform='';
    }
    dist=0;
  });
}

const GIST_SYNC={
  id:'20470ade1d831a08ca6f87955658d8a2',
  tokenKey:'weedverso_gh_sync_token',
  pushTimer:null,
  busy:false,
  statusText:'',
  getToken:function(){
    try{return localStorage.getItem(this.tokenKey)||'';}catch(e){return '';}
  },
  setToken:function(val){
    try{
      if(val) localStorage.setItem(this.tokenKey,val.trim());
      else localStorage.removeItem(this.tokenKey);
    }catch(e){}
  },
  hasToken:function(){
    return Boolean(this.getToken());
  },
  pull:async function(quiet){
    const token=this.getToken();
    this.busy=true;
    if(token) this.updateStatus('☁️ Sincronizando com GitHub...','running');
    try{
      const headers={'Accept':'application/vnd.github+json'};
      if(token) headers['Authorization']='token '+token;
      const resp=await fetch('https://api.github.com/gists/'+this.id,{headers:headers});
      if(!resp.ok){
        if(token && resp.status===401) throw new Error('Token inválido');
        return false;
      }
      const data=await resp.json();
      const fileInfo=data.files && data.files['weedverso_state.json'];
      if(fileInfo && fileInfo.content){
        const parsed=JSON.parse(fileInfo.content);
        if(parsed && typeof parsed==='object'){
          st=normalizeLoadedState(parsed);
          rotateDay();
          writeStoredState(JSON.stringify(st));
          renderAll();
          const hora=new Date().toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'});
          this.updateStatus('☁️ Git Sincronizado '+hora,'ok');
          if(!quiet && token) showToast('☁️ Sincronização concluída! Dados atualizados do GitHub.','ok');
          return true;
        }
      }
    }catch(err){
      console.warn('Gist pull err:',err);
      if(token){
        this.updateStatus('☁️ Git: '+(err.message||'Falha ao sincronizar'),'error');
        if(!quiet) showToast('⚠️ Erro ao sincronizar com GitHub: '+(err.message||'Falha de rede'),'error');
      }
    }finally{
      this.busy=false;
    }
    return false;
  },
  push:async function(){
    const token=this.getToken();
    if(!token||this.busy) return;
    this.busy=true;
    this.updateStatus('☁️ Enviando ao GitHub...','running');
    try{
      const payload={
        files:{
          'weedverso_state.json':{
            content:JSON.stringify(st,null,2)
          }
        }
      };
      const resp=await fetch('https://api.github.com/gists/'+this.id,{
        method:'PATCH',
        headers:{
          'Authorization':'token '+token,
          'Accept':'application/vnd.github+json',
          'Content-Type':'application/json'
        },
        body:JSON.stringify(payload)
      });
      if(!resp.ok) throw new Error('HTTP '+resp.status);
      const hora=new Date().toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'});
      this.updateStatus('☁️ Git Atualizado '+hora,'ok');
    }catch(err){
      console.warn('Gist push err:',err);
      this.updateStatus('☁️ Git: Falha ao enviar','error');
    }finally{
      this.busy=false;
    }
  },
  schedulePush:function(){
    if(!this.hasToken()) return;
    if(this.pushTimer) clearTimeout(this.pushTimer);
    this.pushTimer=setTimeout(()=>this.push(),1200);
  },
  updateStatus:function(text,tone){
    this.statusText=text;
    if(el.codeBackupStatus){
      el.codeBackupStatus.textContent=text;
      el.codeBackupStatus.dataset.tone=tone||'ok';
    }
    if(el.saveCodeBtn){
      el.saveCodeBtn.disabled=false;
      el.saveCodeBtn.style.opacity='1';
      el.saveCodeBtn.textContent=this.hasToken()?'☁️ Nuvem Git':'☁️ Conectar Git';
    }
  },
  handleClick:function(){
    if(!this.hasToken()){
      const token=prompt('Para sincronizar os gastos entre seu iPhone e o computador, cole seu Token do GitHub:');
      if(token && token.trim()){
        this.setToken(token.trim());
        this.pull(false);
      }
    }else{
      const opt=confirm('Sincronizar agora com o GitHub?\n\n(Dica: Para desconectar o token, clique em Cancelar)');
      if(opt){
        this.pull(false);
      }else{
        if(confirm('Deseja desconectar o token do GitHub deste aparelho?')){
          this.setToken('');
          this.updateStatus('☁️ Conectar Git','idle');
          showToast('Token desconectado com sucesso.','ok');
        }
      }
    }
  }
};

const $=s=>document.querySelector(s);
const el={
  app:$('#appName'),appRefreshBtn:$('#appRefreshBtn'),privacyToggleBtn:$('#privacyToggleBtn'),saveCodeBtn:$('#saveCodeBtn'),saveAllBtn:$('#saveAllBtn'),openShareLinkBtn:$('#openShareLinkBtn'),saveStatus:$('#saveStatus'),saveStamp:$('#saveStamp'),saveChannels:$('#saveChannels'),codeBackupStatus:$('#codeBackupStatus'),logoutBtn:$('#logoutBtn'),homePage:$('#homePage'),routinePage:$('#routinePage'),creditPage:$('#creditPage'),debtsPage:$('#debtsPage'),goalsPage:$('#goalsPage'),statementPage:$('#statementPage'),navBtns:document.querySelectorAll('[data-page]'),
  focusPill:$('#focusPill'),heroTitle:$('#heroTitle'),heroDesc:$('#heroDesc'),heroBalance:$('#heroBalance'),heroRisk:$('#heroRisk'),heroDebt:$('#heroDebt'),quickActions:$('#quickActions'),
  financeChartFilters:$('#financeChartFilters'),accountFlowFilters:$('#accountFlowFilters'),accountFlowPeriodLabel:$('#accountFlowPeriodLabel'),
  hForm:$('#habitForm'),hName:$('#hName'),hGoal:$('#hGoal'),hDate:$('#hDate'),focusHabitSelect:$('#focusHabitSelect'),focusMinutesInput:$('#focusMinutesInput'),focusStartBtn:$('#focusStartBtn'),focusPauseBtn:$('#focusPauseBtn'),focusResetBtn:$('#focusResetBtn'),focusClock:$('#focusClock'),focusStatus:$('#focusStatus'),hList:$('#habitList'),mot:$('#motivation'),routineDateInfo:$('#routineDateInfo'),routineLog:$('#routineLog'),routineChart:$('#routineChart'),
  fGrid:$('#finGrid'),hist:$('#history'),foodStmt:$('#foodStmt'),accountFlowChart:$('#accountFlowChart'),accountFlowLegend:$('#accountFlowLegend'),accountFlowTotal:$('#accountFlowTotal'),
  ccEditBtn:$('#ccEditBtn'),ccMeta:$('#ccMeta'),ccMetaSummary:$('#ccMetaSummary'),ccMetaHint:$('#ccMetaHint'),ccName:$('#ccName'),ccValue:$('#ccValue'),ccDesc:$('#ccDesc'),
  ccExpense:$('#ccExpense'),ccPay:$('#ccPay'),ccClear:$('#ccClear'),ccUsed:$('#ccUsed'),ccUncovered:$('#ccUncovered'),ccReserved:$('#ccReserved'),ccReserveValue:$('#ccReserveValue'),ccReserveIn:$('#ccReserveIn'),ccReserveOut:$('#ccReserveOut'),ccBar:$('#ccBar'),ccHistory:$('#ccHistory'),ccDescChart:$('#ccDescChart'),ccDescLegend:$('#ccDescLegend'),ccDescTotal:$('#ccDescTotal'),ccChartMonth:$('#ccChartMonth'),ccChartMonthTag:$('#ccChartMonthTag'),ccChartPrev:$('#ccChartPrev'),ccChartNext:$('#ccChartNext'),ccChartReset:$('#ccChartReset'),financeChart:$('#financeChart'),
  debForm:$('#debForm'),debName:$('#debName'),debAmount:$('#debAmount'),debInstallments:$('#debInstallments'),debInstallmentPreview:$('#debInstallmentPreview'),debNote:$('#debNote'),debPayDate:$('#debPayDate'),debList:$('#debList'),last5Stmt:$('#last5Stmt'),
  mdForm:$('#mdForm'),mdName:$('#mdName'),mdAmount:$('#mdAmount'),mdInstallments:$('#mdInstallments'),mdInstallmentPreview:$('#mdInstallmentPreview'),mdNote:$('#mdNote'),mdPayDate:$('#mdPayDate'),myDebtList:$('#myDebtList'),mdSummaryLine:$('#mdSummaryLine'),mdProgress:$('#mdProgress'),mdWeek:$('#mdWeek'),mdOpenFormBtn:$('#mdOpenFormBtn'),
  goalForm:$('#goalForm'),goalName:$('#goalName'),goalTarget:$('#goalTarget'),goalActiveCount:$('#goalActiveCount'),goalWeekYield:$('#goalWeekYield'),goalList:$('#goalList'),goalStmt:$('#goalStmt'),goalsTotalSavedBox:$('#goalsTotalSavedBox'),
  sPercent:$('#sPercent'),sHabits:$('#sHabits'),sSpent:$('#sSpent'),sCard:$('#sCard'),sDebt:$('#sDebt'),sGoals:$('#sGoals'),sStatus:$('#sStatus'),sMsg:$('#sMsg'),
  homeMissionsCard:$('#homeMissionsCard'),homeHabitList:$('#homeHabitList'),homeAddHabitBtn:$('#homeAddHabitBtn'),
  virtualCreditCard:$('#virtualCreditCard'),ccCardCoverageStatus:$('#ccCardCoverageStatus'),ccCardUsed:$('#ccUsed'),ccCardName:$('#ccCardName'),ccCardReserved:$('#ccReserved'),ccQuickChips:$('#ccQuickChips'),
  debtsSegmentBar:$('#debtsSegmentBar'),debtsMyDebtsView:$('#debtsMyDebtsView'),debtsDebtorsView:$('#debtsDebtorsView'),debtsPageTotalBox:$('#debtsPageTotalBox'),debtsPageCountBox:$('#debtsPageCountBox'),debtsPageDebForm:$('#debForm'),debPageName:$('#debName'),debPageAmount:$('#debAmount'),debPageInstallments:$('#debInstallments'),debPageNote:$('#debNote'),debPagePayDate:$('#debPayDate'),debtsPageDebList:$('#debList'),
  unifiedStatementCard:$('#unifiedStatementCard'),copyStatementBtn:$('#copyStatementBtn'),statementSearchInput:$('#statementSearchInput'),statementFeedFilters:$('#statementFeedFilters'),unifiedStatementFeed:$('#unifiedStatementFeed')
};

const quickAddSheet={
  overlay:null,form:null,valInput:null,noteInput:null,tabBtns:null,accBtns:null,accField:null,
  currentTab:'out',currentAcc:'conta',
  init:function(){
    this.overlay=$('#quickAddOverlay');
    this.form=$('#quickAddForm');
    this.valInput=$('#quickAddValue');
    this.noteInput=$('#quickAddNote');
    this.tabBtns=document.querySelectorAll('#quickAddTabs .sheetTab');
    this.accBtns=document.querySelectorAll('#quickAddAccountPills .sheetPill');
    this.accField=$('#quickAddAccountField');

    const closeBtn=$('#closeQuickAddBtn');
    if(closeBtn) closeBtn.addEventListener('click',()=>this.close());
    if(this.overlay){
      this.overlay.addEventListener('click',e=>{
        if(e.target===this.overlay) this.close();
      });
    }
    if(this.tabBtns){
      this.tabBtns.forEach(btn=>{
        btn.addEventListener('click',()=>{
          this.currentTab=btn.dataset.tab;
          this.updateTabUI();
          haptic('light');
        });
      });
    }
    if(this.accBtns){
      this.accBtns.forEach(btn=>{
        btn.addEventListener('click',()=>{
          this.currentAcc=btn.dataset.acc;
          this.accBtns.forEach(b=>b.classList.toggle('active',b===btn));
          haptic('light');
        });
      });
    }
    const chipContainer=$('#quickCategoryChips');
    if(chipContainer){
      chipContainer.addEventListener('click',e=>{
        const chip=e.target.closest('[data-tag]');
        if(!chip) return;
        if(this.noteInput) this.noteInput.value=chip.dataset.tag;
        haptic('light');
      });
    }
    const preview=$('#quickCalcPreview');
    if(this.valInput){
      this.valInput.addEventListener('input',()=>{
        const v=(this.valInput.value||'').trim();
        if(/[\+\-\*\/]/.test(v)){
          const res=evaluateMathExpression(v);
          if(res!==null && res>=0 && preview){
            preview.style.display='block';
            preview.textContent='= '+money(res);
          }else if(preview){
            preview.style.display='none';
          }
        }else if(preview){
          preview.style.display='none';
        }
      });
    }
    const fab=$('#fabQuickAddBtn');
    if(fab && !fab._bound){
      fab._bound=true;
      fab.addEventListener('click',()=>this.open('out'));
    }
    if(this.form){
      this.form.addEventListener('submit',e=>{
        e.preventDefault();
        let val=evaluateMathExpression(this.valInput.value);
        if(val===null || !Number.isFinite(val) || val<=0){
          const raw=parseFloat((this.valInput.value||'').replace(',','.'));
          val=Number.isFinite(raw)?Math.abs(raw):0;
        }
        if(val<=0){
          showToast('Informe um valor maior que zero.','warn');
          return;
        }
        const note=txt(this.noteInput.value,42);
        const tab=this.currentTab;
        const acc=this.currentAcc||'conta';

        if(tab==='out'){
          move(acc,'out',val,note||'Gasto rápido');
          showToast('✓ Saída de '+money(val)+' salva!','ok');
        }else if(tab==='in'){
          move(acc,'in',val,note||'Entrada');
          showToast('✓ Entrada de '+money(val)+' salva!','ok');
        }else if(tab==='card'){
          st.credit.used += val;
          const meta=categoryMeta(note,'Sem categoria');
          st.credit.tx.unshift({
            id:id(),
            type:'expense',
            value:val,
            desc:note||'Gasto no cartão',
            category:meta.label,
            categoryKey:meta.key,
            at:new Date().toISOString()
          });
          haptic('medium');
          save(true);
          renderCredit();
          renderSummary();
          showToast('✓ Gasto de '+money(val)+' salvo no cartão!','ok');
        }
        this.close();
      });
    }
  },
  open:function(tab='out'){
    this.currentTab=tab;
    this.updateTabUI();
    const preview=$('#quickCalcPreview');
    if(preview) preview.style.display='none';
    if(this.overlay){
      this.overlay.classList.add('open');
      this.overlay.setAttribute('aria-hidden','false');
    }
    setTimeout(()=>{
      if(this.valInput){
        this.valInput.value='';
        this.valInput.focus();
      }
      if(this.noteInput) this.noteInput.value='';
    },80);
  },
  close:function(){
    const preview=$('#quickCalcPreview');
    if(preview) preview.style.display='none';
    if(this.overlay){
      this.overlay.classList.remove('open');
      this.overlay.setAttribute('aria-hidden','true');
    }
    if(this.valInput) this.valInput.blur();
    try{
      if(window.location.hash.includes('quick')){
        history.replaceState(null, '', window.location.pathname + window.location.search);
      }
    }catch(e){}
  },
  updateTabUI:function(){
    if(this.tabBtns){
      this.tabBtns.forEach(btn=>{
        btn.classList.toggle('active',btn.dataset.tab===this.currentTab);
      });
    }
    if(this.accField){
      this.accField.style.display=this.currentTab==='card'?'none':'grid';
    }
  }
};

function loginLocation(){
  return IS_REMOTE_APP ? '/login' : `${API_BASE}/login`;
}
async function ensureSessionAccess(){
  try{
    const res=await fetch(`${API_BASE}/api/session`,{credentials:'same-origin'});
    if(!res.ok) return true;
    const data=await res.json();
    if(data && data.authEnabled && !data.authenticated){
      clearStoredState();
      window.location.replace(loginLocation());
      return false;
    }
  }catch(err){}
  return true;
}

boot();
async function boot(){
  if(API_BASE && !(await ensureSessionAccess())) return;
  rotateDay();
  bind();
  renderPrivacyToggle();
  if(!el.hDate.value) el.hDate.value=today();
  syncPageFromHash();
  renderAll();
  setupPullToRefresh();
  try{ await GIST_SYNC.pull(true); }catch(e){}
  if(API_BASE){
    await hydrateFromServer();
    await hydrateShareInfo();
    await hydrateDesktopCodeBackupStatus();
    serverSync.initialized=true;
    startServerPolling();
  }
}
function bind(){
  for(var i=0;i<el.navBtns.length;i++){
    (function(btn){
      btn.addEventListener('click',function(){showPage(btn.getAttribute('data-page'));});
    })(el.navBtns[i]);
  }
  if(el.appRefreshBtn){
    el.appRefreshBtn.addEventListener('click',async function(){
      showToast('🔄 Atualizando aplicativo...','ok');
      try{
        if('caches' in window){
          const keys=await caches.keys();
          await Promise.all(keys.map(k=>caches.delete(k)));
        }
        if('serviceWorker' in navigator){
          const regs=await navigator.serviceWorker.getRegistrations();
          for(let r of regs){ await r.unregister(); }
        }
      }catch(e){}
      try{ sessionStorage.clear(); }catch(e){}
      try{
        if(window.location.search && !window.location.search.includes('code=')){
          history.replaceState(null, '', window.location.pathname);
        }
      }catch(e){}
      setTimeout(function(){
        window.location.href = window.location.pathname + '?v=' + Date.now();
      },250);
    });
  }
  if(el.logoutBtn){
    el.logoutBtn.addEventListener('click',logout);
  }
  if(el.privacyToggleBtn){
    el.privacyToggleBtn.addEventListener('click',togglePrivacyMode);
  }
  if(el.saveCodeBtn){
    el.saveCodeBtn.addEventListener('click',function(){
      GIST_SYNC.handleClick();
    });
  }
  if(el.saveAllBtn){
    el.saveAllBtn.addEventListener('click',async function(){
      try{
        await publishCurrentState('manual',true);
      }catch(err){}
    });
  }
  if(el.openShareLinkBtn){
    el.openShareLinkBtn.addEventListener('click',function(){
      if(!publishSync.links.preferred) return;
      try{ window.open(publishSync.links.preferred,'_blank','noopener'); }
      catch(err){ window.location.href=publishSync.links.preferred; }
    });
  }
  if(typeof quickAddSheet!=='undefined') quickAddSheet.init();

  function checkUrlQuickAdd(){
    const hash = (window.location.hash || '').toLowerCase();
    const search = (window.location.search || '').toLowerCase();
    if(hash.includes('quick') || search.includes('quick')){
      setTimeout(()=>{
        if(typeof quickAddSheet!=='undefined'){
          const tab = (hash.includes('card') || search.includes('card')) ? 'card' : ((hash.includes('in') || search.includes('in')) ? 'in' : 'out');
          quickAddSheet.open(tab);
        }
      }, 160);
    }
  }
  checkUrlQuickAdd();
  window.addEventListener('hashchange', checkUrlQuickAdd);

  if(el.financeChartFilters){
    el.financeChartFilters.addEventListener('click',e=>{
      const btn=e.target.closest('[data-period]');
      if(!btn) return;
      ui.financePeriod=btn.dataset.period;
      el.financeChartFilters.querySelectorAll('.filterChip').forEach(c=>c.classList.toggle('active',c===btn));
      drawFinanceChart();
      haptic('light');
    });
  }

  if(el.accountFlowFilters){
    el.accountFlowFilters.addEventListener('click',e=>{
      const btn=e.target.closest('[data-period]');
      if(!btn) return;
      ui.accountFlowPeriod=btn.dataset.period;
      el.accountFlowFilters.querySelectorAll('.filterChip').forEach(c=>c.classList.toggle('active',c===btn));
      renderAccountFlowChart();
      haptic('light');
    });
  }

  el.quickActions.addEventListener('click',e=>{
    const btn=e.target.closest('[data-quick]'); if(!btn) return;
    const act=btn.dataset.quick;
    if(act==='expense'){
      quickAddSheet.open('out');
      return;
    }
    if(act==='income'){
      quickAddSheet.open('in');
      return;
    }
    if(act==='card'){
      quickAddSheet.open('card');
      return;
    }
    if(act==='debtor'){
      showPage('debts');
      switchDebtsView('debtors');
      openDvForm();
      return;
    }
    if(act==='goal'){
      showPage('goals');
      scrollNodeIntoView(el.goalForm);
      if(el.goalName) el.goalName.focus();
    }
  });

  if(el.heroDebt){
    const debtBox=el.heroDebt.closest('.heroBox');
    if(debtBox){
      debtBox.style.cursor='pointer';
      debtBox.setAttribute('title','Abrir cobranças a receber');
      debtBox.addEventListener('click',()=>{
        showPage('debts');
        switchDebtsView('debtors');
        haptic('light');
      });
    }
  }

  el.focusStartBtn.addEventListener('click',startFocusSession);
  el.focusPauseBtn.addEventListener('click',pauseFocusSession);
  el.focusResetBtn.addEventListener('click',resetFocusSession);
  el.focusMinutesInput.addEventListener('change',()=>{
    if(st.focusSession.running) return;
    const min=Math.min(180,Math.max(1,parseInt(el.focusMinutesInput.value||'25',10)));
    st.focusSession.secondsLeft=min*60;
    save(); renderFocusSession();
  });
  el.focusHabitSelect.addEventListener('change',()=>{
    st.focusSession.habitId=el.focusHabitSelect.value||'';
    save(); renderFocusSession();
  });

  const openZenBtn=$('#openZenBtn');
  if(openZenBtn) openZenBtn.addEventListener('click',openZenMode);
  const closeZenBtn=$('#closeZenBtn');
  if(closeZenBtn) closeZenBtn.addEventListener('click',closeZenMode);
  const zenPauseBtn=$('#zenPauseBtn');
  if(zenPauseBtn){
    zenPauseBtn.addEventListener('click',()=>{
      if(st.focusSession.running){
        pauseFocusSession();
      }else{
        startFocusSession();
      }
      updateZenDisplay();
    });
  }
  const zenFinishBtn=$('#zenFinishBtn');
  if(zenFinishBtn){
    zenFinishBtn.addEventListener('click',()=>{
      completeFocusSession();
      closeZenMode();
      showToast('✓ Sessão concluída com sucesso!','ok');
    });
  }

  el.hForm.addEventListener('submit',e=>{
    e.preventDefault();
    const n=txt(el.hName.value,60), g=txt(el.hGoal.value,40), d=el.hDate.value||today();
    if(!n) return;
    st.habits.push({id:id(),name:n,goal:g,date:d,done:false});
    pushRoutineLog('add',{name:`${n}${d?` · ${dateBr(d)}`:''}`});
    el.hName.value=''; el.hGoal.value=''; el.hDate.value=today(); save(true); renderHabits(); refreshGame();
    showToast('✓ Hábito criado: '+n,'ok');
    haptic('medium');
  });

  el.hList.addEventListener('click',e=>{
    const c=e.target.closest('[data-id]'); if(!c) return;
    const h=st.habits.find(x=>x.id===c.dataset.id); if(!h) return;
    if(e.target.matches('[data-act="toggle"]')){
      toggleHabit(h.id);
    }
    if(e.target.matches('[data-act="del"]')){
      if(h.done) st.xp=Math.max(0,st.xp-XP_H);
      if(h.done) adjustSkillXp(h.skillTag||detectSkill(h.name),-25);
      pushRoutineLog('remove',h);
      st.habits=st.habits.filter(x=>x.id!==h.id);
      save(true); renderHabits(); refreshGame();
    }
  });

  if(el.homeHabitList){
    el.homeHabitList.addEventListener('click',e=>{
      const c=e.target.closest('[data-id]'); if(!c) return;
      if(e.target.matches('[data-act="toggle"]')){
        toggleHabit(c.dataset.id);
      }
    });
  }

  if(el.homeAddHabitBtn){
    el.homeAddHabitBtn.addEventListener('click',()=>{
      const name=prompt('Qual é a nova missão/hábito de hoje?');
      if(name && name.trim()){
        const n=txt(name.trim(),60);
        st.habits.push({id:id(),name:n,goal:'',done:false,date:today()});
        pushRoutineLog('add',{name:n});
        save(true); renderHabits(); refreshGame();
        haptic('success');
        showToast('✓ Missão criada: '+n,'ok');
      }
    });
  }

  el.hList.addEventListener('input',e=>{
    const c=e.target.closest('[data-id]'); if(!c) return;
    const h=st.habits.find(x=>x.id===c.dataset.id); if(!h) return;
    if(e.target.matches('[data-f="name"]')) h.name=txt(e.target.value,60);
    if(e.target.matches('[data-f="goal"]')) h.goal=txt(e.target.value,40);
    if(e.target.matches('[data-f="date"]')) h.date=e.target.value||today();
    save();
  });

  el.fGrid.addEventListener('click',e=>{
    const card=e.target.closest('[data-acc]'); if(!card) return;
    if(e.target.matches('[data-act="edit-meta"]')){
      const acc=card.dataset.acc;
      ui.balances[acc]=!ui.balances[acc];
      renderFinance();
      return;
    }
    const acc=card.dataset.acc;
    const inp=card.querySelector('[data-v]');
    const noteInp=card.querySelector('[data-note]');
    if(!inp) return;
    const raw=parseFloat((inp.value||'').replace(',','.')); const val=Number.isFinite(raw)?Math.abs(raw):0;
    const note=noteInp?txt(noteInp.value,42):'';
    if(e.target.matches('[data-act="in"]')){ if(val<=0)return; move(acc,'in',val,note); inp.value=''; if(noteInp) noteInp.value=''; }
    if(e.target.matches('[data-act="out"]')){ if(val<=0)return; move(acc,'out',val,note); inp.value=''; if(noteInp) noteInp.value=''; }
    if(e.target.matches('[data-act="set"]')){
      if(!Number.isFinite(raw)) return;
      const prev=st.balances[acc].amount; st.balances[acc].amount=raw;
      const meta=categoryMeta(note,'Ajuste manual');
      st.tx.unshift({id:id(),account:acc,type:'set',value:raw,prev,note,category:meta.label,categoryKey:meta.key,at:new Date().toISOString()});
      save(true); renderFinance(); renderSummary(); flash(document.querySelector(`[data-acc="${acc}"] [data-bal]`),raw>=prev?'in':'out'); inp.value=''; if(noteInp) noteInp.value='';
    }
  });

  el.fGrid.addEventListener('input',e=>{
    const card=e.target.closest('[data-acc]'); if(!card) return;
    const acc=card.dataset.acc; if(!st.balances[acc]) return;
    if(e.target.matches('[data-f="label"]')){ st.balances[acc].label=txt(e.target.value,26)||defLabel(acc); save(); renderHistory(); renderFoodStatement(); renderSummary(); }
  });

  el.ccEditBtn.addEventListener('click',()=>{
    ui.credit=!ui.credit;
    renderCredit();
  });
  el.ccName.addEventListener('input',e=>{
    st.credit.name=txt(e.target.value,30)||'Cartão weedverso';
    save(true); renderCredit(); renderSummary();
  });
  el.ccExpense.addEventListener('click',()=>creditMove('expense'));
  el.ccPay.addEventListener('click',()=>creditMove('payment'));
  el.ccReserveIn.addEventListener('click',()=>creditReserveMove('in'));
  el.ccReserveOut.addEventListener('click',()=>creditReserveMove('out'));
  if(el.ccChartMonth){
    el.ccChartMonth.addEventListener('change',e=>{
      ui.creditChartMonth=String((e.target&&e.target.value)||'');
      renderCreditDescChart();
    });
  }
  if(el.ccChartPrev){
    el.ccChartPrev.addEventListener('click',()=>shiftCreditChartMonthSelection(-1));
  }
  if(el.ccChartNext){
    el.ccChartNext.addEventListener('click',()=>shiftCreditChartMonthSelection(1));
  }
  if(el.ccChartReset){
    el.ccChartReset.addEventListener('click',()=>resetCreditChartMonth());
  }
  el.ccClear.addEventListener('click',()=>{
    st.credit.used=0; st.credit.tx=[]; save(true); renderCredit(); renderSummary();
  });

  if(el.ccQuickChips){
    el.ccQuickChips.addEventListener('click',e=>{
      const btn=e.target.closest('[data-cc-quick]'); if(!btn) return;
      const q=btn.dataset.ccQuick;
      const used=Math.max(0,Number(st.credit.used)||0);
      const reserved=Math.max(0,Number(st.credit.reserved)||0);
      if(q==='coverAll'){
        const diff=Math.max(0,used-reserved);
        if(diff<=0){ showToast('Sua fatura já está totalmente coberta pela reserva!','ok'); return; }
        st.credit.reserved+=diff;
        st.credit.tx.unshift({id:id(),type:'reserve-in',value:diff,desc:'Cobertura total da fatura',category:'Reserva cartao',categoryKey:'reserva',at:new Date().toISOString()});
        haptic('success');
        save(true); renderCredit(); renderSummary();
        showToast(`✓ Fatura 100% coberta (+${money(diff)} na reserva)!`,'ok');
      } else if(q==='res50' || q==='res100' || q==='res200'){
        const amt=q==='res50'?50:(q==='res100'?100:200);
        st.credit.reserved+=amt;
        st.credit.tx.unshift({id:id(),type:'reserve-in',value:amt,desc:`Aporte rápido reserva`,category:'Reserva cartao',categoryKey:'reserva',at:new Date().toISOString()});
        haptic('medium');
        save(true); renderCredit(); renderSummary();
        showToast(`✓ +${money(amt)} guardado na reserva!`,'ok');
      } else if(q==='payAll'){
        if(used<=0){ showToast('Não há fatura em aberto para quitar!','warn'); return; }
        if(!confirm(`Deseja registrar o pagamento integral da fatura de ${money(used)}?`)) return;
        const resUsed=Math.min(reserved,used);
        if(resUsed>0) st.credit.reserved-=resUsed;
        st.credit.used=0;
        st.credit.tx.unshift({id:id(),type:'payment',value:used,desc:'Quitação integral da fatura',category:'Pagamento cartao',categoryKey:'pagamento',at:new Date().toISOString()});
        haptic('success');
        save(true); renderCredit(); renderSummary();
        showToast('✓ Fatura quitada com sucesso!','ok');
      }
    });
  }

  function updateDebInstallmentPreview(){
    if(!el.debInstallmentPreview) return;
    const amount=parseFloat(((el.debAmount&&el.debAmount.value)||'').replace(',','.'));
    const inst=Math.min(999,Math.max(1,parseInt((el.debInstallments&&el.debInstallments.value)||'1',10)||1));
    if(Number.isFinite(amount) && amount>0){
      const val=roundMoneyValue(amount/inst);
      el.debInstallmentPreview.textContent=inst>1?`${inst}x de ${money(val)}`:`1x de ${money(amount)} (à vista)`;
    } else {
      el.debInstallmentPreview.textContent=inst>1?`${inst}x parcelado`:'1x à vista';
    }
  }
  if(el.debAmount) el.debAmount.addEventListener('input',updateDebInstallmentPreview);
  if(el.debInstallments){
    el.debInstallments.addEventListener('input', () => {
      const val = parseInt(el.debInstallments.value || '1', 10);
      document.querySelectorAll('#debInstPresets .sheetTagChip').forEach(chip => {
        chip.classList.toggle('active', parseInt(chip.dataset.inst, 10) === val);
      });
      updateDebInstallmentPreview();
    });
    el.debInstallments.addEventListener('change', updateDebInstallmentPreview);
  }
  const debInstPresetsWrap = document.getElementById('debInstPresets');
  if(debInstPresetsWrap){
    debInstPresetsWrap.addEventListener('click', e => {
      const chip = e.target.closest('[data-inst]');
      if(!chip) return;
      if(el.debInstallments){
        el.debInstallments.value = chip.dataset.inst;
        updateDebInstallmentPreview();
      }
      debInstPresetsWrap.querySelectorAll('.sheetTagChip').forEach(c => c.classList.toggle('active', c === chip));
      haptic('light');
    });
  }

  function openDvForm(){
    const overlay=document.getElementById('dvFormOverlay');
    if(overlay){
      overlay.classList.add('open');
      overlay.setAttribute('aria-hidden','false');
      populateDebtorNameSuggestions();
      const nInp=document.getElementById('debName');
      if(nInp) setTimeout(()=>nInp.focus(), 150);
    }
  }
  function closeDvForm(){
    const overlay=document.getElementById('dvFormOverlay');
    if(overlay){
      overlay.classList.remove('open');
      overlay.setAttribute('aria-hidden','true');
    }
  }
  function openDvSheet(){
    const overlay=document.getElementById('dvSheetOverlay');
    if(overlay){
      overlay.classList.add('open');
      overlay.setAttribute('aria-hidden','false');
    }
  }
  function closeDvSheet(){
    const overlay=document.getElementById('dvSheetOverlay');
    if(overlay){
      overlay.classList.remove('open');
      overlay.setAttribute('aria-hidden','true');
    }
  }

  function populateDebtorNameSuggestions(){
    const dl=document.getElementById('dvNameList');
    if(!dl) return;
    const names=Array.from(new Set((st.debtors||[]).map(d=>d.name).filter(Boolean)));
    dl.innerHTML=names.map(n=>`<option value="${esc(n)}"></option>`).join('');
  }

  const dvOpenBtn=document.getElementById('dvOpenFormBtn');
  if(dvOpenBtn){
    dvOpenBtn.addEventListener('click',()=>{
      openDvForm();
      haptic('light');
    });
  }

  document.querySelectorAll('[data-dv-close]').forEach(btn=>{
    btn.addEventListener('click',()=>{
      closeDvForm();
      closeDvSheet();
    });
  });

  const dvFormOverlayEl=document.getElementById('dvFormOverlay');
  if(dvFormOverlayEl){
    dvFormOverlayEl.addEventListener('click',e=>{
      if(e.target===dvFormOverlayEl) closeDvForm();
    });
  }
  const dvSheetOverlayEl=document.getElementById('dvSheetOverlay');
  if(dvSheetOverlayEl){
    dvSheetOverlayEl.addEventListener('click',e=>{
      if(e.target===dvSheetOverlayEl) closeDvSheet();
    });
  }

  let currentDebtorReason='card';
  const reasonPillsContainer=document.getElementById('dvReasonPills');
  if(reasonPillsContainer){
    reasonPillsContainer.addEventListener('click',e=>{
      const pill=e.target.closest('[data-reason]');
      if(!pill) return;
      currentDebtorReason=pill.dataset.reason;
      reasonPillsContainer.querySelectorAll('.sheetPill').forEach(p=>p.classList.toggle('active',p===pill));
      haptic('light');
    });
  }

  const debNameInput=document.getElementById('debName');
  const debNameHint=document.getElementById('dvNameHint');
  if(debNameInput){
    debNameInput.addEventListener('input',()=>{
      const val=foldText(debNameInput.value);
      if(!val || !debNameHint){ if(debNameHint) debNameHint.hidden=true; return; }
      const existing=(st.debtors||[]).filter(d=>!d.paid && foldText(d.name)===val);
      if(existing.length>0){
        const sum=roundMoneyValue(existing.reduce((s,d)=>s+debtorRemainingAmount(d),0));
        debNameHint.hidden=false;
        debNameHint.innerHTML=`💡 <strong>${safe(existing[0].name)}</strong> já tem <strong>${money(sum)}</strong> em aberto. Esta cobrança será somada ao total da pessoa.`;
      } else {
        debNameHint.hidden=true;
      }
    });
  }

  function handleDebtorFormSubmit(nameVal, amountVal, installmentsVal, noteVal, payDateVal, reasonVal, phoneVal){
    const name=txt(nameVal,30);
    const amount=parseFloat((amountVal||'').replace(',','.'));
    const installments=Math.min(999,Math.max(1,parseInt(installmentsVal||'1',10)||1));
    const note=txt(noteVal,50);
    const payDate=payDateVal||'';
    const reason=['card','loan','split','other'].includes(reasonVal)?reasonVal:'other';
    const phone=String(phoneVal||'').replace(/\D/g,'').slice(0,15);
    if(!name||!Number.isFinite(amount)||amount<=0) return;
    const installmentValue=roundMoneyValue(amount/installments);
    st.debtors.unshift({
      id:id(),
      name,
      amount,
      installmentValue,
      installments,
      installmentsPaid:0,
      reason,
      phone,
      lastChargedAt:'',
      charges:[],
      payments:[],
      note,
      payDate,
      paid:false,
      paidAt:'',
      at:new Date().toISOString()
    });
    st.debtors=st.debtors.slice(0,100);
    save(true); renderDebtors(); renderSummary();
    haptic('medium');
    const instText=installments>1?` em ${installments}x de ${money(installmentValue)}`:'';
    showToast(`✓ Cobrança adicionada para ${name} (${money(amount)}${instText})!`, 'ok');
  }

  if(el.debForm){
    el.debForm.addEventListener('submit',e=>{
      e.preventDefault();
      const phoneInput=document.getElementById('debPhone');
      const phoneVal=phoneInput?phoneInput.value:'';
      handleDebtorFormSubmit(
        el.debName.value,
        el.debAmount.value,
        (el.debInstallments&&el.debInstallments.value)||'1',
        el.debNote.value,
        el.debPayDate.value,
        currentDebtorReason,
        phoneVal
      );
      el.debName.value=''; el.debAmount.value='';
      if(el.debInstallments) el.debInstallments.value='1';
      el.debNote.value=''; el.debPayDate.value='';
      if(phoneInput) phoneInput.value='';
      if(debNameHint) debNameHint.hidden=true;
      updateDebInstallmentPreview();
      closeDvForm();
    });
  }

  function switchDebtsView(view){
    ui.debtsView=view || 'debtors';
    try { localStorage.setItem('weedverso_debts_view', ui.debtsView); } catch(e){}
    if(el.debtsMyDebtsView) el.debtsMyDebtsView.style.display=ui.debtsView==='myDebts'?'grid':'none';
    if(el.debtsDebtorsView) el.debtsDebtorsView.style.display=ui.debtsView==='debtors'?'grid':'none';
    if(el.debtsSegmentBar){
      el.debtsSegmentBar.querySelectorAll('.segmentBtn').forEach(b=>{
        b.classList.toggle('active', b.dataset.debtView===ui.debtsView);
      });
    }
  }
  window.switchDebtsView = switchDebtsView;

  if(el.debtsSegmentBar){
    el.debtsSegmentBar.addEventListener('click',e=>{
      const btn=e.target.closest('[data-debt-view]'); if(!btn) return;
      switchDebtsView(btn.dataset.debtView);
      haptic('light');
    });
  }

  function handleDebtorChargeWhatsApp(debtorId){
    const d=st.debtors.find(x=>x.id===debtorId);
    if(!d) return;
    const inst=debtorInstallments(d);
    const paidInst=debtorPaidInstallments(d);
    const instVal=debtorInstallmentValue(d);
    const remaining=debtorRemainingAmount(d);

    let msg='';
    if(inst>1){
      const nextInst=Math.min(inst, paidInst+1);
      msg=`Oi ${d.name}! Lembrete da parcela ${nextInst}/${inst} de ${money(instVal)} 😉`;
    } else {
      msg=`Oi ${d.name}! Passando pra lembrar do valor de ${money(remaining)} 😉`;
    }

    const nowIso=new Date().toISOString();
    d.lastChargedAt=nowIso;
    d.charges=d.charges||[];
    d.charges.push(nowIso);
    save(true);
    renderDebtors();

    const encoded=encodeURIComponent(msg);
    let url='';
    const cleanPhone=String(d.phone||'').replace(/\D/g,'');
    if(cleanPhone){
      const fullPhone=cleanPhone.length<=11?'55'+cleanPhone:cleanPhone;
      url=`https://wa.me/${fullPhone}?text=${encoded}`;
    } else {
      url=`https://api.whatsapp.com/send?text=${encoded}`;
    }
    window.open(url,'_blank');
    showToast(`Cobrança registrada para ${d.name}!`, 'ok');
  }

  function openDebtorReceiveSheet(debtorId){
    const d=st.debtors.find(x=>x.id===debtorId);
    if(!d) return;
    const remaining=debtorRemainingAmount(d);
    const instVal=debtorInstallmentValue(d);
    const inst=debtorInstallments(d);
    const isMulti=inst>1 && instVal<remaining;

    const defaultAcc=d.reason==='card'?'amex':'conta';

    const sheetTitle=document.getElementById('dvSheetTitle');
    if(sheetTitle) sheetTitle.textContent=`Receber de ${d.name}`;

    const body=document.getElementById('dvSheetBody');
    if(!body) return;

    const initialVal=(isMulti?instVal:remaining).toFixed(2).replace('.',',');

    body.innerHTML=`
      <div style="display:grid;gap:12px;padding:4px 0">
        <div style="display:flex;justify-content:space-between;align-items:center;background:rgba(255,255,255,.03);padding:10px 12px;border-radius:12px;border:1px solid var(--ln)">
          <span class="mut" style="font-size:.82rem">Saldo total em aberto:</span>
          <strong style="font-family:var(--font-display);font-size:1.15rem;color:var(--p)">${money(remaining)}</strong>
        </div>

        <div class="sheetField">
          <label class="mini">Valor a receber agora (valor livre)</label>
          <div class="sheetAmountWrap">
            <span class="sheetCurrency">R$</span>
            <input id="dvReceiveAmountInput" type="text" inputmode="decimal" class="sheetAmountInput" value="${initialVal}" />
          </div>
          <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:4px">
            ${isMulti?`<button type="button" class="sheetPill" data-dv-preset="${instVal}">1 parcela: ${money(instVal)}</button>`:''}
            <button type="button" class="sheetPill" data-dv-preset="${remaining}">Quitar total: ${money(remaining)}</button>
          </div>
        </div>

        <div class="sheetField">
          <label class="mini">Em qual conta o dinheiro caiu?</label>
          <div class="sheetPills" id="dvReceiveAccPills">
            <button type="button" class="sheetPill ${defaultAcc==='conta'?'active':''}" data-acc="conta">🏦 Conta (${money(st.balances.conta.amount)})</button>
            <button type="button" class="sheetPill ${defaultAcc==='amex'?'active':''}" data-acc="amex">💳 Abater AMEX (Usado: ${money(st.credit.used)})</button>
            <button type="button" class="sheetPill ${defaultAcc==='vale1'?'active':''}" data-acc="vale1">🥗 Alelo Alimentação</button>
            <button type="button" class="sheetPill ${defaultAcc==='vale2'?'active':''}" data-acc="vale2">🍽️ Alelo Refeição</button>
          </div>
        </div>

        <button type="button" id="dvConfirmReceiveBtn" class="btn sheetSubmitBtn" style="margin-top:6px">Confirmar Recebimento</button>
      </div>
    `;

    body.querySelectorAll('[data-dv-preset]').forEach(b=>{
      b.addEventListener('click',()=>{
        const val=parseFloat(b.dataset.dvPreset);
        const inp=document.getElementById('dvReceiveAmountInput');
        if(inp) inp.value=val.toFixed(2).replace('.',',');
        haptic('light');
      });
    });

    let selectedAcc=defaultAcc;
    body.querySelectorAll('#dvReceiveAccPills .sheetPill').forEach(b=>{
      b.addEventListener('click',()=>{
        selectedAcc=b.dataset.acc;
        body.querySelectorAll('#dvReceiveAccPills .sheetPill').forEach(x=>x.classList.toggle('active',x===b));
        haptic('light');
      });
    });

    const confirmBtn=document.getElementById('dvConfirmReceiveBtn');
    if(confirmBtn){
      confirmBtn.addEventListener('click',()=>{
        const rawVal=(document.getElementById('dvReceiveAmountInput').value||'').replace(',','.');
        const val=roundMoneyValue(parseFloat(rawVal));
        if(!val || val<=0){
          showToast('Informe um valor válido maior que zero!','warn');
          return;
        }
        executeDebtorPayment(d.id, val, selectedAcc);
        closeDvSheet();
      });
    }

    openDvSheet();
  }

  function executeDebtorPayment(debtorId, val, account){
    const d=st.debtors.find(x=>x.id===debtorId);
    if(!d) return;
    const nowIso=new Date().toISOString();
    val=Math.min(val, debtorRemainingAmount(d) || val);

    const prevStatus={
      paid:d.paid,
      paidAt:d.paidAt,
      installmentsPaid:d.installmentsPaid,
      payments:JSON.parse(JSON.stringify(d.payments||[]))
    };

    let txId=id();
    if(account==='amex'){
      st.credit.used=Math.max(0,(Number(st.credit.used)||0)-val);
      st.credit.tx=st.credit.tx||[];
      st.credit.tx.unshift({
        id:txId,
        type:'payment',
        value:val,
        desc:`Recebido de ${d.name} (abater AMEX)`,
        category:'Pagamento cartao',
        categoryKey:'pagamento',
        at:nowIso
      });
    } else {
      st.balances[account].amount=roundMoneyValue((Number(st.balances[account].amount)||0)+val);
      st.tx.unshift({
        id:txId,
        account:account,
        type:'in',
        value:val,
        note:`Recebido de ${d.name}`,
        category:'Recebimento',
        categoryKey:'recebimento',
        debtorId:d.id,
        at:nowIso
      });
      flash(document.querySelector(`[data-acc="${account}"] [data-bal]`),'in');
    }

    d.payments=d.payments||[];
    const paymentEntry={
      id:id(),
      value:val,
      at:nowIso,
      account:account,
      txId:txId
    };
    d.payments.push(paymentEntry);

    const totalPaid=d.payments.reduce((s,p)=>s+Number(p.value||0),0);
    const totalAmount=roundMoneyValue(Number(d.amount)||0);
    const instVal=debtorInstallmentValue(d);
    if(totalPaid>=totalAmount-0.01){
      d.paid=true;
      d.paidAt=nowIso;
      d.installmentsPaid=d.installments;
    } else {
      d.paid=false;
      d.paidAt='';
      d.installmentsPaid=Math.min(d.installments-1, instVal>0?Math.floor((totalPaid+0.01)/instVal):0);
    }

    save(true);
    renderDebtors();
    renderFinance();
    renderCredit();
    renderSummary();
    haptic('success');
    showToast(`✓ Recebido ${money(val)} de ${d.name}!`, 'ok');

    startDebtorUndo({
      debtorId:d.id,
      paymentEntry,
      account,
      val,
      txId,
      prevStatus,
      debtorName:d.name
    });
  }

  let dvUndoState=null;
  let dvUndoTimer=null;
  let dvUndoCountdown=5;
  let dvUndoInterval=null;

  function startDebtorUndo(snapshot){
    dvUndoState=Object.assign({type:'debtor'}, snapshot);
    dvUndoCountdown=5;
    const bar=document.getElementById('dvUndoBar');
    const text=document.getElementById('dvUndoText');
    const btn=document.getElementById('dvUndoBtn');
    if(!bar || !text || !btn) return;

    if(dvUndoTimer) clearTimeout(dvUndoTimer);
    if(dvUndoInterval) clearInterval(dvUndoInterval);

    text.textContent=`Recebido ${money(snapshot.val)} de ${snapshot.debtorName}`;
    btn.textContent=`Desfazer (5s)`;
    bar.hidden=false;
    bar.style.display='flex';
    bar.classList.add('active');

    dvUndoInterval=setInterval(()=>{
      dvUndoCountdown--;
      if(dvUndoCountdown>0){
        btn.textContent=`Desfazer (${dvUndoCountdown}s)`;
      } else {
        clearInterval(dvUndoInterval);
      }
    },1000);

    dvUndoTimer=setTimeout(()=>{
      hideDebtorUndo();
    },5000);
  }

  function startMyDebtUndo(snapshot){
    dvUndoState=Object.assign({type:'myDebt'}, snapshot);
    dvUndoCountdown=5;
    const bar=document.getElementById('dvUndoBar');
    const text=document.getElementById('dvUndoText');
    const btn=document.getElementById('dvUndoBtn');
    if(!bar || !text || !btn) return;

    if(dvUndoTimer) clearTimeout(dvUndoTimer);
    if(dvUndoInterval) clearInterval(dvUndoInterval);

    text.textContent=`Pago ${money(snapshot.val)} em ${snapshot.debtName}`;
    btn.textContent=`Desfazer (5s)`;
    bar.hidden=false;
    bar.style.display='flex';
    bar.classList.add('active');

    dvUndoInterval=setInterval(()=>{
      dvUndoCountdown--;
      if(dvUndoCountdown>0){
        btn.textContent=`Desfazer (${dvUndoCountdown}s)`;
      } else {
        clearInterval(dvUndoInterval);
      }
    },1000);

    dvUndoTimer=setTimeout(()=>{
      hideDebtorUndo();
    },5000);
  }

  function hideDebtorUndo(){
    if(dvUndoTimer){ clearTimeout(dvUndoTimer); dvUndoTimer=null; }
    if(dvUndoInterval){ clearInterval(dvUndoInterval); dvUndoInterval=null; }
    dvUndoState=null;
    const bar=document.getElementById('dvUndoBar');
    if(bar){
      bar.hidden=true;
      bar.style.display='none';
      bar.classList.remove('active');
    }
  }
  hideDebtorUndo();

  function executeDebtorUndo(){
    if(!dvUndoState) return;
    const { debtorId, account, val, txId, prevStatus, debtorName }=dvUndoState;
    const d=st.debtors.find(x=>x.id===debtorId);
    if(d){
      d.paid=prevStatus.paid;
      d.paidAt=prevStatus.paidAt;
      d.installmentsPaid=prevStatus.installmentsPaid;
      d.payments=prevStatus.payments;
    }
    if(account==='amex'){
      st.credit.used=roundMoneyValue((Number(st.credit.used)||0)+val);
      st.credit.tx=(st.credit.tx||[]).filter(t=>t.id!==txId);
    } else {
      st.balances[account].amount=roundMoneyValue((Number(st.balances[account].amount)||0)-val);
      st.tx=(st.tx||[]).filter(t=>t.id!==txId);
    }

    hideDebtorUndo();
    save(true);
    renderDebtors();
    renderFinance();
    renderCredit();
    renderSummary();
    haptic('medium');
    showToast(`Recebimento de ${debtorName} desfeito com sucesso!`,'ok');
  }

  function executeMyDebtUndo(snapshot){
    const { myDebtId, account, val, txId, prevStatus, debtName }=snapshot;
    const d=st.myDebts.find(x=>x.id===myDebtId);
    if(d){
      d.paid=prevStatus.paid;
      d.paidAt=prevStatus.paidAt;
      d.installmentsPaid=prevStatus.installmentsPaid;
      d.payments=prevStatus.payments;
    }
    if(account && account!=='none' && st.balances[account]){
      st.balances[account].amount=roundMoneyValue((Number(st.balances[account].amount)||0)+val);
      st.tx=(st.tx||[]).filter(t=>t.id!==txId);
    }
    hideDebtorUndo();
    save(true);
    renderMyDebts();
    renderFinance();
    renderUnifiedStatement();
    renderSummary();
    haptic('medium');
    showToast(`Pagamento de ${debtName} desfeito com sucesso!`,'ok');
  }

  const undoBarBtn=document.getElementById('dvUndoBtn');
  if(undoBarBtn){
    undoBarBtn.addEventListener('click',()=>{
      if(!dvUndoState) return;
      if(dvUndoState.type==='myDebt') executeMyDebtUndo(dvUndoState);
      else executeDebtorUndo();
    });
  }

  function openPersonTimelineSheet(personName){
    const target=foldText(personName);
    const items=(st.debtors||[]).filter(d=>foldText(d.name)===target);
    if(!items.length) return;

    const trust=personTrustBadge(personName);
    const title=document.getElementById('dvSheetTitle');
    if(title) title.innerHTML=`👤 ${safe(items[0].name)} <span class="dvTrustBadge ${trust.cls}">${trust.icon} ${trust.label}</span>`;

    const body=document.getElementById('dvSheetBody');
    if(!body) return;

    const events=[];
    let totalBorrowed=0;
    let totalPaid=0;

    items.forEach(d=>{
      const dAmt=Number(d.amount)||0;
      totalBorrowed+=dAmt;
      events.push({
        type:'created',
        date:d.at||new Date().toISOString(),
        title:`Registrou cobrança de ${money(dAmt)}`,
        detail:`${debtorReasonIcon(d.reason)} ${debtorReasonLabel(d.reason)}${d.installments>1?` em ${d.installments}x`:''}${d.note?` (${d.note})`:''}`,
        dotColor:'#39ff8f'
      });
      (d.charges||[]).forEach(c=>{
        events.push({
          type:'charged',
          date:c,
          title:`Lembrete de cobrança enviado`,
          detail:`Via WhatsApp`,
          dotColor:'#ffcf5f'
        });
      });
      (d.payments||[]).forEach(p=>{
        const pVal=Number(p.value)||0;
        totalPaid+=pVal;
        const accNames={conta:'Saldo em Conta',amex:'Abatido no AMEX',vale1:'Alelo Alimentação',vale2:'Alelo Refeição'};
        events.push({
          type:'payment',
          date:p.at,
          title:`Pagou ${money(pVal)}`,
          detail:`Recebido no ${accNames[p.account]||'Saldo em Conta'}`,
          dotColor:'#4cff9e'
        });
      });
      if(d.paid && (!d.payments || !d.payments.length)){
        totalPaid+=dAmt;
        events.push({
          type:'paid',
          date:d.paidAt||d.at,
          title:`Quitou cobrança de ${money(dAmt)}`,
          detail:`Marcado como quitado`,
          dotColor:'#4cff9e'
        });
      }
    });

    events.sort((a,b)=>new Date(b.date)-new Date(a.date));
    const openBalance=Math.max(0,totalBorrowed-totalPaid);

    body.innerHTML=`
      <div style="display:grid;gap:12px;padding:4px 0">
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px;background:rgba(255,255,255,.03);padding:10px;border-radius:12px;border:1px solid var(--ln);text-align:center">
          <div>
            <span class="mini">Total emprestado</span>
            <strong style="font-family:var(--font-display);font-size:.96rem;display:block;margin-top:2px">${money(totalBorrowed)}</strong>
          </div>
          <div>
            <span class="mini">Total recebido</span>
            <strong style="font-family:var(--font-display);font-size:.96rem;color:#4cff9e;display:block;margin-top:2px">${money(totalPaid)}</strong>
          </div>
          <div>
            <span class="mini">Em aberto</span>
            <strong style="font-family:var(--font-display);font-size:.96rem;color:${openBalance>0?'#ffcf5f':'var(--p)'};display:block;margin-top:2px">${money(openBalance)}</strong>
          </div>
        </div>

        <div style="font-size:.76rem;font-weight:700;color:var(--mut);text-transform:uppercase;letter-spacing:.05em">Linha do Tempo</div>

        <div class="dvTimeline">
          ${events.map(ev=>`
            <div class="dvTimelineItem">
              <div class="dvTimelineDot" style="background:${ev.dotColor}"></div>
              <div class="dvTimelineTitle">${ev.title}</div>
              <div class="dvTimelineMeta">${shortDate(ev.date)} · ${ev.detail}</div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
    openDvSheet();
  }

  function openDebtorOptionsMenu(debtorId){
    const d=st.debtors.find(x=>x.id===debtorId);
    if(!d) return;
    const title=document.getElementById('dvSheetTitle');
    if(title) title.textContent=`Opções · ${d.name}`;

    const body=document.getElementById('dvSheetBody');
    if(!body) return;

    body.innerHTML=`
      <div style="display:grid;gap:8px;padding:6px 0" id="dvMenuOptionsWrap">
        <button type="button" class="btn" style="text-align:left;display:flex;align-items:center;gap:10px;padding:10px 14px" data-menu-act="receive">
          <span>✓</span> <span>Registrar recebimento (parcial ou total)</span>
        </button>
        <button type="button" class="ghost" style="text-align:left;display:flex;align-items:center;gap:10px;padding:10px 14px" data-menu-act="charge">
          <span>💬</span> <span>Cobrar no WhatsApp com lembrete</span>
        </button>
        <button type="button" class="ghost" style="text-align:left;display:flex;align-items:center;gap:10px;padding:10px 14px" data-menu-act="timeline">
          <span>📜</span> <span>Ver linha do tempo / histórico</span>
        </button>
        <button type="button" class="ghost" style="text-align:left;display:flex;align-items:center;gap:10px;padding:10px 14px" data-menu-act="edit">
          <span>✏️</span> <span>Editar dados da cobrança</span>
        </button>
        <button type="button" class="ghost" style="text-align:left;display:flex;align-items:center;gap:10px;padding:10px 14px" data-menu-act="toggle">
          <span>🔄</span> <span>${d.paid?'Reabrir cobrança':'Marcar como quitada'}</span>
        </button>
        <button type="button" class="danger" style="text-align:left;display:flex;align-items:center;gap:10px;padding:10px 14px;margin-top:6px" data-menu-act="delete">
          <span>🗑️</span> <span>Excluir cobrança permanentemente</span>
        </button>
      </div>
    `;

    const wrap=document.getElementById('dvMenuOptionsWrap');
    if(wrap){
      wrap.addEventListener('click',e=>{
        const btn=e.target.closest('[data-menu-act]');
        if(!btn) return;
        const act=btn.dataset.menuAct;
        closeDvSheet();
        if(act==='receive') openDebtorReceiveSheet(d.id);
        else if(act==='charge') handleDebtorChargeWhatsApp(d.id);
        else if(act==='timeline') openPersonTimelineSheet(d.name);
        else if(act==='edit') openDebtorEditSheet(d.id);
        else if(act==='toggle'){
          d.paid=!d.paid;
          if(d.paid){
            d.paidAt=new Date().toISOString();
            d.installmentsPaid=d.installments;
          } else {
            d.paidAt='';
          }
          save(true); renderDebtors(); renderSummary();
          showToast(d.paid?`✓ ${d.name} marcado como quitado!`:`Cobrança reaberta!`,'ok');
        }
        else if(act==='delete'){
          if(confirm(`Excluir a cobrança de ${d.name}?`)){
            st.debtors=st.debtors.filter(x=>x.id!==d.id);
            save(true); renderDebtors(); renderSummary();
            showToast('Cobrança excluída.','ok');
          }
        }
      });
    }

    openDvSheet();
  }

  function openDebtorEditSheet(debtorId){
    const d=st.debtors.find(x=>x.id===debtorId);
    if(!d) return;
    const title=document.getElementById('dvSheetTitle');
    if(title) title.textContent=`Editar cobrança · ${d.name}`;

    const body=document.getElementById('dvSheetBody');
    if(!body) return;

    const inst=debtorInstallments(d);
    body.innerHTML=`
      <form id="dvEditForm" style="display:grid;gap:10px;padding:4px 0">
        <div class="sheetField">
          <label class="mini">Motivo</label>
          <div class="sheetPills" id="dvEditReasonPills">
            <button type="button" class="sheetPill ${d.reason==='card'?'active':''}" data-reason="card">💳 Passei no cartão</button>
            <button type="button" class="sheetPill ${d.reason==='loan'?'active':''}" data-reason="loan">💵 Emprestei</button>
            <button type="button" class="sheetPill ${d.reason==='split'?'active':''}" data-reason="split">🍕 Racha</button>
            <button type="button" class="sheetPill ${d.reason==='other'?'active':''}" data-reason="other">📦 Outro</button>
          </div>
        </div>
        <div class="sheetField">
          <label class="mini">Nome</label>
          <input id="dvEditName" type="text" class="sheetInput" value="${esc(d.name)}" maxlength="30" required />
        </div>
        <div class="two">
          <div class="sheetField">
            <label class="mini">Valor Total (R$)</label>
            <input id="dvEditAmount" type="number" step="0.01" class="sheetInput" value="${Number(d.amount)||0}" required />
          </div>
          <div class="sheetField">
            <label class="mini">Parcelas (até 999)</label>
            <div style="position:relative;display:flex;align-items:center;">
              <input id="dvEditInstallments" type="number" min="1" max="999" step="1" inputmode="numeric" class="sheetInput dvInstInput" value="${inst}" style="padding-right:24px;text-align:center;font-weight:700;min-height:44px;" required />
              <span style="position:absolute;right:8px;font-size:0.84rem;font-weight:700;color:var(--mut);pointer-events:none;">x</span>
            </div>
          </div>
        </div>
        <div class="sheetTagChips" id="dvEditInstPresets" style="margin-top:2px;">
          <span class="mut" style="font-size:.72rem;margin-right:2px;align-self:center;">Atalhos:</span>
          ${[1,2,3,6,10,12,24,36,48,60,120].map(n => `<button type="button" class="sheetTagChip ${inst===n?'active':''}" data-inst="${n}">${n}x</button>`).join('')}
        </div>
        <div class="two">
          <div class="sheetField">
            <label class="mini">1º vencimento</label>
            <input id="dvEditPayDate" type="date" class="sheetInput" value="${d.payDate||''}" />
          </div>
          <div class="sheetField">
            <label class="mini">WhatsApp com DDD</label>
            <input id="dvEditPhone" type="tel" class="sheetInput" value="${esc(d.phone||'')}" placeholder="(XX) 9XXXX-XXXX" />
          </div>
        </div>
        <div class="sheetField">
          <label class="mini">Observação</label>
          <input id="dvEditNote" type="text" class="sheetInput" value="${esc(d.note||'')}" maxlength="50" placeholder="Observação opcional" />
        </div>
        <button type="submit" class="btn sheetSubmitBtn" style="margin-top:4px">Salvar Alterações</button>
      </form>
    `;

    const dvEditChips = body.querySelector('#dvEditInstPresets');
    const dvEditInstInp = document.getElementById('dvEditInstallments');
    if(dvEditChips && dvEditInstInp){
      dvEditChips.addEventListener('click', e => {
        const chip = e.target.closest('[data-inst]');
        if(!chip) return;
        dvEditInstInp.value = chip.dataset.inst;
        dvEditChips.querySelectorAll('.sheetTagChip').forEach(c => c.classList.toggle('active', c === chip));
        haptic('light');
      });
      dvEditInstInp.addEventListener('input', () => {
        const val = parseInt(dvEditInstInp.value || '1', 10);
        dvEditChips.querySelectorAll('.sheetTagChip').forEach(c => c.classList.toggle('active', parseInt(c.dataset.inst, 10) === val));
      });
    }

    let editReason=d.reason||'other';
    body.querySelectorAll('#dvEditReasonPills .sheetPill').forEach(p=>{
      p.addEventListener('click',()=>{
        editReason=p.dataset.reason;
        body.querySelectorAll('#dvEditReasonPills .sheetPill').forEach(x=>x.classList.toggle('active',x===p));
        haptic('light');
      });
    });

    const form=document.getElementById('dvEditForm');
    if(form){
      form.addEventListener('submit',e=>{
        e.preventDefault();
        const newName=txt(document.getElementById('dvEditName').value, 30);
        const newAmt=parseFloat(document.getElementById('dvEditAmount').value);
        const newInst=Math.min(999, Math.max(1, parseInt(document.getElementById('dvEditInstallments').value, 10)||1));
        if(!newName || !Number.isFinite(newAmt) || newAmt<=0) return;

        d.name=newName;
        d.amount=roundMoneyValue(newAmt);
        d.installments=newInst;
        d.installmentValue=roundMoneyValue(newAmt/newInst);
        d.payDate=document.getElementById('dvEditPayDate').value||'';
        d.phone=String(document.getElementById('dvEditPhone').value||'').replace(/\D/g,'').slice(0,15);
        d.note=txt(document.getElementById('dvEditNote').value, 50);
        d.reason=editReason;

        const totalPaid=(d.payments||[]).reduce((s,p)=>s+Number(p.value||0), 0);
        if(totalPaid>=d.amount-0.01){
          d.paid=true;
          d.installmentsPaid=d.installments;
        } else {
          d.paid=false;
          d.installmentsPaid=Math.min(d.installments-1, d.installmentValue>0?Math.floor((totalPaid+0.01)/d.installmentValue):0);
        }

        save(true);
        renderDebtors();
        renderSummary();
        closeDvSheet();
        showToast('✓ Cobrança atualizada!','ok');
      });
    }
    openDvSheet();
  }

  function handleDebtorBoardClick(e){
    const chargeBtn=e.target.closest('[data-act="dv-charge-wa"]');
    if(chargeBtn){
      handleDebtorChargeWhatsApp(chargeBtn.dataset.deb);
      return;
    }
    const receiveBtn=e.target.closest('[data-act="dv-open-receive"]');
    if(receiveBtn){
      openDebtorReceiveSheet(receiveBtn.dataset.deb);
      return;
    }
    const menuBtn=e.target.closest('[data-act="dv-open-menu"]');
    if(menuBtn){
      openDebtorOptionsMenu(menuBtn.dataset.deb);
      return;
    }
    const historyBtn=e.target.closest('[data-act="dv-person-history"]');
    if(historyBtn){
      openPersonTimelineSheet(historyBtn.dataset.person);
      return;
    }
    const groupHead=e.target.closest('[data-act="dv-toggle-group"]');
    if(groupHead){
      const key=groupHead.dataset.personKey;
      ui.debtors['grp_'+key]=!ui.debtors['grp_'+key];
      renderDebtors();
      return;
    }
  }

  if(el.debList) el.debList.addEventListener('click', handleDebtorBoardClick);
  if(el.debtsPageDebList && el.debtsPageDebList !== el.debList) el.debtsPageDebList.addEventListener('click', handleDebtorBoardClick);

  // Long press support on mobile cards
  let dvTouchTimer=null;
  let dvTouchMoved=false;
  if(el.debList){
    el.debList.addEventListener('touchstart',e=>{
      const card=e.target.closest('.dvCard');
      if(!card || e.target.closest('button')) return;
      dvTouchMoved=false;
      dvTouchTimer=setTimeout(()=>{
        if(!dvTouchMoved && card.dataset.deb){
          haptic('medium');
          openDebtorOptionsMenu(card.dataset.deb);
        }
      },520);
    },{passive:true});
    el.debList.addEventListener('touchmove',()=>{ dvTouchMoved=true; if(dvTouchTimer) clearTimeout(dvTouchTimer); },{passive:true});
    el.debList.addEventListener('touchend',()=>{ if(dvTouchTimer) clearTimeout(dvTouchTimer); },{passive:true});
    el.debList.addEventListener('touchcancel',()=>{ if(dvTouchTimer) clearTimeout(dvTouchTimer); },{passive:true});
  }

  // Modern Minhas Dívidas System
  function openMdForm(){
    const overlay = document.getElementById('mdFormOverlay');
    if(!overlay) return;
    overlay.classList.add('open');
    overlay.setAttribute('aria-hidden', 'false');
    populateMyDebtNameSuggestions();
    const nameInput = document.getElementById('mdName');
    if(nameInput) setTimeout(() => nameInput.focus(), 150);
  }

  function closeMdForm(){
    const overlay = document.getElementById('mdFormOverlay');
    if(!overlay) return;
    overlay.classList.remove('open');
    overlay.setAttribute('aria-hidden', 'true');
  }

  function openMdSheet(){
    const overlay = document.getElementById('mdSheetOverlay');
    if(!overlay) return;
    overlay.classList.add('open');
    overlay.setAttribute('aria-hidden', 'false');
  }

  function closeMdSheet(){
    const overlay = document.getElementById('mdSheetOverlay');
    if(!overlay) return;
    overlay.classList.remove('open');
    overlay.setAttribute('aria-hidden', 'true');
  }

  const mdOpenBtn = document.getElementById('mdOpenFormBtn');
  if(mdOpenBtn) mdOpenBtn.addEventListener('click', openMdForm);

  document.querySelectorAll('[data-md-close]').forEach(b => {
    b.addEventListener('click', () => { closeMdForm(); closeMdSheet(); });
  });

  const mdFormOverlayEl = document.getElementById('mdFormOverlay');
  if(mdFormOverlayEl){
    mdFormOverlayEl.addEventListener('click', e => {
      if(e.target === mdFormOverlayEl) closeMdForm();
    });
  }
  const mdSheetOverlayEl = document.getElementById('mdSheetOverlay');
  if(mdSheetOverlayEl){
    mdSheetOverlayEl.addEventListener('click', e => {
      if(e.target === mdSheetOverlayEl) closeMdSheet();
    });
  }

  let currentMyDebtReason = 'house';
  const mdReasonPills = document.getElementById('mdReasonPills');
  if(mdReasonPills){
    mdReasonPills.addEventListener('click', e => {
      const pill = e.target.closest('[data-reason]');
      if(!pill) return;
      currentMyDebtReason = pill.dataset.reason;
      mdReasonPills.querySelectorAll('.sheetPill').forEach(p => p.classList.toggle('active', p === pill));
      haptic('light');
    });
  }

  function populateMyDebtNameSuggestions(){
    const datalist = document.getElementById('mdNameList');
    const chipsWrap = document.getElementById('mdNameSuggestions');
    const debts = st.myDebts || [];
    const uniqueNames = Array.from(new Set(debts.map(d => (d.name || '').trim()).filter(Boolean)));
    if(datalist){
      datalist.innerHTML = uniqueNames.map(n => `<option value="${esc(n)}"></option>`).join('');
    }
    if(chipsWrap){
      if(!uniqueNames.length){
        chipsWrap.innerHTML = '';
      } else {
        chipsWrap.innerHTML = uniqueNames.slice(0, 6).map(n => 
          `<button type="button" class="tagChip" data-md-suggest="${esc(n)}">${safe(n)}</button>`
        ).join('');
      }
    }
  }

  const mdNameSuggestionsEl = document.getElementById('mdNameSuggestions');
  if(mdNameSuggestionsEl){
    mdNameSuggestionsEl.addEventListener('click', e => {
      const chip = e.target.closest('[data-md-suggest]');
      if(!chip) return;
      const inp = document.getElementById('mdName');
      if(inp){
        inp.value = chip.dataset.mdSuggest;
        inp.dispatchEvent(new Event('input'));
        haptic('light');
      }
    });
  }

  const mdNameInput = document.getElementById('mdName');
  const mdNameHint = document.getElementById('mdNameHint');
  if(mdNameInput){
    mdNameInput.addEventListener('input', () => {
      const val = foldText(mdNameInput.value);
      if(!val || !mdNameHint){ if(mdNameHint) { mdNameHint.hidden = true; mdNameHint.style.display = 'none'; } return; }
      const existing = (st.myDebts || []).filter(d => !d.paid && foldText(d.name) === val);
      if(existing.length > 0){
        const sum = roundMoneyValue(existing.reduce((s,d) => s + debtRemainingAmount(d), 0));
        mdNameHint.hidden = false;
        mdNameHint.style.display = 'block';
        mdNameHint.innerHTML = `💡 <strong>${safe(existing[0].name)}</strong> já tem <strong>${money(sum)}</strong> em aberto. Esta conta será somada ao favorecido.`;
      } else {
        mdNameHint.hidden = true;
        mdNameHint.style.display = 'none';
      }
    });
  }

  function updateMdInstallmentPreview(){
    const prev = document.getElementById('mdInstallmentPreview');
    const amtInp = document.getElementById('mdAmount');
    const instInp = document.getElementById('mdInstallments');
    if(!prev) return;
    const amount = parseFloat(((amtInp && amtInp.value) || '').replace(',', '.'));
    const inst = Math.min(999, Math.max(1, parseInt(((instInp && instInp.value) || '1'), 10) || 1));
    if(Number.isFinite(amount) && amount > 0){
      const val = roundMoneyValue(amount / inst);
      prev.textContent = inst > 1 ? `${inst}x de ${money(val)}` : `1x de ${money(amount)} (à vista)`;
    } else {
      prev.textContent = inst > 1 ? `${inst}x parcelado` : '1x à vista';
    }
  }

  const mdAmountInp = document.getElementById('mdAmount');
  const mdInstallmentsInp = document.getElementById('mdInstallments');
  if(mdAmountInp) mdAmountInp.addEventListener('input', updateMdInstallmentPreview);
  if(mdInstallmentsInp){
    mdInstallmentsInp.addEventListener('input', () => {
      const val = parseInt(mdInstallmentsInp.value || '1', 10);
      document.querySelectorAll('#mdInstPresets .sheetTagChip').forEach(chip => {
        chip.classList.toggle('active', parseInt(chip.dataset.inst, 10) === val);
      });
      updateMdInstallmentPreview();
    });
    mdInstallmentsInp.addEventListener('change', updateMdInstallmentPreview);
  }

  const mdInstPresetsWrap = document.getElementById('mdInstPresets');
  if(mdInstPresetsWrap){
    mdInstPresetsWrap.addEventListener('click', e => {
      const chip = e.target.closest('[data-inst]');
      if(!chip) return;
      const instVal = chip.dataset.inst;
      if(mdInstallmentsInp){
        mdInstallmentsInp.value = instVal;
        updateMdInstallmentPreview();
      }
      mdInstPresetsWrap.querySelectorAll('.sheetTagChip').forEach(c => c.classList.toggle('active', c === chip));
      haptic('light');
    });
  }

  const mdFormEl = document.getElementById('mdForm');
  if(mdFormEl){
    mdFormEl.addEventListener('submit', e => {
      e.preventDefault();
      const name = txt((document.getElementById('mdName')||{}).value, 30);
      const rawAmt = ((document.getElementById('mdAmount')||{}).value || '').replace(',', '.');
      const amount = parseFloat(rawAmt);
      const installments = Math.min(999, Math.max(1, parseInt(((document.getElementById('mdInstallments')||{}).value || '1'), 10) || 1));
      const payDate = ((document.getElementById('mdPayDate')||{}).value || '').trim();
      const note = txt((document.getElementById('mdNote')||{}).value, 50);
      if(!name || !Number.isFinite(amount) || amount <= 0) return;

      const unitValue = roundMoneyValue(amount / installments);
      const newEntry = {
        id: id(),
        name,
        amount: unitValue,
        installmentValue: unitValue,
        installments,
        installmentsPaid: 0,
        note,
        payDate,
        paid: false,
        paidAt: '',
        at: new Date().toISOString(),
        reason: currentMyDebtReason || 'house',
        payments: []
      };

      if(!Array.isArray(st.myDebts)) st.myDebts = [];
      st.myDebts.unshift(newEntry);
      st.myDebts = st.myDebts.slice(0, 100);

      save(true);
      renderMyDebts();
      renderSummary();
      closeMdForm();
      haptic('success');
      showToast(`✓ Dívida "${name}" adicionada com sucesso!`, 'ok');

      mdFormEl.reset();
      if(mdNameHint) { mdNameHint.hidden = true; mdNameHint.style.display = 'none'; }
      updateMdInstallmentPreview();
    });
  }

  function openMyDebtPaySheet(debtId){
    const d = (st.myDebts || []).find(x => x.id === debtId);
    if(!d) return;

    const title = document.getElementById('mdSheetTitle');
    if(title) title.textContent = `Pagar parcela · ${d.name}`;

    const body = document.getElementById('mdSheetBody');
    if(!body) return;

    const inst = debtInstallments(d);
    const paidInst = debtPaidInstallments(d);
    const instVal = debtInstallmentValue(d);
    const remaining = debtRemainingAmount(d);
    const suggestedVal = instVal > 0 && instVal < remaining ? instVal : remaining;

    body.innerHTML = `
      <div style="display:grid;gap:12px;padding:4px 0">
        <div style="background:rgba(255,255,255,.03);padding:10px 12px;border-radius:12px;border:1px solid var(--ln);display:flex;justify-content:space-between;align-items:center">
          <div>
            <strong style="font-size:.94rem;color:#fff">${safe(d.name)}</strong>
            <span style="display:block;font-size:.72rem;color:var(--mut);margin-top:2px">
              ${inst > 1 ? `Parcela ${paidInst + 1}/${inst} · unitária ${money(instVal)}` : 'À vista'}
            </span>
          </div>
          <div style="text-align:right">
            <span class="mini">Total pendente</span>
            <strong style="display:block;font-family:var(--font-display);font-size:1.02rem;color:var(--p)">${money(remaining)}</strong>
          </div>
        </div>

        <div class="sheetField">
          <label class="mini">Valor a pagar agora</label>
          <div class="sheetAmountWrap">
            <span class="sheetCurrency">R$</span>
            <input id="mdPayVal" type="number" step="0.01" inputmode="decimal" class="sheetAmountInput" value="${suggestedVal}" required />
          </div>
          <div style="display:flex;gap:6px;margin-top:4px;flex-wrap:wrap">
            <button type="button" class="sheetPill active" data-md-quick="${suggestedVal}">Parcela: ${money(suggestedVal)}</button>
            ${remaining !== suggestedVal ? `<button type="button" class="sheetPill" data-md-quick="${remaining}">Quitar tudo: ${money(remaining)}</button>` : ''}
          </div>
        </div>

        <div class="sheetField">
          <label class="mini">De qual conta saiu o dinheiro?</label>
          <div class="sheetPills" id="mdPayAccPills">
            <button type="button" class="sheetPill active" data-acc="conta">🏦 Conta (${money(st.balances.conta.amount)})</button>
            <button type="button" class="sheetPill" data-acc="vale1">🥗 VA Mercado (${money(st.balances.vale1.amount)})</button>
            <button type="button" class="sheetPill" data-acc="vale2">🍽️ VA Refeição (${money(st.balances.vale2.amount)})</button>
            <button type="button" class="sheetPill" data-acc="none">⚪ Apenas registrar baixa</button>
          </div>
        </div>

        <button type="button" id="mdConfirmPayBtn" class="btn sheetSubmitBtn" style="margin-top:4px">
          ✓ Confirmar pagamento de ${money(suggestedVal)}
        </button>
      </div>
    `;

    let selectedAcc = 'conta';
    const payValInp = document.getElementById('mdPayVal');
    const confirmBtn = document.getElementById('mdConfirmPayBtn');
    const accPillsWrap = document.getElementById('mdPayAccPills');

    function updateConfirmBtn(){
      const val = parseFloat((payValInp && payValInp.value) || 0) || 0;
      if(confirmBtn) confirmBtn.textContent = `✓ Confirmar pagamento de ${money(val)}`;
    }

    if(payValInp) payValInp.addEventListener('input', updateConfirmBtn);

    body.addEventListener('click', e => {
      const qBtn = e.target.closest('[data-md-quick]');
      if(qBtn){
        const val = parseFloat(qBtn.dataset.mdQuick);
        if(payValInp) payValInp.value = val;
        body.querySelectorAll('[data-md-quick]').forEach(b => b.classList.toggle('active', b === qBtn));
        updateConfirmBtn();
        haptic('light');
        return;
      }
      const accBtn = e.target.closest('[data-acc]');
      if(accBtn && accPillsWrap && accPillsWrap.contains(accBtn)){
        selectedAcc = accBtn.dataset.acc;
        accPillsWrap.querySelectorAll('.sheetPill').forEach(b => b.classList.toggle('active', b === accBtn));
        haptic('light');
      }
    });

    if(confirmBtn){
      confirmBtn.addEventListener('click', () => {
        const val = parseFloat((payValInp && payValInp.value) || 0);
        if(!Number.isFinite(val) || val <= 0){
          showToast('Informe um valor de pagamento válido.', 'warn');
          return;
        }

        const prevStatus = {
          paid: d.paid,
          paidAt: d.paidAt || '',
          installmentsPaid: debtPaidInstallments(d),
          payments: [...(d.payments || [])]
        };

        const paymentEntry = {
          id: id(),
          value: val,
          account: selectedAcc,
          at: new Date().toISOString()
        };

        if(!Array.isArray(d.payments)) d.payments = [];
        d.payments.push(paymentEntry);

        const totalPaid = d.payments.reduce((s,p) => s + Number(p.value || 0), 0);
        const totalDebt = roundMoneyValue(inst * instVal);

        if(totalPaid >= totalDebt - 0.01){
          d.paid = true;
          d.paidAt = new Date().toISOString();
          d.installmentsPaid = inst;
        } else {
          d.paid = false;
          d.installmentsPaid = instVal > 0 ? Math.min(inst - 1, Math.floor((totalPaid + 0.01) / instVal)) : 0;
        }

        let txId = null;
        if(selectedAcc !== 'none' && st.balances[selectedAcc]){
          st.balances[selectedAcc].amount = roundMoneyValue((Number(st.balances[selectedAcc].amount) || 0) - val);
          txId = id();
          const nextInst = Math.min(inst, prevStatus.installmentsPaid + 1);
          const note = inst > 1 ? `Parcela ${nextInst}/${inst} ${txt(d.name, 30)}` : `Pagamento ${txt(d.name, 30)}`;
          const meta = categoryMeta(note, 'Parcela divida');
          st.tx.unshift({
            id: txId,
            account: selectedAcc,
            type: 'out',
            value: val,
            note,
            category: meta.label,
            categoryKey: meta.key,
            myDebtId: d.id,
            myDebtInstallment: nextInst,
            at: new Date().toISOString()
          });
        }

        closeMdSheet();
        save(true);
        renderMyDebts();
        renderFinance();
        renderUnifiedStatement();
        renderSummary();
        haptic('success');
        showToast(`✓ Pagamento de ${money(val)} em ${d.name} registrado!`, 'ok');

        startMyDebtUndo({
          myDebtId: d.id,
          account: selectedAcc,
          val,
          txId,
          prevStatus,
          debtName: d.name
        });
      });
    }

    openMdSheet();
  }

  function openMyDebtOptionsMenu(debtId){
    const d = (st.myDebts || []).find(x => x.id === debtId);
    if(!d) return;

    const title = document.getElementById('mdSheetTitle');
    if(title) title.textContent = `Opções · ${d.name}`;

    const body = document.getElementById('mdSheetBody');
    if(!body) return;

    body.innerHTML = `
      <div style="display:grid;gap:8px;padding:6px 0" id="mdMenuOptionsWrap">
        <button type="button" class="btn" style="text-align:left;display:flex;align-items:center;gap:10px;padding:10px 14px" data-menu-act="pay">
          <span>✓</span> <span>Registrar pagamento (parcela ou livre)</span>
        </button>
        <button type="button" class="ghost" style="text-align:left;display:flex;align-items:center;gap:10px;padding:10px 14px" data-menu-act="change-inst">
          <span>🔢</span> <span>Alterar parcelas (${debtPaidInstallments(d)}/${debtInstallments(d)}x)</span>
        </button>
        <button type="button" class="ghost" style="text-align:left;display:flex;align-items:center;gap:10px;padding:10px 14px" data-menu-act="timeline">
          <span>📜</span> <span>Ver linha do tempo / histórico</span>
        </button>
        <button type="button" class="ghost" style="text-align:left;display:flex;align-items:center;gap:10px;padding:10px 14px" data-menu-act="edit">
          <span>✏️</span> <span>Editar dados completos da dívida</span>
        </button>
        <button type="button" class="ghost" style="text-align:left;display:flex;align-items:center;gap:10px;padding:10px 14px" data-menu-act="toggle">
          <span>🔄</span> <span>${d.paid ? 'Reabrir dívida' : 'Marcar como quitada'}</span>
        </button>
        <button type="button" class="danger" style="text-align:left;display:flex;align-items:center;gap:10px;padding:10px 14px;margin-top:6px" data-menu-act="delete">
          <span>🗑️</span> <span>Excluir dívida permanentemente</span>
        </button>
      </div>
    `;

    const wrap = document.getElementById('mdMenuOptionsWrap');
    if(wrap){
      wrap.addEventListener('click', e => {
        const btn = e.target.closest('[data-menu-act]');
        if(!btn) return;
        const act = btn.dataset.menuAct;
        closeMdSheet();
        if(act === 'pay') openMyDebtPaySheet(d.id);
        else if(act === 'change-inst') openMyDebtChangeInstallmentsSheet(d.id);
        else if(act === 'timeline') openCreditorTimelineSheet(d.name);
        else if(act === 'edit') openMyDebtEditSheet(d.id);
        else if(act === 'toggle'){
          d.paid = !d.paid;
          if(d.paid){
            d.paidAt = new Date().toISOString();
            d.installmentsPaid = debtInstallments(d);
          } else {
            d.paidAt = '';
          }
          save(true);
          renderMyDebts();
          renderSummary();
          showToast(d.paid ? `✓ ${d.name} marcada como quitada!` : 'Dívida reaberta!', 'ok');
        }
        else if(act === 'delete'){
          if(confirm(`Excluir a dívida de ${d.name}?`)){
            st.myDebts = (st.myDebts || []).filter(x => x.id !== d.id);
            st.tx = (st.tx || []).map(t => t.myDebtId === d.id ? Object.assign({}, t, { myDebtId: '', myDebtInstallment: 0 }) : t);
            save(true);
            renderMyDebts();
            renderSummary();
            showToast('Dívida excluída.', 'ok');
          }
        }
      });
    }

    openMdSheet();
  }

  function openCreditorTimelineSheet(creditorName){
    const target = foldText(creditorName);
    const items = (st.myDebts || []).filter(d => foldText(d.name) === target);
    if(!items.length) return;

    const title = document.getElementById('mdSheetTitle');
    const reasonIcon = myDebtReasonIcon(items[0]);
    if(title) title.innerHTML = `${reasonIcon} ${safe(items[0].name)} <span class="tag ok" style="margin-left:6px">${items.length} ${items.length===1?'conta':'contas'}</span>`;

    const body = document.getElementById('mdSheetBody');
    if(!body) return;

    let totalContracted = 0;
    let totalPaid = 0;
    const events = [];

    items.forEach(d => {
      const inst = debtInstallments(d);
      const instVal = debtInstallmentValue(d);
      const dTotal = roundMoneyValue(inst * instVal);
      totalContracted += dTotal;

      events.push({
        type: 'created',
        date: d.at || new Date().toISOString(),
        title: `Cadastrou dívida de ${money(dTotal)}`,
        detail: inst > 1 ? `${inst}x de ${money(instVal)} · ${d.note || 'Sem observação'}` : `${d.note || 'À vista'}`,
        dotColor: '#39ff8f'
      });

      (d.payments || []).forEach(p => {
        const pVal = Number(p.value) || 0;
        totalPaid += pVal;
        const accNames = { conta: 'Saldo em Conta', vale1: 'VA Mercado', vale2: 'VA Refeição', none: 'Baixa direta' };
        events.push({
          type: 'payment',
          date: p.at,
          title: `Pagou ${money(pVal)}`,
          detail: `Debitado de ${accNames[p.account] || 'Saldo em Conta'}`,
          dotColor: '#4cff9e'
        });
      });

      if(d.paid && (!d.payments || !d.payments.length)){
        totalPaid += dTotal;
        events.push({
          type: 'paid',
          date: d.paidAt || d.at,
          title: `Quitou conta de ${money(dTotal)}`,
          detail: 'Marcado como quitado',
          dotColor: '#4cff9e'
        });
      }
    });

    events.sort((a,b) => new Date(b.date) - new Date(a.date));
    const openBalance = Math.max(0, totalContracted - totalPaid);

    body.innerHTML = `
      <div style="display:grid;gap:12px;padding:4px 0">
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px;background:rgba(255,255,255,.03);padding:10px;border-radius:12px;border:1px solid var(--ln);text-align:center">
          <div>
            <span class="mini">Total contratado</span>
            <strong style="font-family:var(--font-display);font-size:.96rem;display:block;margin-top:2px">${money(totalContracted)}</strong>
          </div>
          <div>
            <span class="mini">Total pago</span>
            <strong style="font-family:var(--font-display);font-size:.96rem;color:#4cff9e;display:block;margin-top:2px">${money(totalPaid)}</strong>
          </div>
          <div>
            <span class="mini">Em aberto</span>
            <strong style="font-family:var(--font-display);font-size:.96rem;color:${openBalance > 0 ? '#ffcf5f' : 'var(--p)'};display:block;margin-top:2px">${money(openBalance)}</strong>
          </div>
        </div>

        <div style="font-size:.76rem;font-weight:700;color:var(--mut);text-transform:uppercase;letter-spacing:.05em">Linha do Tempo</div>

        <div class="dvTimeline">
          ${events.map(ev => `
            <div class="dvTimelineItem">
              <div class="dvTimelineDot" style="background:${ev.dotColor}"></div>
              <div class="dvTimelineTitle">${ev.title}</div>
              <div class="dvTimelineMeta">${shortDate(ev.date)} · ${ev.detail}</div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
    openMdSheet();
  }

  function openMyDebtChangeInstallmentsSheet(debtId){
    const d = (st.myDebts || []).find(x => x.id === debtId);
    if(!d) return;

    const title = document.getElementById('mdSheetTitle');
    if(title) title.textContent = `Alterar parcelas · ${d.name}`;

    const body = document.getElementById('mdSheetBody');
    if(!body) return;

    const totalInst = debtInstallments(d);
    const paidInst = debtPaidInstallments(d);
    const instVal = debtInstallmentValue(d);

    body.innerHTML = `
      <form id="mdChangeInstForm" style="display:grid;gap:12px;padding:4px 0">
        <div style="padding:10px 12px;border-radius:10px;background:rgba(255,255,255,.04);border:1px solid var(--ln);font-size:.82rem;line-height:1.4">
          <div style="font-weight:700;color:#fff">${esc(d.name)}</div>
          <div class="mut">Atualmente: <strong style="color:var(--txt)">${paidInst}/${totalInst} parcelas</strong> de ${money(instVal)}</div>
        </div>

        <div class="sheetField">
          <label class="mini">Total de parcelas (1 a 999)</label>
          <div style="position:relative;display:flex;align-items:center;">
            <input id="mdQuickTotalInst" type="number" min="1" max="999" step="1" inputmode="numeric" class="sheetInput dvInstInput" value="${totalInst}" style="padding-right:26px;text-align:center;font-weight:700;font-size:1.1rem;min-height:46px;" required />
            <span style="position:absolute;right:12px;font-size:.9rem;font-weight:700;color:var(--mut);pointer-events:none;">x</span>
          </div>
          <div class="sheetTagChips" id="mdQuickInstPresets" style="margin-top:6px;">
            <span class="mut" style="font-size:.72rem;margin-right:2px;align-self:center;">Atalhos:</span>
            ${[1, 2, 3, 6, 10, 12, 18, 24, 36, 48, 60, 120, 240, 360].map(n => `<button type="button" class="sheetTagChip ${totalInst===n?'active':''}" data-inst="${n}">${n}x</button>`).join('')}
          </div>
        </div>

        <div class="sheetField">
          <label class="mini">Quantas parcelas já foram pagas?</label>
          <input id="mdQuickPaidInst" type="number" min="0" max="999" step="1" inputmode="numeric" class="sheetInput" value="${paidInst}" style="text-align:center;font-weight:700;min-height:42px;" required />
        </div>

        <button type="submit" class="btn sheetSubmitBtn" style="margin-top:4px">Salvar novas parcelas</button>
      </form>
    `;

    const presetsWrap = document.getElementById('mdQuickInstPresets');
    const totalInput = document.getElementById('mdQuickTotalInst');
    if(presetsWrap && totalInput){
      presetsWrap.addEventListener('click', e => {
        const btn = e.target.closest('[data-inst]');
        if(!btn) return;
        totalInput.value = btn.dataset.inst;
        presetsWrap.querySelectorAll('.sheetTagChip').forEach(b => b.classList.toggle('active', b === btn));
        haptic('light');
      });
      totalInput.addEventListener('input', () => {
        const val = parseInt(totalInput.value || '1', 10);
        presetsWrap.querySelectorAll('.sheetTagChip').forEach(b => b.classList.toggle('active', parseInt(b.dataset.inst, 10) === val));
      });
    }

    const form = document.getElementById('mdChangeInstForm');
    if(form){
      form.addEventListener('submit', e => {
        e.preventDefault();
        const newTotal = Math.min(999, Math.max(1, parseInt(((document.getElementById('mdQuickTotalInst')||{}).value || '1'), 10) || 1));
        const newPaid = Math.min(newTotal, Math.max(0, parseInt(((document.getElementById('mdQuickPaidInst')||{}).value || '0'), 10) || 0));

        d.installments = newTotal;
        d.installmentsPaid = newPaid;
        d.paid = newPaid >= newTotal;
        if(d.paid){
          if(!d.paidAt) d.paidAt = new Date().toISOString();
        } else {
          d.paidAt = '';
        }

        save(true);
        renderMyDebts();
        renderSummary();
        closeMdSheet();
        haptic('success');
        showToast(`✓ Parcelas de ${d.name} alteradas para ${newPaid}/${newTotal}!`, 'ok');
      });
    }

    openMdSheet();
  }

  function openMyDebtEditSheet(debtId){
    const d = (st.myDebts || []).find(x => x.id === debtId);
    if(!d) return;

    const title = document.getElementById('mdSheetTitle');
    if(title) title.textContent = `Editar dívida · ${d.name}`;

    const body = document.getElementById('mdSheetBody');
    if(!body) return;

    const inst = debtInstallments(d);
    const instVal = debtInstallmentValue(d);
    const currentReason = myDebtReasonKey(d);

    body.innerHTML = `
      <form id="mdEditForm" style="display:grid;gap:10px;padding:4px 0">
        <div class="sheetField">
          <label class="mini">Categoria</label>
          <div class="sheetPills" id="mdEditReasonPills">
            <button type="button" class="sheetPill ${currentReason==='house'?'active':''}" data-reason="house">🏠 Contas da Casa</button>
            <button type="button" class="sheetPill ${currentReason==='loan'?'active':''}" data-reason="loan">🏦 Empréstimo</button>
            <button type="button" class="sheetPill ${currentReason==='card'?'active':''}" data-reason="card">💳 Fatura / Cartão</button>
            <button type="button" class="sheetPill ${currentReason==='service'?'active':''}" data-reason="service">📱 Serviços</button>
            <button type="button" class="sheetPill ${currentReason==='other'?'active':''}" data-reason="other">📦 Outro</button>
          </div>
        </div>

        <div class="sheetField">
          <label class="mini">Para quem ou qual conta</label>
          <input id="mdEditName" type="text" maxlength="30" class="sheetInput" value="${esc(d.name)}" required />
        </div>

        <div class="dvFormRow">
          <div class="sheetField">
            <label class="mini">Valor da parcela (R$)</label>
            <input id="mdEditAmount" type="number" step="0.01" inputmode="decimal" class="sheetInput" value="${instVal}" required />
          </div>
          <div class="sheetField">
            <label class="mini">Parcelas (até 999)</label>
            <div style="position:relative;display:flex;align-items:center;">
              <input id="mdEditInstallments" type="number" min="1" max="999" step="1" inputmode="numeric" class="sheetInput dvInstInput" value="${inst}" style="padding-right:24px;text-align:center;font-weight:700;min-height:46px;" required />
              <span style="position:absolute;right:8px;font-size:0.84rem;font-weight:700;color:var(--mut);pointer-events:none;">x</span>
            </div>
          </div>
        </div>
        <div class="sheetTagChips" id="mdEditInstPresets" style="margin-top:2px;">
          <span class="mut" style="font-size:.72rem;margin-right:2px;align-self:center;">Atalhos:</span>
          ${[1,2,3,6,10,12,24,36,48,60,120].map(n => `<button type="button" class="sheetTagChip ${inst===n?'active':''}" data-inst="${n}">${n}x</button>`).join('')}
        </div>

        <div class="sheetField">
          <label class="mini">Data de vencimento</label>
          <input id="mdEditPayDate" type="date" class="sheetInput" value="${d.payDate || ''}" />
        </div>

        <div class="sheetField">
          <label class="mini">Observação</label>
          <input id="mdEditNote" type="text" maxlength="50" class="sheetInput" value="${esc(d.note || '')}" placeholder="Opcional" />
        </div>

        <button type="submit" class="btn sheetSubmitBtn" style="margin-top:6px">Salvar alterações</button>
      </form>
    `;

    const editChipsWrap = document.getElementById('mdEditInstPresets');
    const editInstInput = document.getElementById('mdEditInstallments');
    if(editChipsWrap && editInstInput){
      editChipsWrap.addEventListener('click', e => {
        const chip = e.target.closest('[data-inst]');
        if(!chip) return;
        editInstInput.value = chip.dataset.inst;
        editChipsWrap.querySelectorAll('.sheetTagChip').forEach(c => c.classList.toggle('active', c === chip));
        haptic('light');
      });
      editInstInput.addEventListener('input', () => {
        const val = parseInt(editInstInput.value || '1', 10);
        editChipsWrap.querySelectorAll('.sheetTagChip').forEach(c => c.classList.toggle('active', parseInt(c.dataset.inst, 10) === val));
      });
    }

    let editReason = currentReason;
    const pillsWrap = document.getElementById('mdEditReasonPills');
    if(pillsWrap){
      pillsWrap.addEventListener('click', e => {
        const pill = e.target.closest('[data-reason]');
        if(!pill) return;
        editReason = pill.dataset.reason;
        pillsWrap.querySelectorAll('.sheetPill').forEach(p => p.classList.toggle('active', p === pill));
        haptic('light');
      });
    }

    const editForm = document.getElementById('mdEditForm');
    if(editForm){
      editForm.addEventListener('submit', e => {
        e.preventDefault();
        const newName = txt((document.getElementById('mdEditName')||{}).value, 30);
        const newAmt = parseFloat(((document.getElementById('mdEditAmount')||{}).value || '').replace(',', '.'));
        const newInst = Math.min(999, Math.max(1, parseInt(((document.getElementById('mdEditInstallments')||{}).value || '1'), 10) || 1));
        const newPayDate = ((document.getElementById('mdEditPayDate')||{}).value || '').trim();
        const newNote = txt((document.getElementById('mdEditNote')||{}).value, 50);

        if(!newName || !Number.isFinite(newAmt) || newAmt <= 0) return;

        d.name = newName;
        d.amount = newAmt;
        d.installmentValue = newAmt;
        d.installments = newInst;
        d.payDate = newPayDate;
        d.note = newNote;
        d.reason = editReason;

        const totalPaid = (d.payments || []).reduce((s,p) => s + Number(p.value || 0), 0);
        const totalDebt = roundMoneyValue(newInst * newAmt);
        if(totalPaid >= totalDebt - 0.01){
          d.paid = true;
          d.installmentsPaid = newInst;
        } else {
          d.paid = false;
          d.installmentsPaid = newAmt > 0 ? Math.min(newInst - 1, Math.floor((totalPaid + 0.01) / newAmt)) : 0;
        }

        save(true);
        renderMyDebts();
        renderSummary();
        closeMdSheet();
        haptic('success');
        showToast('✓ Dívida atualizada!', 'ok');
      });
    }

    openMdSheet();
  }

  function handleMyDebtBoardClick(e){
    const payBtn = e.target.closest('[data-act="md-open-pay"]');
    if(payBtn){
      openMyDebtPaySheet(payBtn.dataset.mydeb);
      return;
    }
    const changeInstBtn = e.target.closest('[data-act="md-change-inst"]');
    if(changeInstBtn){
      openMyDebtChangeInstallmentsSheet(changeInstBtn.dataset.mydeb);
      return;
    }
    const menuBtn = e.target.closest('[data-act="md-menu"]');
    if(menuBtn){
      openMyDebtOptionsMenu(menuBtn.dataset.mydeb);
      return;
    }
    const timelineBtn = e.target.closest('[data-act="md-timeline"]');
    if(timelineBtn){
      openCreditorTimelineSheet(timelineBtn.dataset.creditor);
      return;
    }
  }

  const myDebtListEl = document.getElementById('myDebtList');
  if(myDebtListEl) myDebtListEl.addEventListener('click', handleMyDebtBoardClick);

  let mdTouchTimer = null;
  let mdTouchMoved = false;
  if(myDebtListEl){
    myDebtListEl.addEventListener('touchstart', e => {
      const card = e.target.closest('.dvCard');
      if(!card || e.target.closest('button')) return;
      mdTouchMoved = false;
      mdTouchTimer = setTimeout(() => {
        if(!mdTouchMoved && card.dataset.mydeb){
          haptic('medium');
          openMyDebtOptionsMenu(card.dataset.mydeb);
        }
      }, 520);
    }, { passive: true });
    myDebtListEl.addEventListener('touchmove', () => { mdTouchMoved = true; if(mdTouchTimer) clearTimeout(mdTouchTimer); }, { passive: true });
    myDebtListEl.addEventListener('touchend', () => { if(mdTouchTimer) clearTimeout(mdTouchTimer); }, { passive: true });
    myDebtListEl.addEventListener('touchcancel', () => { if(mdTouchTimer) clearTimeout(mdTouchTimer); }, { passive: true });
  }

  el.goalForm.addEventListener('submit',e=>{
    e.preventDefault();
    const name=txt(el.goalName.value,36);
    const target=parseFloat((el.goalTarget.value||'').replace(',','.'));
    if(!name||!Number.isFinite(target)||target<=0) return;
    st.goals.unshift({id:id(),name,target,saved:0,tx:[]});
    st.goals=st.goals.slice(0,60);
    el.goalName.value=''; el.goalTarget.value='';
    save(true); renderGoals(); renderGoalStatement(); renderSummary();
  });

  el.goalList.addEventListener('click',e=>{
    const card=e.target.closest('[data-goal-id]'); if(!card) return;
    const goal=st.goals.find(g=>g.id===card.dataset.goalId); if(!goal) return;

    const quickAporte=e.target.dataset.goalDeposit;
    if(quickAporte){
      const amt=parseFloat(quickAporte);
      if(amt>0){
        goalMove(goal,'deposit',amt);
        haptic('success');
        showToast(`✓ Aporte de ${money(amt)} em ${goal.name}!`, 'ok');
        return;
      }
    }

    const input=card.querySelector('[data-goal-value]');
    const inputValue=input ? input.value : '';
    const raw=parseFloat((inputValue||'').replace(',','.'));
    const value=Number.isFinite(raw)?Math.abs(raw):0;

    if(e.target.matches('[data-act="goal-edit"]')){
      ui.goals[goal.id]=!ui.goals[goal.id];
      renderGoals();
      return;
    }

    if(e.target.matches('[data-act="goal-remove"]')){
      if(!confirm(`Deseja realmente remover o objetivo "${goal.name}"?`)) return;
      st.goals=st.goals.filter(g=>g.id!==goal.id);
      delete ui.goals[goal.id];
      save(true); renderGoals(); renderGoalStatement(); renderSummary();
      return;
    }

    if(value<=0) return;
    if(e.target.matches('[data-act="goal-deposit"]')) goalMove(goal,'deposit',value);
    if(e.target.matches('[data-act="goal-withdraw"]')) goalMove(goal,'withdraw',value);
    if(e.target.matches('[data-act="goal-yield"]')) goalMove(goal,'yield',value);

    if(input) input.value='';
  });

  if(el.copyStatementBtn){
    el.copyStatementBtn.addEventListener('click',copyStatementSummary);
  }

  if(el.statementSearchInput){
    el.statementSearchInput.addEventListener('input',e=>{
      ui.statementSearch=e.target.value||'';
      renderUnifiedStatement();
    });
  }

  if(el.statementFeedFilters){
    el.statementFeedFilters.addEventListener('click',e=>{
      const chip=e.target.closest('[data-stmt-filter]'); if(!chip) return;
      ui.statementFilter=chip.dataset.stmtFilter;
      el.statementFeedFilters.querySelectorAll('.filterChip').forEach(c=>c.classList.toggle('active',c===chip));
      haptic('light');
      renderUnifiedStatement();
    });
  }

  el.goalList.addEventListener('input',e=>{
    const card=e.target.closest('[data-goal-id]'); if(!card) return;
    const goal=st.goals.find(g=>g.id===card.dataset.goalId); if(!goal) return;
    if(e.target.matches('[data-f="goal-name"]')) goal.name=txt(e.target.value,36);
    if(e.target.matches('[data-f="goal-target"]')){
      const t=parseFloat((e.target.value||'').replace(',','.'));
      if(Number.isFinite(t)&&t>0) goal.target=t;
    }
    save(); renderGoalStatement(); renderSummary();
  });

  el.statementPage.addEventListener('click',e=>{
    const toggle=e.target.closest('[data-statement-toggle]');
    if(toggle){
      const section=toggle.getAttribute('data-statement-toggle');
      if(!Object.prototype.hasOwnProperty.call(ui.statement,section)) return;
      ui.statement[section]=!ui.statement[section];
      if(!ui.statement[section] && ui.statementEditor && ui.statementEditor.section===section){
        ui.statementEditor=null;
      }
      renderAll();
      return;
    }

    const editBtn=e.target.closest('[data-tx-edit]');
    if(editBtn){
      ui.statementEditor={
        section:editBtn.getAttribute('data-statement-section')||'',
        source:editBtn.getAttribute('data-source')||'',
        txId:editBtn.getAttribute('data-tx-edit')||'',
        goalId:editBtn.getAttribute('data-goal-id')||''
      };
      renderAll();
      return;
    }

    const cancelBtn=e.target.closest('[data-tx-cancel]');
    if(cancelBtn){
      ui.statementEditor=null;
      renderAll();
      return;
    }

    const saveBtn=e.target.closest('[data-tx-save]');
    if(saveBtn){
      saveStatementEdit(
        saveBtn.getAttribute('data-statement-section')||'',
        saveBtn.getAttribute('data-source')||'',
        saveBtn.getAttribute('data-tx-save')||'',
        saveBtn.getAttribute('data-goal-id')||'',
        saveBtn
      );
      return;
    }

    const removeBtn=e.target.closest('[data-tx-del]');
    if(!removeBtn) return;
    removeStatementTransaction(
      removeBtn.getAttribute('data-source'),
      removeBtn.getAttribute('data-tx-del'),
      removeBtn.getAttribute('data-goal-id') || ''
    );
  });
}

function renderAll(){renderPrivacyToggle();renderPage();renderProfile();renderHabits();renderAchievements();renderFocusSession();refreshGame();renderFinance();renderCredit();renderDebtors();renderMyDebts();renderGoals();renderGoalStatement();renderStatementControls();renderRoutineTimeline();renderSummary();renderPublishStatus();renderDesktopCodeBackupStatus();renderUnifiedStatement();if(typeof switchDebtsView==='function')switchDebtsView(ui.debtsView||'debtors');}
function showPage(page){
  if(page==='goals') page='home';
  ui.page=['home','credit','debts','statement'].includes(page)?page:'home';
  renderPage();
  if(ui.page==='debts' && typeof switchDebtsView==='function'){
    switchDebtsView(ui.debtsView || 'debtors');
  }
  syncHash(ui.page);
  scrollTopSafe();
}
function renderPage(){
  setVisible(el.homePage, ui.page==='home');
  setVisible(el.routinePage, false);
  setVisible(el.creditPage, ui.page==='credit');
  setVisible(el.debtsPage, ui.page==='debts');
  setVisible(el.goalsPage, false);
  setVisible(el.statementPage, ui.page==='statement');
  for(var i=0;i<el.navBtns.length;i++){
    setActive(el.navBtns[i], el.navBtns[i].getAttribute('data-page')===ui.page);
  }
  if(ui.page==='statement') renderUnifiedStatement();
}
function renderProfile(){
  el.app.textContent=st.appName;
}

function renderFocusHabitOptions(){
  const opts=st.habits.map(h=>`<option value="${h.id}">${safe(h.name)}</option>`).join('');
  el.focusHabitSelect.innerHTML=opts||'<option value="">Sem hábitos cadastrados</option>';
  if(st.focusSession.habitId && st.habits.some(h=>h.id===st.focusSession.habitId)){
    el.focusHabitSelect.value=st.focusSession.habitId;
  } else {
    st.focusSession.habitId=st.habits[0] ? st.habits[0].id : '';
    el.focusHabitSelect.value=st.focusSession.habitId;
  }
}

function renderFocusSession(){
  st.focusSession=Object.assign({},DEF.focusSession,st.focusSession||{});
  const sec=Math.max(0,parseInt(st.focusSession.secondsLeft||0,10));
  const mm=String(Math.floor(sec/60)).padStart(2,'0');
  const ss=String(sec%60).padStart(2,'0');
  el.focusClock.textContent=`${mm}:${ss}`;
  const habit=st.habits.find(h=>h.id===st.focusSession.habitId);
  const name=habit?habit.name:'hábito';
  el.focusStatus.textContent=st.focusSession.running?`Sessão ativa: ${name}`:`Pronto para focar em: ${name}`;
  updateZenDisplay();
}

function startFocusSession(){
  if(!st.habits.length){el.focusStatus.textContent='Cadastre um hábito antes de iniciar sessão.'; return;}
  const min=Math.min(180,Math.max(1,parseInt(el.focusMinutesInput.value||'25',10)));
  if(!st.focusSession.secondsLeft||st.focusSession.secondsLeft<=0||!st.focusSession.running){
    st.focusSession.secondsLeft=min*60;
  }
  st.focusSession.habitId=el.focusHabitSelect.value||st.habits[0].id;
  st.focusSession.running=true;
  if(focusTick) clearInterval(focusTick);
  focusTick=setInterval(tickFocusSession,1000);
  save(); renderFocusSession();
}

function pauseFocusSession(){
  st.focusSession.running=false;
  if(focusTick){clearInterval(focusTick); focusTick=null;}
  save(); renderFocusSession();
}

function resetFocusSession(){
  if(focusTick){clearInterval(focusTick); focusTick=null;}
  const min=Math.min(180,Math.max(1,parseInt(el.focusMinutesInput.value||'25',10)));
  st.focusSession.running=false;
  st.focusSession.secondsLeft=min*60;
  save(); renderFocusSession();
}

function tickFocusSession(){
  if(!st.focusSession.running) return;
  st.focusSession.secondsLeft=Math.max(0,(st.focusSession.secondsLeft||0)-1);
  if(st.focusSession.secondsLeft<=0){
    completeFocusSession();
    return;
  }
  renderFocusSession();
}

function completeFocusSession(){
  pauseFocusSession();
  const habit=st.habits.find(h=>h.id===st.focusSession.habitId);
  if(habit){
    st.xp=Math.max(0,st.xp+10);
    const skill=habit.skillTag||detectSkill(habit.name);
    adjustSkillXp(skill,10);
    pushRoutineLog('done',{name:`Sprint: ${habit.name}`});
  }
  const min=Math.min(180,Math.max(1,parseInt(el.focusMinutesInput.value||'25',10)));
  st.focusSession.secondsLeft=min*60;
  save(); refreshGame();
  el.focusStatus.textContent='Sprint concluído. XP e skill adicionados.';
}

function renderCharts(){
  drawRoutineChart();
  drawFinanceChart();
}

function drawRoutineChart(){
  if(!el.routineChart) return;
  const ctx=el.routineChart.getContext('2d');
  const days=last7DayKeys();
  const values=days.map(k=>{
    const stat = st.dailyStats && st.dailyStats[k] ? st.dailyStats[k] : {};
    return Math.max(0,Math.min(100,Number(stat.percent)||0));
  });
  drawBarChart(ctx,days.map(k=>k.slice(8,10)+'/'+k.slice(5,7)),values,100,'#39ff8f');
}

function getFinancePeriodDays(period){
  const now=new Date();
  now.setHours(0,0,0,0);
  const out=[];
  if(period==='month'){
    const year=now.getFullYear(), month=now.getMonth(), currentDay=now.getDate();
    for(let day=1; day<=currentDay; day++){
      const d=new Date(year, month, day);
      out.push(dateKey(d));
    }
  } else if(period==='all'){
    for(let i=29; i>=0; i--){
      const d=new Date(now);
      d.setDate(now.getDate()-i);
      out.push(dateKey(d));
    }
  } else {
    return last7DayKeys();
  }
  return out;
}

function drawFinanceChart(){
  if(!el.financeChart) return;
  const ctx=el.financeChart.getContext('2d');
  const period=ui.financePeriod || '7d';
  const days=getFinancePeriodDays(period);
  const net=days.map(k=>dailyNetConta(k));
  const card=days.map(k=>dailyCardSpend(k));
  drawDualLineChart(ctx,days.map(k=>k.slice(8,10)+'/'+k.slice(5,7)),net,card);
}

function drawBarChart(ctx,labels,values,maxValue,color){
  const viewport=canvasViewport(ctx.canvas,260);
  if(!viewport) return;
  ctx=viewport.ctx;
  const w=viewport.w,h=viewport.h;
  ctx.fillStyle='rgba(255,255,255,.75)';
  ctx.font='11px -apple-system,BlinkMacSystemFont,sans-serif';
  const left=44,right=18,top=20,bottom=34,gw=w-left-right,gh=h-top-bottom;
  ctx.strokeStyle='rgba(255,255,255,.14)';
  for(let i=0;i<=4;i++){ const y=top+(gh*i/4); ctx.beginPath(); ctx.moveTo(left,y); ctx.lineTo(left+gw,y); ctx.stroke(); }
  const bw=gw/Math.max(1,labels.length);
  labels.forEach((lb,i)=>{
    const v=values[i]||0;
    const bh=(v/maxValue)*gh;
    const x=left+i*bw+bw*0.18;
    const y=top+gh-bh;
    ctx.fillStyle=color;
    ctx.fillRect(x,y,bw*0.64,bh);
    ctx.fillStyle='rgba(255,255,255,.78)';
    ctx.fillText(lb,x-2,top+gh+16);
  });
}

function drawDualLineChart(ctx,labels,aVals,bVals){
  const viewport=canvasViewport(ctx.canvas,260);
  if(!viewport) return;
  ctx=viewport.ctx;
  const w=viewport.w,h=viewport.h;
  const left=44,right=18,top=20,bottom=34,gw=w-left-right,gh=h-top-bottom;
  const all=aVals.concat(bVals,[0]);
  const min=Math.min(...all), max=Math.max(...all,1), span=(max-min)||1;
  ctx.strokeStyle='rgba(255,255,255,.14)';
  for(let i=0;i<=4;i++){ const y=top+(gh*i/4); ctx.beginPath(); ctx.moveTo(left,y); ctx.lineTo(left+gw,y); ctx.stroke(); }

  const drawSeries=(vals,color)=>{
    ctx.strokeStyle=color; ctx.lineWidth=2; ctx.beginPath();
    vals.forEach((v,i)=>{
      const x=left+(gw*(i/(vals.length-1||1)));
      const y=top+gh-((v-min)/span)*gh;
      if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
    });
    ctx.stroke();
  };
  drawSeries(aVals,'#39ff8f');
  drawSeries(bVals,'#ffb341');
  ctx.fillStyle='rgba(255,255,255,.78)';
  ctx.font='11px -apple-system,BlinkMacSystemFont,sans-serif';
  const step=labels.length>18?4:labels.length>9?2:1;
  labels.forEach((lb,i)=>{
    if(i%step===0 || i===labels.length-1){
      const x=left+(gw*(i/(labels.length-1||1)));
      ctx.fillText(lb,x-14,top+gh+16);
    }
  });
}


function renderCreditDescChart(){
  syncCreditExpenseMonthPicker();
  const activeMonthKey = creditExpenseMonthKey();
  const activeMonthLabel = monthLabelFromKey(activeMonthKey);
  const breakdown = creditExpenseBreakdown(activeMonthKey);
  
  const catColors = ['#651fff','#d500f9','#f50057','#ff3d00','#ffea00','#00e5ff','#1de9b6'];
  const cats = compressBreakdown(buildCategoryBreakdown(
    breakdown.map(r => ({ value: r.value, label: r.label, key: r.label })),
    catColors, 'Sem categoria'
  ), 6, 'Outros');
  
  const total = cats.reduce((s,c) => s + c.value, 0);
  const wrap = el.ccDescLegend;
  if(!wrap) return;
  
  if(el.ccDescTotal) el.ccDescTotal.textContent = money(total);
  if(document.getElementById('ccDescMonth')) document.getElementById('ccDescMonth').textContent = `em ${activeMonthLabel}`;
  if(el.ccChartMonthTag) el.ccChartMonthTag.textContent = activeMonthLabel;
  if(el.ccDescChart) el.ccDescChart.style.display = 'none';
  
  if(!total) {
    wrap.innerHTML = `<div class="ft-panel"><div class="empty">Sem gastos classificados em ${safe(activeMonthLabel)}.</div></div>`;
    return;
  }
  
  let buckets = [];
  const color = '#b388ff';
  let chartHtml = '';
  
  if(activeMonthKey !== 'all' && st.credit && st.credit.tx) {
    const [y, m] = activeMonthKey.split('-');
    if(y && m) {
      const start = new Date(Number(y), Number(m)-1, 1);
      const end = new Date(Number(y), Number(m), 1);
      const inRange = st.credit.tx.filter(x => x.type === 'expense' && x.at >= start.toISOString() && x.at < end.toISOString());
      const daysInMonth = new Date(Number(y), Number(m), 0).getDate();
      for(let i=1; i<=daysInMonth; i++) {
        const d = new Date(Number(y), Number(m)-1, i);
        const dayTotal = inRange.filter(x => new Date(x.at).getDate() === i).reduce((s,x) => s + Number(x.value||0), 0);
        buckets.push({ val: dayTotal, tip: `${i}/${m}` });
      }
      
      const { svg, coords } = generateCurveSVG(buckets.map(b => b.val), 100, 100, color, 'grad-cc');
      
      chartHtml = `
        <div class="ft-chart-container" id="ccChartTouch">
          ${svg}
          <div class="ft-chart-axis">
            <span>1</span>
            <span>${daysInMonth}</span>
          </div>
          <div class="ft-chart-tooltip"></div>
          <div class="ft-chart-point" data-color="${color}"></div>
          <div class="ft-chart-touch"></div>
        </div>
      `;
      setTimeout(() => attachChartInteraction('ccChartTouch', coords, buckets.map(b => b.tip)), 50);
    }
  }

  let html = `
    <div class="ft-panel" style="background: linear-gradient(180deg, rgba(20,16,36,0.95), rgba(14,10,24,0.98)); border-color: rgba(179,136,255,0.15);">
      <div class="ft-header">
        <div>
          <div class="ft-title" style="color:#b388ff">GASTOS DO CARTÃO · ${activeMonthLabel.toUpperCase()}</div>
          <div class="ft-amount">${money(total).replace(',','<span>,').replace('.','.')}</span></div>
        </div>
      </div>
      
      ${chartHtml}
      
      <div class="ft-cats">
        ${cats.map((c, i) => `
          <div class="ft-cat" style="animation-delay: ${i*60}ms">
            <div class="ft-cat-icon" style="background: ${c.color}22; color: ${c.color}; border: 1px solid ${c.color}44;">${spxEmoji(c.label)}</div>
            <div class="ft-cat-info">
              <div class="ft-cat-name">${safe(c.label)}</div>
              <div class="ft-cat-bar-wrap"><div class="ft-cat-bar" style="width: ${Math.max(4, c.pct)}%; background: ${c.color}; box-shadow: 0 0 8px ${c.color}aa;"></div></div>
            </div>
            <div class="ft-cat-val">
              <strong>${money(c.value)}</strong>
              <span>${c.pct}%</span>
            </div>
          </div>
        `).join('')}
      </div>
    </div>
  `;
  
  wrap.innerHTML = html;
}


function creditExpenseBreakdown(monthKey){
  return buildCategoryBreakdown(
    (st.credit.tx||[])
      .filter(t=>t.type==='expense'&&(!monthKey||monthKeyFromValue(t.at)===monthKey))
      .map(t=>({value:Number(t.value)||0,label:t.category||t.desc,key:t.categoryKey})),
    ['#39ff8f','#2df5b4','#26c8ff','#2f89ff','#ffd447','#ff9a3c','#ff6f4e','#ff5f70','#d96cff','#8f7cff','#5cf2ff','#9dff5c'],
    'Sem categoria'
  );
}
function creditExpenseMonths(){
  const unique=new Set(
    (st.credit.tx||[])
      .filter(t=>t.type==='expense'&&(Number(t.value)||0)>0)
      .map(t=>monthKeyFromValue(t.at))
      .filter(Boolean)
  );
  const months=Array.from(unique);
  months.sort((a,b)=>a===b?0:(a<b?1:-1));
  return months.length?months:[currentMonthKey()];
}
function creditChartMonths(){
  const creditMonths=(st.credit.tx||[]).map(t=>monthKeyFromValue(t.at)).filter(Boolean);
  const chosen=String(ui.creditChartMonth||'').trim();
  const current=currentMonthKey();
  const rawKeys=creditMonths.concat([chosen,current]).filter(Boolean);
  const validKeys=rawKeys.filter(key=>monthIndexFromKey(key)>=0).sort((a,b)=>monthIndexFromKey(a)-monthIndexFromKey(b));
  const startKey=validKeys[0]||current;
  const baseEnd=validKeys[validKeys.length-1]||current;
  const futureEnd=shiftMonthKey(current,6);
  const endKey=monthIndexFromKey(baseEnd)>monthIndexFromKey(futureEnd)?baseEnd:futureEnd;
  const months=[];
  for(let key=startKey; monthIndexFromKey(key)<=monthIndexFromKey(endKey); key=shiftMonthKey(key,1)){
    months.push(key);
  }
  return months;
}
function creditChartMonthHasData(monthKey){
  return (st.credit.tx||[]).some(t=>t.type==='expense'&&monthKeyFromValue(t.at)===monthKey&&(Number(t.value)||0)>0);
}
function setCreditChartMonth(key){
  const normalized=/^\d{4}-\d{2}$/.test(String(key||''))?String(key):currentMonthKey();
  ui.creditChartMonth=normalized;
  if(el.ccChartMonth) el.ccChartMonth.value=normalized;
  renderCreditDescChart();
}
function shiftCreditChartMonthSelection(offset){
  const months=creditChartMonths();
  const active=creditExpenseMonthKey();
  const currentIndex=Math.max(0,months.indexOf(active));
  const nextIndex=Math.min(months.length-1,Math.max(0,currentIndex+Number(offset||0)));
  setCreditChartMonth(months[nextIndex]||active);
}
function resetCreditChartMonth(){
  const targetMonth=creditExpenseMonthKey();
  if(!targetMonth||!creditChartMonthHasData(targetMonth)){
    showToast('Não há gastos do cartão nesse mês para zerar.','warn');
    return;
  }
  const monthLabelText=monthLabelFromKey(targetMonth);
  const ok=window.confirm(`Zerar ${monthLabelText}? Isso remove os gastos do cartão desse mês do gráfico e recalcula a fatura.`);
  if(!ok) return;
  st.credit.tx=(st.credit.tx||[]).filter(t=>!(t.type==='expense'&&monthKeyFromValue(t.at)===targetMonth));
  recomputeCreditState();
  save(true);
  renderCredit();
  renderSummary();
}
function syncCreditExpenseMonthPicker(){
  if(!el.ccChartMonth) return;
  const months=creditChartMonths();
  const currentValue=creditExpenseMonthKey();
  el.ccChartMonth.innerHTML=months.map(key=>`<option value="${esc(key)}">${safe(monthLabelFromKey(key))}</option>`).join('');
  el.ccChartMonth.value=months.includes(currentValue)?currentValue:months[0];
  if(el.ccChartPrev){
    const idx=months.indexOf(currentValue);
    el.ccChartPrev.disabled=idx<=0;
  }
  if(el.ccChartNext){
    const idx=months.indexOf(currentValue);
    el.ccChartNext.disabled=idx<0||idx>=months.length-1;
  }
  if(el.ccChartReset){
    el.ccChartReset.disabled=!creditChartMonthHasData(currentValue);
  }
}
function monthIndexFromKey(key){
  if(!/^\d{4}-\d{2}$/.test(key||'')) return -1;
  const [year,month]=key.split('-').map(Number);
  if(!year||!month||month<1||month>12) return -1;
  return year*12+(month-1);
}
function shiftMonthKey(key,offset){
  if(!/^\d{4}-\d{2}$/.test(key||'')) return '';
  const [year,month]=key.split('-').map(Number);
  const d=new Date(year,month-1+Number(offset||0),1);
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`;
}
function archiveTimelineStartKey(items,getMonthKey){
  const fallback=`${today().slice(0,4)}-04`;
  const keys=(items||[]).map(item=>getMonthKey(item)).filter(Boolean).sort((a,b)=>monthIndexFromKey(a)-monthIndexFromKey(b));
  if(keys.length&&monthIndexFromKey(keys[0])>=0&&monthIndexFromKey(keys[0])<monthIndexFromKey(fallback)) return keys[0];
  return fallback;
}
function buildArchiveMonthGroups(items,getMonthKey,getValue,count){
  const rows=Array.isArray(items)?items.slice():[];
  const startKey=archiveTimelineStartKey(rows,getMonthKey);
  const grouped={};
  rows.forEach(item=>{
    const key=getMonthKey(item)||'sem-mes';
    if(!grouped[key]) grouped[key]={key,label:key==='sem-mes'?'Sem mês definido':monthLabelFromKey(key),items:[],total:0};
    grouped[key].items.push(item);
    grouped[key].total=roundMoneyValue(grouped[key].total+(Number(getValue(item))||0));
  });
  const existingKeys=Object.keys(grouped).filter(key=>key!=='sem-mes').sort((a,b)=>monthIndexFromKey(a)-monthIndexFromKey(b));
  const defaultEnd=shiftMonthKey(startKey,Math.max(0,(count||24)-1));
  const lastExisting=existingKeys.length?existingKeys[existingKeys.length-1]:startKey;
  const endKey=monthIndexFromKey(lastExisting)>monthIndexFromKey(defaultEnd)?lastExisting:defaultEnd;
  const groups=[];
  for(let key=startKey; monthIndexFromKey(key)<=monthIndexFromKey(endKey); key=shiftMonthKey(key,1)){
    groups.push(grouped[key]||{key,label:monthLabelFromKey(key),items:[],total:0});
  }
  if(grouped['sem-mes']) groups.push(grouped['sem-mes']);
  return groups;
}
function buildArchiveMonthGroupsUsedOnly(items,getMonthKey,getValue){
  const rows=Array.isArray(items)?items.slice():[];
  const grouped={};
  rows.forEach(item=>{
    const key=getMonthKey(item)||'sem-mes';
    if(!grouped[key]) grouped[key]={key,label:key==='sem-mes'?'Sem mês definido':monthLabelFromKey(key),items:[],total:0};
    grouped[key].items.push(item);
    grouped[key].total=roundMoneyValue(grouped[key].total+(Number(getValue(item))||0));
  });
  return Object.values(grouped).sort((a,b)=>{
    if(a.key==='sem-mes') return 1;
    if(b.key==='sem-mes') return -1;
    return monthIndexFromKey(a.key)-monthIndexFromKey(b.key);
  });
}

function accountOutRows(){
  const rows=[];
  (st.tx||[]).forEach(t=>{
    if(t.account!=='conta') return;
    const d=t.at?new Date(t.at):null;
    if(!d||isNaN(d.getTime())) return;
    let v=0;
    if(t.type==='out') v=Number(t.value)||0;
    else if(t.type==='set'){const diff=(Number(t.value)||0)-(Number(t.prev)||0); if(diff<0) v=Math.abs(diff);}
    if(v>0) rows.push({value:v,date:d,label:t.category||t.note,key:t.categoryKey,note:t.note||''});
  });
  return rows;
}
function spxDayKey(d){return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');}
function spxMonthKey(d){return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0');}
function spxEmoji(label){
  const k=String(label||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
  const map=[
    [/mercad|supermerc|feira|atacad|hortifruti|acougue/,'🛒'],
    [/uber|\b99\b|taxi|transporte|onibus|metro|gasolina|combust|posto|estaciona|pedagio|carro/,'🚗'],
    [/ifood|lanche|restaur|comida|pizza|burger|hamburg|almoco|janta|delivery|padaria|cafe|acai|sushi/,'🍔'],
    [/aluguel|condominio|casa|luz|energia|agua|internet|\bgas\b|celular|telefone/,'🏠'],
    [/farmac|remedio|saude|medic|consulta|academia|dentista/,'💊'],
    [/assinatura|netflix|spotify|streaming|prime|youtube|icloud|disney/,'📺'],
    [/roupa|loja|shopping|tenis|presente/,'🛍️'],
    [/\bbar\b|cerveja|bebida|festa|role|lazer|cinema|show|balada/,'🎉'],
    [/cartao|fatura|amex|credito/,'💳'],
    [/divida|emprest|parcela|boleto/,'🧾'],
    [/tabac|seda|cigarro|erva|weed|head ?shop/,'🌿'],
    [/pix|transfer|ted|saque/,'💸'],
    [/pet|racao|veterin/,'🐾'],
    [/curso|livro|escola|faculdade|estudo/,'📚'],
    [/outras/,'📦']
  ];
  for(const [re,ic] of map){ if(re.test(k)) return ic; }
  return '💰';
}

function renderAccountFlowChart(){
  const period = ui.accountFlowPeriod || 'month';
  const all = accountOutRows();
  const now = new Date(), today0 = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const end = new Date(today0); end.setDate(end.getDate() + 1);
  const wd = ['Dom','Seg','Ter','Qua','Qui','Sex','Sáb'], mn = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
  
  let buckets = [], start, prevStart = null, prevEnd = null, label = '', unit = 'day';
  
  if(period === '7d'){
    start = new Date(today0); start.setDate(start.getDate() - 6);
    prevStart = new Date(start); prevStart.setDate(prevStart.getDate() - 7); prevEnd = start;
    for(let i=0; i<7; i++){ const d = new Date(start); d.setDate(start.getDate() + i); buckets.push({ key: spxDayKey(d), label: wd[d.getDay()], tip: `${d.getDate()}/${d.getMonth()+1}`, value: 0 }); }
    label = 'Últimos 7 dias';
  } else if(period === 'all'){
    unit = 'month';
    start = new Date(now.getFullYear(), now.getMonth() - 5, 1);
    for(let i=0; i<6; i++){ const d = new Date(start.getFullYear(), start.getMonth() + i, 1); buckets.push({ key: spxMonthKey(d), label: mn[d.getMonth()], tip: `${mn[d.getMonth()]}`, value: 0 }); }
    label = 'Últimos 6 meses';
  } else {
    start = new Date(now.getFullYear(), now.getMonth(), 1);
    prevStart = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    prevEnd = new Date(now.getFullYear(), now.getMonth() - 1, now.getDate() + 1);
    for(let i=1; i<=now.getDate(); i++){ buckets.push({ key: spxDayKey(new Date(now.getFullYear(), now.getMonth(), i)), label: String(i), tip: `${i}/${now.getMonth()+1}`, value: 0 }); }
    label = 'Neste mês';
  }
  
  const inRange = all.filter(r => r.date >= start && r.date < end);
  const bmap = {}; buckets.forEach(b => bmap[b.key] = b);
  inRange.forEach(r => { const b = bmap[unit === 'month' ? spxMonthKey(r.date) : spxDayKey(r.date)]; if(b) b.value += r.value; });
  
  const total = inRange.reduce((s,r) => s + r.value, 0);
  let trendHtml = `<div class="ft-badge neutral">Sem dados</div>`;
  
  if(prevStart){
    const prev = all.filter(r => r.date >= prevStart && r.date < prevEnd).reduce((s,r) => s + r.value, 0);
    if(prev > 0){
      const diff = Math.round(((total - prev) / prev) * 100);
      trendHtml = diff > 0 ? `<div class="ft-badge up">▲ ${diff}% vs ant.</div>` : `<div class="ft-badge down">▼ ${Math.abs(diff)}% vs ant.</div>`;
    }
  }
  
  const catColors = ['#00e676','#18ffff','#b388ff','#ff4081','#ffeb3b','#ff9800','#00b0ff'];
  const cats = compressBreakdown(buildCategoryBreakdown(
    inRange.map(r => ({ value: r.value, label: r.label, key: r.key })),
    catColors, 'Sem categoria'
  ), 6, 'Outros');
  
  const wrap = document.getElementById('accountFlowLegend');
  if(!wrap) return;
  if(!total) {
    wrap.innerHTML = `<div class="ft-panel"><div class="empty">Nenhuma saída no período (${label}).</div></div>`;
    return;
  }
  
  const color = '#00e676';
  const { svg, coords } = generateCurveSVG(buckets.map(b => b.value), 100, 100, color, 'grad-acc');
  
  let html = `
    <div class="ft-panel">
      <div class="ft-header">
        <div>
          <div class="ft-title">SAÍDAS DA CONTA · ${label.toUpperCase()}</div>
          <div class="ft-amount">${money(total).replace(',','<span>,').replace('.','.')}</span></div>
        </div>
        ${trendHtml}
      </div>
      
      <div class="ft-chart-container" id="accChartTouch">
        ${svg}
        <div class="ft-chart-axis">
          <span>${buckets[0].label}</span>
          <span>${buckets[buckets.length-1].label}</span>
        </div>
        <div class="ft-chart-tooltip"></div>
        <div class="ft-chart-point" data-color="${color}"></div>
        <div class="ft-chart-touch"></div>
      </div>
      
      <div class="ft-cats">
        ${cats.map((c, i) => `
          <div class="ft-cat" style="animation-delay: ${i*60}ms">
            <div class="ft-cat-icon" style="background: ${c.color}22; color: ${c.color}; border: 1px solid ${c.color}44;">${spxEmoji(c.label)}</div>
            <div class="ft-cat-info">
              <div class="ft-cat-name">${safe(c.label)}</div>
              <div class="ft-cat-bar-wrap"><div class="ft-cat-bar" style="width: ${Math.max(4, c.pct)}%; background: ${c.color}; box-shadow: 0 0 8px ${c.color}aa;"></div></div>
            </div>
            <div class="ft-cat-val">
              <strong>${money(c.value)}</strong>
              <span>${c.pct}%</span>
            </div>
          </div>
        `).join('')}
      </div>
    </div>
  `;
  
  wrap.innerHTML = html;
  if(el.accountFlowTotal) el.accountFlowTotal.textContent = money(total);
  if(el.accountFlowPeriodLabel) el.accountFlowPeriodLabel.textContent = label;
  
  setTimeout(() => attachChartInteraction('accChartTouch', coords, buckets.map(b => b.tip)), 50);
}


function accountOutflowBreakdown(period){
  const targetPeriod=period || ui.accountFlowPeriod || 'all';
  const currentMonth=currentMonthKey();
  const start7d=lastDaysStart(7);
  const rows=[];
  (st.tx||[]).forEach(t=>{
    if(t.account!=='conta') return;
    if(targetPeriod==='month'){
      if(monthKeyFromValue(t.at)!==currentMonth) return;
    }else if(targetPeriod==='7d'){
      const txDate=t.at?new Date(t.at):null;
      if(!txDate||txDate<start7d) return;
    }
    if(t.type==='out'){
      rows.push({value:Number(t.value)||0,label:t.category||t.note,key:t.categoryKey});
      return;
    }
    if(t.type==='set'){
      const diff=(Number(t.value)||0)-(Number(t.prev)||0);
      if(diff<0) rows.push({value:Math.abs(diff),label:t.category||t.note,key:t.categoryKey});
    }
  });
  return buildCategoryBreakdown(
    rows,
    ['#26c8ff','#4de7ff','#39ff8f','#2f89ff','#7bc0ff','#ffd447','#ff9a3c','#ff6f4e','#d96cff','#8f7cff','#5cf2ff','#9dff5c'],
    'Sem categoria'
  );
}

function buildCategoryBreakdown(items,colors,fallback){
  const genericLabels=new Set(['sem categoria','adicionar','entrada','saida','deposito','retirada','gasto rapido','reserva cartao','ajuste manual','ajuste']);
  const grouped={};
  (items||[]).forEach(item=>{
    const value=Math.abs(Number(item && item.value)||0);
    if(value<=0) return;
    const rawLabel=item && (item.key||item.label);
    const meta=categoryMeta(rawLabel,fallback);
    const safeKey=normalizeCategoryKey(meta.key||meta.label);
    const normalizedLabel=genericLabels.has(safeKey)?categoryMeta(fallback,fallback).label:meta.label;
    const key=item && item.key ? normalizeCategoryKey(item.key) : meta.key;
    if(!grouped[key]) grouped[key]={label:normalizedLabel,value:0};
    grouped[key].value += value;
  });
  const total=Object.values(grouped).reduce((sum,item)=>sum+item.value,0);
  return Object.values(grouped)
    .sort((a,b)=>b.value-a.value)
    .map((item,index)=>Object.assign(item,{color:colors[index%colors.length],pct:total?Math.round((item.value/total)*100):0,rank:index+1}));
}

function compressBreakdown(data,maxItems,label){
  const items=Array.isArray(data)?data.slice():[];
  if(items.length<=maxItems) return items;
  const head=items.slice(0,maxItems-1);
  const tail=items.slice(maxItems-1);
  const othersValue=tail.reduce((sum,item)=>sum+(Number(item.value)||0),0);
  if(othersValue>0){
    head.push({label:label||'Outros',value:othersValue,color:'#74878a',pct:0,rank:maxItems});
  }
  const total=head.reduce((sum,item)=>sum+(Number(item.value)||0),0);
  return head.map((item,index)=>Object.assign({},item,{pct:total?Math.round(((Number(item.value)||0)/total)*100):0,rank:index+1}));
}

function canvasViewport(canvas,minSize){
  if(!canvas||!canvas.getContext) return null;
  const rect=canvas.getBoundingClientRect();
  const displayWidth=Math.max(minSize||220,Math.round(rect.width||canvas.clientWidth||canvas.width||minSize||220));
  const displayHeight=Math.max(minSize||220,Math.round(rect.height||canvas.clientHeight||canvas.height||minSize||220));
  const dpr=Math.max(1,Math.min(2,window.devicePixelRatio||1));
  const renderWidth=Math.round(displayWidth*dpr);
  const renderHeight=Math.round(displayHeight*dpr);
  if(canvas.width!==renderWidth||canvas.height!==renderHeight){
    canvas.width=renderWidth;
    canvas.height=renderHeight;
  }
  const ctx=canvas.getContext('2d');
  ctx.setTransform(dpr,0,0,dpr,0,0);
  ctx.clearRect(0,0,displayWidth,displayHeight);
  return {ctx,w:displayWidth,h:displayHeight};
}


function generateCurveSVG(points, width, height, strokeColor, fillGradientId) {
  if (!points || points.length === 0) return { svg: '', coords: [] };
  const pData = points.length === 1 ? [points[0], points[0]] : points;
  const max = Math.max(...pData) || 1;
  const min = Math.min(...pData);
  const padTop = 15, padBot = 15;
  const innerW = width;
  const innerH = height - padTop - padBot;
  
  const coords = pData.map((val, i) => {
    const x = (i / (pData.length - 1)) * innerW;
    const y = padTop + innerH - (val / max) * innerH;
    return { x, y, val };
  });
  
  let d = `M ${coords[0].x},${coords[0].y}`;
  for (let i = 0; i < coords.length - 1; i++) {
    const cp1x = coords[i].x + (coords[i+1].x - coords[i].x) / 2;
    const cp2x = cp1x;
    d += ` C ${cp1x},${coords[i].y} ${cp2x},${coords[i+1].y} ${coords[i+1].x},${coords[i+1].y}`;
  }
  
  const areaD = `${d} L ${width},${height} L 0,${height} Z`;
  const pathLength = width * 2;
  
  const svg = `
    <svg class="ft-chart-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
      <defs>
        <linearGradient id="${fillGradientId}" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="${strokeColor}" stop-opacity="0.4" />
          <stop offset="100%" stop-color="${strokeColor}" stop-opacity="0.0" />
        </linearGradient>
        <filter id="glow-${fillGradientId}" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      </defs>
      <path d="${areaD}" fill="url(#${fillGradientId})" />
      <path d="${d}" fill="none" stroke="${strokeColor}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" filter="url(#glow-${fillGradientId})" style="stroke-dasharray: ${pathLength}; stroke-dashoffset: ${pathLength}; animation: svgDraw 1.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;" />
    </svg>
  `;
  return { svg, coords };
}

function attachChartInteraction(containerId, coords, labels) {
  const container = document.getElementById(containerId);
  if(!container) return;
  const touchArea = container.querySelector('.ft-chart-touch');
  const tooltip = container.querySelector('.ft-chart-tooltip');
  const point = container.querySelector('.ft-chart-point');
  if(!touchArea || !tooltip || !point) return;
  
  const update = (e) => {
    const rect = touchArea.getBoundingClientRect();
    const x = (e.touches ? e.touches[0].clientX : e.clientX) - rect.left;
    let closest = coords[0], minDist = Infinity, bestIdx = 0;
    coords.forEach((c, i) => {
      const dist = Math.abs((c.x / 100 * rect.width) - x);
      if(dist < minDist) { minDist = dist; closest = c; bestIdx = i; }
    });
    const px = (closest.x / 100) * rect.width;
    const py = (closest.y / 100) * rect.height;
    point.style.transform = `translate(-50%, -50%) translate(${px}px, ${py}px)`;
    point.style.opacity = '1';
    point.style.boxShadow = `0 0 12px ${point.dataset.color}`;
    tooltip.innerHTML = `<span>${labels[bestIdx]}</span><br/><strong>${money(closest.val)}</strong>`;
    tooltip.style.left = `${px}px`;
    tooltip.style.top = `${py}px`;
    tooltip.style.opacity = '1';
  };
  
  const leave = () => { point.style.opacity = '0'; tooltip.style.opacity = '0'; };
  
  touchArea.addEventListener('mousemove', update);
  touchArea.addEventListener('touchmove', (e)=>{ e.preventDefault(); update(e); }, {passive:false});
  touchArea.addEventListener('mouseleave', leave);
  touchArea.addEventListener('touchend', leave);
}

function drawDoughnutChart(canvas,data){
  const viewport=canvasViewport(canvas,260);
  if(!viewport) return;
  const ctx=viewport.ctx;
  const w=viewport.w,h=viewport.h,cx=w/2,cy=h/2;
  const radius=Math.min(w,h)*0.34;
  const thickness=Math.max(18,Math.min(w,h)*0.14);
  const total=data.reduce((sum,item)=>sum+item.value,0);
  let start=-Math.PI/2;
  const gap=0.03;

  ctx.beginPath();
  ctx.arc(cx,cy,radius,0,Math.PI*2);
  ctx.strokeStyle='rgba(255,255,255,.08)';
  ctx.lineWidth=thickness;
  ctx.lineCap='round';
  ctx.stroke();

  data.forEach(item=>{
    const angle=total?(item.value/total)*(Math.PI*2-gap*data.length):0;
    const segmentStart=start+(gap/2);
    const end=segmentStart+angle;
    ctx.beginPath();
    ctx.arc(cx,cy,radius,segmentStart,end);
    ctx.strokeStyle=item.color;
    ctx.lineWidth=thickness;
    ctx.lineCap='round';
    ctx.shadowBlur=12;
    ctx.shadowColor=item.color;
    ctx.stroke();
    start=end+(gap/2);
  });
  ctx.shadowBlur=0;

  const innerRadius=Math.max(0,radius-(thickness/2)-12);
  ctx.beginPath();
  ctx.arc(cx,cy,innerRadius,0,Math.PI*2);
  ctx.fillStyle='rgba(6,10,8,.94)';
  ctx.fill();
  ctx.beginPath();
  ctx.arc(cx,cy,radius+(thickness/2)+8,0,Math.PI*2);
  ctx.strokeStyle='rgba(255,255,255,.05)';
  ctx.lineWidth=1;
  ctx.stroke();
}

function drawAccountHudChart(canvas,data){
  const viewport=canvasViewport(canvas,260);
  if(!viewport) return;
  const ctx=viewport.ctx;
  const w=viewport.w,h=viewport.h,cx=w/2,cy=h/2;
  const outer=Math.min(w,h)*0.345;
  const thickness=Math.max(18,Math.min(w,h)*0.15);
  const core=Math.max(0,outer-(thickness/2)-18);
  const total=data.reduce((sum,item)=>sum+item.value,0);
  let start=-Math.PI/2;
  const gap=0.032;

  const bg=ctx.createRadialGradient(cx,cy,12,cx,cy,outer+22);
  bg.addColorStop(0,'rgba(58,214,255,.1)');
  bg.addColorStop(.42,'rgba(20,38,64,.12)');
  bg.addColorStop(1,'rgba(7,11,18,0)');
  ctx.fillStyle=bg;
  ctx.fillRect(0,0,w,h);

  ctx.strokeStyle='rgba(95,176,214,.1)';
  ctx.lineWidth=1;
  [outer+14,outer*0.84,outer*0.63].forEach(radius=>{
    ctx.beginPath();
    ctx.arc(cx,cy,radius,0,Math.PI*2);
    ctx.stroke();
  });

  ctx.beginPath();
  ctx.arc(cx,cy,outer,0,Math.PI*2);
  ctx.strokeStyle='rgba(120,228,255,.08)';
  ctx.lineWidth=thickness;
  ctx.lineCap='round';
  ctx.stroke();

  data.forEach(item=>{
    const angle=total?(item.value/total)*(Math.PI*2-gap*data.length):0;
    const segmentStart=start+(gap/2);
    const segmentEnd=segmentStart+angle;
    if(segmentEnd>segmentStart+0.01){
      ctx.beginPath();
      ctx.arc(cx,cy,outer,segmentStart,segmentEnd);
      ctx.strokeStyle=item.color;
      ctx.lineWidth=thickness;
      ctx.lineCap='round';
      ctx.shadowBlur=14;
      ctx.shadowColor=item.color;
      ctx.stroke();
    }
    start=segmentEnd+(gap/2);
  });

  ctx.shadowBlur=0;
  const coreGlow=ctx.createRadialGradient(cx,cy,6,cx,cy,core+12);
  coreGlow.addColorStop(0,'rgba(125,243,255,.18)');
  coreGlow.addColorStop(.6,'rgba(16,28,48,.94)');
  coreGlow.addColorStop(1,'rgba(6,10,18,.98)');
  ctx.beginPath();
  ctx.arc(cx,cy,core,0,Math.PI*2);
  ctx.fillStyle=coreGlow;
  ctx.fill();

  ctx.beginPath();
  ctx.arc(cx,cy,core+8,0,Math.PI*2);
  ctx.strokeStyle='rgba(136,232,255,.18)';
  ctx.lineWidth=1;
  ctx.stroke();

  ctx.beginPath();
  ctx.arc(cx,cy,core-14,0,Math.PI*2);
  ctx.strokeStyle='rgba(136,232,255,.1)';
  ctx.stroke();
}

function clearCanvas(canvas){
  const viewport=canvasViewport(canvas,220);
  if(!viewport) return;
  viewport.ctx.clearRect(0,0,viewport.w,viewport.h);
}

function last7DayKeys(){
  const out=[]; const d=new Date(); d.setHours(0,0,0,0);
  for(let i=6;i>=0;i--){ const n=new Date(d); n.setDate(d.getDate()-i); out.push(dateKey(n)); }
  return out;
}

function dailyNetConta(dayKey){
  return (st.tx||[])
    .filter(t=>t.account==='conta'&&dateKey(t.at)===dayKey)
    .reduce((sum,t)=>{
      if(t.type==='set') return sum+((Number(t.value)||0)-(Number(t.prev)||0));
      return sum+(t.type==='in'?(Number(t.value)||0):-(Number(t.value)||0));
    },0);
}

function dailyCardSpend(dayKey){
  return (st.credit.tx||[])
    .filter(t=>t.type==='expense'&&dateKey(t.at)===dayKey)
    .reduce((sum,t)=>sum+(Number(t.value)||0),0);
}

function pruneDailyStats(maxDays){
  const cutoff=lastDaysStart(maxDays);
  const keep={};
  Object.entries(st.dailyStats||{}).forEach(([k,v])=>{ if(parse(k)>=cutoff) keep[k]=v; });
  st.dailyStats=keep;
}

// Funções de rotina/hábitos
function toggleHabit(habitId){
  const h=st.habits.find(x=>x.id===habitId); if(!h) return;
  h.done=!h.done; st.xp=Math.max(0,st.xp+(h.done?XP_H:-XP_H));
  if(h.done){
    h.lastDoneAt=new Date().toISOString();
    h.skillTag=detectSkill(h.name)||'';
    adjustSkillXp(h.skillTag,25);
    pushRoutineLog('done',h);
    haptic('success');
    showToast('✓ Hábito cumprido! +'+XP_H+' XP','ok');
    const allDone=st.habits.length>0 && st.habits.every(x=>x.done);
    if(allDone){
      triggerConfetti();
      showToast('🎉 Parabéns! 100% da rotina diária concluída!','ok');
    }
  } else {
    adjustSkillXp(h.skillTag||detectSkill(h.name),-25);
    h.skillTag='';
    pushRoutineLog('undo',h);
    haptic('light');
  }
  save(true); renderHabits(); refreshGame();
}

function renderHabits(){
  const emptyHtml='<p class="empty" style="padding:12px;">Nenhum hábito ainda. Adicione o primeiro para começar hoje!</p>';
  if(!st.habits.length){
    if(el.hList) el.hList.innerHTML=emptyHtml;
    if(el.homeHabitList) el.homeHabitList.innerHTML='<p class="empty" style="padding:14px;">Nenhuma missão ativa para hoje. Clique em "+ Novo Hábito" para começar!</p>';
    renderFocusHabitOptions(); renderFocusSession(); renderRoutineTimeline(); return;
  }
  if(el.hList){
    el.hList.innerHTML=st.habits.map(h=>`
      <article class="habit ${h.done?'done':''}" data-id="${h.id}">
        <div class="r1">
          <input data-f="name" type="text" value="${esc(h.name)}" placeholder="Nome do hábito" />
          <button class="ck ${h.done?'done':''}" type="button" data-act="toggle">${h.done?'✓':'○'}</button>
        </div>
        <div class="two">
          <input data-f="goal" type="text" value="${esc(h.goal||'')}" placeholder="Meta (min, quantidade...)" />
          <input data-f="date" type="date" value="${h.date||today()}" />
        </div>
        <div class="line">
          <span class="mut">${h.done?'Concluído':'Pendente'}${h.lastDoneAt?` · Última: ${shortDate(h.lastDoneAt)}`:''}${h.date?` · Data: ${dateBr(h.date)}`:''}</span>
          <button class="danger" type="button" data-act="del">Remover</button>
        </div>
      </article>`).join('');
  }
  if(el.homeHabitList){
    el.homeHabitList.innerHTML=st.habits.map(h=>`
      <div class="habit ${h.done?'done':''}" data-id="${h.id}" style="display:flex;justify-content:space-between;align-items:center;padding:10px 12px;border-radius:12px;background:rgba(255,255,255,.02);border:1px solid var(--ln);">
        <div style="display:grid;gap:2px;min-width:0;">
          <strong style="font-size:.9rem;${h.done?'text-decoration:line-through;color:var(--mut);':''}">${safe(h.name)}</strong>
          <span class="mut" style="font-size:.73rem;">${h.goal?safe(h.goal):'Sem meta definida'}${h.done?' · ✓ Cumprido':' · Pendente'}</span>
        </div>
        <button class="ck ${h.done?'done':''}" type="button" data-act="toggle" style="width:36px;height:36px;border-radius:10px;font-size:1.1rem;flex-shrink:0;">${h.done?'✓':'○'}</button>
      </div>
    `).join('');
  }
  renderFocusHabitOptions();
  renderFocusSession();
  renderRoutineTimeline();
}

function renderRoutineTimeline(){
  el.routineDateInfo.textContent=`Hoje: ${fullDate(new Date())} · cada hábito pode ser registrado com a própria data.`;
  const start=lastDaysStart(5);
  const logs=(st.routineLog||[]).filter(r=>new Date(r.at)>=start).sort((a,b)=>new Date(b.at)-new Date(a.at)).slice(0,16);
  if(!logs.length){el.routineLog.innerHTML='<p class="empty">Sem eventos de rotina nos últimos 5 dias.</p>';return;}
  el.routineLog.innerHTML=logs.map(r=>{
    const action=r.action==='done'?'Concluiu':r.action==='undo'?'Desmarcou':r.action==='add'?'Criou':'Removeu';
    return `<p class="h"><span>${action}: ${safe(r.habit||'Hábito')}</span><span>${shortDate(r.at)}</span></p>`;
  }).join('');
}

function pushRoutineLog(action,habit){
  st.routineLog=Array.isArray(st.routineLog)?st.routineLog:[];
  st.routineLog.unshift({id:id(),action,habit:txt(habit && habit.name ? habit.name : 'Hábito',60),at:new Date().toISOString()});
  st.routineLog=st.routineLog.slice(0,240);
}

function refreshGame(){
  const total=st.habits.length, done=st.habits.filter(h=>h.done).length, p=total?Math.round(done/total*100):0;
  st.dailyStats=st.dailyStats||{};
  st.dailyStats[today()]={done,total,percent:p};
  pruneDailyStats(90);
  streakByDay(total,done); motivation(p,done,total); renderSummary(); renderAchievements();
}

// Funções de atualização de XP, nível e streak
function streakByDay(total,done){
  if(total>0&&done===total&&!st.routineDone){st.routineDone=true;st.streak+=1;}
  if(done<total&&st.routineDone){st.routineDone=false;st.streak=Math.max(0,st.streak-1);}
  save();
}
function motivation(p,done,total){
  const msg=total===0?'Seu sistema começa com o primeiro hábito. Crie sua base.':p===100?'Você cumpriu tudo. Isso é disciplina weedverso.':p>=75?'Falta pouco. Termine forte e mantenha o streak.':p>=45?'Bom ritmo. A consistência está aparecendo.':done>0?'Você já iniciou. Continue e acelere sua evolução.':'Você está construindo sua melhor versão.';
  el.mot.textContent=msg;
}
// Funções de finanças/saldos
function renderFinance(){
  el.fGrid.innerHTML=Object.entries(st.balances).map(([k,a])=>{
    const editing=Boolean(ui.balances[k]);
    return `<article class="fcard" data-acc="${k}">
      <div class="line">
        <div>
          <span class="mini">${k==='conta'?'Conta principal':'Saldo disponível'}</span>
          <strong>${safe(a.label)}</strong>
        </div>
        <button type="button" class="iconBtn ${editing?'active':''}" data-act="edit-meta" title="Editar ${esc(a.label)}">✎</button>
      </div>
      ${editing?`<input data-f="label" type="text" maxlength="26" value="${esc(a.label)}" placeholder="Nome da carteira" />`:''}
      <div data-bal class="bal">${money(a.amount)}</div>
      <div class="actionLayout">
        <div class="actionFields">
          <div class="two">
            <input data-v type="number" step="0.01" inputmode="decimal" placeholder="Valor" />
            <input data-note type="text" maxlength="42" placeholder="Categoria ou descrição" />
          </div>
        </div>
        <div class="actionStack">
          <button type="button" class="btn" data-act="in">+ Entrada</button>
          <button type="button" class="danger" data-act="out">- Saída</button>
          ${editing?`<button type="button" class="ghost" data-act="set">Definir saldo</button>`:''}
        </div>
      </div>
    </article>`;
  }).join('');
  renderHistory();
  renderFoodStatement();
  renderAccountFlowChart();
}

function move(acc,type,value,note){
  if(!st.balances[acc]) return;
  st.balances[acc].amount += type==='in'?value:-value;
  const meta=categoryMeta(note,'Sem categoria');
  st.tx.unshift({id:id(),account:acc,type,value,note:txt(note,42),category:meta.label,categoryKey:meta.key,at:new Date().toISOString()});
  haptic('medium');
  save(true); renderFinance(); renderSummary(); flash(document.querySelector(`[data-acc="${acc}"] [data-bal]`),type);
}

function renderHistory(){
  const editing=Boolean(ui.statement.wallet);
  const banner=editing?renderStatementModeBanner('Modo edição ativo na conta principal. Use o lápis para alterar a transação e o X para remover.'):'';
  const items=sortTransactionsDesc((st.tx||[]).filter(t=>t.account==='conta')).slice(0,12);
  if(!items.length){el.hist.innerHTML=`${banner}<p class="empty">Sem movimentações na conta principal ainda.</p>`;return;}
  el.hist.innerHTML=banner+items.map(t=>{
    const name=(st.balances[t.account] && st.balances[t.account].label) ? st.balances[t.account].label : defLabel(t.account), d=shortDate(t.at);
    const isEditing=isStatementEditorActive('wallet','wallet',t.id,'');
    if(t.type==='set'){
      const note=t.note?` · ${safe(t.note)}`:'';
      return renderStatementRow({
        section:'wallet',
        primaryHtml:`Ajuste em ${safe(name)}`,
        secondaryHtml:`${money(t.prev)} → ${money(t.value)}${note}`,
        meta:d,
        editable:editing,
        isEditing:isEditing,
        editorHtml:isEditing?renderStatementEditor({section:'wallet',source:'wallet',txId:t.id,goalId:''}):'',
        txId:t.id,
        source:'wallet'
      });
    }
    const s=t.type==='in'?'+':'-',c=t.type==='in'?'pos':'neg';
    const note=t.note?` · ${safe(t.note)}`:'';
    return renderStatementRow({
      section:'wallet',
      primaryHtml:`<span class="${c}">${s} ${money(t.value)}</span> em ${safe(name)}${note}`,
      secondaryHtml:safe(t.category||'Sem categoria'),
      meta:d,
      editable:editing,
      isEditing:isEditing,
      editorHtml:isEditing?renderStatementEditor({section:'wallet',source:'wallet',txId:t.id,goalId:''}):'',
      txId:t.id,
      source:'wallet'
    });
  }).join('');
}

function renderFoodStatement(){
  const editing=Boolean(ui.statement.food);
  const banner=editing?renderStatementModeBanner('Modo edição ativo nos cartões alimentação. Você pode ajustar VA Mercado e VA Refeição por aqui.'):'';
  const items=sortTransactionsDesc((st.tx||[]).filter(t=>t.account==='vale1'||t.account==='vale2')).slice(0,18);
  if(!el.foodStmt) return;
  if(!items.length){el.foodStmt.innerHTML=`${banner}<p class="empty">Sem movimentações nos cartões alimentação ainda.</p>`;return;}
  el.foodStmt.innerHTML=banner+items.map(t=>{
    const name=(st.balances[t.account] && st.balances[t.account].label) ? st.balances[t.account].label : defLabel(t.account), d=shortDate(t.at), monthTag=monthLabel(t.at);
    const isEditing=isStatementEditorActive('food','wallet',t.id,'');
    if(t.type==='set'){
      const note=t.note?` · ${safe(t.note)}`:'';
      return renderStatementRow({
        section:'food',
        primaryHtml:`Ajuste em ${safe(name)}`,
        secondaryHtml:`${money(t.prev)} → ${money(t.value)}${note} · ${safe(monthTag)}`,
        meta:d,
        editable:editing,
        isEditing:isEditing,
        editorHtml:isEditing?renderStatementEditor({section:'food',source:'wallet',txId:t.id,goalId:''}):'',
        txId:t.id,
        source:'wallet'
      });
    }
    const s=t.type==='in'?'+':'-',c=t.type==='in'?'pos':'neg';
    const note=t.note?` · ${safe(t.note)}`:'';
    return renderStatementRow({
      section:'food',
      primaryHtml:`<span class="${c}">${s} ${money(t.value)}</span> em ${safe(name)}${note}`,
      secondaryHtml:`${safe(t.category||'Sem categoria')} · ${safe(monthTag)}`,
      meta:d,
      editable:editing,
      isEditing:isEditing,
      editorHtml:isEditing?renderStatementEditor({section:'food',source:'wallet',txId:t.id,goalId:''}):'',
      txId:t.id,
      source:'wallet'
    });
  }).join('');
}

function shortTime(iso){
  try{
    const d=new Date(iso);
    return isNaN(d)?'':`${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
  }catch(e){return '';}
}

function allTransactions(){
  const account=(st.tx||[]).map(t=>{
    const labelName=(st.balances[t.account] && st.balances[t.account].label) ? st.balances[t.account].label : defLabel(t.account);
    const isIn=t.type==='in';
    const isSet=t.type==='set';
    const diff=(Number(t.value)||0)-(Number(t.prev)||0);
    const val=isSet?Math.abs(diff):Math.abs(Number(t.value)||0);
    const sign=isSet?(diff>=0?'+':'-'):(isIn?'+':'-');
    const isFood=t.account==='vale1'||t.account==='vale2';
    return {
      id:t.id,at:t.at,value:val,sign,cls:sign==='+'?'pos':'neg',
      title:isSet?`Ajuste ${labelName}`:`${isIn?'Entrada':'Saída'} ${labelName}`,
      note:t.note||'',category:t.category||'Sem categoria',
      source:isFood?'food':'wallet',
      icon:isFood?'🍽️':'💰'
    };
  });

  const card=(st.credit.tx||[]).map(t=>{
    const isExpense=t.type==='expense';
    const isPayment=t.type==='payment';
    const isReserveIn=t.type==='reserve-in';
    const isReserveOut=t.type==='reserve-out';
    const sign=(isExpense||isReserveOut)?'-':'+';
    const label=isExpense?'Gasto no Cartão':(isPayment?'Pagamento Cartão':(isReserveIn?'Entrada Reserva Cartão':'Saída Reserva Cartão'));
    return {
      id:t.id,at:t.at,value:Math.abs(Number(t.value)||0),sign,cls:sign==='+'?'pos':'neg',
      title:label,note:t.desc||'',category:t.category||'Crédito',
      source:'credit',
      icon:isExpense?'💳':(isPayment?'💵':'🛡️')
    };
  });

  const goals=(st.goals||[]).reduce((acc,g)=>{
    const gtx=(Array.isArray(g.tx)?g.tx:[]).map(t=>{
      const isWithdraw=t.type==='withdraw';
      const label=t.type==='yield'?'Rendimento':(isWithdraw?'Resgate':'Aporte');
      return {
        id:t.id,at:t.at,value:Math.abs(Number(t.value)||0),sign:isWithdraw?'-':'+',cls:isWithdraw?'neg':'pos',
        title:`${label} · ${g.name||'Meta'}`,note:t.note||'',category:'Objetivos',
        source:'goal',
        icon:'🎯'
      };
    });
    return acc.concat(gtx);
  },[]);

  return account.concat(card).concat(goals).sort((a,b)=>new Date(b.at)-new Date(a.at));
}

function renderUnifiedStatement(){
  if(!el.unifiedStatementFeed) return;
  let items=allTransactions();

  if(ui.statementFilter && ui.statementFilter!=='all'){
    items=items.filter(i=>i.source===ui.statementFilter);
  }

  if(ui.statementSearch && ui.statementSearch.trim()){
    const q=ui.statementSearch.trim().toLowerCase();
    items=items.filter(i=>{
      return (i.title||'').toLowerCase().includes(q) ||
             (i.note||'').toLowerCase().includes(q) ||
             (i.category||'').toLowerCase().includes(q) ||
             String(i.value).includes(q);
    });
  }

  if(!items.length){
    el.unifiedStatementFeed.innerHTML='<p class="empty" style="padding:16px;">Nenhuma movimentação encontrada com os filtros atuais.</p>';
    return;
  }

  let html='';
  let lastDay='';
  const todayStr=today();

  items.slice(0,60).forEach(i=>{
    const day=(i.at||'').slice(0,10);
    if(day && day!==lastDay){
      lastDay=day;
      let dayTitle=dateBr(day);
      if(day===todayStr) dayTitle='Hoje';
      html+=`<div class="statementDateHeader">${dayTitle}</div>`;
    }
    const noteText=i.note?` · ${safe(i.note)}`:'';
    html+=`
      <div class="feedRow">
        <div class="feedIcon">${i.icon}</div>
        <div class="feedBody">
          <div class="feedTitle">${safe(i.title)}${noteText}</div>
          <div class="feedSubtitle">${safe(i.category)} · ${shortTime(i.at)}</div>
        </div>
        <div class="feedAmount ${i.cls}">${i.sign} ${money(i.value)}</div>
      </div>
    `;
  });

  el.unifiedStatementFeed.innerHTML=html;
}

function copyStatementSummary(){
  const items=allTransactions().slice(0,35);
  if(!items.length){ showToast('Não há movimentações para copiar.','warn'); return; }
  let text=`📊 RESUMO DE MOVIMENTAÇÕES - WEEDVERSO\nGerado em: ${fullDate(new Date())}\n\n`;
  items.forEach(i=>{
    text+=`${i.sign} ${money(i.value)} | ${i.title}${i.note?' ('+i.note+')':''} [${shortDate(i.at)}]\n`;
  });
  if(navigator.clipboard && navigator.clipboard.writeText){
    navigator.clipboard.writeText(text).then(()=>{
      haptic('success');
      showToast('✓ Resumo copiado para a área de transferência!','ok');
    }).catch(()=>{
      showToast('Não foi possível acessar a área de transferência.','error');
    });
  } else {
    showToast('Área de transferência indisponível.','warn');
  }
}

function renderFiveDayStatement(){
  const editing=Boolean(ui.statement.five);
  const items=last5DaysTransactions();
  const banner=editing?renderStatementModeBanner('Modo edição ativo no consolidado. Você pode ajustar conta principal, cartões alimentação e cartão de crédito.'):'';
  if(!items.length){el.last5Stmt.innerHTML=`${banner}<p class="empty">Sem entradas/saídas da conta principal, alimentação e cartão nos últimos 5 dias.</p>`;return;}
  el.last5Stmt.innerHTML=banner+items.map(i=>{
    const note=i.note?` · ${safe(i.note)}`:'';
    const isEditing=isStatementEditorActive('five',i.source,i.txId,i.goalId||'');
    return renderStatementRow({
      section:'five',
      primaryHtml:`<span class="${i.cls}">${i.sign} ${money(i.value)}</span> ${safe(i.label)}${note}`,
      secondaryHtml:safe(i.category||''),
      meta:shortDate(i.at),
      editable:editing,
      isEditing:isEditing,
      editorHtml:isEditing?renderStatementEditor({section:'five',source:i.source,txId:i.txId,goalId:i.goalId||''}):'',
      txId:i.txId,
      source:i.source,
      goalId:i.goalId
    });
  }).join('');
}

function last5DaysTransactions(){
  const start=lastDaysStart(5);
  const account=(st.tx||[])
    .filter(t=>['conta','vale1','vale2'].includes(t.account)&&new Date(t.at)>=start)
    .map(t=>{
      const labelName=(st.balances[t.account] && st.balances[t.account].label) ? st.balances[t.account].label : defLabel(t.account);
      if(t.type==='set'){
        const diff=(Number(t.value)||0)-(Number(t.prev)||0);
        return {at:t.at,value:Math.abs(diff),sign:diff>=0?'+':'-',cls:diff>=0?'pos':'neg',label:`Ajuste ${labelName}`,note:t.note||'',category:t.category||'Ajuste manual',source:'wallet',txId:t.id};
      }
      const isIn=t.type==='in';
      return {at:t.at,value:Math.abs(Number(t.value)||0),sign:isIn?'+':'-',cls:isIn?'pos':'neg',label:`${isIn?'Entrada':'Saída'} ${labelName}`,note:t.note||'',category:t.category||'Sem categoria',source:'wallet',txId:t.id};
    });

  const card=(st.credit.tx||[])
    .filter(t=>new Date(t.at)>=start)
    .map(t=>{
      const isExpense=t.type==='expense';
      const isPayment=t.type==='payment';
      const isReserveIn=t.type==='reserve-in';
      return {
        at:t.at,
        value:Math.abs(Number(t.value)||0),
        sign:(isExpense||t.type==='reserve-out')?'-':'+',
        cls:(isExpense||t.type==='reserve-out')?'neg':'pos',
        label:isExpense?'Gasto cartão crédito':(isPayment?'Pagamento cartão crédito':(isReserveIn?'Entrada reserva cartão':'Saída reserva cartão')),
        note:t.desc||'',
        category:t.category||'Sem categoria',
        source:'credit',
        txId:t.id
      };
    });

  return account.concat(card).sort((a,b)=>new Date(b.at)-new Date(a.at)).slice(0,40);
}

function renderCredit(){
  const editing=Boolean(ui.statement.credit);
  el.ccName.value=st.credit.name||'Cartão weedverso';
  const used=Math.max(0,Number(st.credit.used)||0), reserved=Math.max(0,Number(st.credit.reserved)||0), uncovered=Math.max(0,used-reserved), pct=used>0?Math.min(100,Math.round((reserved/used)*100)):(reserved>0?100:0);
  el.ccMeta.hidden=!ui.credit;
  setActive(el.ccEditBtn, ui.credit);
  if(el.ccMetaSummary) el.ccMetaSummary.textContent=`${st.credit.name||'Cartão weedverso'}`;
  if(el.ccMetaHint) el.ccMetaHint.textContent=ui.credit?'Edição do cartão ativa.':creditReserveStatus(used,reserved);
  if(el.ccUsed){
    el.ccUsed.textContent=money(used);
    el.ccUsed.style.color=used>reserved&&used>0?'#ffcf5f':'#ffffff';
  }
  if(el.ccUncovered) el.ccUncovered.textContent=money(uncovered);
  if(el.ccReserved) el.ccReserved.textContent=money(reserved);
  if(el.ccUncovered) el.ccUncovered.style.color=uncovered>0?'#ffcf5f':'var(--p)';
  if(el.ccBar) el.ccBar.style.width=`${pct}%`;

  // Atualiza dados no Cartão Virtual
  if(el.ccCardUsed && el.ccCardUsed !== el.ccUsed) el.ccCardUsed.textContent=money(used);
  if(el.ccCardReserved && el.ccCardReserved !== el.ccReserved) el.ccCardReserved.textContent=money(reserved);
  if(el.ccCardName) el.ccCardName.textContent=st.credit.name||'weedverso Black';
  if(el.ccCardCoverageStatus){
    if(used>0 && uncovered<=0){
      el.ccCardCoverageStatus.className='virtualCardStatus ok';
      el.ccCardCoverageStatus.textContent='🛡️ 100% Coberta';
    } else if(uncovered>0){
      el.ccCardCoverageStatus.className='virtualCardStatus warn';
      el.ccCardCoverageStatus.textContent=`⚠️ Falta ${money(uncovered)}`;
    } else {
      el.ccCardCoverageStatus.className='virtualCardStatus ok';
      el.ccCardCoverageStatus.textContent='✓ Zerado';
    }
  }

  renderCreditDescChart();

  const banner=editing?renderStatementModeBanner('Modo edição ativo no cartão. Ajuste o lançamento com o lápis ou remova com o X.'):'';
  const items=sortTransactionsDesc(st.credit.tx).slice(0,8);
  if(!items.length){el.ccHistory.innerHTML=`${banner}<p class="empty">Sem lançamentos no cartão.</p>`;return;}
  el.ccHistory.innerHTML=banner+items.map(t=>{
    const map={
      expense:{sign:'-',cls:'neg',kind:'Gasto'},
      payment:{sign:'+',cls:'pos',kind:'Pagamento'},
      'reserve-in':{sign:'+',cls:'pos',kind:'Reserva cartão'},
      'reserve-out':{sign:'-',cls:'neg',kind:'Saída da reserva'}
    };
    const isEditing=isStatementEditorActive('credit','credit',t.id,'');
    const kindData=map[t.type]||map.payment, desc=t.desc?` · ${safe(t.desc)}`:'', monthTag=monthLabel(t.at);
    return renderStatementRow({
      section:'credit',
      primaryHtml:`<span class="${kindData.cls}">${kindData.sign} ${money(t.value)}</span> ${kindData.kind}${desc}`,
      secondaryHtml:`${safe(t.category||'Sem categoria')} · ${safe(monthTag)}`,
      meta:shortDate(t.at),
      editable:editing,
      isEditing:isEditing,
      editorHtml:isEditing?renderStatementEditor({section:'credit',source:'credit',txId:t.id,goalId:''}):'',
      txId:t.id,
      source:'credit'
    });
  }).join('');
}

function creditMove(type){
  const raw=parseFloat((el.ccValue.value||'').replace(',','.')), v=Number.isFinite(raw)?Math.abs(raw):0;
  const desc=txt(el.ccDesc.value,42);
  if(v<=0) return;
  if(type==='expense') st.credit.used += v;
  else st.credit.used=Math.max(0,st.credit.used-v);
  const meta=categoryMeta(desc,type==='expense'?'Sem categoria':'Pagamento cartao');
  st.credit.tx.unshift({id:id(),type,value:v,desc,category:meta.label,categoryKey:meta.key,at:new Date().toISOString()});
  haptic('medium');
  save(true); renderCredit(); renderSummary();
  el.ccValue.value=''; el.ccDesc.value='';
  showToast(type==='expense'?'✓ Gasto no cartão salvo!':'✓ Pagamento de fatura salvo!','ok');
}

function creditReserveMove(type){
  const raw=parseFloat((el.ccReserveValue.value||'').replace(',','.')), v=Number.isFinite(raw)?Math.abs(raw):0;
  if(v<=0) return;
  st.credit.reserved=Math.max(0,(Number(st.credit.reserved)||0)+(type==='in'?v:-v));
  const meta=categoryMeta('Reserva cartao','Reserva cartao');
  st.credit.tx.unshift({id:id(),type:type==='in'?'reserve-in':'reserve-out',value:v,desc:'Reserva cartão',category:meta.label,categoryKey:meta.key,at:new Date().toISOString()});
  haptic('medium');
  save(true); renderCredit(); renderSummary();
  el.ccReserveValue.value='';
  showToast(type==='in'?'✓ Reserva adicionada!':'✓ Retirada da reserva efetuada!','ok');
}

function creditReserveStatus(used,reserved){
  if(used<=0&&reserved<=0) return 'Sem fatura e sem saldo reservado no momento.';
  if(used<=0&&reserved>0) return `Reserva pronta: ${money(reserved)} disponível para a próxima fatura.`;
  const uncovered=Math.max(0,used-reserved);
  const coverage=Math.min(100,Math.round((reserved/used)*100));
  return uncovered>0?`Reserva cobre ${coverage}% da fatura. Faltam ${money(uncovered)}.`:`Reserva cobre 100% da fatura atual.`;
}

function debtInstallments(item){
  return Math.min(999,Math.max(1,parseInt((item&&item.installments)||1,10)||1));
}
function debtPaidInstallments(item){
  return Math.min(debtInstallments(item),Math.max(0,parseInt((item&&item.installmentsPaid)||0,10)||0));
}
function debtInstallmentValue(item){
  return Math.max(0,Number(item&&((item.installmentValue!=null)?item.installmentValue:item.amount))||0);
}
function roundMoneyValue(value){
  return Math.round((Number(value)||0)*100)/100;
}
function debtRemainingAmount(item){
  if(!item || item.paid) return 0;
  const inst = debtInstallments(item);
  const instVal = debtInstallmentValue(item);
  const totalDebt = roundMoneyValue(inst * instVal);
  if(Array.isArray(item.payments) && item.payments.length > 0){
    const paidSoFar = item.payments.reduce((s,p) => s + Number(p.value||0), 0);
    return roundMoneyValue(Math.max(0, totalDebt - paidSoFar));
  }
  const remaining = Math.max(0, inst - debtPaidInstallments(item));
  return roundMoneyValue(instVal * remaining);
}
function debtPaidAmount(item){
  if(!item) return 0;
  if(Array.isArray(item.payments) && item.payments.length > 0){
    return roundMoneyValue(item.payments.reduce((s,p) => s + Number(p.value||0), 0));
  }
  return roundMoneyValue(debtInstallmentValue(item)*debtPaidInstallments(item));
}
function debtCompletionPct(item){
  const installments=debtInstallments(item);
  return Math.min(100,Math.round((debtPaidInstallments(item)/installments)*100));
}
function myDebtPortfolioTotal(){
  return (st.myDebts||[]).reduce((sum,item)=>sum+debtRemainingAmount(item),0);
}
function myDebtMonthlyTotal(){
  return (st.myDebts||[]).reduce((sum,item)=>{
    if(item && !item.paid){
      return sum + debtInstallmentValue(item);
    }
    return sum;
  },0);
}
function myDebtPaidTotal(){
  return (st.myDebts||[]).reduce((sum,item)=>sum+debtPaidAmount(item),0);
}

function sortDebtEntries(items){
  return (items||[]).slice().sort((a,b)=>{
    if(shouldShowDebtorNow(a)!==shouldShowDebtorNow(b)) return shouldShowDebtorNow(a)?-1:1;
    const monthDiff=compareDebtorMonth(a,b);
    if(monthDiff!==0) return monthDiff;
    if(Number(a.paid)!==Number(b.paid)) return Number(a.paid)-Number(b.paid);
    return new Date(b.at||0)-new Date(a.at||0);
  });
}
function sortMyDebtEntries(items){
  return (items||[]).slice().sort((a,b)=>{
    const dateA=String(a.payDate||'9999-12-31');
    const dateB=String(b.payDate||'9999-12-31');
    if(dateA!==dateB) return dateA<dateB?-1:1;
    return new Date(b.at||0)-new Date(a.at||0);
  });
}
function compareMonthGroupKeys(a,b,desc){
  if(a===b) return 0;
  if(a==='sem-mes') return 1;
  if(b==='sem-mes') return -1;
  return desc?(a<b?1:-1):(a>b?1:-1);
}
function groupMyDebtEntries(items,desc){
  const grouped={};
  sortMyDebtEntries(items).forEach(item=>{
    const key=monthKeyFromValue(item.payDate)||'sem-mes';
    if(!grouped[key]){
      grouped[key]={
        key,
        label:key==='sem-mes'?'Sem mês definido':monthLabelFromKey(key),
        items:[],
        remaining:0,
        paid:0
      };
    }
    grouped[key].items.push(item);
    grouped[key].remaining=roundMoneyValue(grouped[key].remaining+debtRemainingAmount(item));
    grouped[key].paid=roundMoneyValue(grouped[key].paid+debtPaidAmount(item));
  });
  return Object.values(grouped).sort((a,b)=>compareMonthGroupKeys(a.key,b.key,desc));
}
const MD_REASONS = {
  house: { label: 'Contas da Casa', icon: '🏠' },
  loan: { label: 'Empréstimo', icon: '🏦' },
  card: { label: 'Fatura / Cartão', icon: '💳' },
  service: { label: 'Serviços', icon: '📱' },
  other: { label: 'Outro', icon: '📦' }
};

function inferMyDebtReason(name){
  const n = foldText(name||'');
  if(/aluguel|luz|agua|água|energia|internet|condominio|condomínio|gas|gás|enel|sabesp|cpfl|claro|vivo|oi/.test(n)) return 'house';
  if(/emprestimo|empréstimo|banco|financiamento|consignado|parcela carro|carro|moto|veiculo|veículo|caixa/.test(n)) return 'loan';
  if(/cartao|cartão|fatura|nubank|inter|itau|itaú|bradesco|santander|amex|c6|picpay/.test(n)) return 'card';
  if(/spotify|netflix|academia|plano|celular|assinatura|curso|faculdade|escola|youtube/.test(n)) return 'service';
  return 'other';
}

function myDebtReasonKey(d){
  return (d && d.reason && MD_REASONS[d.reason]) ? d.reason : inferMyDebtReason(d && d.name);
}

function myDebtReasonIcon(d){
  const k = myDebtReasonKey(d);
  return (MD_REASONS[k] && MD_REASONS[k].icon) || '🏠';
}

function myDebtUrgencyInfo(d){
  if(d.paid) return { level: 4, tagHtml: '<span class="tag ok">✓ Quitada</span>', statusText: 'Quitada', delayDays: 0 };
  if(!d.payDate){
    return { level: 3, tagHtml: '<span class="tag" style="opacity:.7">Sem pressa</span>', statusText: 'Sem pressa', delayDays: 0 };
  }
  const todayStr = today();
  const diff = days(todayStr, d.payDate); // negative if overdue
  if(diff < 0){
    const delay = Math.abs(diff);
    let tagCls = 'dvTagDelayYellow';
    let label = `venceu há ${delay}d`;
    if(delay > 30){
      tagCls = 'dvTagDelayRed';
      label = `🔥 venceu há ${delay}d`;
    } else if(delay > 7){
      tagCls = 'dvTagDelayOrange';
      label = `venceu há ${delay}d`;
    }
    return {
      level: 1, // 🔴 Vencidas
      tagHtml: `<span class="${tagCls}">${label}</span>`,
      statusText: label,
      delayDays: delay,
      isOverdue: true
    };
  }
  if(diff <= 7){
    const label = diff === 0 ? 'vence hoje' : (diff === 1 ? 'vence amanhã' : `vence em ${diff}d`);
    return {
      level: 2, // 🟡 Esta semana
      tagHtml: `<span class="tag warn" style="background:rgba(255,207,95,.15);color:#ffd056;border-color:rgba(255,207,95,.4)">${label}</span>`,
      statusText: label,
      delayDays: 0,
      isWeek: true
    };
  }
  return {
    level: 3, // ⚪ Sem pressa
    tagHtml: `<span class="tag month" style="color:#9fb3a8">vence em ${dateBr(d.payDate)}</span>`,
    statusText: `vence em ${dateBr(d.payDate)}`,
    delayDays: 0
  };
}

function renderMyDebtSingleCard(d, isNested=false){
  const inst = debtInstallments(d);
  const paidInst = debtPaidInstallments(d);
  const instVal = debtInstallmentValue(d);
  const remaining = debtRemainingAmount(d);
  const reasonKey = myDebtReasonKey(d);
  const reasonIcon = (MD_REASONS[reasonKey] && MD_REASONS[reasonKey].icon) || '🏠';
  const urgency = myDebtUrgencyInfo(d);

  let dotsHtml = '';
  if(inst > 1){
    const maxDots = Math.min(6, inst);
    const dots = Array.from({length: maxDots}, (_, i) => {
      const isDone = i < paidInst;
      return `<span style="color:${isDone ? '#39ff8f' : 'rgba(255,255,255,.2)'}">${isDone ? '●' : '○'}</span>`;
    }).join('');
    const extraLabel = inst > 6 ? `<span style="font-size:.65rem;opacity:.55;margin-left:1px">+${inst-6}</span>` : '';
    dotsHtml = `<span class="dvDots" data-act="md-change-inst" data-mydeb="${d.id}" title="Toque para alterar parcelas (${paidInst}/${inst})" style="cursor:pointer">${dots}${extraLabel} <span style="font-size:.68rem;opacity:.8;font-weight:700">${paidInst}/${inst}</span></span>`;
  }

  return `
    <article class="dvCard ${d.paid ? 'paid' : ''}" data-mydeb="${d.id}" ${isNested ? 'style="border-color:rgba(57,255,143,.18);background:rgba(255,255,255,.02);margin-top:2px"' : ''}>
      <div class="dvCardLine1">
        <div class="dvPersonNameWrap">
          <span class="dvReasonIcon" title="${MD_REASONS[reasonKey]?MD_REASONS[reasonKey].label:''}">${reasonIcon}</span>
          <span class="dvPersonName" data-act="md-timeline" data-creditor="${esc(d.name)}" title="Ver histórico">${safe(d.name)}</span>
          ${dotsHtml}
        </div>
        <div class="dvCardAmount">${money(remaining > 0 ? remaining : (d.paid ? debtPaidAmount(d) : instVal))}</div>
      </div>
      <div class="dvCardLine2">
        <div class="dvMetaLeft">
          ${urgency.tagHtml}
          ${inst > 1 ? `<span>· parcela ${money(instVal)}</span>` : ''}
          ${d.note ? `<span>· ${safe(d.note)}</span>` : ''}
        </div>
        <div class="dvMetaRight">
          ${!d.paid ? `<button type="button" class="dvActionBtn receive" data-act="md-open-pay" data-mydeb="${d.id}">✓ Paguei</button>` : ''}
          <button type="button" class="dvActionBtn menu" data-act="md-menu" data-mydeb="${d.id}" title="Mais opções">⋯</button>
        </div>
      </div>
    </article>
  `;
}

function renderMyDebtGroupCard(creditorName, items){
  if(items.length === 1) return renderMyDebtSingleCard(items[0]);
  const totalOpen = roundMoneyValue(items.filter(d=>!d.paid).reduce((s,d)=>s+debtRemainingAmount(d), 0));
  const openCount = items.filter(d=>!d.paid).length;
  const reasonIcon = myDebtReasonIcon(items[0]);

  const anyOverdue = items.some(d=>myDebtUrgencyInfo(d).isOverdue);
  const anyWeek = items.some(d=>myDebtUrgencyInfo(d).isWeek);
  let badgeHtml = '';
  if(anyOverdue) badgeHtml = '<span class="dvTagDelayRed">🔴 Contém vencidas</span>';
  else if(anyWeek) badgeHtml = '<span class="tag warn" style="background:rgba(255,207,95,.15);color:#ffd056;border-color:rgba(255,207,95,.4)">🟡 Vence esta semana</span>';

  return `
    <details class="dvGroupCard" data-group="${esc(creditorName)}">
      <summary class="dvGroupHead">
        <div class="dvCardLine1">
          <div class="dvPersonNameWrap">
            <span class="dvReasonIcon">${reasonIcon}</span>
            <strong style="font-size:.88rem;color:var(--txt)">${safe(creditorName)}</strong>
            <span style="font-size:.7rem;color:var(--mut);background:rgba(255,255,255,.05);padding:2px 6px;border-radius:999px;margin-left:4px">${items.length} contas</span>
          </div>
          <div class="dvCardAmount">${money(totalOpen)}</div>
        </div>
        <div class="dvCardLine2">
          <div class="dvMetaLeft">
            ${badgeHtml}
            <span>${openCount} conta(s) em aberto</span>
          </div>
          <div class="dvMetaRight">
            <span style="font-size:.74rem;color:var(--p)">Ver contas ▾</span>
          </div>
        </div>
      </summary>
      <div class="dvGroupSubItems">
        ${items.map(d=>renderMyDebtSingleCard(d, true)).join('')}
      </div>
    </details>
  `;
}
function debtorInstallments(d){
  return Math.min(999,Math.max(1,parseInt(d&&d.installments||'1',10)||1));
}
function debtorPaidInstallments(d){
  return Math.max(0,parseInt(d&&d.installmentsPaid||'0',10)||0);
}
function debtorInstallmentValue(d){
  if(!d) return 0;
  const inst=debtorInstallments(d);
  const raw=Number(d.installmentValue);
  return Number.isFinite(raw)&&raw>0?raw:roundMoneyValue((Number(d.amount)||0)/inst);
}
function debtorPaidAmount(d){
  if(!d) return 0;
  if(Array.isArray(d.payments)&&d.payments.length){
    return roundMoneyValue(d.payments.reduce((s,p)=>s+Number(p.value||0),0));
  }
  if(d.paid) return roundMoneyValue(Number(d.amount)||0);
  const paid=debtorPaidInstallments(d);
  const val=debtorInstallmentValue(d);
  return roundMoneyValue(paid*val);
}
function debtorRemainingAmount(d){
  if(!d||d.paid) return 0;
  const total=roundMoneyValue(Number(d.amount)||0);
  const paid=debtorPaidAmount(d);
  return roundMoneyValue(Math.max(0,total-paid));
}

function foldText(s){
  return String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();
}

function debtorReasonIcon(reason){
  switch(reason){
    case 'card': return '💳';
    case 'loan': return '💵';
    case 'split': return '🍕';
    default: return '📦';
  }
}
function debtorReasonLabel(reason){
  switch(reason){
    case 'card': return 'Passei no cartão';
    case 'loan': return 'Emprestei';
    case 'split': return 'Racha';
    default: return 'Outro';
  }
}

function personTrustBadge(personName){
  if(!personName) return { label: 'Novo', cls: 'neutral', icon: '⚪' };
  const target = foldText(personName);
  const items = (st.debtors||[]).filter(d=>foldText(d.name)===target);
  if(!items.length) return { label: 'Novo', cls: 'neutral', icon: '⚪' };

  const todayStr = today();
  let hasSevereOverdue = false;
  let hasPaidHistory = false;

  items.forEach(d=>{
    if(!d.paid && d.payDate){
      const diff = days(todayStr, d.payDate);
      if(diff < -7){
        hasSevereOverdue = true;
      }
    }
    if(d.paid || (Array.isArray(d.payments)&&d.payments.length>0)){
      hasPaidHistory = true;
    }
  });

  if(hasSevereOverdue){
    return { label: 'Costuma atrasar', cls: 'warn', icon: '⚠️' };
  }
  if(hasPaidHistory){
    return { label: 'Paga em dia', cls: 'ok', icon: '⭐' };
  }
  return { label: 'Novo', cls: 'neutral', icon: '⚪' };
}

function debtorUrgencyInfo(d){
  if(d.paid) return { level: 4, tagHtml: '<span class="tag ok">✓ Quitado</span>', statusText: 'Quitado', delayDays: 0 };
  if(!d.payDate){
    return { level: 3, tagHtml: '<span class="tag" style="opacity:.7">Sem pressa</span>', statusText: 'Sem pressa', delayDays: 0 };
  }
  const todayStr = today();
  const diff = days(todayStr, d.payDate); // negative if overdue
  if(diff < 0){
    const delay = Math.abs(diff);
    let tagCls = 'dvTagDelayYellow';
    let label = `venceu há ${delay}d`;
    if(delay > 30){
      tagCls = 'dvTagDelayRed';
      label = `🔥 venceu há ${delay}d`;
    } else if(delay > 7){
      tagCls = 'dvTagDelayOrange';
      label = `venceu há ${delay}d`;
    }
    return {
      level: 1, // 🔴 Vencidas
      tagHtml: `<span class="${tagCls}">${label}</span>`,
      statusText: label,
      delayDays: delay,
      isOverdue: true
    };
  }
  if(diff <= 7){
    const label = diff === 0 ? 'vence hoje' : (diff === 1 ? 'vence amanhã' : `vence em ${diff}d`);
    return {
      level: 2, // 🟡 Esta semana
      tagHtml: `<span class="tag warn" style="background:rgba(255,207,95,.15);color:#ffd056;border-color:rgba(255,207,95,.4)">${label}</span>`,
      statusText: label,
      delayDays: 0,
      isWeek: true
    };
  }
  return {
    level: 3, // ⚪ Sem pressa
    tagHtml: `<span class="tag month" style="color:#9fb3a8">vence em ${dateBr(d.payDate)}</span>`,
    statusText: `vence em ${dateBr(d.payDate)}`,
    delayDays: 0
  };
}

function formatChargedTime(iso){
  if(!iso) return '';
  const diffDays = Math.round((Date.now() - new Date(iso).getTime()) / 86400000);
  if(diffDays <= 0) return 'cobrado hoje';
  return `cobrado há ${diffDays}d`;
}

function renderDebtorSingleCard(d, isNested=false){
  const inst = debtorInstallments(d);
  const paidInst = debtorPaidInstallments(d);
  const instVal = debtorInstallmentValue(d);
  const remainingAmount = debtorRemainingAmount(d);
  const isMulti = inst > 1;
  const reason = d.reason || 'other';
  const reasonIcon = debtorReasonIcon(reason);
  const reasonLabel = debtorReasonLabel(reason);
  const urgency = debtorUrgencyInfo(d);
  const trust = personTrustBadge(d.name);

  let dotsHtml = '';
  if(isMulti){
    const maxDots = Math.min(6, inst);
    const dots = Array.from({length: maxDots}, (_, i) => {
      const isDone = i < paidInst;
      return `<span style="color:${isDone ? '#39ff8f' : 'rgba(255,255,255,.2)'}">${isDone ? '●' : '○'}</span>`;
    }).join('');
    const extraLabel = inst > 6 ? `<span style="font-size:.65rem;opacity:.55;margin-left:1px">+${inst-6}</span>` : '';
    dotsHtml = `<span class="dvDots" title="${paidInst}/${inst} parcelas">${dots}${extraLabel} <span style="font-size:.68rem;opacity:.8;font-weight:700">${paidInst}/${inst}</span></span>`;
  }

  const chargedText = d.lastChargedAt ? formatChargedTime(d.lastChargedAt) : '';

  return `
    <article class="dvCard ${d.paid?'paid':''}" data-deb="${d.id}" data-deb-name="${esc(d.name)}">
      <div class="dvCardLine1">
        <div class="dvPersonNameWrap">
          <span class="dvReasonIcon" title="${reasonLabel}">${reasonIcon}</span>
          <span class="dvPersonName" data-act="dv-person-history" data-person="${esc(d.name)}" title="Ver histórico de ${esc(d.name)}">${safe(d.name)}</span>
          ${!isNested ? `<span class="dvTrustBadge ${trust.cls}">${trust.icon} ${trust.label}</span>` : ''}
          ${dotsHtml}
        </div>
        <div class="dvCardAmount">${money(d.paid ? d.amount : remainingAmount)}</div>
      </div>
      <div class="dvCardLine2">
        <div class="dvMetaLeft">
          ${urgency.tagHtml}
          ${isMulti && !d.paid ? `<span>· parcela ${money(instVal)}</span>` : ''}
          ${chargedText ? `<span>· ${chargedText}</span>` : ''}
          ${d.note ? `<span class="mut" title="${esc(d.note)}">· ${safe(d.note)}</span>` : ''}
        </div>
        <div class="dvMetaRight">
          ${!d.paid ? `<button type="button" class="dvActionBtn charge" data-act="dv-charge-wa" data-deb="${d.id}" title="Cobrar no WhatsApp">💬 Cobrar</button>` : ''}
          ${!d.paid ? `<button type="button" class="dvActionBtn receive" data-act="dv-open-receive" data-deb="${d.id}">✓ Recebi</button>` : ''}
          <button type="button" class="dvActionBtn menu" data-act="dv-open-menu" data-deb="${d.id}" title="Opções">⋯</button>
        </div>
      </div>
    </article>
  `;
}

function renderPersonGroupCard(personName, groupItems){
  const total = roundMoneyValue(groupItems.reduce((s,d)=>s+debtorRemainingAmount(d),0));
  const trust = personTrustBadge(personName);
  const isExpanded = Boolean(ui.debtors['grp_'+foldText(personName)]);
  return `
    <article class="dvGroupCard" data-group-person="${esc(personName)}">
      <div class="dvGroupHead" data-act="dv-toggle-group" data-person-key="${esc(foldText(personName))}">
        <div class="dvCardLine1">
          <div class="dvPersonNameWrap">
            <span class="dvReasonIcon">👥</span>
            <span class="dvPersonName" data-act="dv-person-history" data-person="${esc(personName)}">${safe(personName)}</span>
            <span class="dvTrustBadge ${trust.cls}">${trust.icon} ${trust.label}</span>
            <span class="tag" style="font-size:.68rem">${groupItems.length} cobranças</span>
          </div>
          <div class="dvCardAmount">${money(total)}</div>
        </div>
        <div class="dvCardLine2">
          <span class="mut" style="font-size:.72rem">Cobranças agrupadas · toque para ${isExpanded?'recolher ▲':'abrir ▼'}</span>
          <span style="font-size:.74rem;color:var(--p);font-weight:700">${isExpanded?'▲ Fechar':'▼ Ver todas'}</span>
        </div>
      </div>
      <div class="dvGroupSubItems" style="display:${isExpanded?'grid':'none'}">
        ${groupItems.map(d=>renderDebtorSingleCard(d, true)).join('')}
      </div>
    </article>
  `;
}

function renderDebtorItemsWithGrouping(items){
  const byPerson = {};
  items.forEach(d=>{
    const k = foldText(d.name);
    byPerson[k] = byPerson[k] || [];
    byPerson[k].push(d);
  });
  return Object.keys(byPerson).map(k=>{
    const pItems = byPerson[k];
    if(pItems.length === 1){
      return renderDebtorSingleCard(pItems[0]);
    }
    return renderPersonGroupCard(pItems[0].name, pItems);
  }).join('');
}

function renderDebtorBucket(title, badgeClass, items, isQuitadas=false){
  if(!items.length) return '';
  const total = roundMoneyValue(items.reduce((s,d)=>s+(isQuitadas?debtorPaidAmount(d):debtorRemainingAmount(d)), 0));
  const content = isQuitadas
    ? `<div style="display:grid;gap:6px">${items.map(d=>renderDebtorSingleCard(d)).join('')}</div>`
    : renderDebtorItemsWithGrouping(items);

  if(isQuitadas){
    return `
      <details class="dvArchiveDetails" style="margin-top:8px;border:1px solid rgba(57,255,143,.18);border-radius:12px;padding:8px 10px;background:rgba(255,255,255,.015)">
        <summary style="cursor:pointer;display:flex;justify-content:space-between;align-items:center;font-size:.76rem;color:var(--mut);font-weight:700">
          <span>${title} (${items.length})</span>
          <span class="tag ok">${money(total)}</span>
        </summary>
        <div style="margin-top:8px;display:grid;gap:6px">
          ${content}
        </div>
      </details>
    `;
  }

  return `
    <div class="dvSection">
      <div class="dvSectionHead">
        <span>${title} (${items.length})</span>
        <span class="tag ${badgeClass}">${money(total)}</span>
      </div>
      <div class="debtorList">
        ${content}
      </div>
    </div>
  `;
}

function renderDebtors(){
  const all = st.debtors || [];
  const openItems = all.filter(d=>!d.paid);
  const paidItems = all.filter(d=>d.paid);

  // Item 1: Summary Line
  const summaryEl = document.getElementById('dvSummaryLine');
  if(summaryEl){
    const openTotal = roundMoneyValue(openItems.reduce((s,d)=>s+debtorRemainingAmount(d),0));
    const uniqueNames = new Set(openItems.map(d=>foldText(d.name)).filter(Boolean));
    const peopleCount = uniqueNames.size;
    const overdueTotal = roundMoneyValue(openItems.filter(d=>debtorUrgencyInfo(d).isOverdue).reduce((s,d)=>s+debtorRemainingAmount(d),0));

    summaryEl.innerHTML = `
      <span>Me devem <strong>${money(openTotal)}</strong></span>
      <span class="dvSummaryDot">·</span>
      <span><strong>${peopleCount}</strong> ${peopleCount===1?'pessoa':'pessoas'}</span>
      ${overdueTotal > 0 ? `<span class="dvSummaryDot">·</span><span class="dvOverdueBadge">${money(overdueTotal)} vencido</span>` : ''}
    `;
  }

  // Item 2: Progress Bar
  const progressEl = document.getElementById('dvProgress');
  if(progressEl){
    const openTotal = roundMoneyValue(openItems.reduce((s,d)=>s+debtorRemainingAmount(d),0));
    const paidTotal = roundMoneyValue(all.reduce((s,d)=>s+debtorPaidAmount(d),0));
    const totalTracked = roundMoneyValue(openTotal + paidTotal);
    if(totalTracked > 0){
      progressEl.hidden = false;
      const pct = Math.min(100, Math.round((paidTotal / totalTracked) * 100));
      progressEl.innerHTML = `
        <div class="dvProgressTrack">
          <div class="dvProgressFill" style="width:${pct}%"></div>
        </div>
        <div class="dvProgressMeta">
          <span><strong>${pct}% recebido</strong> — ${money(paidTotal)} de ${money(totalTracked)}</span>
        </div>
      `;
    } else {
      progressEl.hidden = true;
    }
  }

  // Item 3: Destaque Esta Semana
  const weekEl = document.getElementById('dvWeek');
  if(weekEl){
    const weekItems = openItems.filter(d=>debtorUrgencyInfo(d).isWeek);
    const weekTotal = roundMoneyValue(weekItems.reduce((s,d)=>{
      const instVal = debtorInstallmentValue(d);
      const rem = debtorRemainingAmount(d);
      return s + (instVal > 0 && instVal < rem ? instVal : rem);
    }, 0));
    if(weekTotal > 0){
      weekEl.hidden = false;
      const names = Array.from(new Set(weekItems.map(d=>d.name).filter(Boolean)));
      weekEl.innerHTML = `<span>📥 Esta semana entram <strong>${money(weekTotal)}</strong> (${names.map(safe).join(', ')})</span>`;
    } else {
      weekEl.hidden = true;
    }
  }

  // Item 8: Ordem por urgência
  const v1 = openItems.filter(d=>debtorUrgencyInfo(d).level === 1); // 🔴 Vencidas
  const v2 = openItems.filter(d=>debtorUrgencyInfo(d).level === 2); // 🟡 Esta semana
  const v3 = openItems.filter(d=>debtorUrgencyInfo(d).level === 3); // ⚪ Sem pressa

  // Sort within buckets by payDate
  const sortFn = (a,b)=>(a.payDate||'9999-99-99').localeCompare(b.payDate||'9999-99-99');
  v1.sort(sortFn);
  v2.sort(sortFn);
  v3.sort(sortFn);
  paidItems.sort((a,b)=>new Date(b.paidAt||b.at||0) - new Date(a.paidAt||a.at||0));

  let html = '';
  if(!openItems.length && !paidItems.length){
    html = '<p class="empty">Nenhuma cobrança registrada ainda. Toque em "+ Cobrar alguém" para começar.</p>';
  } else {
    html = [
      renderDebtorBucket('🔴 Vencidas', 'danger', v1),
      renderDebtorBucket('🟡 Esta semana', 'warn', v2),
      renderDebtorBucket('⚪ Sem pressa', 'month', v3),
      renderDebtorBucket('✅ Quitadas', 'ok', paidItems, true)
    ].filter(Boolean).join('');
  }

  if(el.debList){
    el.debList.className = 'list debtBoard';
    el.debList.innerHTML = html;
  }
  if(el.debtsPageDebList && el.debtsPageDebList !== el.debList){
    el.debtsPageDebList.className = 'list debtBoard';
    el.debtsPageDebList.innerHTML = html;
  }
  const openTotal = roundMoneyValue(openItems.reduce((sum,d)=>sum+debtorRemainingAmount(d),0));
  if(el.debtsPageTotalBox) el.debtsPageTotalBox.textContent = money(openTotal);
  if(el.debtsPageCountBox) el.debtsPageCountBox.textContent = String(openItems.length);
}

function renderMyDebts(){
  if(!Array.isArray(st.myDebts)) st.myDebts = [];
  const all = st.myDebts;
  const openItems = all.filter(d => !d.paid);
  const paidItems = all.filter(d => d.paid);

  const openTotal = roundMoneyValue(openItems.reduce((s,d)=>s+debtRemainingAmount(d), 0));
  const overdueItems = openItems.filter(d => myDebtUrgencyInfo(d).isOverdue);
  const overdueTotal = roundMoneyValue(overdueItems.reduce((s,d)=>s+debtRemainingAmount(d), 0));

  // 1. Resumo em 1 linha (#mdSummaryLine)
  const summaryEl = document.getElementById('mdSummaryLine');
  if(summaryEl){
    let overdueHtml = '';
    if(overdueTotal > 0){
      overdueHtml = `<span class="dvSummaryDot">·</span> <span class="dvOverdueBadge">🔴 ${money(overdueTotal)} vencido</span>`;
    }
    summaryEl.innerHTML = `
      <span>Devo <strong>${money(openTotal)}</strong></span>
      <span class="dvSummaryDot">·</span>
      <span><strong>${openItems.length}</strong> ${openItems.length===1?'conta':'contas'}</span>
      ${overdueHtml}
    `;
  }

  // 2. Barra de quanto já foi pago (#mdProgress)
  const progressEl = document.getElementById('mdProgress');
  if(progressEl){
    const paidTotal = roundMoneyValue(all.reduce((s,d)=>s+debtPaidAmount(d), 0));
    const totalTracked = roundMoneyValue(openTotal + paidTotal);
    if(totalTracked > 0){
      progressEl.hidden = false;
      progressEl.style.display = 'grid';
      const pct = Math.min(100, Math.round((paidTotal / totalTracked) * 100));
      progressEl.innerHTML = `
        <div class="dvProgressTrack">
          <div class="dvProgressFill" style="width:${pct}%"></div>
        </div>
        <div class="dvProgressMeta">
          <span><strong>${pct}% pago</strong> — ${money(paidTotal)} de ${money(totalTracked)}</span>
        </div>
      `;
    } else {
      progressEl.hidden = true;
      progressEl.style.display = 'none';
    }
  }

  // 3. Destaque esta semana (#mdWeek)
  const weekEl = document.getElementById('mdWeek');
  if(weekEl){
    const weekItems = openItems.filter(d => myDebtUrgencyInfo(d).isWeek);
    const weekTotal = roundMoneyValue(weekItems.reduce((s,d)=>{
      const instVal = debtInstallmentValue(d);
      const rem = debtRemainingAmount(d);
      return s + (instVal > 0 && instVal < rem ? instVal : rem);
    }, 0));
    if(weekTotal > 0){
      weekEl.hidden = false;
      weekEl.style.display = 'flex';
      const names = Array.from(new Set(weekItems.map(d=>d.name).filter(Boolean)));
      weekEl.innerHTML = `<span>📤 Esta semana vencem <strong>${money(weekTotal)}</strong> (${names.map(safe).join(', ')})</span>`;
    } else {
      weekEl.hidden = true;
      weekEl.style.display = 'none';
    }
  }

  const listEl = el.myDebtList || document.getElementById('myDebtList');
  if(!listEl) return;

  if(!all.length){
    listEl.className = 'list debtBoard';
    listEl.innerHTML = '<p class="empty" style="text-align:center;padding:24px 12px">Nenhuma dívida a pagar cadastrada.<br>Toque em <strong>+ Adicionar dívida</strong> para registrar suas contas.</p>';
    return;
  }

  // 4. Buckets de urgência
  const v1 = openItems.filter(d => myDebtUrgencyInfo(d).level === 1); // 🔴 Vencidas
  const v2 = openItems.filter(d => myDebtUrgencyInfo(d).level === 2); // 🟡 Esta semana
  const v3 = openItems.filter(d => myDebtUrgencyInfo(d).level === 3); // ⚪ Sem pressa

  const sortFn = (a,b) => (a.payDate || '9999-99-99').localeCompare(b.payDate || '9999-99-99');
  v1.sort(sortFn);
  v2.sort(sortFn);
  v3.sort(sortFn);
  paidItems.sort((a,b) => (b.paidAt || b.at || '').localeCompare(a.paidAt || a.at || ''));

  function groupCreditors(items){
    const map = new Map();
    items.forEach(item => {
      const key = foldText(item.name);
      if(!map.has(key)) map.set(key, { name: item.name, list: [] });
      map.get(key).list.push(item);
    });
    const rendered = [];
    map.forEach(val => {
      rendered.push(renderMyDebtGroupCard(val.name, val.list));
    });
    return rendered.join('');
  }

  let html = '';
  if(v1.length > 0){
    const v1Total = roundMoneyValue(v1.reduce((s,d)=>s+debtRemainingAmount(d), 0));
    html += `
      <section class="dvSection">
        <div class="dvSectionHead" style="color:#ff7d8d">
          <span>🔴 Vencidas (${v1.length})</span>
          <span style="font-family:var(--font-display);font-size:.9rem">${money(v1Total)}</span>
        </div>
        ${groupCreditors(v1)}
      </section>
    `;
  }

  if(v2.length > 0){
    const v2Total = roundMoneyValue(v2.reduce((s,d)=>s+debtRemainingAmount(d), 0));
    html += `
      <section class="dvSection">
        <div class="dvSectionHead" style="color:#ffd056">
          <span>🟡 Vencem esta semana (${v2.length})</span>
          <span style="font-family:var(--font-display);font-size:.9rem">${money(v2Total)}</span>
        </div>
        ${groupCreditors(v2)}
      </section>
    `;
  }

  if(v3.length > 0){
    const v3Total = roundMoneyValue(v3.reduce((s,d)=>s+debtRemainingAmount(d), 0));
    html += `
      <section class="dvSection">
        <div class="dvSectionHead">
          <span>⚪ Próximos vencimentos (${v3.length})</span>
          <span style="font-family:var(--font-display);font-size:.9rem">${money(v3Total)}</span>
        </div>
        ${groupCreditors(v3)}
      </section>
    `;
  }

  if(paidItems.length > 0){
    const paidTotal = roundMoneyValue(paidItems.reduce((s,d)=>s+debtPaidAmount(d), 0));
    html += `
      <details class="archiveMonth" style="margin-top:10px">
        <summary class="archiveSummary">
          <div>
            <strong style="color:#4cff9e">✅ Contas Quitadas (${paidItems.length})</strong>
            <span style="font-size:.7rem;color:var(--mut)">Total já pago nestas contas</span>
          </div>
          <span style="font-family:var(--font-display);font-size:.92rem;color:#4cff9e">${money(paidTotal)}</span>
        </summary>
        <div class="archiveBody" style="display:grid;gap:6px;padding-top:6px">
          ${paidItems.map(d=>renderMyDebtSingleCard(d)).join('')}
        </div>
      </details>
    `;
  }

  if(!html){
    html = '<p class="empty" style="text-align:center;padding:24px 12px">Todas as suas dívidas cadastradas estão quitadas! 🎉</p>';
  }

  listEl.className = 'list debtBoard';
  listEl.innerHTML = html;
}

function goalThemeIcon(name){
  const s=(name||'').toLowerCase();
  if(/viagem|praia|ferias|voo|passagem/i.test(s)) return '✈️';
  if(/carro|moto|veiculo|ipva|cnh|auto/i.test(s)) return '🚗';
  if(/reserva|emergencia|seguranca|colchao/i.test(s)) return '🛡️';
  if(/casa|ape|apartamento|reforma|aluguel|constru/i.test(s)) return '🏠';
  if(/invest|renda|bolsa|fii|cdi|selic|cripto|btc/i.test(s)) return '📈';
  if(/pc|mac|computador|setup|iphone|ipad|tech/i.test(s)) return '💻';
  return '🎯';
}

function renderGoals(){
  if(!Array.isArray(st.goals)) st.goals=[];
  const weekYield=goalsWeekYield();
  const totalSaved=goalsTotalSaved();
  if(el.goalActiveCount) el.goalActiveCount.textContent=String(st.goals.length);
  if(el.goalWeekYield) el.goalWeekYield.textContent=money(weekYield);
  if(el.goalsTotalSavedBox) el.goalsTotalSavedBox.textContent=money(totalSaved);
  if(!st.goals.length){el.goalList.innerHTML='<p class="empty">Nenhum objetivo ainda. Crie o primeiro para acompanhar seu patrimônio.</p>';return;}

  el.goalList.innerHTML=st.goals.map(g=>{
    const editing=Boolean(ui.goals[g.id]);
    const target=Math.max(0,Number(g.target)||0);
    const saved=Math.max(0,Number(g.saved)||0);
    const left=Math.max(0,target-saved);
    const pct=target>0?Math.min(100,Math.round((saved/target)*100)):0;
    const icon=goalThemeIcon(g.name);
    return `<article class="goal" data-goal-id="${g.id}">
      <div class="goalHeaderRow">
        <div class="goalTitleWrap">
          <span class="goalIconBadge">${icon}</span>
          <div>
            <strong style="font-size:.95rem;">${safe(g.name)}</strong>
            <p class="mut" style="font-size:.74rem;">${left>0?`Faltam ${money(left)}`:'🎉 Meta alcançada!'}</p>
          </div>
        </div>
        <div class="line" style="align-items:center;">
          <span class="tag ok">${pct}%</span>
          <button class="iconBtn ${editing?'active':''}" type="button" data-act="goal-edit" title="Editar objetivo">✎</button>
        </div>
      </div>
      <div class="goalMetaRow" style="margin-top:2px;">
        <strong class="goalMoney">${money(saved)} <span class="mut" style="font-size:.82rem;">de ${money(target)}</span></strong>
        <span class="goalPct">${pct}%</span>
      </div>
      ${editing?`<div class="two" style="margin-top:4px;">
        <input data-f="goal-name" type="text" value="${esc(g.name)}" maxlength="36" />
        <input data-f="goal-target" type="number" step="0.01" inputmode="decimal" value="${target}" />
      </div>`:''}
      <div class="track"><div class="fill goal" style="width:${pct}%"></div></div>
      
      <!-- Quick Aportes Chips -->
      <div class="wrap" style="margin-top:2px;">
        <span class="mini">Aporte Rápido</span>
        <div class="quickChipsRow">
          <button type="button" class="quickActionChip highlight" data-goal-deposit="20" data-goal-id="${g.id}">+R$ 20</button>
          <button type="button" class="quickActionChip highlight" data-goal-deposit="50" data-goal-id="${g.id}">+R$ 50</button>
          <button type="button" class="quickActionChip highlight" data-goal-deposit="100" data-goal-id="${g.id}">+R$ 100</button>
          <button type="button" class="quickActionChip highlight" data-goal-deposit="200" data-goal-id="${g.id}">+R$ 200</button>
        </div>
      </div>

      <div class="goalActionsWrap" style="margin-top:6px;">
        <div class="actionFields">
          <input data-goal-value type="number" step="0.01" inputmode="decimal" placeholder="Outro valor (R$)" />
        </div>
        <div class="actionStack">
          <button class="btn" type="button" data-act="goal-deposit">Aportar</button>
          <button class="danger" type="button" data-act="goal-withdraw">Resgatar</button>
          <button class="ghost" type="button" data-act="goal-yield">Rendimento</button>
        </div>
      </div>
      <button class="danger" type="button" data-act="goal-remove" style="margin-top:4px;">Remover objetivo</button>
    </article>`;
  }).join('');
}

function renderGoalStatement(){
  const editing=Boolean(ui.statement.goal);
  const items=(st.goals||[])
    .reduce((acc,g)=>acc.concat((Array.isArray(g.tx)?g.tx:[]).map(t=>Object.assign({goal:g.name||'Objetivo',goalId:g.id},t))),[])
    .sort((a,b)=>new Date(b.at)-new Date(a.at))
    .slice(0,18);
  const banner=editing?renderStatementModeBanner('Modo edição ativo nos objetivos. Você pode alterar tipo, valor e data antes de salvar.'):'';
  if(!items.length){el.goalStmt.innerHTML=`${banner}<p class="empty">Sem movimentações de objetivos ainda.</p>`;return;}
  el.goalStmt.innerHTML=banner+items.map(t=>{
    const sign=t.type==='withdraw'?'-':'+'; 
    const cls=t.type==='withdraw'?'neg':'pos';
    const label=t.type==='yield'?'Rendimento':(t.type==='deposit'?'Entrada':'Saída');
    const isEditing=isStatementEditorActive('goal','goal',t.id,t.goalId);
    return renderStatementRow({
      section:'goal',
      primaryHtml:`<span class="${cls}">${sign} ${money(t.value)}</span> ${safe(t.goal)} · ${label}`,
      meta:shortDate(t.at),
      editable:editing,
      isEditing:isEditing,
      editorHtml:isEditing?renderStatementEditor({section:'goal',source:'goal',txId:t.id,goalId:t.goalId}):'',
      txId:t.id,
      source:'goal',
      goalId:t.goalId
    });
  }).join('');
}

function goalMove(goal,type,value){
  if(!goal||value<=0) return;
  if(type==='withdraw') goal.saved=Math.max(0,(Number(goal.saved)||0)-value);
  else goal.saved=(Number(goal.saved)||0)+value;
  goal.tx=Array.isArray(goal.tx)?goal.tx:[];
  goal.tx.unshift({id:id(),type,value,at:new Date().toISOString()});
  save(true); renderGoals(); renderGoalStatement(); renderSummary();
}

function renderHero(){
  const debtOpen=debtOpenTotal(), used=Math.max(0,Number(st.credit.used)||0), reserved=Math.max(0,Number(st.credit.reserved)||0), uncovered=Math.max(0,used-reserved), coverageRate=used>0?(reserved/used):1;
  const balance=Number((st.balances&&st.balances.conta&&st.balances.conta.amount)||0);
  const spent=spentToday();

  let risk='Baixo', riskClass='ok';
  if(uncovered>=1200||debtOpen>=2000||balance<0){risk='Alto'; riskClass='hot';}
  else if(uncovered>0||debtOpen>0||coverageRate<0.85){risk='Médio'; riskClass='mid';}

  let mode='EM DIA', modeClass='ok', title='Finanças sob controle', desc=spent>0?`Hoje você já gastou ${money(spent)}. Continue registrando cada saída.`:'Nenhum gasto registrado hoje. Registre cada saída na hora.';
  if(balance<0){
    mode='NEGATIVO'; modeClass='hot';
    title='Conta no vermelho';
    desc=`Seu saldo em conta está em ${money(balance)}. Evite novas saídas até regularizar.`;
  } else if(uncovered>0 && coverageRate<0.35){
    mode='ATENÇÃO'; modeClass='hot';
    title='Fatura do cartão descoberta';
    desc=`Faltam ${money(uncovered)} para cobrir a fatura atual. Reforce a reserva do cartão.`;
  } else if(uncovered>0){
    mode='AJUSTAR'; modeClass='mid';
    title='Complete a reserva do cartão';
    desc=`A reserva cobre ${Math.round(coverageRate*100)}% da fatura. Faltam ${money(uncovered)}.`;
  } else if(debtOpen>0){
    mode='A RECEBER'; modeClass='mid';
    title='Você tem valores a receber';
    desc=`${money(debtOpen)} em aberto com devedores. Vale cobrar hoje.`;
  }

  el.focusPill.className=`focusPill ${modeClass}`;
  el.focusPill.textContent=mode;
  el.heroTitle.textContent=title;
  el.heroDesc.textContent=desc;
  if(el.heroBalance){
    el.heroBalance.textContent=money(balance);
    el.heroBalance.style.color=balance<0?'var(--d)':'var(--p)';
  }
  el.heroRisk.textContent=risk;
  el.heroRisk.style.color=riskClass==='hot'?'var(--d)':(riskClass==='mid'?'#ffcf5f':'var(--p)');
  el.heroDebt.textContent=money(debtOpen);
  el.heroDebt.style.color=debtOpen>0?'#ffcf5f':'var(--p)';
}

function renderSummary(){
  const total=st.habits.length, done=st.habits.filter(h=>h.done).length, p=total?Math.round(done/total*100):0, spent=spentToday();
  const cardOpen=Math.max(0,Number(st.credit.used)||0), reserved=Math.max(0,Number(st.credit.reserved)||0), debtOpen=debtOpenTotal(), uncovered=Math.max(0,cardOpen-reserved), coverageRate=cardOpen>0?(reserved/cardOpen):1;
  const savedGoals=goalsTotalSaved();
  el.sPercent.textContent=`${p}%`; el.sHabits.textContent=`${done} / ${total}`; el.sSpent.textContent=money(spent);
  el.sCard.textContent=money(cardOpen); el.sDebt.textContent=money(debtOpen); el.sGoals.textContent=money(savedGoals);
  renderHero();
  renderFiveDayStatement();
  renderCharts();

  if(cardOpen>0&&coverageRate<0.35){el.sStatus.textContent='Atenção no cartão';el.sMsg.textContent='Sua reserva cobre pouco da fatura atual. Reforce esse saldo.';}
  else if(uncovered>0){el.sStatus.textContent='Reserva parcial';el.sMsg.textContent=`Faltam ${money(uncovered)} para cobrir toda a fatura.`;}
  else if(debtOpen>0){el.sStatus.textContent='Cobrança pendente';el.sMsg.textContent='Você tem valores a receber. Priorize as cobranças do dia.';}
  else if(spent>0){el.sStatus.textContent='Em dia';el.sMsg.textContent='Fatura coberta e nada pendente. Só segue registrando os gastos.';}
  else{el.sStatus.textContent='Tudo certo';el.sMsg.textContent='Fatura coberta, nada a receber e nenhum gasto hoje.';}
}

function rotateDay(){
  const t=today(); if(!st.lastDate){st.lastDate=t;save();return;} if(st.lastDate===t)return;
  const gap=days(st.lastDate,t); if(gap>1||(gap===1&&!st.routineDone)) st.streak=0;
  st.habits=st.habits.map(h=>Object.assign({},h,{done:false})); st.routineDone=false; st.lastDate=t;
  if(focusTick){clearInterval(focusTick); focusTick=null;}
  st.focusSession.running=false;
  st.focusSession.secondsLeft=1500;
  save();
}

function spentToday(){
  const t=today();
  const walletOut=st.tx.filter(x=>x.type==='out'&&dateKey(x.at)===t).reduce((a,x)=>a+x.value,0);
  const cardOut=(st.credit.tx||[]).filter(x=>x.type==='expense'&&dateKey(x.at)===t).reduce((a,x)=>a+x.value,0);
  return walletOut+cardOut;
}
function debtOpenTotal(){return st.debtors.filter(x=>!x.paid&&shouldShowDebtorNow(x)).reduce((a,x)=>a+debtorRemainingAmount(x),0);}
function goalsTotalSaved(){return (st.goals||[]).reduce((a,g)=>a+Math.max(0,Number(g.saved)||0),0);}
function isStatementEditorActive(section,source,txId,goalId){
  return Boolean(
    ui.statementEditor &&
    ui.statementEditor.section===section &&
    ui.statementEditor.source===source &&
    ui.statementEditor.txId===txId &&
    (ui.statementEditor.goalId||'')===(goalId||'')
  );
}
function renderStatementModeBanner(message){
  return `<div class="statementModeBanner">${safe(message)}</div>`;
}
function renderStatementControls(){
  const toggles=el.statementPage ? el.statementPage.querySelectorAll('[data-statement-toggle]') : [];
  for(var i=0;i<toggles.length;i++){
    const btn=toggles[i];
    const key=btn.getAttribute('data-statement-toggle');
    const active=Boolean(ui.statement[key]);
    setActive(btn,active);
    btn.textContent=active?'Encerrar edição':'Editar transações';
  }
}
function statementField(label, html){
  return `<label class="statementField"><span>${safe(label)}</span>${html}</label>`;
}
function toDateTimeLocal(value){
  const date=new Date(value||Date.now());
  if(Number.isNaN(date.getTime())) return '';
  const pad=num=>String(num).padStart(2,'0');
  return `${date.getFullYear()}-${pad(date.getMonth()+1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
function fromDateTimeLocal(value,fallback){
  if(!value) return fallback||new Date().toISOString();
  const date=new Date(value);
  return Number.isNaN(date.getTime())?(fallback||new Date().toISOString()):date.toISOString();
}
function statementTarget(source,txId,goalId){
  if(source==='wallet'){
    const tx=st.tx.find(t=>t.id===txId);
    return tx?{tx}:null;
  }
  if(source==='credit'){
    const tx=(st.credit.tx||[]).find(t=>t.id===txId);
    return tx?{tx}:null;
  }
  if(source==='goal'){
    const goal=(st.goals||[]).find(g=>g.id===goalId);
    if(!goal||!Array.isArray(goal.tx)) return null;
    const tx=goal.tx.find(t=>t.id===txId);
    return tx?{tx,goal}:null;
  }
  return null;
}
function renderStatementEditor(opts){
  const target=statementTarget(opts.source,opts.txId,opts.goalId);
  if(!target||!target.tx) return '';
  const tx=target.tx;
  const goalAttr=opts.goalId?` data-goal-id="${esc(opts.goalId)}"`:'';
  const sectionAttr=` data-statement-section="${esc(opts.section)}"`;
  const commonDate=statementField('Data e hora',`<input data-edit-field="at" type="datetime-local" value="${esc(toDateTimeLocal(tx.at))}" />`);
  let fields='';
  let hint='Salve para recalcular o extrato e os totais desta seção.';

  if(opts.source==='wallet'){
    const accountOptions=Object.entries(st.balances||{}).map(([key,item])=>`<option value="${esc(key)}"${key===tx.account?' selected':''}>${safe(item && item.label ? item.label : defLabel(key))}</option>`).join('');
    const typeOptions=[
      {value:'in',label:'Entrada'},
      {value:'out',label:'Saída'},
      {value:'set',label:'Definir saldo'}
    ].map(item=>`<option value="${item.value}"${item.value===tx.type?' selected':''}>${item.label}</option>`).join('');
    fields=[
      statementField('Conta',`<select data-edit-field="account">${accountOptions}</select>`),
      statementField('Tipo',`<select data-edit-field="type">${typeOptions}</select>`),
      statementField('Valor',`<input data-edit-field="value" type="number" step="0.01" inputmode="decimal" value="${esc(Number(tx.value)||0)}" />`),
      statementField('Descrição / categoria',`<input data-edit-field="note" type="text" maxlength="42" value="${esc(tx.note||tx.category||'')}" />`),
      commonDate
    ].join('');
    hint='Edite conta, tipo, valor, descrição e data. Os saldos das carteiras serão recalculados ao salvar.';
  }else if(opts.source==='credit'){
    const typeOptions=[
      {value:'expense',label:'Gasto'},
      {value:'payment',label:'Pagamento'},
      {value:'reserve-in',label:'Entrada reserva'},
      {value:'reserve-out',label:'Saída reserva'}
    ].map(item=>`<option value="${item.value}"${item.value===tx.type?' selected':''}>${item.label}</option>`).join('');
    fields=[
      statementField('Tipo',`<select data-edit-field="type">${typeOptions}</select>`),
      statementField('Valor',`<input data-edit-field="value" type="number" step="0.01" inputmode="decimal" value="${esc(Number(tx.value)||0)}" />`),
      statementField('Descrição / categoria',`<input data-edit-field="desc" type="text" maxlength="42" value="${esc(tx.desc||tx.category||'')}" />`),
      commonDate
    ].join('');
    hint='Edite o lançamento do cartão e salve para atualizar fatura e reserva automaticamente.';
  }else if(opts.source==='goal'){
    const typeOptions=[
      {value:'deposit',label:'Entrada'},
      {value:'withdraw',label:'Saída'},
      {value:'yield',label:'Rendimento'}
    ].map(item=>`<option value="${item.value}"${item.value===tx.type?' selected':''}>${item.label}</option>`).join('');
    fields=[
      statementField('Objetivo',`<input type="text" value="${esc(target.goal && target.goal.name ? target.goal.name : 'Objetivo')}" readonly />`),
      statementField('Tipo',`<select data-edit-field="type">${typeOptions}</select>`),
      statementField('Valor',`<input data-edit-field="value" type="number" step="0.01" inputmode="decimal" value="${esc(Number(tx.value)||0)}" />`),
      commonDate
    ].join('');
    hint='A movimentação do objetivo será recalculada com o novo tipo, valor e data.';
  }else{
    return '';
  }

  return `<div class="statementEditor">
    <div class="statementEditorGrid">${fields}</div>
    <div class="statementEditorHint">${safe(hint)}</div>
    <div class="statementEditorActions">
      <button type="button" class="ghost" data-tx-cancel="${esc(opts.txId)}" data-source="${esc(opts.source)}"${sectionAttr}${goalAttr}>Cancelar</button>
      <button type="button" class="btn" data-tx-save="${esc(opts.txId)}" data-source="${esc(opts.source)}"${sectionAttr}${goalAttr}>Salvar ajustes</button>
    </div>
  </div>`;
}
function renderStatementRow(opts){
  opts=opts||{};
  const editable=Boolean(opts.editable&&opts.txId&&opts.source);
  const editing=Boolean(opts.isEditing);
  const secondary=opts.secondaryHtml?`<span class="statementSecondary">${opts.secondaryHtml}</span>`:'';
  const goalAttr=opts.goalId?` data-goal-id="${esc(opts.goalId)}"`:'';
  const sectionAttr=opts.section?` data-statement-section="${esc(opts.section)}"`:'';
  return `<div class="statementRow${editing?' editing':''}">
    <div class="statementBody">
      <span class="statementPrimary">${opts.primaryHtml||''}</span>
      ${secondary}
    </div>
    <div class="statementAside">
      <span class="statementMeta">${safe(opts.meta||'')}</span>
      ${editable?`<div class="statementActions">
        <button type="button" class="iconBtn statementEditAction${editing?' active':''}" title="Editar transação" data-tx-edit="${esc(opts.txId)}" data-source="${esc(opts.source)}"${sectionAttr}${goalAttr}>✎</button>
        <button type="button" class="iconBtn danger statementDelete" title="Apagar transação" data-tx-del="${esc(opts.txId)}" data-source="${esc(opts.source)}"${goalAttr}>✕</button>
      </div>`:''}
    </div>
    ${editing&&opts.editorHtml?`<div class="statementEditorWrap">${opts.editorHtml}</div>`:''}
  </div>`;
}
function parseEditorValue(root,field){
  const node=root ? root.querySelector(`[data-edit-field="${field}"]`) : null;
  return node ? node.value : '';
}
function saveStatementEdit(section,source,txId,goalId,trigger){
  const row=trigger ? trigger.closest('.statementRow') : null;
  const valueRaw=parseFloat(String(parseEditorValue(row,'value')||'').replace(',','.'));
  const value=Number.isFinite(valueRaw)?Math.abs(valueRaw):0;
  if(value<=0){
    showToast('Informe um valor maior que zero para salvar a transação.','warn');
    return;
  }

  if(source==='wallet'){
    const tx=st.tx.find(item=>item.id===txId);
    if(!tx) return;
    const baselines=captureWalletBaselines();
    const account=parseEditorValue(row,'account');
    const type=parseEditorValue(row,'type');
    tx.account=st.balances[account]?account:tx.account;
    tx.type=['in','out','set'].includes(type)?type:tx.type;
    tx.value=value;
    tx.note=txt(parseEditorValue(row,'note'),42);
    tx.at=fromDateTimeLocal(parseEditorValue(row,'at'),tx.at);
    const meta=categoryMeta(tx.note,tx.type==='set'?'Ajuste manual':'Sem categoria');
    tx.category=meta.label;
    tx.categoryKey=meta.key;
    recomputeWalletBalances(baselines);
  }else if(source==='credit'){
    const tx=(st.credit.tx||[]).find(item=>item.id===txId);
    if(!tx) return;
    const type=parseEditorValue(row,'type');
    tx.type=['expense','payment','reserve-in','reserve-out'].includes(type)?type:tx.type;
    tx.value=value;
    tx.desc=txt(parseEditorValue(row,'desc'),42);
    tx.at=fromDateTimeLocal(parseEditorValue(row,'at'),tx.at);
    const fallback=tx.type==='expense'?'Sem categoria':(tx.type==='payment'?'Pagamento cartao':'Reserva cartao');
    const meta=categoryMeta(tx.desc,fallback);
    tx.category=meta.label;
    tx.categoryKey=meta.key;
    recomputeCreditState();
  }else if(source==='goal'){
    const goal=(st.goals||[]).find(item=>item.id===goalId);
    if(!goal||!Array.isArray(goal.tx)) return;
    const tx=goal.tx.find(item=>item.id===txId);
    if(!tx) return;
    const type=parseEditorValue(row,'type');
    tx.type=['deposit','withdraw','yield'].includes(type)?type:tx.type;
    tx.value=value;
    tx.at=fromDateTimeLocal(parseEditorValue(row,'at'),tx.at);
    recomputeGoalSaved(goal);
  }else{
    return;
  }

  ui.statementEditor=null;
  save(true);
  renderAll();
}
function removeStatementTransaction(source,txId,goalId){
  if(!source||!txId) return;
  if(source==='wallet'){
    const baselines=captureWalletBaselines();
    const existing=st.tx.find(t=>t.id===txId);
    if(!existing) return;
    if(existing.debtorId){
      const debtor=st.debtors.find(d=>d.id===existing.debtorId);
      if(debtor){debtor.paid=false; debtor.paidAt='';}
    }
    if(existing.myDebtId){
      const myDebt=(st.myDebts||[]).find(d=>d.id===existing.myDebtId);
      if(myDebt){
        const installments=debtInstallments(myDebt);
        const removedInstallment=Math.max(0,parseInt(existing.myDebtInstallment||'0',10)||0);
        const fallbackPaid=debtPaidInstallments(myDebt);
        myDebt.installmentsPaid=Math.max(0,Math.min(installments,removedInstallment ? removedInstallment-1 : fallbackPaid-1));
        myDebt.paid=myDebt.installmentsPaid>=installments;
        if(!myDebt.paid) myDebt.paidAt='';
      }
    }
    st.tx=st.tx.filter(t=>t.id!==txId);
    recomputeWalletBalances(baselines);
  }else if(source==='credit'){
    if(!(st.credit.tx||[]).some(t=>t.id===txId)) return;
    st.credit.tx=(st.credit.tx||[]).filter(t=>t.id!==txId);
    recomputeCreditState();
  }else if(source==='goal'){
    const goal=st.goals.find(g=>g.id===goalId);
    if(!goal||!Array.isArray(goal.tx)||!goal.tx.some(t=>t.id===txId)) return;
    goal.tx=goal.tx.filter(t=>t.id!==txId);
    recomputeGoalSaved(goal);
  }else{
    return;
  }
  if(ui.statementEditor && ui.statementEditor.source===source && ui.statementEditor.txId===txId && (ui.statementEditor.goalId||'')===(goalId||'')){
    ui.statementEditor=null;
  }
  save(true);
  renderAll();
}
function sortTransactionsAsc(items){
  return (Array.isArray(items)?items:[]).slice().sort((a,b)=>new Date(a.at)-new Date(b.at));
}
function sortTransactionsDesc(items){
  return (Array.isArray(items)?items:[]).slice().sort((a,b)=>new Date(b.at)-new Date(a.at));
}
function captureWalletBaselines(){
  const baselines={};
  Object.keys(st.balances||{}).forEach(key=>{
    baselines[key]=Number((st.balances[key]||{}).amount)||0;
  });
  (st.tx||[]).forEach(t=>{
    if(!t||!t.account||!Object.prototype.hasOwnProperty.call(baselines,t.account)) return;
    if(t.type==='set') baselines[t.account]-=(Number(t.value)||0)-(Number(t.prev)||0);
    else if(t.type==='in') baselines[t.account]-=Number(t.value)||0;
    else if(t.type==='out') baselines[t.account]+=Number(t.value)||0;
  });
  return baselines;
}
function recomputeWalletBalances(baselines){
  const seed=baselines||captureWalletBaselines();
  Object.keys(st.balances||{}).forEach(key=>{
    st.balances[key].amount=Number(seed[key])||0;
  });
  sortTransactionsAsc(st.tx).forEach(t=>{
    if(!t||!st.balances[t.account]) return;
    if(t.type==='set'){
      t.prev=Number(st.balances[t.account].amount)||0;
      st.balances[t.account].amount=Number(t.value)||0;
    }
    else if(t.type==='in') st.balances[t.account].amount += Number(t.value)||0;
    else if(t.type==='out') st.balances[t.account].amount -= Number(t.value)||0;
  });
}
function recomputeCreditState(){
  st.credit.used=0;
  st.credit.reserved=0;
  sortTransactionsAsc(st.credit.tx).forEach(t=>{
    const value=Math.abs(Number(t.value)||0);
    if(t.type==='expense') st.credit.used += value;
    else if(t.type==='payment') st.credit.used=Math.max(0,st.credit.used-value);
    else if(t.type==='reserve-in') st.credit.reserved += value;
    else if(t.type==='reserve-out') st.credit.reserved=Math.max(0,st.credit.reserved-value);
  });
}
function recomputeGoalSaved(goal){
  if(!goal) return;
  goal.saved=0;
  sortTransactionsAsc(goal.tx).forEach(t=>{
    const value=Math.abs(Number(t.value)||0);
    if(t.type==='withdraw') goal.saved=Math.max(0,goal.saved-value);
    else goal.saved += value;
  });
}
function goalsWeekYield(){
  const start=startOfWeek(new Date());
  return (st.goals||[]).reduce((sum,g)=>{
    const tx=Array.isArray(g.tx)?g.tx:[];
    return sum+tx.filter(t=>t.type==='yield'&&new Date(t.at)>=start).reduce((a,t)=>a+(Number(t.value)||0),0);
  },0);
}
function normalizeSkills(sk){
  const s=sk||{};
  return {
    estudar:Math.max(0,Number(s.estudar)||0),
    treinar:Math.max(0,Number(s.treinar)||0),
    trabalhar:Math.max(0,Number(s.trabalhar)||0)
  };
}
function detectSkill(name){
  const n=String(name||'').toLowerCase();
  if(n.includes('estud')) return 'estudar';
  if(n.includes('trein')||n.includes('academ')||n.includes('exerc')) return 'treinar';
  if(n.includes('trabalh')||n.includes('job')||n.includes('servi')) return 'trabalhar';
  return '';
}
function adjustSkillXp(skill,delta){
  if(!skill) return;
  st.skills=normalizeSkills(st.skills);
  st.skills[skill]=Math.max(0,(Number(st.skills[skill])||0)+delta);
}
function flash(node,type){if(!node)return;const c=type==='in'?'flashIn':'flashOut';node.classList.remove('flashIn','flashOut');void node.offsetWidth;node.classList.add(c);}
function debtorMonthValue(payDate){
  if(!payDate||!/^\d{4}-\d{2}-\d{2}$/.test(payDate)) return 0;
  return parseInt(payDate.slice(0,4)+payDate.slice(5,7),10);
}
function currentMonthValue(){
  const now=today();
  return parseInt(now.slice(0,4)+now.slice(5,7),10);
}
function shouldShowDebtorNow(debtor){
  if(!debtor||!debtor.payDate) return true;
  return debtorMonthValue(debtor.payDate)<=currentMonthValue();
}
function compareDebtorMonth(a,b){
  const monthA=debtorMonthValue(a.payDate);
  const monthB=debtorMonthValue(b.payDate);
  return monthA-monthB;
}
function normalizeCategoryKey(value){
  return String(value||'')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g,'')
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g,' ')
    .replace(/\s+/g,' ')
    .trim();
}
function titleizeCategory(key){
  const lowers={de:1,da:1,do:1,das:1,dos:1,e:1,em:1,para:1,pra:1,pro:1,no:1,na:1,nos:1,nas:1};
  return String(key||'').split(' ').filter(Boolean).map((word,index)=>index&&lowers[word]?word:(word.charAt(0).toUpperCase()+word.slice(1))).join(' ');
}
function categoryMeta(rawValue,fallback){
  const key=normalizeCategoryKey(rawValue)||normalizeCategoryKey(fallback)||'sem categoria';
  return {key:key.slice(0,48),label:(titleizeCategory(key)||fallback||'Sem categoria').slice(0,42)};
}
function normalizeWalletTxEntry(item){
  item=item||{};
  const note=txt(item.note||'',60);
  const meta=categoryMeta(item.category||note,item.type==='set'?'Ajuste manual':'Sem categoria');
  return Object.assign({},item,{note,category:meta.label,categoryKey:meta.key,prev:Number(item.prev)||0,value:Number(item.value)||0,debtorId:item.debtorId?String(item.debtorId):'',myDebtId:item.myDebtId?String(item.myDebtId):'',myDebtInstallment:Math.max(0,parseInt(item.myDebtInstallment||'0',10)||0)});
}
function normalizeCreditTxEntry(item){
  item=item||{};
  const desc=txt(item.desc||'',60);
  const fallback=item.type==='payment'?'Pagamento cartao':'Reserva cartao';
  const meta=categoryMeta(item.category||desc,item.type==='expense'?'Sem categoria':fallback);
  return Object.assign({},item,{desc,category:meta.label,categoryKey:meta.key,value:Number(item.value)||0});
}
function normalizeDebtorEntry(item){
  item=item||{};
  const installments=Math.min(999,Math.max(1,parseInt(item.installments||'1',10)||1));
  let paid=Boolean(item.paid);
  const rawAmount=Math.max(0,Number(item.amount)||0);
  const rawInstVal=Number(item.installmentValue);
  const installmentValue=Number.isFinite(rawInstVal)&&rawInstVal>0?rawInstVal:roundMoneyValue(installments>1&&rawAmount>0?rawAmount/installments:rawAmount);
  const reason=['card','loan','split','other'].includes(item.reason)?item.reason:'other';
  const phone=String(item.phone||'').replace(/\D/g,'').slice(0,15);
  const lastChargedAt=item.lastChargedAt||'';
  const charges=Array.isArray(item.charges)?item.charges.map(String).slice(-20):[];
  let payments=[];
  if(Array.isArray(item.payments)){
    payments=item.payments.filter(p=>p&&Number(p.value)>0).map(p=>({
      id:p.id||id(),
      value:roundMoneyValue(p.value),
      at:p.at||new Date().toISOString(),
      account:['conta','vale1','vale2','amex'].includes(p.account)?p.account:'conta',
      txId:p.txId||''
    }));
  }
  const totalPaid=payments.reduce((s,p)=>s+p.value,0);
  let installmentsPaid=Math.max(0,Math.min(installments,parseInt(item.installmentsPaid||String(paid?installments:0),10)||0));
  if(payments.length>0){
    paid=rawAmount>0 && totalPaid>=(rawAmount-0.01);
    installmentsPaid=paid?installments:Math.min(installments,installmentValue>0?Math.floor((totalPaid+0.01)/installmentValue):0);
  } else if(paid && installmentsPaid<installments){
    installmentsPaid=installments;
  }
  return Object.assign({},item,{
    id:item.id||id(),
    name:txt(item.name||'',30),
    amount:rawAmount,
    installmentValue:installmentValue,
    installments:installments,
    installmentsPaid:installmentsPaid,
    reason:reason,
    phone:phone,
    lastChargedAt:lastChargedAt,
    charges:charges,
    payments:payments,
    note:txt(item.note||'',50),
    payDate:item.payDate||'',
    paid:paid||installmentsPaid>=installments,
    paidAt:item.paidAt||'',
    at:item.at||new Date().toISOString()
  });
}

function normalizeDebtEntry(item){
  item=item||{};
  const installments=Math.min(999,Math.max(1,parseInt(item.installments||'1',10)||1));
  const paid=Boolean(item.paid);
  const installmentsPaid=Math.max(0,Math.min(installments,parseInt(item.installmentsPaid||String(paid?installments:0),10)||0));
  const rawInstallmentValue=Number(item.installmentValue);
  const rawAmount=Math.max(0,Number(item.amount)||0);
  const installmentValue=Math.max(0,Number.isFinite(rawInstallmentValue)&&rawInstallmentValue>0 ? rawInstallmentValue : (installments>1 ? rawAmount/installments : rawAmount));
  const reason=['house','loan','card','service','other'].includes(item.reason)?item.reason:'house';
  const payments=Array.isArray(item.payments)?item.payments.map(p=>({
    id:p.id||id(),
    value:Math.max(0,Number(p.value)||0),
    account:['conta','vale1','vale2','none'].includes(p.account)?p.account:'conta',
    at:p.at||new Date().toISOString()
  })).filter(p=>p.value>0):[];
  return Object.assign({},item,{
    id:item.id||id(),
    name:txt(item.name||'',30),
    amount:installmentValue,
    installmentValue:installmentValue,
    installments:installments,
    installmentsPaid:paid&&installmentsPaid<installments?installments:installmentsPaid,
    note:txt(item.note||'',50),
    payDate:item.payDate||'',
    paid:paid||installmentsPaid>=installments,
    paidAt:item.paidAt||'',
    reason,
    payments
  });
}
function pageFromHash(){
  const raw=String(window.location.hash||'').replace('#','');
  return ['home','credit','debts','goals','statement'].includes(raw)?raw:'home';
}
function syncPageFromHash(){
  ui.page=pageFromHash();
}
function syncHash(page){
  const next='#'+page;
  if(window.location.hash===next) return;
  try{
    if(window.history && window.history.replaceState) window.history.replaceState(null,'',next);
    else window.location.hash=next;
  }catch(err){
    window.location.hash=next;
  }
}
function scrollTopSafe(){
  try{ window.scrollTo({top:0,behavior:'smooth'}); }
  catch(err){ window.scrollTo(0,0); }
}
function scrollNodeIntoView(node){
  if(!node) return;
  try{ node.scrollIntoView({behavior:'smooth',block:'center'}); }
  catch(err){
    try{ node.scrollIntoView(true); }
    catch(err2){}
  }
}
function normalizeLoadedState(p){
  p=p||{};
  const parsedCredit = p.credit || {};
  const parsedCreditName = txt(parsedCredit.name || '',30);
  const creditName=parsedCreditName==='Cartão Prime'||!parsedCreditName?DEF.credit.name:parsedCredit.name;
  const base=Object.assign({},DEF,p,{appName:DEF.appName});
  return Object.assign(base,{
    habits:Array.isArray(p.habits)?p.habits.map(h=>Object.assign({},h,{date:h.date||today()})):DEF.habits,
    balances:Object.assign({},DEF.balances,p.balances||{}),
    tx:Array.isArray(p.tx)?p.tx.map(normalizeWalletTxEntry):[],
    credit:Object.assign({},DEF.credit,parsedCredit,{name:creditName,reserved:Math.max(0,Number(parsedCredit.reserved)||0),tx:Array.isArray(parsedCredit.tx)?parsedCredit.tx.map(normalizeCreditTxEntry):[]}),
    debtors:Array.isArray(p.debtors)?p.debtors.map(normalizeDebtorEntry):[],
    myDebts:Array.isArray(p.myDebts)?p.myDebts.map(normalizeDebtEntry):[],
    routineLog:Array.isArray(p.routineLog)?p.routineLog:[],
    skills:normalizeSkills(p.skills),
    goals:Array.isArray(p.goals)?p.goals.map(g=>({id:g.id||id(),name:g.name||'Objetivo',target:Number(g.target)||0,saved:Number(g.saved)||0,tx:Array.isArray(g.tx)?g.tx:[]})):[],
    dailyStats:typeof p.dailyStats==='object'&&p.dailyStats?p.dailyStats:{},
    focusSession:Object.assign({},DEF.focusSession,p.focusSession||{}),
    lastDate:p.lastDate||today()
  });
}
async function requestApi(path, options){
  if(!API_BASE) throw new Error('no_api_base');
  const req=Object.assign({},options||{});
  req.headers=Object.assign({'Content-Type':'application/json'},(options&&options.headers)||{});
  req.credentials='same-origin';
  const res=await fetch(API_BASE+path,req);
  if(res.status===401){
    clearStoredState();
    window.location.replace(loginLocation());
    throw new Error('unauthorized');
  }
  if(!res.ok) throw new Error('api_unavailable');
  return res.json();
}
function publishChannelsText(notifications){
  notifications=notifications||{};
  const labelMap={sent:'enviado',unconfigured:'off',no_chat:'sem chat',failed:'falhou',idle:'aguardando'};
  const telegram=labelMap[notifications.telegram]||'aguardando';
  const discord=labelMap[notifications.discord]||'aguardando';
  return `Telegram ${telegram} · Discord ${discord}`;
}
function publishReasonText(reason){
  const reasonMap={manual:'manual',close:'fechamento',autosave:'autosave',sync:'sync'};
  return reasonMap[reason]||'sync';
}
function publishStatusText(){
  if(publishSync.busy) return 'Sincronizando painel...';
  if(publishSync.lastError) return 'Falha ao publicar';
  if(publishSync.version>0){
    return `Link v${publishSync.version} sincronizado`;
  }
  return 'Link pronto para publicar';
}
function publishStampText(){
  if(publishSync.busy) return 'Sincronizando link e notificações do telefone.';
  if(publishSync.lastError) return 'Tente publicar novamente para atualizar a versão que abre no celular.';
  if(publishSync.version>0){
    const moment=formatStatusMoment(publishSync.updatedAt);
    const reason=publishReasonText(publishSync.reason);
    return moment?`Atualizado em ${moment} · ${reason}`:`Versão ${publishSync.version} pronta para abrir no telefone.`;
  }
  return 'Publique quando quiser gerar o link mais novo do telefone.';
}
function applyPublishInfo(info){
  info=info||{};
  publishSync.version=Math.max(0,Number(info.version)||0);
  publishSync.updatedAt=String(info.updatedAt||'');
  publishSync.reason=String(info.reason||'');
  publishSync.links=Object.assign({preferred:'',local:'',public:''},info.links||{});
  publishSync.notifications=Object.assign({telegram:'idle',discord:'idle'},info.notifications||{});
  publishSync.lastError='';
  renderPublishStatus();
}
function renderPublishStatus(){
  if(el.saveStatus){
    el.saveStatus.textContent=publishStatusText();
    el.saveStatus.title=publishSync.lastError||publishSync.links.preferred||'';
  }
  if(el.saveStamp){
    el.saveStamp.textContent=publishStampText();
    el.saveStamp.title=publishSync.links.preferred||'';
  }
  if(el.saveChannels){
    el.saveChannels.textContent=publishChannelsText(publishSync.notifications);
    el.saveChannels.title=publishSync.links.preferred||'';
  }
  if(el.saveAllBtn){
    el.saveAllBtn.disabled=publishSync.busy;
    el.saveAllBtn.textContent=publishSync.busy?'Salvando...':'Salvar tudo';
  }
  if(el.openShareLinkBtn){
    const hasLink=Boolean(publishSync.links.preferred);
    el.openShareLinkBtn.disabled=!hasLink;
    el.openShareLinkBtn.style.opacity=hasLink?'1':'.55';
  }
}
function desktopBackupStamp(info){
  info=info||{};
  return String(info.finishedAt||info.lastRunAt||info.startedAt||'');
}
function desktopBackupTone(){
  if(codeBackupSync.launching||codeBackupSync.status==='running') return 'running';
  if(codeBackupSync.status==='ok') return 'ok';
  if(codeBackupSync.status==='error') return 'error';
  return 'idle';
}
function formatStatusMoment(value){
  if(!value) return '';
  try{
    return new Date(value).toLocaleString('pt-BR',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});
  }catch(err){
    return value;
  }
}
function desktopBackupStatusText(){
  if(!DESKTOP_BACKUP_SUPPORTED) return 'GitHub via desktop';
  if(codeBackupSync.launching) return 'GitHub iniciando';
  if(codeBackupSync.status==='running') return 'GitHub salvando';
  if(codeBackupSync.status==='ok') return 'GitHub salvo';
  if(codeBackupSync.status==='error') return 'GitHub falhou';
  return 'GitHub aguardando';
}
function desktopBackupDetailText(){
  if(!DESKTOP_BACKUP_SUPPORTED) return 'Use esse botão no Weedverso aberto pelo desktop Windows.';
  if(codeBackupSync.status==='ok'){
    const parts=[];
    if(codeBackupSync.branch) parts.push(`branch ${codeBackupSync.branch}`);
    if(codeBackupSync.commit) parts.push(`commit ${codeBackupSync.commit}`);
    if(codeBackupSync.finishedAt) parts.push(`às ${formatStatusMoment(codeBackupSync.finishedAt)}`);
    return parts.join(' | ')||'Código confirmado no GitHub.';
  }
  if(codeBackupSync.status==='error'){
    const parts=[];
    if(codeBackupSync.message) parts.push(codeBackupSync.message);
    if(codeBackupSync.lastError) parts.push(codeBackupSync.lastError);
    return parts.join(' | ')||'O desktop não conseguiu salvar o código no GitHub.';
  }
  if(codeBackupSync.status==='running'||codeBackupSync.launching){
    return 'O botão dispara o backup do código no seu PC e devolve o resultado aqui.';
  }
  return 'Esse botão salva o código atual do PC no repositório GitHub sem abrir terminal.';
}
function applyDesktopCodeBackupStatus(info){
  info=info||{};
  codeBackupSync.status=String(info.status||'idle');
  codeBackupSync.message=String(info.message||'');
  codeBackupSync.startedAt=String(info.startedAt||'');
  codeBackupSync.finishedAt=String(info.finishedAt||'');
  codeBackupSync.lastRunAt=String(info.lastRunAt||'');
  codeBackupSync.branch=String(info.branch||'');
  codeBackupSync.commit=String(info.commit||'');
  codeBackupSync.remote=String(info.remote||'');
  codeBackupSync.changedFiles=Math.max(0,Number(info.changedFiles)||0);
  codeBackupSync.lastError=String(info.lastError||'');
  codeBackupSync.lastSeenAt=desktopBackupStamp(info);
  if(codeBackupSync.status!=='running') codeBackupSync.launching=false;
  renderDesktopCodeBackupStatus();
}
function renderDesktopCodeBackupStatus(){
  if(GIST_SYNC.hasToken()){
    GIST_SYNC.updateStatus(GIST_SYNC.statusText || '☁️ Git Conectado', 'ok');
    return;
  }
  if(el.codeBackupStatus){
    el.codeBackupStatus.textContent='☁️ Conecte o Git para espelhar no PC';
    el.codeBackupStatus.dataset.tone='idle';
    el.codeBackupStatus.title='Clique em Conectar Git para vincular com o PC';
  }
  if(el.saveCodeBtn){
    el.saveCodeBtn.disabled=false;
    el.saveCodeBtn.style.opacity='1';
    el.saveCodeBtn.textContent='☁️ Conectar Git';
    el.saveCodeBtn.title='Vincular sincronização com o GitHub';
  }
}

function stopDesktopCodeBackupPolling(){
  if(codeBackupSync.poller){
    clearInterval(codeBackupSync.poller);
    codeBackupSync.poller=null;
  }
}
async function hydrateDesktopCodeBackupStatus(){
  try{
    const info=await requestApi('/api/desktop-code-backup-status');
    applyDesktopCodeBackupStatus(info);
    return info;
  }catch(err){
    codeBackupSync.launching=false;
    renderDesktopCodeBackupStatus();
    return null;
  }
}
function launchDesktopBackupProtocol(){
  const uri='weedverso://github-backup?source=cloud-ui';
  const link=document.createElement('a');
  link.href=uri;
  link.style.display='none';
  document.body.appendChild(link);
  link.click();
  setTimeout(function(){
    try{ link.remove(); }catch(err){}
  },500);
}
function startDesktopCodeBackupPolling(previousSeenAt){
  stopDesktopCodeBackupPolling();
  codeBackupSync.pollDeadline=Date.now()+35000;
  let observedNewRun=false;
  const tick=async function(){
    try{
      const info=await requestApi('/api/desktop-code-backup-status');
      const seenAt=desktopBackupStamp(info);
      if(seenAt && seenAt!==previousSeenAt) observedNewRun=true;
      applyDesktopCodeBackupStatus(info);
      if(observedNewRun && String(info.status||'')!=='running'){
        stopDesktopCodeBackupPolling();
        return;
      }
      if(!observedNewRun && Date.now()>codeBackupSync.pollDeadline){
        codeBackupSync.launching=false;
        codeBackupSync.status='error';
        codeBackupSync.message='O desktop não respondeu ao pedido de backup.';
        codeBackupSync.lastError='';
        renderDesktopCodeBackupStatus();
        stopDesktopCodeBackupPolling();
      }
    }catch(err){
      if(Date.now()>codeBackupSync.pollDeadline){
        codeBackupSync.launching=false;
        codeBackupSync.status='error';
        codeBackupSync.message='Não consegui confirmar o backup do código na interface.';
        codeBackupSync.lastError='';
        renderDesktopCodeBackupStatus();
        stopDesktopCodeBackupPolling();
      }
    }
  };
  tick();
  codeBackupSync.poller=setInterval(tick,2000);
}
function triggerDesktopCodeBackup(){
  if(!DESKTOP_BACKUP_SUPPORTED) return;
  const previousSeenAt=codeBackupSync.lastSeenAt||desktopBackupStamp(codeBackupSync);
  codeBackupSync.launching=true;
  codeBackupSync.message='Pedindo backup do código ao desktop...';
  codeBackupSync.lastError='';
  renderDesktopCodeBackupStatus();
  try{
    launchDesktopBackupProtocol();
  }catch(err){
    codeBackupSync.launching=false;
    codeBackupSync.status='error';
    codeBackupSync.message='Não consegui chamar o app do desktop.';
    codeBackupSync.lastError=String(err&&err.message||'');
    renderDesktopCodeBackupStatus();
    return;
  }
  startDesktopCodeBackupPolling(previousSeenAt);
}
async function hydrateShareInfo(){
  try{
    const info=await requestApi('/api/share-info');
    applyPublishInfo(info);
  }catch(err){
    publishSync.lastError='Link ainda não publicado';
    renderPublishStatus();
  }
}
async function publishCurrentState(reason, force){
  if(publishSync.busy) return null;
  publishSync.busy=true;
  publishSync.lastError='';
  renderPublishStatus();
  try{
    writeStoredState(JSON.stringify(st));
    const payload=snapshotState();
    const response=await requestApi('/api/publish',{method:'POST',body:JSON.stringify({state:JSON.parse(payload),reason:reason||'manual',force:Boolean(force)})});
    serverSync.available=true;
    serverSync.lastSnapshot=payload;
    if(response && response.publish) applyPublishInfo(response.publish);
    return response && response.publish ? response.publish : null;
  }catch(err){
    serverSync.available=false;
    publishSync.lastError='Falha ao publicar o link';
    renderPublishStatus();
    throw err;
  }finally{
    publishSync.busy=false;
    renderPublishStatus();
  }
}
function snapshotState(){
  return JSON.stringify(st);
}
function hasMeaningfulData(state){
  state=state||{};
  const balances=state.balances||{};
  const credit=state.credit||{};
  return Boolean(
    txt(state.userName||'',24)||
    (Array.isArray(state.habits)&&state.habits.length)||
    (Array.isArray(state.tx)&&state.tx.length)||
    (Array.isArray(state.goals)&&state.goals.length)||
    (Array.isArray(state.debtors)&&state.debtors.length)||
    (Array.isArray(state.myDebts)&&state.myDebts.length)||
    Math.abs(Number((balances.conta||{}).amount)||0)>0||
    Math.abs(Number((balances.vale1||{}).amount)||0)>0||
    Math.abs(Number((balances.vale2||{}).amount)||0)>0||
    Math.abs(Number(credit.used)||0)>0||
    Math.abs(Number(credit.reserved)||0)>0
  );
}
async function hydrateFromServer(){
  try{
    const remote=await requestApi('/api/state');
    serverSync.available=true;
    if(remote && hasMeaningfulData(remote)){
      st=normalizeLoadedState(remote);
      rotateDay();
      writeStoredState(JSON.stringify(st));
      serverSync.lastSnapshot=snapshotState();
      renderAll();
    } else {
      serverSync.lastSnapshot=snapshotState();
      if(hasMeaningfulData(st)){
        await requestApi('/api/state',{method:'PUT',body:serverSync.lastSnapshot});
      }
    }
  }catch(err){
    serverSync.available=false;
    serverSync.lastSnapshot=snapshotState();
  }
}
function startServerPolling(){
  if(!API_BASE) return;
  if(serverSync.poller) clearInterval(serverSync.poller);
  const delay=document.visibilityState==='visible'?SERVER_POLL_ACTIVE_MS:SERVER_POLL_BACKGROUND_MS;
  serverSync.poller=setInterval(pullServerState,delay);
}
async function pullServerState(){
  if(!API_BASE || serverSync.pushing) return;
  try{
    const remote=await requestApi('/api/state');
    const next=JSON.stringify(remote||{});
    serverSync.available=true;
    if(next && next!==serverSync.lastSnapshot){
      st=normalizeLoadedState(remote);
      rotateDay();
      writeStoredState(JSON.stringify(st));
      serverSync.lastSnapshot=snapshotState();
      renderAll();
      hydrateShareInfo().catch(function(){});
    }
  }catch(err){
    serverSync.available=false;
  }
}
function scheduleServerPush(){
  if(!serverSync.initialized) return;
  if(serverSync.timer) clearTimeout(serverSync.timer);
  serverSync.timer=setTimeout(pushServerState,350);
}
async function pushServerState(options){
  serverSync.timer=null;
  if(!serverSync.initialized) return;
  if(serverSync.pushing) return;
  serverSync.pushing=true;
  try{
    const payload=snapshotState();
    await requestApi('/api/state',{method:'PUT',body:payload,keepalive:Boolean(options&&options.keepalive)});
    serverSync.available=true;
    serverSync.lastSnapshot=payload;
  }catch(err){
    serverSync.available=false;
  }finally{
    serverSync.pushing=false;
  }
}
function flushStateOnly(){
  if(!serverSync.initialized) return;
  const payload=snapshotState();
  if(serverSync.timer){
    clearTimeout(serverSync.timer);
    serverSync.timer=null;
  }
  try{
    if(navigator.sendBeacon){
      const blob=new Blob([payload],{type:'application/json'});
      const sent=navigator.sendBeacon(API_BASE+'/api/state-sync',blob);
      if(sent){
        serverSync.lastSnapshot=payload;
        return;
      }
    }
  }catch(err){}
  pushServerState({keepalive:true});
}
function flushServerState(reason){
  if(!serverSync.initialized) return;
  const payload=snapshotState();
  const syncPayload=JSON.stringify({state:JSON.parse(payload),reason:reason||'close',force:false});
  if(serverSync.timer){
    clearTimeout(serverSync.timer);
    serverSync.timer=null;
  }
  try{
    if(navigator.sendBeacon){
      const blob=new Blob([syncPayload],{type:'application/json'});
      const sent=navigator.sendBeacon(API_BASE+'/api/publish-sync',blob);
      if(sent){
        serverSync.lastSnapshot=payload;
        return;
      }
    }
  }catch(err){}
  publishCurrentState(reason||'close',false).catch(function(){});
}
function setVisible(node, visible){
  if(!node) return;
  if(visible) node.classList.remove('hidden');
  else node.classList.add('hidden');
}
function setActive(node, active){
  if(!node) return;
  if(active) node.classList.add('active');
  else node.classList.remove('active');
}

function readStoredState(){
  try{
    return STORAGE.getItem(KEY);
  }catch(err){
    return null;
  }
}
function writeStoredState(value){
  try{
    STORAGE.setItem(KEY,value);
  }catch(err){}
}
function readPrivacyMode(){
  try{
    return STORAGE.getItem(PRIVACY_KEY)==='1';
  }catch(err){
    return false;
  }
}
function writePrivacyMode(value){
  try{
    STORAGE.setItem(PRIVACY_KEY,value?'1':'0');
  }catch(err){}
}
function clearStoredState(){
  try{
    STORAGE.removeItem(KEY);
  }catch(err){}
}
function renderPrivacyToggle(){
  if(!el.privacyToggleBtn) return;
  setActive(el.privacyToggleBtn, ui.privacy);
  el.privacyToggleBtn.textContent=ui.privacy?'🙈':'👁';
  el.privacyToggleBtn.title=ui.privacy?'Mostrar resultados':'Ocultar resultados';
  el.privacyToggleBtn.setAttribute('aria-pressed', ui.privacy?'true':'false');
  document.body.setAttribute('data-privacy', ui.privacy?'on':'off');
}
function togglePrivacyMode(){
  ui.privacy=!ui.privacy;
  writePrivacyMode(ui.privacy);
  renderAll();
}
async function logout(){
  try{
    await requestApi('/api/logout',{method:'POST',body:'{}'});
  }catch(err){}
  clearStoredState();
  window.location.replace(loginLocation());
}

function load(){
  try{
    const raw=readStoredState();
    if(!raw) return normalizeLoadedState(DEF);
    const parsed=JSON.parse(raw);
    if(!hasMeaningfulData(parsed) && hasMeaningfulData(DEF)){
      return normalizeLoadedState(DEF);
    }
    return normalizeLoadedState(parsed);
  }catch(err){return normalizeLoadedState(DEF);}
}
function save(immediate){
  writeStoredState(JSON.stringify(st));
  if(typeof GIST_SYNC!=='undefined') GIST_SYNC.schedulePush();
  if(immediate) pushServerState({keepalive:true});
  else scheduleServerPush();
}
function money(v){return ui.privacy?'R$ ••••':new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(v||0);} 
function shortDate(i){return new Date(i).toLocaleString('pt-BR',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});} 
function fullDate(i){return new Date(i).toLocaleDateString('pt-BR',{weekday:'long',day:'2-digit',month:'2-digit',year:'numeric'});}
function dateBr(v){if(!v)return '--';const d=/^\d{4}-\d{2}-\d{2}$/.test(v)?parse(v):new Date(v);return d.toLocaleDateString('pt-BR',{day:'2-digit',month:'2-digit',year:'numeric'});}
function monthKeyFromValue(v,fallback){
  const raw=v||fallback||'';
  if(!raw) return '';
  let d;
  if(/^\d{4}-\d{2}-\d{2}$/.test(raw)) d=parse(raw);
  else d=new Date(raw);
  if(!(d instanceof Date)||Number.isNaN(d.getTime())) return '';
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`;
}
function monthLabelFromKey(key){
  if(!/^\d{4}-\d{2}$/.test(key||'')) return 'Sem mês';
  const [year,month]=key.split('-').map(Number);
  if(!year||!month||month<1||month>12) return 'Sem mês';
  const labels=(typeof MONTH_SHORT_LABELS!=='undefined'&&Array.isArray(MONTH_SHORT_LABELS))?MONTH_SHORT_LABELS:['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
  return `${labels[month-1]}/${year}`;
}
function currentMonthKey(){
  const d=new Date();
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`;
}
function creditExpenseMonthKey(){
  const months=creditChartMonths();
  const current=currentMonthKey();
  const chosen=String(ui.creditChartMonth||'').trim();
  if(chosen&&months.includes(chosen)) return chosen;
  if(months.includes(current)) return current;
  ui.creditChartMonth=months[0]||current;
  return ui.creditChartMonth;
}
function monthLabel(v,fallback){
  return monthLabelFromKey(monthKeyFromValue(v,fallback));
}
function monthInfoLabel(v,fallback){
  const label=monthLabel(v,fallback);
  return label==='Sem mês'?'Mês não definido':`Mês ${label}`;
}
function lastDaysStart(days){const d=new Date();d.setHours(0,0,0,0);d.setDate(d.getDate()-(days-1));return d;}
function startOfWeek(date){const d=new Date(date);const day=(d.getDay()+6)%7;d.setHours(0,0,0,0);d.setDate(d.getDate()-day);return d;}
function today(){const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;}
function dateKey(i){const d=new Date(i);return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;}
function days(a,b){const A=parse(a),B=parse(b);return Math.round((B-A)/86400000);} function parse(k){const [y,m,d]=k.split('-').map(Number);return new Date(y,m-1,d);} 
function id(){return Math.random().toString(36).slice(2,10)+Date.now().toString(36).slice(-5);} 
function defLabel(k){return k==='vale1'?'VA Mercado':k==='vale2'?'VA Refeição':'Saldo em Conta';}
function txt(v,m){return String(v||'').replace(/\s+/g,' ').trim().slice(0,m);} 
function esc(v){return String(v||'').replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function safe(v){return String(v||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function initial(n){return (n||'U').trim().charAt(0).toUpperCase();}
window.showPage=showPage;
window.addEventListener('hashchange',function(){
  syncPageFromHash();
  renderPage();
});
window.addEventListener('visibilitychange',function(){
  if(API_BASE && document.visibilityState==='hidden') flushStateOnly();
  if(API_BASE) startServerPolling();
  if(document.visibilityState==='visible'){
    if(API_BASE) pullServerState();
    if(typeof GIST_SYNC!=='undefined' && GIST_SYNC.hasToken()) GIST_SYNC.pull(true);
  }
});
window.addEventListener('pagehide',function(){ if(API_BASE) flushServerState('close'); });
window.addEventListener('beforeunload',function(){ if(API_BASE) flushServerState('close'); });
window.addEventListener('focus',function(){ if(API_BASE) pullServerState(); });
window.addEventListener('online',function(){
  if(typeof GIST_SYNC!=='undefined' && GIST_SYNC.hasToken()){
    GIST_SYNC.updateStatus('🌐 Reconectado! Sincronizando...','running');
    GIST_SYNC.push();
    GIST_SYNC.pull(true);
  }
});
window.addEventListener('offline',function(){
  if(typeof GIST_SYNC!=='undefined'){
    GIST_SYNC.updateStatus('📴 Modo Offline (dados salvos no aparelho)','idle');
  }
});
if('serviceWorker' in navigator){
  var swRefreshing=false;
  navigator.serviceWorker.addEventListener('controllerchange',function(){
    if(!swRefreshing && sessionStorage.getItem('sw_ctrl_reload')!=='v18'){
      swRefreshing=true;
      sessionStorage.setItem('sw_ctrl_reload','v18');
      window.location.href = window.location.pathname + '?v=' + Date.now();
    }
  });
  window.addEventListener('load',function(){
    navigator.serviceWorker.register('sw.js?v=18', { updateViaCache: 'none' }).then(function(reg){
      reg.update();
      if(reg.waiting){
        reg.waiting.postMessage({type:'SKIP_WAITING'});
      }
    }).catch(function(){});
  });
  document.addEventListener('visibilitychange',function(){
    if(document.visibilityState==='visible'){
      navigator.serviceWorker.getRegistration().then(function(reg){
        if(reg) reg.update();
      }).catch(function(){});
    }
  });
}


const mockEl = { ccDescLegend: {}, ccDescChart: {style:{}}, ccChartMonthTag: {} };
const el = new Proxy(mockEl, { get: (t, p) => t[p] || {} });
const st = { credit: { tx: [] } };
function creditExpenseMonthKey() { return '2023-10'; }
function monthLabelFromKey() { return 'Outubro'; }
function creditExpenseBreakdown() { return [{value:10, label:'Food', key:'Food'}]; }
function syncCreditExpenseMonthPicker(){}
function buildCategoryBreakdown() { return [{value:10, label:'Food', pct: 100, color: '#f00'}]; }
function compressBreakdown() { return [{value:10, label:'Food', pct: 100, color: '#f00'}]; }
function safe(x) { return x; }
function money(x) { return x.toString(); }
function spxEmoji(x) { return 'a'; }
const document = { getElementById: () => null };

try {
  renderCreditDescChart();
  console.log(el.ccDescLegend.innerHTML);
} catch (e) {}
