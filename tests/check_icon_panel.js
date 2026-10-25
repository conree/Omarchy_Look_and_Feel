// Evaluate the actual panel selection/Apply/Undo functions with inert I/O.
const fs = require('fs'), vm = require('vm'), assert = require('assert'), path = require('path');
const panel = fs.readFileSync(path.join(__dirname, '../Panel.qml'), 'utf8');
function production(name) {
  const start = panel.indexOf('  function ' + name + '(');
  assert(start >= 0, name);
  const end = panel.indexOf('\n  function ', start + 1);
  return panel.slice(start, end < 0 ? panel.length : end);
}
function fixture(failedStep) {
  const calls = [];
  const root = {icons: [{id: 'icon:installed', name: 'Installed'}], selectedIconId: '',
    appearanceActionMessages: {theme: 'Keep theme result'}, sectionResults: {}, inventoryLoaded: false,
    selectedSystemFontId: 'font:system', selectedTerminalFontId: 'font:terminal',
    selectedLightThemeId: 'theme:light', selectedDarkThemeId: 'theme:dark', selectedBackgroundId: 'background:test',
    unlockApplyAvailable: false, unlockSelectionChanged: true, selectedUnlockId: 'unlock:test'};
  const context = {root, Qt: {callLater: f => f()}};
  vm.createContext(context);
  for (const name of ['setSectionResult', 'adoptIconSelection', 'globalApplyStepName', 'applyAllSelectedSettings',
                      'applyNextGlobalStep', 'finishGlobalApplyStep', 'applySelectedIcons', 'undoAppearanceAction']) {
    vm.runInContext(production(name), context);
    root[name] = context[name];
  }
  function complete(step) {calls.push(step); root.finishGlobalApplyStep(step !== failedStep, 'fixture result'); return true;}
  root.applySelectedTheme = () => complete('theme');
  root.applyGlobalFonts = () => complete('fonts');
  root.applySelectedBackground = () => complete('background');
  root.runAppearanceAction = (kind, args, fromGlobal) => {
    if (fromGlobal) return complete(kind);
    calls.push(Array.from(args)); return true;
  };
  return {root, calls};
}

let {root, calls} = fixture();
root.adoptIconSelection('icon:removed', 'Installed', true);
assert.equal(root.selectedIconId, '');
assert(root.appearanceActionMessages.icons.includes('unavailable'));
assert.equal(root.appearanceActionMessages.theme, 'Keep theme result');
root.applyAllSelectedSettings();
assert.deepEqual(calls, ['theme', 'fonts', 'background']);

({root, calls} = fixture());
root.adoptIconSelection('icon:installed', '', true);
root.applyAllSelectedSettings();
assert.deepEqual(calls, ['theme', 'fonts', 'background', 'icons']);
assert.equal(root.globalApplyRunning, false);
root.undoAppearanceAction('icons');
assert.deepEqual(calls.at(-1), ['rollback-appearance', 'icons']);

({root, calls} = fixture('fonts'));
root.adoptIconSelection('', 'Installed', true);
assert.equal(root.selectedIconId, 'icon:installed');
root.applyAllSelectedSettings();
assert.deepEqual(calls, ['theme', 'fonts']);
assert(root.globalApplyStatus.includes('Apply stopped at Fonts'));

({root} = fixture());
root.selectedIconId = 'icon:installed';
root.adoptIconSelection('icon:other', '', false);
assert.equal(root.selectedIconId, 'icon:installed'); // preserve unsaved valid selection
root.icons = [];
root.adoptIconSelection('icon:installed', '', false);
assert.equal(root.selectedIconId, ''); // refresh removes a now-unavailable selection
console.log('Actual panel icon functions passed: unavailable selection refusal, four-step Apply, failure stop, Undo routing, and refresh preservation.');
