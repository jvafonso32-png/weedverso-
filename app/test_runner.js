const fs = require('fs');
const path = require('path');

let jsCode;
if (fs.existsSync('d:/weedverso/core/app.js')) {
  jsCode = fs.readFileSync('d:/weedverso/core/app.js', 'utf8');
} else if (fs.existsSync('d:/weedverso/app/core/app.js')) {
  jsCode = fs.readFileSync('d:/weedverso/app/core/app.js', 'utf8');
} else {
  const html = fs.readFileSync('d:/weedverso/app/index.html', 'utf8');
  jsCode = html.split('<script>')[1].split('</script>')[0];
}

const fakeEl = {
  style: {},
  innerHTML: '',
  textContent: '',
  value: '',
  appendChild: () => {},
  querySelector: () => fakeEl,
  querySelectorAll: () => [fakeEl],
  addEventListener: () => {},
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
  closest: () => fakeEl
};
fakeEl.parentNode.parentNode = fakeEl;

const location = { hash: '', search: '', protocol: 'https:', origin: 'https://test.local', pathname: '/' };
const window = {
  addEventListener: () => {},
  location,
  requestAnimationFrame: (cb) => cb(),
  history: { replaceState: () => {} },
  WEEDVERSO_CONFIG: {
    userId: 'default',
    userName: 'João',
    theme: 'emerald',
    storageKey: 'rotina_prime_v2'
  }
};
const document = {
  getElementById: () => fakeEl,
  querySelector: () => fakeEl,
  querySelectorAll: () => [fakeEl],
  addEventListener: () => {},
  createElement: () => fakeEl,
  body: fakeEl
};

const navigator = {
  userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
  serviceWorker: { register: () => Promise.resolve(), addEventListener: () => {}, getRegistration: () => Promise.resolve() },
  storage: { persist: () => Promise.resolve() }
};
const localStorage = { getItem: () => null, setItem: () => {}, removeItem: () => {} };
const sessionStorage = { getItem: () => null, setItem: () => {}, removeItem: () => {} };

let errored = false;

try {
  eval(jsCode);
} catch (e) {
  console.error('SYNTAX / EVAL ERROR:', e);
  errored = true;
}

if (!errored) {
  try {
    if (typeof renderAll === 'function') {
      renderAll();
      console.log('renderAll passed without throwing!');
      process.exit(0);
    } else {
      console.log('Weedverso Core mounted successfully!');
      process.exit(0);
    }
  } catch (e) {
    console.error('RUNTIME ERROR:', e);
    process.exit(1);
  }
} else {
  process.exit(1);
}
