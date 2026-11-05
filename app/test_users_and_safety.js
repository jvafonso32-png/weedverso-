const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

console.log('=== TESTE DE SEGURANÇA E MULTI-USUÁRIO WEEDVERSO ===\n');

const coreJsPath = fs.existsSync(path.join(__dirname, 'core/app.js'))
  ? path.join(__dirname, 'core/app.js')
  : (fs.existsSync(path.join(__dirname, '../core/app.js'))
      ? path.join(__dirname, '../core/app.js')
      : path.join(__dirname, 'app/core/app.js'));
const coreJsCode = fs.readFileSync(coreJsPath, 'utf8');

function createMockEnvironment(config, initialStorage = {}, elementsMap = null) {
  const store = { ...initialStorage };
  const localStorageMock = {
    getItem: (k) => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
    removeItem: (k) => { delete store[k]; },
    clear: () => { Object.keys(store).forEach(k => delete store[k]); },
    _store: store
  };

  const createDefaultEl = () => {
    const el = {
      style: {},
      innerHTML: '',
      textContent: '',
      value: '',
      appendChild: () => {},
      querySelector: () => el,
      querySelectorAll: () => [el],
      addEventListener: function(evt, cb) {
        this.listeners = this.listeners || {};
        this.listeners[evt] = this.listeners[evt] || [];
        this.listeners[evt].push(cb);
      },
      click: function() {
        if (this.onclick) this.onclick();
        if (this.listeners && this.listeners.click) {
          this.listeners.click.forEach(cb => cb());
        }
      },
      classList: { add: ()=>{}, remove: ()=>{}, toggle: ()=>{}, contains: ()=>false },
      setAttribute: () => {},
      removeAttribute: () => {},
      getAttribute: (a) => (a === 'data-page' ? 'home' : null),
      dataset: {},
      getBoundingClientRect: () => ({width:100, height:100, left:0, top:0}),
      parentNode: { parentNode: {} },
      focus: () => {},
      getContext: () => ({
        clearRect: () => {},
        beginPath: () => {},
        arc: () => {},
        moveTo: () => {},
        lineTo: () => {},
        fill: () => {},
        stroke: () => {}
      }),
      closest: () => el
    };
    el.parentNode.parentNode = el;
    return el;
  };

  const fakeEl = createDefaultEl();

  const getEl = (sel) => {
    if (!elementsMap) return fakeEl;
    const key = String(sel || '').replace(/^[#.]/, '');
    if (!elementsMap[key]) {
      elementsMap[key] = createDefaultEl();
    }
    return elementsMap[key];
  };

  const sandbox = {
    console,
    setTimeout,
    clearTimeout,
    setInterval,
    clearInterval,
    Intl,
    Date,
    Math,
    JSON,
    Array,
    Object,
    String,
    Number,
    Boolean,
    RegExp,
    Map,
    Set,
    fetch: async () => ({ ok: false, status: 404, json: async () => ({}) }),
    location: { hash: '', search: '', protocol: 'https:', origin: 'https://test.local', pathname: '/' },
    window: null,
    document: {
      getElementById: (id) => getEl(id),
      querySelector: (sel) => getEl(sel),
      querySelectorAll: (sel) => [getEl(sel)],
      addEventListener: () => {},
      createElement: () => createDefaultEl(),
      body: fakeEl,
      visibilityState: 'visible'
    },
    navigator: {
      userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
      serviceWorker: { register: () => Promise.resolve(), addEventListener: () => {}, getRegistration: () => Promise.resolve() },
      storage: { persist: () => Promise.resolve() }
    },
    localStorage: localStorageMock,
    sessionStorage: localStorageMock,
  };

  sandbox.window = {
    addEventListener: () => {},
    location: sandbox.location,
    requestAnimationFrame: (cb) => cb(),
    history: { replaceState: () => {} },
    WEEDVERSO_CONFIG: config,
    localStorage: localStorageMock,
    sessionStorage: localStorageMock
  };

  return { sandbox, store };
}

// -------------------------------------------------------------
// TESTE 1: CARREGAMENTO DE TODOS OS PERFIS DE USUÁRIOS
// -------------------------------------------------------------
console.log('--- TESTE 1: Montagem de todos os usuários (João, André, Júlia) ---');

const usersConfig = [
  {
    name: 'João (Default)',
    config: {
      userId: 'default',
      userName: 'João',
      theme: 'aqua',
      storageKey: 'rotina_prime_v2'
    }
  },
  {
    name: 'André',
    config: {
      userId: 'andre',
      userName: 'André',
      theme: 'blue',
      storageKey: 'weedverso_andre_v1',
      defaultBalances: { conta: {label:'Conta Principal', amount: 0}, reserva: {label:'Reserva', amount: 0} },
      defaultCreditName: 'Cartão Principal'
    }
  },
  {
    name: 'Júlia',
    config: {
      userId: 'julia',
      userName: 'Júlia',
      theme: 'crimson',
      storageKey: 'weedverso_julia_v1',
      defaultBalances: { conta: {label:'Conta Principal', amount: 0}, reserva: {label:'Reserva', amount: 0} },
      defaultCreditName: 'Cartão Principal'
    }
  }
];

usersConfig.forEach(u => {
  const { sandbox } = createMockEnvironment(u.config);
  vm.createContext(sandbox);
  vm.runInContext(coreJsCode, sandbox);
  assert(typeof sandbox.window.mergeStates === 'function', 'mergeStates deve estar exposto');
  assert(typeof sandbox.window.saveSecuritySnapshot === 'function', 'saveSecuritySnapshot deve estar exposto');
  console.log(`  [OK] Perfil ${u.name} montou perfeitamente.`);
});

// -------------------------------------------------------------
// TESTE 2: HIGIENIZAÇÃO NÃO-DESTRUTIVA E SNAPSHOT DE SEGURANÇA
// -------------------------------------------------------------
console.log('\n--- TESTE 2: Higienização Não-Destrutiva no André e Snapshot ---');

const andreConfig = {
  userId: 'andre',
  userName: 'André',
  theme: 'blue',
  storageKey: 'weedverso_andre_v1',
  defaultBalances: { conta: {label:'Conta Principal', amount: 0}, reserva: {label:'Reserva', amount: 0} },
  defaultCreditName: 'Cartão Principal',
  defaultCreditUsed: 0,
  defaultCreditReserved: 0
};

// Simulando que o celular do André tinha dados cadastrados (transações, dívidas, hábitos, metas),
// mas os saldos vazaram do usuário padrão (AMEX e 5803.23).
const leakedAndreState = {
  appName: 'weedverso',
  userName: 'André',
  balances: {
    conta: { label: 'Saldo em Conta', amount: 5803.23 },
    vale1: { label: 'Alelo Alimentação', amount: 2075.92 }
  },
  credit: {
    name: 'AMEX',
    used: 4758.75,
    reserved: 814.82,
    tx: [{ id: 'ctx-1', desc: 'Uber', val: 25.5, at: '2026-11-01' }]
  },
  tx: [
    { id: 'tx-101', desc: 'Salário André', val: 3500, type: 'in', cat: 'salario', at: '2026-11-01' },
    { id: 'tx-102', desc: 'Mercado Mensal', val: 450, type: 'out', cat: 'mercado', at: '2026-11-02' }
  ],
  debtors: [
    { id: 'deb-1', name: 'Carlos', total: 150, tx: [] }
  ],
  myDebts: [
    { id: 'mdeb-1', name: 'Empréstimo', total: 600, tx: [] }
  ],
  habits: [
    { id: 'hab-a1', name: 'Água (2L)', goal: '2000ml', done: true, lastDoneAt: '2026-11-02T10:00:00Z', skillTag: 'saude' }
  ],
  goals: [
    { id: 'g-1', name: 'Reserva Emergência', target: 5000, saved: 1200, tx: [] }
  ]
};

const initialStore = {
  'weedverso_andre_v1': JSON.stringify(leakedAndreState)
};

const { sandbox: andreSandbox, store: andreStore } = createMockEnvironment(andreConfig, initialStore);
vm.createContext(andreSandbox);
vm.runInContext(coreJsCode, andreSandbox);

// 2.1 Verifica que o snapshot de seguranca foi criado ANTES da higienizacao
const snapshotKey = 'weedverso_andre_v1_snap_migration';
assert(andreStore[snapshotKey], `Snapshot ${snapshotKey} DEVE existir no localStorage`);
const parsedSnapshot = JSON.parse(andreStore[snapshotKey]);
assert.strictEqual(parsedSnapshot.balances.conta.amount, 5803.23, 'Snapshot deve conter o estado original pré-sanitização');
assert.strictEqual(parsedSnapshot.tx.length, 2, 'Snapshot deve conter as transações');
console.log(`  [OK] Snapshot versionado salvo com sucesso em: "${snapshotKey}"`);

// 2.2 Verifica que os saldos foram sanitizados para os valores do André (0 e Cartão Principal)
const savedSanitizedState = JSON.parse(andreStore['weedverso_andre_v1']);
assert.strictEqual(savedSanitizedState.balances.conta.amount, 0, 'Saldo em conta deve ser sanitizado para 0');
assert.strictEqual(savedSanitizedState.balances.conta.label, 'Conta Principal', 'Label deve ser do André');
assert.strictEqual(savedSanitizedState.credit.name, 'Cartão Principal', 'Nome do cartão deve ser Cartão Principal');
assert.strictEqual(savedSanitizedState.credit.used, 0, 'Credit used deve ser 0');
assert.strictEqual(savedSanitizedState.credit.reserved, 0, 'Credit reserved deve ser 0');
console.log('  [OK] Higienização sanitizou saldos e cartão para os padrões do André.');

// 2.3 CRÍTICO: Verifica que as transações, dívidas, hábitos e metas NUNCA foram zeradas!
assert.strictEqual(savedSanitizedState.tx.length, 2, 'Transações (tx) NÃO podem ser zeradas');
assert.strictEqual(savedSanitizedState.tx[0].desc, 'Salário André');
assert.strictEqual(savedSanitizedState.tx[1].desc, 'Mercado Mensal');
assert.strictEqual(savedSanitizedState.credit.tx.length, 1, 'Transações do cartão NÃO podem ser zeradas');
assert.strictEqual(savedSanitizedState.debtors.length, 1, 'Devedores (debtors) NÃO podem ser zerados');
assert.strictEqual(savedSanitizedState.debtors[0].name, 'Carlos');
assert.strictEqual(savedSanitizedState.myDebts.length, 1, 'Minhas dívidas (myDebts) NÃO podem ser zeradas');
assert.strictEqual(savedSanitizedState.myDebts[0].name, 'Empréstimo');
assert.strictEqual(savedSanitizedState.habits.length, 1, 'Hábitos (habits) NÃO podem ser zerados');
assert.strictEqual(savedSanitizedState.habits[0].done, true);
assert.strictEqual(savedSanitizedState.goals.length, 1, 'Metas (goals) NÃO podem ser zeradas');
assert.strictEqual(savedSanitizedState.goals[0].name, 'Reserva Emergência');
console.log('  [OK] NENHUM dado do usuário foi perdido: tx, debtors, myDebts, habits e goals 100% PRESERVADOS!');

// -------------------------------------------------------------
// TESTE 2.1: HIGIENIZAÇÃO NÃO-DESTRUTIVA NA JÚLIA E SNAPSHOT
// -------------------------------------------------------------
console.log('\n--- TESTE 2.1: Higienização Não-Destrutiva na Júlia e Snapshot ---');

const juliaConfig = {
  userId: 'julia',
  userName: 'Júlia',
  theme: 'crimson',
  storageKey: 'weedverso_julia_v1',
  defaultBalances: { conta: {label:'Conta Principal', amount: 0}, reserva: {label:'Reserva', amount: 0} },
  defaultCreditName: 'Cartão Principal',
  defaultCreditUsed: 0,
  defaultCreditReserved: 0
};

const leakedJuliaState = {
  appName: 'weedverso',
  userName: 'Júlia',
  balances: {
    conta: { label: 'Saldo em Conta', amount: 5803.23 }
  },
  credit: {
    name: 'AMEX',
    used: 4758.75,
    reserved: 814.82,
    tx: []
  },
  tx: [
    { id: 'tx-j1', desc: 'Presente', val: 120, at: '2026-11-01' }
  ],
  debtors: [
    { id: 'deb-j1', name: 'Amiga', total: 50, tx: [] }
  ],
  myDebts: [],
  habits: [
    { id: 'hab-j1', name: 'Água (2L)', done: true }
  ],
  goals: []
};

const { sandbox: juliaSandbox, store: juliaStore } = createMockEnvironment(juliaConfig, {
  'weedverso_julia_v1': JSON.stringify(leakedJuliaState)
});
vm.createContext(juliaSandbox);
vm.runInContext(coreJsCode, juliaSandbox);

const juliaSnapKey = 'weedverso_julia_v1_snap_migration';
assert(juliaStore[juliaSnapKey], `Snapshot ${juliaSnapKey} deve existir no localStorage`);
const savedSanitizedJulia = JSON.parse(juliaStore['weedverso_julia_v1']);
assert.strictEqual(savedSanitizedJulia.balances.conta.amount, 0, 'Saldo Júlia sanitizado para 0');
assert.strictEqual(savedSanitizedJulia.credit.name, 'Cartão Principal', 'Cartão Júlia sanitizado');
assert.strictEqual(savedSanitizedJulia.tx.length, 1, 'Transação da Júlia mantida');
assert.strictEqual(savedSanitizedJulia.debtors.length, 1, 'Devedor da Júlia mantido');
assert.strictEqual(savedSanitizedJulia.habits.length, 1, 'Hábito da Júlia mantido');
console.log(`  [OK] Snapshot versionado salvo com sucesso em: "${juliaSnapKey}"`);
console.log('  [OK] Júlia: saldos sanitizados e transações/dívidas 100% PRESERVADAS!');

// -------------------------------------------------------------
// TESTE 3: PROTEÇÃO CONTRA SOBRESCRITA POR GIST VAZIO
// -------------------------------------------------------------
console.log('\n--- TESTE 3: Proteção contra sobrescrita por Gist vazio no mergeStates e pull ---');

const mergeStatesFn = andreSandbox.window.mergeStates;

const localStateWithData = {
  lastUpdatedAt: '2026-11-01T12:00:00.000Z',
  balances: { conta: { label: 'Conta Principal', amount: 1500 } },
  credit: { name: 'Cartão Principal', used: 300, reserved: 50, tx: [{ id: 'ctx-local', desc: 'Farmácia', val: 50, at: '2026-11-01' }] },
  tx: [
    { id: 'tx-1', desc: 'Salário', val: 5000, at: '2026-11-01' },
    { id: 'tx-2', desc: 'Aluguel', val: 1200, at: '2026-11-02' }
  ],
  debtors: [{ id: 'deb-1', name: 'Marcos', total: 80, tx: [] }],
  myDebts: [{ id: 'md-1', name: 'Parcela TV', total: 200, tx: [] }],
  habits: [{ id: 'h-1', name: 'Treino', done: true }],
  goals: [{ id: 'g-1', name: 'Carro', target: 20000, saved: 3000, tx: [] }]
};

// Cenário A: Remote é vazio ({})
const emptyRemote1 = {};
const result1 = mergeStatesFn(localStateWithData, emptyRemote1);
assert.strictEqual(result1.tx.length, 2, 'mergeStates não deve apagar tx quando remote é {}');
assert.strictEqual(result1.balances.conta.amount, 1500, 'mergeStates não deve apagar saldos');
assert.strictEqual(result1.debtors.length, 1, 'mergeStates não deve apagar debtors');
console.log('  [OK] mergeStates com Remote={}: Dados locais mantidos intactos.');

// Cenário B: Remote é objeto com arrays vazios e timestamp mais recente (simulando Gist recém-criado)
const emptyRemoteWithNewDate = {
  lastUpdatedAt: '2026-11-02T23:59:59.000Z',
  tx: [],
  debtors: [],
  myDebts: [],
  goals: [],
  credit: { used: 0, reserved: 0, tx: [] },
  balances: { conta: { amount: 0 } }
};
const result2 = mergeStatesFn(localStateWithData, emptyRemoteWithNewDate);
assert.strictEqual(result2.tx.length, 2, 'mergeStates não deve apagar tx mesmo se Gist remoto vazio tiver timestamp mais novo');
assert.strictEqual(result2.balances.conta.amount, 1500, 'Saldos locais não devem ser zerados');
assert.strictEqual(result2.credit.used, 300, 'Crédito local não deve ser zerado');
assert.strictEqual(result2.debtors.length, 1, 'Devedores mantidos');
assert.strictEqual(result2.myDebts.length, 1, 'Minhas dívidas mantidas');
assert.strictEqual(result2.goals.length, 1, 'Metas mantidas');
console.log('  [OK] mergeStates com Gist vazio de timestamp novo: Dados locais NUNCA são sobrescritos.');

// Cenário C: Remote tem dados válidos (deve mesclar sem perder locais)
const validRemote = {
  lastUpdatedAt: '2026-11-02T15:00:00.000Z',
  balances: { conta: { label: 'Conta Principal', amount: 1450 } },
  credit: { name: 'Cartão Principal', used: 350, reserved: 50, tx: [{ id: 'ctx-remote', desc: 'Restaurante', val: 50, at: '2026-11-02' }] },
  tx: [
    { id: 'tx-3', desc: 'Lanche', val: 50, at: '2026-11-02' }
  ],
  debtors: [{ id: 'deb-2', name: 'Ana', total: 40, tx: [] }]
};
const result3 = mergeStatesFn(localStateWithData, validRemote);
assert.strictEqual(result3.tx.length, 3, 'mergeStates com dados remotos válidos deve conter 3 transações (2 locais + 1 remota)');
assert.strictEqual(result3.credit.tx.length, 2, 'Deve conter as transações de crédito locais e remotas');
assert.strictEqual(result3.debtors.length, 2, 'Deve conter os devedores locais e remotos');
console.log('  [OK] mergeStates com Remote válido: Mesclagem perfeita de transações e dívidas.');

// -------------------------------------------------------------
// TESTE 4: PULL COM GIST REMOTO VAZIO
// -------------------------------------------------------------
console.log('\n--- TESTE 4: Simulação de GIST_SYNC.pull com resposta vazia ---');

async function testGistPullEmptyProtection() {
  const { sandbox, store } = createMockEnvironment(andreConfig, {
    'weedverso_andre_v1': JSON.stringify(localStateWithData),
    'weedverso_andre_gh_sync_token': 'fake_token_123',
    'weedverso_andre_gh_sync_gist_id': 'fake_gist_456'
  });

  // Mock fetch retornando Gist com arquivo vazio ou {}
  sandbox.fetch = async (url) => {
    return {
      ok: true,
      status: 200,
      json: async () => ({
        files: {
          'weedverso_state.json': {
            content: '{}' // Gist vazio
          }
        }
      })
    };
  };

  vm.createContext(sandbox);
  vm.runInContext(coreJsCode, sandbox);

  // Executa GIST_SYNC.pull
  const GIST_SYNC = sandbox.window.GIST_SYNC;
  assert(GIST_SYNC, 'GIST_SYNC deve existir no window');
  const pullResult = await GIST_SYNC.pull(true);

  // Verifica estado apos pull
  const stateAfterPull = JSON.parse(store['weedverso_andre_v1']);
  assert.strictEqual(stateAfterPull.tx.length, 2, 'Transações locais NÃO foram apagadas pelo Gist vazio');
  assert.strictEqual(stateAfterPull.balances.conta.amount, 1500, 'Saldos mantidos');
  assert.strictEqual(stateAfterPull.debtors.length, 1, 'Devedores mantidos');
  console.log('  [OK] GIST_SYNC.pull protegeu os dados locais e impediu que o Gist vazio apagasse nada.');
}

testGistPullEmptyProtection().then(() => {
  // -------------------------------------------------------------
  // TESTE 5: CUSTOMIZAÇÕES EXCLUSIVAS DO USUÁRIO JOÃO (IS_DEFAULT_USER)
  // -------------------------------------------------------------
  console.log('\n--- TESTE 5: Customizações Exclusivas do Usuário João ---');

  const joaoInitialState = {
    appName: 'weedverso',
    userName: 'João',
    balances: {
      conta: { label: 'Saldo em Conta', amount: 1785.15 },
      vale1: { label: 'Alelo Alimentação', amount: 981.06 },
      vale2: { label: 'Alelo Refeição', amount: 693.18 },
      reserva: { label: 'Reserva', amount: 50.0 }
    },
    credit: {
      name: 'AMEX',
      used: 4758.75,
      reserved: 814.82,
      tx: []
    },
    tx: [],
    debtors: [],
    myDebts: [],
    habits: [],
    goals: []
  };

  const joaoElements = {};
  const joaoEnv = createMockEnvironment({
    userId: 'default',
    userName: 'João',
    theme: 'aqua',
    storageKey: 'rotina_prime_v2'
  }, {
    'rotina_prime_v2': JSON.stringify(joaoInitialState)
  }, joaoElements);

  vm.createContext(joaoEnv.sandbox);
  vm.runInContext(coreJsCode, joaoEnv.sandbox);

  // 5.1 Verifica snapshot de backup automático salvo para o João
  const joaoSnapKey = 'rotina_prime_v2_snap_joao_backup';
  assert(joaoEnv.store[joaoSnapKey], 'Snapshot ' + joaoSnapKey + ' deve ter sido salvo');
  console.log('  [OK] Snapshot de backup do João salvo com sucesso em: ' + joaoSnapKey);

  // 5.2 Verifica que na tela inicial (finGrid) o box de saldo reserva foi removido
  const joaoStateAfterLoad = JSON.parse(joaoEnv.store['rotina_prime_v2']);
  assert.strictEqual(joaoStateAfterLoad.balances.reserva, undefined, 'Chave reserva não deve existir em balances no João');
  assert.strictEqual(joaoStateAfterLoad.balances.conta.amount, 1835.15, 'Saldo residual de 50 da reserva foi somado na conta corrente do João');
  console.log('  [OK] Tela inicial do João: Box saldo reserva removido e saldo preservado na conta corrente.');

  // 5.3 Verifica que na aba cartões as ações rápidas NÃO existem mais (ocultas) e layout remodelado
  assert.strictEqual(joaoElements['ccQuickActionsSection'].style.display, 'none', 'Ações rápidas devem estar ocultas no João');
  assert.strictEqual(joaoElements['ccReserveStandardLayout'].style.display, 'none', 'Ajuste padrão deve estar oculto no João');
  assert.strictEqual(joaoElements['ccReserveDefaultLayout'].style.display, 'block', 'Layout remodelado deve estar ativo no João');
  console.log('  [OK] Aba cartões do João: Ações Rápidas removidas e ajuste de reserva remodelado.');

  // 5.4 Teste do box de adicionar e remover saldo SOMENTE na reserva (como era antes)
  const defaultReserveVal = joaoElements['ccDefaultReserveValue'];
  const defaultReserveIn = joaoElements['ccDefaultReserveIn'];
  const defaultReserveOut = joaoElements['ccDefaultReserveOut'];
  assert(defaultReserveVal && defaultReserveIn && defaultReserveOut, 'Box de adicionar e remover saldo na reserva deve existir');

  // Adiciona 100 na reserva
  defaultReserveVal.value = '100.00';
  defaultReserveIn.click();
  let stateAfterAdd = JSON.parse(joaoEnv.store['rotina_prime_v2']);
  assert.strictEqual(stateAfterAdd.credit.reserved, 914.82, 'Reserva do cartão deve ser incrementada em 100');
  assert.strictEqual(stateAfterAdd.balances.conta.amount, 1835.15, 'Conta corrente NÃO deve ser alterada ao adicionar saldo somente na reserva');
  assert(stateAfterAdd.credit.tx.some(t => t.type === 'reserve-in' && t.value === 100), 'Transação reserve-in registrada');

  // Remove 14.82 da reserva
  defaultReserveVal.value = '14.82';
  defaultReserveOut.click();
  let stateAfterSub = JSON.parse(joaoEnv.store['rotina_prime_v2']);
  assert.strictEqual(stateAfterSub.credit.reserved, 900, 'Reserva do cartão deve ter sido reduzida para 900');
  assert.strictEqual(stateAfterSub.balances.conta.amount, 1835.15, 'Conta corrente permanece intacta ao retirar da reserva');
  console.log('  [OK] Box de adicionar e remover saldo funcionou exclusivamente na reserva sem afetar conta corrente!');

  // 5.5 Teste do botão: Levar saldo da reserva direto para a conta corrente e zerar
  const transferBtn = joaoElements['ccTransferToContaBtn'];
  assert(transferBtn, 'Botão de transferência da reserva deve existir');

  // Simula clique no botão remodelado
  transferBtn.click();

  const joaoFinalState = JSON.parse(joaoEnv.store['rotina_prime_v2']);
  assert.strictEqual(joaoFinalState.credit.reserved, 0, 'Reserva do cartão do João deve ser ZERADA');
  assert.strictEqual(joaoFinalState.balances.conta.amount, 2735.15, 'Saldo da conta corrente do João recebeu os 900.00 da reserva');
  assert(joaoFinalState.credit.tx.some(t => t.type === 'reserve-out' && t.value === 900), 'Transação reserve-out registrada no cartão');
  assert(joaoFinalState.tx.some(t => t.account === 'conta' && t.type === 'in' && t.value === 900), 'Transação de entrada registrada na conta');
  console.log('  [OK] Botão remodelado funcionou: Transferiu R$ 900,00 para a conta corrente e zerou a reserva com histórico!');

  // -------------------------------------------------------------
  // TESTE 6: GARANTIA ABSOLUTA DE NÃO ALTERAÇÃO NO ANDRÉ E NA JÚLIA
  // -------------------------------------------------------------
  console.log('\n--- TESTE 6: Garantia de Não Alteração para André e Júlia ---');

  const andreElements = {};
  const andreEnv = createMockEnvironment({
    userId: 'andre',
    userName: 'André',
    theme: 'blue',
    storageKey: 'weedverso_andre_v1',
    defaultBalances: { conta: {label:'Conta Principal', amount: 0}, reserva: {label:'Reserva', amount: 150} }
  }, {}, andreElements);

  vm.createContext(andreEnv.sandbox);
  vm.runInContext(coreJsCode, andreEnv.sandbox);

  // 6.1 André mantém ações rápidas visíveis
  assert.strictEqual(andreElements['ccQuickActionsSection'].style.display, 'block', 'Ações rápidas devem permanecer visíveis no André');
  assert.strictEqual(andreElements['ccReserveStandardLayout'].style.display, 'block', 'Ajuste padrão deve permanecer visível no André');
  assert.strictEqual(andreElements['ccReserveDefaultLayout'].style.display, 'none', 'Layout remodelado deve permanecer oculto no André');

  // 6.2 André mantém o box de reserva na tela inicial (finGrid)
  const andreState = JSON.parse(andreEnv.store['weedverso_andre_v1']);
  assert(andreState.balances.reserva, 'André DEVE manter o saldo reserva em balances');
  assert.strictEqual(andreState.balances.reserva.label, 'Reserva', 'Label de reserva do André mantido');
  console.log('  [OK] André: 100% INTACTO (Ações Rápidas, Ajuste Padrão e Box de Reserva na tela inicial mantidos).');

  const juliaElements = {};
  const juliaEnv = createMockEnvironment({
    userId: 'julia',
    userName: 'Júlia',
    theme: 'crimson',
    storageKey: 'weedverso_julia_v1',
    defaultBalances: { conta: {label:'Conta Principal', amount: 0}, reserva: {label:'Reserva', amount: 200} }
  }, {}, juliaElements);

  vm.createContext(juliaEnv.sandbox);
  vm.runInContext(coreJsCode, juliaEnv.sandbox);

  assert.strictEqual(juliaElements['ccQuickActionsSection'].style.display, 'block', 'Ações rápidas devem permanecer visíveis na Júlia');
  assert.strictEqual(juliaElements['ccReserveStandardLayout'].style.display, 'block', 'Ajuste padrão deve permanecer visível na Júlia');
  assert.strictEqual(juliaElements['ccReserveDefaultLayout'].style.display, 'none', 'Layout remodelado deve permanecer oculto na Júlia');
  const juliaState = JSON.parse(juliaEnv.store['weedverso_julia_v1']);
  assert(juliaState.balances.reserva, 'Júlia DEVE manter o saldo reserva em balances');
  console.log('  [OK] Júlia: 100% INTACTA (Ações Rápidas, Ajuste Padrão e Box de Reserva na tela inicial mantidos).');

  console.log('\n========================================');
  console.log(' TODOS OS TESTES PASSARAM COM SUCESSO! ');
  console.log('========================================\n');
  process.exit(0);
}).catch(err => {
  console.error('\n[ERRO NO TESTE]:', err);
  process.exit(1);
});
