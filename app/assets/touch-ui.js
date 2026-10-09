/* Additive UI features. Never migrate, replace or reset financial state. */
(function () {
  'use strict';
  const FAVORITES_KEY = 'weedverso_ui_favorites_v1';
  const ACCOUNT_KEY = 'weedverso_ui_last_account_v1';
  const $touch = id => document.getElementById(id);
  const text = value => String(value || '');
  const accountName = key => (st.balances[key] || {}).label || defLabel(key);
  let favorites = readFavorites();
  let managingFavorites = false;
  let undoAction = null;
  let undoTimeout = null;
  let activeOverlay = null;
  let modalTrigger = null;
  let initialized = false;

  function readFavorites() {
    try {
      const rows = JSON.parse(localStorage.getItem(FAVORITES_KEY) || '[]');
      return Array.isArray(rows) ? rows.filter(f => f && typeof f.id === 'string' && typeof f.note === 'string' && ['out','in','card'].includes(f.tab) && ['conta','vale1','vale2'].includes(f.acc)).slice(0,8) : [];
    } catch (_) { return []; }
  }
  function writeFavorites() {
    try { localStorage.setItem(FAVORITES_KEY, JSON.stringify(favorites)); }
    catch (_) { showToast('Favoritos disponíveis nesta sessão; o navegador não permitiu salvá-los.', 'warn'); }
    renderFavorites();
  }
  function renderFavorites() {
    const list = $touch('touchFavorites');
    if (!list) return;
    list.innerHTML = favorites.length ? favorites.map(f => `<div class="touch-favorite"><button type="button" class="ghost touch-favorite-pick" data-touch-favorite="${esc(f.id)}">★ ${safe(f.note)}<small>${f.tab==='card'?'Cartão':safe(accountName(f.acc))} · ${f.tab==='in'?'Entrada':'Saída'}${Number(f.value)>0?' · '+money(Number(f.value)):''}</small></button>${managingFavorites?`<button type="button" class="iconBtn touch-favorite-remove" data-touch-remove-favorite="${esc(f.id)}" aria-label="Remover favorito ${esc(f.note)}">×</button>`:''}</div>`).join('') : '<p class="touch-favorites-hint">Preencha uma descrição e salve seu primeiro favorito abaixo.</p>';
    $touch('touchManageFavorites').hidden = !favorites.length;
    $touch('touchManageFavorites').textContent = managingFavorites ? 'Concluir' : 'Organizar';
  }
  function addFavorite(favorite) {
    if (!favorite.note.trim()) { showToast('Preencha a descrição para salvar um favorito.', 'warn'); return; }
    const existing = favorites.findIndex(f => f.note===favorite.note && f.acc===favorite.acc && f.tab===favorite.tab);
    if (existing<0 && favorites.length>=8) { showToast('Você já tem 8 favoritos. Use Organizar para remover um.', 'warn'); return; }
    const row = Object.assign({}, favorite, {id:existing>=0?favorites[existing].id:id(), note:txt(favorite.note,42)});
    if (existing>=0) favorites[existing] = row; else favorites.push(row);
    writeFavorites();
    showToast('Favorito salvo. Nenhum lançamento foi registrado.', 'ok');
  }
  function applyFavorite(favorite) {
    quickAddSheet.currentTab = favorite.tab;
    quickAddSheet.currentAcc = favorite.acc;
    quickAddSheet.updateTabUI();
    quickAddSheet.noteInput.value = favorite.note;
    quickAddSheet.valInput.value = Number(favorite.value)>0 ? String(Number(favorite.value)).replace('.',',') : '';
    $touch('touchQuickDetails').open = true;
    quickAddSheet.valInput.dispatchEvent(new Event('input', {bubbles:true}));
    quickAddSheet.valInput.focus();
    haptic('light');
  }
  function prepareQuick() {
    try {
      const account = localStorage.getItem(ACCOUNT_KEY);
      if (['conta','vale1','vale2'].includes(account)) quickAddSheet.currentAcc = account;
    } catch (_) {}
    const details = $touch('touchQuickDetails');
    if (details) details.open = false;
    managingFavorites = false;
    renderFavorites();
  }
  function updateQuickContext() {
    if (!quickAddSheet.accBtns) return;
    quickAddSheet.accBtns.forEach(b => {
      b.classList.toggle('active', b.dataset.acc===quickAddSheet.currentAcc);
      b.setAttribute('aria-pressed', String(b.dataset.acc===quickAddSheet.currentAcc));
    });
    quickAddSheet.tabBtns.forEach(b => b.setAttribute('aria-pressed', String(b.dataset.tab===quickAddSheet.currentTab)));
    const note = $touch('touchQuickContext');
    if (note) note.textContent = quickAddSheet.currentTab==='card' ? 'O gasto será registrado na fatura do cartão.' : `${quickAddSheet.currentTab==='in'?'Entrada em':'Saída de'} ${accountName(quickAddSheet.currentAcc)}. Confira antes de confirmar.`;
  }
  function updateFab() {
    const fab = $touch('fabQuickAddBtn');
    const labels = {home:'Lançamento rápido', credit:'Novo gasto no cartão', invest:'Aporte ou resgate', debts:'Nova dívida ou cobrança', statement:'Novo lançamento'};
    const label = labels[ui.page] || labels.home;
    fab.title = label;
    fab.setAttribute('aria-label', label);
    fab.innerHTML = `<span aria-hidden="true">+</span><span class="touch-fab-label">${ui.page==='invest'?'Movimentar':ui.page==='credit'?'Gasto':'Novo'}</span>`;
    document.querySelectorAll('.navBtn[data-page]').forEach(b => {
      if (b.dataset.page===ui.page) b.setAttribute('aria-current','page'); else b.removeAttribute('aria-current');
    });
  }
  function openTouchSheet(title, html) {
    const overlay = $touch('touchActionOverlay');
    $touch('touchActionTitle').textContent = title;
    $touch('touchActionBody').innerHTML = html;
    overlay.classList.add('open');
    overlay.setAttribute('aria-hidden','false');
    requestAnimationFrame(() => overlay.querySelector('.sheetClose').focus());
  }
  function closeTouchSheet() {
    const overlay = $touch('touchActionOverlay');
    overlay.classList.remove('open');
    overlay.setAttribute('aria-hidden','true');
  }
  function openContextAdd() {
    if (ui.page==='invest') {
      openTouchSheet('Movimentar investimentos', '<div class="touch-context-actions"><button type="button" class="ghost" data-touch-context="invest-add">+ Aporte<small>Somar um valor ao saldo investido</small></button><button type="button" class="ghost" data-touch-context="invest-sub">− Resgate<small>Registrar a retirada de um valor</small></button></div>');
    } else if (ui.page==='debts') {
      openTouchSheet('O que você quer adicionar?', '<div class="touch-context-actions"><button type="button" class="ghost" data-touch-context="debt-receive">A receber<small>Adicionar uma cobrança de quem deve a você</small></button><button type="button" class="ghost" data-touch-context="debt-pay">A pagar<small>Adicionar uma conta ou dívida sua</small></button></div>');
    } else quickAddSheet.open(ui.page==='credit'?'card':'out');
  }
  function chooseContext(action) {
    closeTouchSheet();
    if (action==='invest-add' || action==='invest-sub') {
      $touch(action==='invest-add'?'investOpenAddBtn':'investOpenSubBtn').click();
      requestAnimationFrame(() => {
        $touch('investFormBox').scrollIntoView({block:'center',behavior:'smooth'});
        $touch('investFormValue').focus({preventScroll:true});
      });
    } else {
      switchDebtsView(action==='debt-pay'?'myDebts':'debtors');
      $touch(action==='debt-pay'?'mdOpenFormBtn':'dvOpenFormBtn').click();
    }
  }
  function openTransaction(idValue, source, goalId) {
    const item = allTransactions().find(t => t.id===idValue && t.source===source && (t.goalId||'')===(goalId||''));
    if (!item) { showToast('Esse lançamento não está mais disponível. Atualize o extrato.', 'warn'); return; }
    const section = source==='food'?'food':source==='credit'?'credit':source==='goal'?'goal':'wallet';
    const editorSource = source==='food'?'wallet':source;
    openTouchSheet('Detalhes da movimentação', `<div class="touch-transaction-value ${item.cls}">${item.sign} ${money(item.value)}</div><dl class="touch-transaction-details"><div><dt>Movimentação</dt><dd>${safe(item.title)}</dd></div><div><dt>Descrição</dt><dd>${safe(item.note||'Sem descrição')}</dd></div><div><dt>Categoria</dt><dd>${safe(item.category)}</dd></div><div><dt>Data e horário</dt><dd>${safe(shortDate(item.at))}</dd></div></dl><button type="button" class="btn" data-touch-edit="${esc(idValue)}" data-touch-section="${esc(section)}" data-touch-source="${esc(editorSource)}" data-touch-goal="${esc(goalId||'')}">Editar lançamento</button>`);
  }
  function editTransaction(button) {
    const section = button.dataset.touchSection;
    closeTouchSheet();
    ui.statement[section] = true;
    ui.statementEditor = {section, source:button.dataset.touchSource, txId:button.dataset.touchEdit, goalId:button.dataset.touchGoal||''};
    renderAll();
    requestAnimationFrame(() => {
      const editor = document.querySelector('#statementPage .statementEditor');
      if (editor) { editor.scrollIntoView({block:'center',behavior:'smooth'}); const field=editor.querySelector('input'); if(field) field.focus({preventScroll:true}); }
    });
  }

  // Undo only the exact new operation, and only while its affected balance is
  // unchanged. A server refresh, edit or later operation must never be overwritten.
  function captureQuick(tab, acc) {
    return {kind:tab==='card'?'credit':'wallet',acc,tab,before:tab==='card'?Number(st.credit.used):Number((st.balances[acc]||{}).amount)};
  }
  function offerQuickUndo(before) {
    const row = before.kind==='credit' ? st.credit.tx[0] : st.tx[0];
    if (!row) return;
    before.entry = JSON.stringify(row);
    before.id = row.id;
    before.after = before.kind==='credit'?Number(st.credit.used):Number(st.balances[before.acc].amount);
    offerUndo(before, 'Lançamento registrado');
  }
  function captureInvestment(total) {
    return {kind:'investment',before:total,historyLength:st.investments.history.length};
  }
  function offerInvestmentUndo(before) {
    const rows=st.investments.history;
    if (rows.length!==before.historyLength+1) return;
    before.entry=JSON.stringify(rows[rows.length-1]);
    before.after=Number(st.investments.total);
    offerUndo(before, 'Investimento atualizado');
  }
  function clearUndo() {
    clearTimeout(undoTimeout);
    undoAction=null;
    $touch('touchUndoBar').hidden=true;
    document.body.classList.remove('touch-has-undo');
  }
  function offerUndo(action, message) {
    clearUndo();
    undoAction=action;
    $touch('touchUndoText').textContent=message;
    $touch('touchUndoBar').hidden=false;
    document.body.classList.add('touch-has-undo');
    undoTimeout=setTimeout(clearUndo,15000);
  }
  function undoLastAction() {
    const action=undoAction;
    if (!action) return;
    let valid=false;
    if (action.kind==='investment') {
      const rows=st.investments.history;
      valid=rows.length===action.historyLength+1 && JSON.stringify(rows[rows.length-1])===action.entry && Number(st.investments.total)===action.after;
      if (valid) { rows.pop(); st.investments.total=action.before; }
    } else {
      const rows=action.kind==='credit'?st.credit.tx:st.tx;
      const rowIndex=rows.findIndex(row=>row.id===action.id);
      const current=action.kind==='credit'?Number(st.credit.used):Number((st.balances[action.acc]||{}).amount);
      valid=rowIndex>=0 && JSON.stringify(rows[rowIndex])===action.entry && current===action.after;
      // Detect later entries even if their net effect happens to be zero.
      valid=valid && !rows.slice(0,rowIndex).some(row=>action.kind==='credit'||row.account===action.acc);
      if(valid) { rows.splice(rowIndex,1); if(action.kind==='credit') st.credit.used=action.before; else st.balances[action.acc].amount=action.before; }
    }
    clearUndo();
    if(!valid) { showToast('O saldo ou lançamento mudou. Use o extrato para revisar sem desfazer outras alterações.', 'warn'); return; }
    save(true); renderAll(); haptic('light'); showToast('A última operação foi desfeita.', 'ok');
  }

  function syncModalAccess() {
    const overlays=Array.from(document.querySelectorAll('.sheetOverlay'));
    const opened=overlays.filter(o=>o.classList.contains('open'));
    const next=opened[opened.length-1] || null;
    overlays.forEach(o=>{ o.inert=o!==next; });
    document.querySelectorAll('main.app,.dock,#fabQuickAddBtn').forEach(node=>{ node.inert=Boolean(next); });
    document.body.classList.toggle('touch-sheet-open',Boolean(next));
    if(next && !activeOverlay) modalTrigger=document.activeElement;
    if(!next && activeOverlay && modalTrigger && modalTrigger.isConnected) modalTrigger.focus({preventScroll:true});
    activeOverlay=next;
  }
  function handleModalKeys(event) {
    if(!activeOverlay) return;
    if(event.key==='Escape') {
      const close=activeOverlay.querySelector('.sheetClose,[data-touch-close]');
      if(close) { event.preventDefault(); close.click(); }
      return;
    }
    if(event.key!=='Tab') return;
    const targets=Array.from(activeOverlay.querySelectorAll('button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),summary,[tabindex="0"]')).filter(n=>n.getClientRects().length && !n.closest('[hidden]'));
    if(!targets.length) return;
    const first=targets[0],last=targets[targets.length-1];
    if(event.shiftKey && document.activeElement===first) { event.preventDefault(); last.focus(); }
    else if(!event.shiftKey && document.activeElement===last) { event.preventDefault(); first.focus(); }
  }
  function updateViewport() {
    const viewport=window.visualViewport;
    document.documentElement.style.setProperty('--touch-visible-height', `${viewport?viewport.height:window.innerHeight}px`);
    document.documentElement.style.setProperty('--touch-dock-height', `${Math.ceil(document.querySelector('.dock').getBoundingClientRect().height)}px`);
  }
  function init() {
    if(initialized || !quickAddSheet.noteInput) return;
    initialized=true;
    const form=$touch('quickAddForm');
    const notes=quickAddSheet.noteInput.closest('.sheetField');
    const categoryChips=$touch('quickCategoryChips');
    const details=document.createElement('details');
    details.id='touchQuickDetails'; details.className='touch-details';
    details.innerHTML='<summary>Descrição e atalhos (opcional)</summary>';
    form.insertBefore(details,notes); details.append(notes,categoryChips);
    notes.querySelector('label').htmlFor='quickAddNote';
    quickAddSheet.valInput.setAttribute('aria-label','Valor do lançamento em reais');
    quickAddSheet.valInput.setAttribute('enterkeyhint','next');
    quickAddSheet.noteInput.setAttribute('enterkeyhint','done');
    details.insertAdjacentHTML('beforeend','<button type="button" class="ghost" id="touchSaveFavorite">☆ Salvar como favorito</button>');
    const accountField=$touch('quickAddAccountField');
    accountField.insertAdjacentHTML('afterend','<p id="touchQuickContext" class="touch-context-note"></p>');
    $touch('quickCalcPreview').insertAdjacentHTML('afterend','<div class="touch-favorite-heading"><strong>Favoritos</strong><button type="button" class="ghost" id="touchManageFavorites" hidden>Organizar</button></div><div id="touchFavorites" class="touch-favorites"></div>');
    document.body.insertAdjacentHTML('beforeend','<div id="touchActionOverlay" class="sheetOverlay" aria-hidden="true" inert><div class="sheetCard" role="dialog" aria-modal="true" aria-labelledby="touchActionTitle"><div class="sheetHandle"></div><div class="sheetHeader"><h3 id="touchActionTitle" class="sheetTitle"></h3><button type="button" class="sheetClose" data-touch-close aria-label="Fechar detalhes">×</button></div><div id="touchActionBody" class="sheetForm"></div></div></div><div id="touchUndoBar" class="touch-undo" hidden><span id="touchUndoText" role="status" aria-live="polite"></span><button type="button" id="touchUndoButton" class="btn">Desfazer</button></div>');
    $touch('touchSaveFavorite').addEventListener('click',()=>{
      const value=evaluateMathExpression(quickAddSheet.valInput.value);
      addFavorite({note:quickAddSheet.noteInput.value,tab:quickAddSheet.currentTab,acc:quickAddSheet.currentAcc,value:Number.isFinite(value)&&value>0?value:0});
    });
    $touch('touchManageFavorites').addEventListener('click',()=>{ managingFavorites=!managingFavorites; renderFavorites(); });
    $touch('touchFavorites').addEventListener('click',event=>{
      const pick=event.target.closest('[data-touch-favorite]');
      const remove=event.target.closest('[data-touch-remove-favorite]');
      if(pick) { const favorite=favorites.find(f=>f.id===pick.dataset.touchFavorite); if(favorite) applyFavorite(favorite); }
      if(remove) { favorites=favorites.filter(f=>f.id!==remove.dataset.touchRemoveFavorite); writeFavorites(); }
    });
    quickAddSheet.accBtns.forEach(b=>b.addEventListener('click',()=>{ try{localStorage.setItem(ACCOUNT_KEY,quickAddSheet.currentAcc);}catch(_){} updateQuickContext(); }));
    $touch('quickAddValue').addEventListener('keydown',event=>{ if(event.key==='Enter') { event.preventDefault(); details.open=true; quickAddSheet.noteInput.focus(); } });
    $touch('touchActionOverlay').addEventListener('click',event=>{
      if(event.target===$touch('touchActionOverlay') || event.target.closest('[data-touch-close]')) closeTouchSheet();
      const action=event.target.closest('[data-touch-context]'); if(action) chooseContext(action.dataset.touchContext);
      const edit=event.target.closest('[data-touch-edit]'); if(edit) editTransaction(edit);
    });
    $touch('unifiedStatementFeed').addEventListener('click',event=>{ const row=event.target.closest('[data-touch-transaction]'); if(row) openTransaction(row.dataset.touchTransaction,row.dataset.touchSource,row.dataset.touchGoal); });
    $touch('touchUndoButton').addEventListener('click',undoLastAction);
    document.addEventListener('keydown',handleModalKeys);
    const observer=new MutationObserver(syncModalAccess);
    document.querySelectorAll('.sheetOverlay').forEach(o=>observer.observe(o,{attributes:true,attributeFilter:['class']}));
    if(window.visualViewport) window.visualViewport.addEventListener('resize',updateViewport);
    window.addEventListener('resize',updateViewport);
    if(window.ResizeObserver) new ResizeObserver(updateViewport).observe(document.querySelector('.dock'));
    updateViewport(); syncModalAccess(); renderFavorites(); updateFab(); updateQuickContext();
  }
  window.WEEDVERSO_TOUCH_UI={init,openContextAdd,prepareQuick,updateQuickContext,updateFab,captureQuick,offerQuickUndo,captureInvestment,offerInvestmentUndo};
  init();
})();
