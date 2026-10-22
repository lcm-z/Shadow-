// Testes de funções e temporizadores, sem abrir janela nem executar ações do PC.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('ui/app.js', 'utf8').replace(/\r\n?/g, '\n');
function extract(name, text = source) {
  text = text.replace(/\r\n?/g, '\n');
  const start = text.indexOf(`function ${name}(`);
  assert.notEqual(start, -1, `Função ausente: ${name}`);
  const next = text.indexOf('\n}', start);
  // As funções curtas ficam inteiras em uma única linha.
  const line = text.slice(start, text.indexOf('\n', start));
  return line.trimEnd().endsWith('}') ? line : text.slice(start, next + 2);
}
test('intervalo respeita modo leve e escolha de cinco segundos', () => {
  const context = vm.createContext({ uiPreferences: { lightweight: false, interval_seconds: 1 } });
  vm.runInContext(extract('effectiveIntervalMs'), context);
  assert.equal(context.effectiveIntervalMs(), 1000);
  context.uiPreferences.lightweight = true;
  assert.equal(context.effectiveIntervalMs(), 3000);
  context.uiPreferences.interval_seconds = 5;
  assert.equal(context.effectiveIntervalMs(), 5000);
});
test('sensor ausente é diferente de zero', () => {
  const context = vm.createContext({}); vm.runInContext(extract('sensorValue'), context);
  assert.equal(context.sensorValue(null, '%'), 'indisponível');
  assert.equal(context.sensorValue(0, '%'), '0.0%');
});
test('fechar cancela todos os temporizadores', () => {
  const cancelled = [];
  const context = vm.createContext({ appClosing: false, liveTimer: 1, performanceTimer: 2, telemetryTimer: 3, presentationTimer: 4, livePausedByVisibility: true, window: { clearInterval: id => cancelled.push(id), clearTimeout: id => cancelled.push(id) } });
  vm.runInContext(extract('stopUiTimers'), context); context.stopUiTimers();
  assert.equal(context.appClosing, true);
  assert.deepEqual(cancelled, [1, 2, 3, 4]);
  assert.equal(context.livePausedByVisibility, false);
});
test('modo leve e acessibilidade desativam efeitos de canvas', () => {
  const context = vm.createContext({ uiPreferences: {lightweight: false, effects: 'full'}, window: {matchMedia: () => ({matches: false})} });
  vm.runInContext(extract('effectsEnabled'), context);
  assert.equal(context.effectsEnabled(), true);
  context.uiPreferences.lightweight = true;
  assert.equal(context.effectsEnabled(), false);
  context.uiPreferences.lightweight = false; context.window.matchMedia = () => ({matches: true});
  assert.equal(context.effectsEnabled(), false);
});
test('IDs HTML únicos e elementos JavaScript existentes', () => {
  const html = fs.readFileSync('ui/index.html', 'utf8');
  const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(m => m[1]);
  assert.equal(new Set(ids).size, ids.length);
  for (const match of source.matchAll(/querySelector\("#([a-z][\w-]*)"\)/g)) assert.ok(ids.includes(match[1]), match[1]);
});

test('extração funciona com CRLF e espaços no fim da linha', () => {
  const windowsSource = source.replace(/\n/g, '\r\n');
  for (const name of ['effectiveIntervalMs', 'effectsEnabled', 'sensorValue', 'stopUiTimers']) {
    assert.equal(extract(name, windowsSource), extract(name));
    assert.ok(!extract(name, windowsSource).includes('analyzeButton.addEventListener'));
  }
  assert.match(extract('sample', 'function sample() { return 1; }   \r\n'), /return 1/);
});

test('script completo inicia apresentação sem disparar análise', () => {
  const timers = [];
  const elements = new Map();
  function element(key) {
    if (elements.has(key)) return elements.get(key);
    const node = { dataset: {}, style: {}, textContent: '', offsetWidth: 100,
      classList: {toggle() {}, add() {}, remove() {}, contains() {return false;}},
      addEventListener() {}, setAttribute() {}, removeAttribute() {}, getAttribute() {return null;},
      querySelector: selector => element(key + selector), getContext: () => ({}), focus() {},
    };
    elements.set(key, node); return node;
  }
  const api = {start_scan() {throw new Error('Não deve analisar ao abrir');}};
  const context = vm.createContext({
    document: { querySelector: element, querySelectorAll: () => [], addEventListener() {}, body: element('body') },
    localStorage: {getItem: () => null},
    window: {addEventListener() {}, matchMedia: () => ({matches:false}), clearTimeout() {},
      setTimeout: (fn, delay) => {timers.push(delay); return 1;}, pywebview:{api}},
  });
  vm.runInContext(source, context);
  assert.deepEqual(timers, [1900]);
});
