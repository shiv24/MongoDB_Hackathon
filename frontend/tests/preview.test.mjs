import {test} from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {HISTORY_BRIDGE, previewDocument} from '../preview.mjs';

test('blocked sandbox URL updates do not interrupt local rendering', () => {
  const blocked = () => { const e = new Error('Opaque origin'); e.name = 'SecurityError'; throw e; };
  const context = {history:{pushState:blocked,replaceState:blocked}, rendered:false};
  vm.runInNewContext(HISTORY_BRIDGE + "history.replaceState({}, '', '?search=Alex'); history.pushState({}, '', '?page=2'); rendered=true;", context);
  assert.equal(context.rendered, true);
});
test('real implementation errors remain visible', () => {
  const context = {history:{pushState(){},replaceState(){throw new TypeError('Bad state');}}};
  assert.throws(() => vm.runInNewContext(HISTORY_BRIDGE + 'history.replaceState();', context), /Bad state/);
});
test('bridge preserves allowed history calls and receivers', () => {
  const history = {pushState(value){this.value=value;return 7;},replaceState(){}};
  const context = {history};
  vm.runInNewContext(HISTORY_BRIDGE, context);
  assert.equal(history.pushState('ok'),7);
  assert.equal(history.value,'ok');
});
test('bridge precedes generated code, leaving static snapshots unchanged', () => {
  const html = '<html><head><meta content="policy"></head><body><script>render()</script></body></html>';
  assert.equal(previewDocument({html}),html);
  const output = previewDocument({html,version:2});
  assert.ok(output.indexOf(HISTORY_BRIDGE) < output.indexOf('render()'));
  assert.ok(output.includes('<meta content="policy">'));
});
