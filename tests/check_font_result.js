// Run the production evaluator and completion function against result/event races.
const fs = require('fs'), vm = require('vm'), assert = require('assert'), path = require('path');
const base = path.resolve(__dirname, '..');
const evaluator = {}; vm.createContext(evaluator);
vm.runInContext(fs.readFileSync(path.join(base, 'FontActionResult.js'), 'utf8'), evaluator);
const evaluate = evaluator.evaluate;
assert(evaluate('{"transaction":"ok"}', 'harmless diagnostic', 0).success);
assert(!evaluate('{"transaction":"ok"}', 'write failed', 1).success);
assert(!evaluate('{"blocked":true,"unsupportedManualCount":2}', '', 0).success);
assert(!evaluate('invalid', '', 0).success);
assert(!evaluate('null', '', 0).success);
assert(!evaluate('{}', '', 0).success);
assert(evaluate('{"rolledBack":"ok"}', '', 0).refreshInventory);
assert(evaluate('', '', 42).message.includes('42'));
assert(evaluate('', 'managed path component does not exist: /home/example/.config/missing', 1).message.includes('[settings path]'));
const panel = fs.readFileSync(path.join(base, 'Panel.qml'), 'utf8');
const fn = panel.slice(panel.indexOf('  function finishGlobalFontAction()'), panel.indexOf('  function applyAllSelectedSettings()'));
const permutations = [['out','err','exit'],['out','exit','err'],['err','out','exit'],['err','exit','out'],['exit','out','err'],['exit','err','out']];
for (const events of permutations) {
  let calls = [];
  const context = {
    FontActionResult: evaluator,
    globalFontProcess: {outputText:'{"transaction":"ok"}',errorText:'warning',resultExitCode:0,handled:false},
    root: {globalApplyRunning:true, globalApplyCurrentStep:'fonts', fontActionRunning:true,
      finishGlobalApplyStep: (success,detail)=>calls.push([success,detail])},
    Qt: {callLater: fn=>fn()}
  };
  vm.createContext(context); vm.runInContext(fn, context);
  for (const [i,event] of events.entries()) {
    context.globalFontProcess[{out:'stdoutFinished',err:'stderrFinished',exit:'exitSeen'}[event]]=true;
    context.finishGlobalFontAction();
    assert.equal(calls.length, i===2 ? 1 : 0);
  }
  context.finishGlobalFontAction();
  assert.equal(calls.length,1); assert(calls[0][0]); assert(context.root.fontUndoAvailable);
}
console.log('9 result cases and all 6 stdout/stderr/exit arrival orders passed.');
