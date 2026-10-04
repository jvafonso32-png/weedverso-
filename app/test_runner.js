const fs = require('fs');

const html = fs.readFileSync('d:/weedverso/app/index.html', 'utf8');
const jsCode = html.split('<script>')[1].split('</script>')[0];

const fakeEl = {
  style: {},
  innerHTML: '',
  textContent: '',
  value: '',
  appendChild: () => {},
  querySelector: () => fakeEl,
  querySelectorAll: () => [],
  addEventListener: () => {},
  classList: { add: ()=>{}, remove: ()=>{}, toggle: ()=>{} },
  setAttribute: () => {},
  removeAttribute: () => {},
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

const location = { hash: '' };
const window = { addEventListener: () => {}, location, requestAnimationFrame: (cb) => cb() };
const document = {
  getElementById: () => fakeEl,
  querySelector: () => fakeEl,
  querySelectorAll: () => [],
  addEventListener: () => {},
  createElement: () => fakeEl,
  body: fakeEl
};

const navigator = { serviceWorker: { register: () => Promise.resolve(), addEventListener: () => {} } };
const localStorage = { getItem: () => null, setItem: () => {} };

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
    } else {
      console.error('renderAll not found in evaluated JS');
    }
  } catch (e) {
    console.error('RUNTIME ERROR:', e);
  }
}
