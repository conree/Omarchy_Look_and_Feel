// Exercise production Panel functions with queued callbacks and inert processes.
// This verifies interaction/state behavior, not native QML layout or rendering.
const fs = require('fs'), path = require('path'), vm = require('vm'), assert = require('assert');
const sourceRoot = path.resolve(__dirname, '..');
const panel = fs.readFileSync(path.join(sourceRoot, 'Panel.qml'), 'utf8');
const plain = value => JSON.parse(JSON.stringify(value));

function productionFunction(name) {
  const match = new RegExp('^  function ' + name + '\\(', 'm').exec(panel);
  assert(match, 'Missing production function: ' + name);
  // Let the JS parser find the complete function; braces in strings, regexes,
  // comments and nested functions must not truncate the extracted production code.
  for (let at = panel.indexOf('}', match.index); at >= 0; at = panel.indexOf('}', at + 1)) {
    const candidate = panel.slice(match.index, at + 1);
    try { new vm.Script('(' + candidate + ')'); return candidate; }
    catch (error) { if (!(error instanceof SyntaxError)) throw error; }
  }
  throw new Error('Incomplete production function: ' + name);
}

function inventory() {
  return {
    catalog_entries: {
      fonts: [{id: 'font:system', name: 'System Sans', monospace: false},
              {id: 'font:mono', name: 'System Mono', monospace: true},
              {id: 'font:draft', name: 'Draft Sans', monospace: false}],
      themes: [{id: 'theme:light', name: 'Light', selectable: true},
               {id: 'theme:dark', name: 'Dark', selectable: true},
               {id: 'theme:draft', name: 'Draft', selectable: true}],
      backgrounds: [{id: 'background:one', name: 'One', source: '/themes/light/backgrounds/one.png', selectable: true},
                    {id: 'background:two', name: 'Two', source: '/themes/dark/backgrounds/two.png', selectable: true}],
      icons: [{id: 'icon:one', name: 'One', selectable: true},
              {id: 'icon:two', name: 'Two', selectable: true}],
      unlocks: [{id: 'unlock:preview', name: 'Preview', selectable: true, preview: '/fixture/unlock.png'}]
    },
    preferences: {systemFontId: 'font:system', terminalFontId: 'font:mono',
                  systemFontSizePt: 12, terminalFontSizePt: 12},
    desiredAppearance: {theme: {mode: 'automatic', light: 'Light', dark: 'Dark'}, icons: 'icon:one'},
    global_font_undo_available: true,
    appearance_action_status: {theme: {expectedValue: 'Light', observedValue: 'Light', undoAvailable: true},
      background: {observedValue: '/themes/light/backgrounds/one.png', undoAvailable: true},
      icons: {observedValue: 'One', undoAvailable: true}, unlock: {previousValue: 'old', undoAvailable: true}}
  };
}

const draftKeys = ['selectedSystemFontId', 'selectedTerminalFontId', 'selectedSystemSize',
  'selectedTerminalSize', 'selectedThemeMode', 'selectedOpacity', 'selectedLightThemeId', 'selectedDarkThemeId',
  'selectedBackgroundId', 'selectedIconId', 'selectedUnlockId', 'selectedUnlockPreview',
  'unlockSelectionChanged', 'onlyMonospacedTerminalFonts'];
function draft(root) { return Object.fromEntries(draftKeys.map(key => [key, root[key]])); }

function fixture({loaded = true} = {}) {
  const queue = [], commands = [];
  const root = {fonts: [], themes: [], backgrounds: [], icons: [], unlockDesigns: [],
    inventoryLoaded: false, previewCacheLoaded: false, selectedSystemSize: 12, selectedTerminalSize: 12,
    selectedIconId: '', selectedUnlockId: '', selectedUnlockPreview: '',
    onlyMonospacedTerminalFonts: false, unlockSelectionChanged: false, unlockApplyAvailable: false,
    appearanceActionMessages: {theme: '', background: '', icons: '', unlock: ''},
    appearanceActionStatuses: {}, fontActionStatus: '', fontActionNeedsAttention: false,
    themeActionNeedsAttention: false, globalApplyStatus: '', globalApplyRunning: false,
    appearanceActionRunning: false, fontActionRunning: false, manualAppActionRunning: false,
    manualAuditClearRunning: false, lastAppliedThemeSetThisSession: false,
    globalApplySteps: [], globalApplyStepIndex: 0, globalApplyCurrentStep: '',
    popupForeground: '#eeeeee', popupBackground: '#111111', activeTab: 0,
    sectionResults: {}, pendingBySection: {fonts: [], theme: []}, inventoryError: '',
    refreshFontSelection: false, hostWidget: null};
  function color(value) {
    if (typeof value === 'object') return value;
    assert(/^#[0-9a-f]{6}$/i.test(value), 'Color fixture only accepts six-digit hex');
    return {r: parseInt(value.slice(1, 3), 16) / 255, g: parseInt(value.slice(3, 5), 16) / 255,
      b: parseInt(value.slice(5, 7), 16) / 255};
  }
  const context = {root, console, Qt: {
    callLater: callback => queue.push(callback),
    resolvedUrl: name => 'file:///fixture/' + name, color,
    rgba: (r, g, b, a) => ({r, g, b, a})
  }};
  for (const match of panel.matchAll(/^  (?:readonly )?property \w+ (\w+)\s*:/gm)) {
    const key = match[1];
    Object.defineProperty(context, key, {configurable: true, get: () => root[key], set: value => { root[key] = value; }});
  }
  root.controller = {show: () => { root.opened = true; }, hide: () => { root.opened = false; }};
  for (const id of ['appearanceActionProcess', 'globalFontProcess', 'inventoryProcess',
                    'appearanceAuditProcess', 'manualAppProcess', 'manualAuditClearProcess',
                    'unlockApplyProcess', 'unlockStatusProcess']) {
    let command = [];
    context[id] = {running: false, outputText: '', errorText: '', resultExitCode: -1,
      handled: false, stdoutFinished: false, stderrFinished: false, exitSeen: false};
    Object.defineProperty(context[id], 'command', {get: () => command, set: value => {
      command = Array.from(value); commands.push({process: id, command});
    }});
  }
  context.unlockStatusTimer = {start() {}, stop() {}};
  context.manualAppField = {clear() { root.manualAppQuery = ''; }};
  context.contentViewport = {contentY: 123};
  vm.createContext(context);
  for (const match of panel.matchAll(/^import "([^"\n]+\.js)" as (\w+)/gm)) {
    const js = fs.readFileSync(path.join(sourceRoot, match[1]), 'utf8').replace(/^\.pragma .*$/gm, '');
    const namespace = {Qt: context.Qt}; vm.createContext(namespace); vm.runInContext(js, namespace);
    context[match[2]] = namespace;
  }
  for (const match of panel.matchAll(/^  function (\w+)\(/gm)) {
    vm.runInContext(productionFunction(match[1]), context);
    root[match[1]] = context[match[1]];
  }
  const attention = /^  readonly property var attentionItems:\s*([^\n]+)/m.exec(panel);
  assert(attention, 'Missing production attention binding');
  Object.defineProperty(root, 'attentionItems', {get: () => vm.runInContext(attention[1], context)});
  // Audits are separate operations; this harness records only the interaction
  // functions and never executes a controller, process or desktop operation.
  root.runAppearanceAudit = () => {};
  function flush() {
    let count = 0;
    while (queue.length) { assert(++count < 100, 'Unbounded callback loop'); queue.shift()(); }
  }
  function finish(process, fn, output, exitCode = 0, order = ['out', 'err', 'exit']) {
    const priorIndex = root.globalApplyStepIndex;
    Object.assign(process, {handled: false, stdoutFinished: false, stderrFinished: false,
      exitSeen: false, outputText: typeof output === 'string' ? output : JSON.stringify(output),
      errorText: exitCode ? 'Fixture failure' : '', resultExitCode: exitCode});
    for (const [index, event] of order.entries()) {
      process[{out: 'stdoutFinished', err: 'stderrFinished', exit: 'exitSeen'}[event]] = true;
      fn(); flush();
      if (index < 2) {
        assert.equal(process.handled, false, 'Result finalized before both streams and exit');
        assert.equal(root.globalApplyStepIndex, priorIndex, 'Apply advanced before complete process evidence');
      }
    }
    fn(); flush(); // Duplicate completion must have no effect.
  }
  function appearance(output, exitCode, order) {
    finish(context.appearanceActionProcess, root.finishAppearanceAction, output, exitCode, order);
  }
  function fonts(output, exitCode, order) {
    finish(context.globalFontProcess, root.finishGlobalFontAction, output, exitCode, order);
  }
  if (loaded) root.adoptInventory(JSON.stringify(inventory()));
  return {root, context, commands, flush, appearance, fonts};
}

function actionSteps(f) {
  return f.commands.filter(row => row.command[3] && row.command[3].startsWith('apply-')).map(row =>
    row.command[3] === 'apply-global-fonts' ? 'fonts' : row.command[3] === 'apply-theme' ? 'theme' : row.command[3] === 'apply-opacity' ? 'opacity' : row.command[4]);
}
function footerSummary(f) {
  const start = panel.indexOf('objectName: "panelFooter"');
  assert(start >= 0, 'Missing production footer');
  const expression = /\btext:\s*([^\n]+)/.exec(panel.slice(start));
  assert(expression, 'Missing production footer summary binding');
  return vm.runInContext(expression[1], f.context);
}
function finishAll(f, {fontResult, themeResult} = {}) {
  for (let count = 0; f.root.globalApplyRunning; count++) {
    assert(count < 8, 'Apply did not finish');
    const step = f.root.globalApplyCurrentStep;
    if (step === 'fonts') f.fonts(fontResult || {transaction: 'fonts-test', targetCount: 14, desktopFontsVerified: true});
    else f.appearance(step === 'theme' && themeResult ? themeResult : {state: 'committed', readback: step});
  }
}

const tests = [];
function test(name, body) { tests.push([name, body]); }

test('blur follows opacity independently, preserves Off drafts and supports Undo', () => {
  const f = fixture(); f.root.selectedOpacity = 70; f.root.selectedBlur = 'off';
  f.root.applyAllSelectedSettings();
  f.appearance({state: 'committed', readback: 'Light'});
  f.appearance({state: 'committed', readback: '70%', opacityPercent: 70});
  assert.equal(f.root.globalApplyCurrentStep, 'blur');
  assert.deepStrictEqual(f.commands.at(-1).command.slice(3), ['apply-blur','off']);
  f.appearance({state: 'committed', readback: 'Off', blurEnabled: false});
  assert.equal(f.root.selectedOpacity, 70);
  finishAll(f);
  const fresh=inventory(); fresh.desiredAppearance.blur=true;
  f.root.adoptInventory(JSON.stringify(fresh));
  assert.equal(f.root.selectedBlur,'off');
  f.root.undoAppearanceAction('blur');
  f.appearance({rolledBack:'blur-test', savedBlur:null});
  assert.equal(f.root.selectedBlur,'keep');
  assert.equal(f.root.selectedOpacity,70);
});

test('opacity is independent, keeps drafts, reports pending work and supports Undo', () => {
  const f = fixture();
  assert.equal(f.root.selectedOpacity, -1);
  f.root.selectedOpacity = 70;
  f.root.applyAllSelectedSettings();
  f.appearance({state: 'committed', readback: 'Light'});
  assert.equal(f.root.globalApplyCurrentStep, 'opacity');
  assert.deepStrictEqual(f.commands.at(-1).command.slice(3), ['apply-opacity', '70']);
  f.appearance({state: 'committed', readback: '70%', opacityPercent: 70,
    pendingApplications: [{app: 'Foot', action: 'reopen', reason: 'Open a new window.'}]});
  finishAll(f);
  assert.deepStrictEqual(actionSteps(f), ['theme', 'opacity', 'fonts', 'background', 'icons']);
  assert.equal(f.root.sectionResults.opacity.state, 'pending');
  assert.match(f.root.globalApplyStatus, /attention/);
  f.root.selectedOpacity = 85;
  const fresh = inventory(); fresh.desiredAppearance.opacity = 70;
  f.root.adoptInventory(JSON.stringify(fresh));
  assert.equal(f.root.selectedOpacity, 85);
  f.root.undoAppearanceAction('opacity');
  f.appearance({rolledBack: 'opacity-test', savedPercent: null});
  assert.equal(f.root.selectedOpacity, -1);
  assert(!f.root.opacityActionNeedsAttention);
});

test('zero opacity can be applied and failed opacity stops later steps', () => {
  const f = fixture(); f.root.selectedOpacity = 0;
  f.root.applyAllSelectedSettings();
  f.appearance({state: 'committed', readback: 'Light'});
  assert.equal(f.root.globalApplyCurrentStep, 'opacity');
  assert.equal(f.commands.at(-1).command.at(-1), '0');
  f.appearance({}, 1);
  assert(!f.root.globalApplyRunning);
  assert.equal(f.root.selectedOpacity, 0);
  assert.deepStrictEqual(actionSteps(f), ['theme', 'opacity']);
});

test('successful icon and blur apply and undo invalidate their reconciliation section', () => {
  const f = fixture(), sections = [];
  f.root.hostWidget = {restartApplications: [], reconciliationPending: [], sectionApplied: section => sections.push(section)};
  for (const kind of ['icons', 'blur']) {
    assert(f.root.runAppearanceAction(kind, ['fixture']));
    f.appearance({state: 'committed', readback: 'value'});
    assert(f.root.runAppearanceAction(kind, ['fixture']));
    f.appearance({rolledBack: 'transaction'});
  }
  assert.deepStrictEqual(sections, ['icons', 'icons', 'blur', 'blur']);
});

test('cached examples display before discovery without authorizing Apply or Undo', () => {
  const f = fixture({loaded: false});
  f.root.adoptPreviewCache(JSON.stringify({schemaVersion: 1, inventory: inventory()}));
  assert(f.root.previewCacheLoaded); assert(!f.root.inventoryLoaded);
  assert.equal(f.root.themes.length, 3); assert.equal(f.root.selectedBackgroundId, 'background:one');
  assert(!f.root.fontUndoAvailable); assert.deepStrictEqual(plain(f.root.appearanceActionStatuses), {});
  f.root.applyAllSelectedSettings(); f.root.applySelectedTheme(); f.root.applySelectedIcons();
  f.root.applySelectedBackground(); f.root.applyGlobalFonts();
  f.root.undoAppearanceAction('theme'); f.root.undoAppearanceAction('icons'); f.root.undoGlobalFonts();
  assert.equal(f.commands.length, 0, 'Cached data launched a write');
  const fresh = inventory(); fresh.preferences.systemFontSizePt = 18;
  fresh.desiredAppearance.theme.light = 'Draft';
  f.root.adoptInventory(JSON.stringify(fresh));
  assert(f.root.inventoryLoaded); assert.equal(f.root.selectedSystemSize, 18);
  assert.equal(f.root.selectedLightThemeId, 'theme:draft', 'Fresh defaults were shadowed by cache');
  f.root.selectedSystemSize = 20;
  f.root.adoptPreviewCache(JSON.stringify({schemaVersion: 1, inventory: inventory()}));
  f.root.adoptInventory(JSON.stringify(fresh));
  assert.equal(f.root.selectedSystemSize, 20, 'Late cache or refresh replaced a live draft');
  const missing = fixture({loaded: false}), cached = inventory();
  cached.preferences.systemFontSizePt = 24; cached.preferences.terminalFontSizePt = 28;
  missing.root.adoptPreviewCache(JSON.stringify({schemaVersion: 1, inventory: cached}));
  cached.preferences.systemFontSizePt = null; cached.preferences.terminalFontSizePt = 99;
  missing.root.adoptInventory(JSON.stringify(cached));
  assert.equal(missing.root.selectedSystemSize, 12); assert.equal(missing.root.selectedTerminalSize, 12);
});

test('invalid preview caches are optional and opening does not duplicate an active scan', () => {
  const f = fixture({loaded: false});
  for (const raw of ['{broken', '{}', JSON.stringify({schemaVersion: 2, inventory: inventory()}),
                     JSON.stringify({schemaVersion: 1, inventory: {catalog_entries: {fonts: [], themes: [], icons: {}}}})]) {
    f.root.adoptPreviewCache(raw);
    assert(!f.root.previewCacheLoaded); assert(!f.root.inventoryLoaded); assert.equal(f.root.inventoryError, '');
  }
  f.root.refreshInventory(); f.root.open(); f.root.refreshInventory();
  assert.equal(f.commands.length, 1); assert.equal(f.commands[0].command.at(-1), 'panel-inventory');
  f.root.adoptInventory(JSON.stringify(inventory()));
  f.root.adoptPreviewCache(JSON.stringify({schemaVersion: 1, inventory: inventory()}));
  assert(f.root.inventoryLoaded); assert(!f.root.previewCacheLoaded);
});

test('global Apply executes all four production actions and never boot unlock', () => {
  const f = fixture(); f.root.selectedUnlockId = 'unlock:preview'; f.root.unlockSelectionChanged = true;
  f.root.applyAllSelectedSettings(); finishAll(f);
  assert.deepStrictEqual(actionSteps(f), ['theme', 'fonts', 'background', 'icons']);
  assert.equal(f.root.globalApplyStepIndex, 4); assert.equal(f.root.globalApplyRunning, false);
  assert.equal(f.context.unlockApplyProcess.running, false);
  assert.equal(f.root.fontActionNeedsAttention, false); assert.equal(f.root.themeActionNeedsAttention, false);
});

test('optional icons, required selections and busy-operation guards retain their meaning', () => {
  let f = fixture(); f.root.selectedIconId = ''; f.root.applyAllSelectedSettings(); finishAll(f);
  assert.deepStrictEqual(actionSteps(f), ['theme', 'fonts', 'background']);
  for (const key of ['selectedSystemFontId', 'selectedTerminalFontId', 'selectedLightThemeId', 'selectedDarkThemeId', 'selectedBackgroundId']) {
    f = fixture(); f.root[key] = ''; f.root.applyAllSelectedSettings(); assert.deepStrictEqual(actionSteps(f), []);
  }
  for (const key of ['fontActionRunning', 'appearanceActionRunning', 'manualAppActionRunning', 'manualAuditClearRunning', 'globalApplyRunning']) {
    f = fixture(); f.root[key] = true; f.root.applyAllSelectedSettings(); assert.deepStrictEqual(actionSteps(f), []);
  }
});

test('missing required selection cannot produce a saved-success footer', () => {
  const f = fixture(); f.root.selectedSystemFontId = ''; f.root.applyAllSelectedSettings();
  assert.deepStrictEqual(actionSteps(f), []);
  assert(!/settings saved/i.test(footerSummary(f)), 'Footer falsely reports a successful save after selection validation fails');
});

test('font failure stops later actions while retaining the failed draft', () => {
  const f = fixture(); f.root.selectedSystemSize = 14;
  f.root.applyAllSelectedSettings(); f.appearance({state: 'committed', readback: 'Light'});
  f.fonts({}, 1);
  assert.deepStrictEqual(actionSteps(f), ['theme', 'fonts']); assert.equal(f.root.globalApplyRunning, false);
  assert.equal(f.root.selectedSystemSize, 14); assert(f.root.globalApplyStatus.includes('Fixture failure'));
});

test('malformed successful appearance output cannot advance the Apply sequence', () => {
  for (const output of [{}, null, [], {state: 'committed'}, 'invalid JSON']) {
    const f = fixture(); f.root.applyAllSelectedSettings(); f.appearance(output);
    assert.deepStrictEqual(actionSteps(f), ['theme']); assert.equal(f.root.globalApplyRunning, false);
  }
});

test('process stream arrival order cannot skip or duplicate global Apply steps', () => {
  const orders = [['out', 'err', 'exit'], ['out', 'exit', 'err'], ['err', 'out', 'exit'],
    ['err', 'exit', 'out'], ['exit', 'out', 'err'], ['exit', 'err', 'out']];
  for (const order of orders) {
    const f = fixture(); f.root.applyAllSelectedSettings();
    f.appearance({state: 'committed', readback: 'Light'}, 0, order);
    assert.deepStrictEqual(actionSteps(f), ['theme', 'fonts']);
    f.fonts({transaction: 'fonts-stream-order', targetCount: 14}, 0, order);
    assert.deepStrictEqual(actionSteps(f), ['theme', 'fonts', 'background']);
    f.appearance({state: 'already-current', after: '/fixture/background.png'}, 0, order);
    assert.deepStrictEqual(actionSteps(f), ['theme', 'fonts', 'background', 'icons']);
    f.appearance({state: 'committed', readback: 'One'}, 0, order);
    assert.equal(f.root.globalApplyStepIndex, 4); assert.equal(f.root.globalApplyRunning, false);
  }
});

test('pending application work and failed reloads remain attention states after successful saves', () => {
  const f = fixture(); f.root.applyAllSelectedSettings();
  finishAll(f, {fontResult: {transaction: 'fonts-pending', targetCount: 14,
    pendingApplications: [{app: 'Brave', action: 'apply-when-closed', reason: 'Close Brave and apply fonts.'}]},
    themeResult: {state: 'committed', readback: 'Light', pendingApplications: [],
      runtimeRefresh: {terminalReload: {failed: ['ghostty']}}}});
  assert.deepStrictEqual(actionSteps(f), ['theme', 'fonts', 'background', 'icons']);
  assert(f.root.fontActionNeedsAttention); assert(f.root.themeActionNeedsAttention);
  assert(f.root.fontActionStatus.includes('Brave')); assert(f.root.appearanceActionMessages.theme.includes('ghostty'));
});

test('valid inventory refresh and panel reopening preserve every unsaved draft', () => {
  const f = fixture();
  Object.assign(f.root, {selectedSystemFontId: 'font:draft', selectedSystemSize: 14,
    selectedThemeMode: 'dark', selectedLightThemeId: 'theme:draft', selectedDarkThemeId: 'theme:draft',
    selectedBackgroundId: 'background:two', selectedIconId: 'icon:two', onlyMonospacedTerminalFonts: true,
    selectedUnlockId: 'unlock:preview', selectedUnlockPreview: '/fixture/unlock.png', unlockSelectionChanged: true});
  const before = draft(f.root); f.root.close(); f.root.open(); f.root.adoptInventory(JSON.stringify(inventory()));
  assert.deepStrictEqual(draft(f.root), before);
});

test('tab navigation preserves drafts and results without applying or refreshing configuration', () => {
  const f = fixture(); f.root.selectedSystemSize = 14; f.root.selectedIconId = 'icon:two';
  f.root.setSectionResult('fonts', 'pending', 'Close Brave and Apply again.');
  const before = draft(f.root), results = plain(f.root.sectionResults), commandCount = f.commands.length;
  for (const tab of [1, 2, 0, 2, 1, 0]) {
    f.context.contentViewport.contentY = 123;
    f.root.selectTab(tab); assert.equal(f.root.activeTab, tab); assert.equal(f.context.contentViewport.contentY, 0);
    assert.deepStrictEqual(draft(f.root), before); assert.deepStrictEqual(plain(f.root.sectionResults), results);
    assert.equal(f.commands.length, commandCount);
  }
  for (const tab of [-1, 3]) { f.root.selectTab(tab); assert.equal(f.root.activeTab, 0); }
});

test('a failed inventory refresh preserves the existing drafts and usable catalog', () => {
  const f = fixture(); f.root.selectedBackgroundId = 'background:two'; f.root.selectedIconId = 'icon:two';
  const before = draft(f.root), catalog = plain(f.root.fonts);
  f.root.adoptInventory('{broken JSON');
  assert.deepStrictEqual(draft(f.root), before); assert.deepStrictEqual(plain(f.root.fonts), catalog);
  assert(f.root.inventoryError); assert(f.root.collectAttention().some(item => item.app === 'Catalog'));
  f.root.adoptInventory(JSON.stringify(inventory())); assert.equal(f.root.inventoryError, '');
});

test('structured results distinguish working, saved, pending and failed operations', () => {
  const f = fixture(); f.root.applyAllSelectedSettings();
  assert.equal(f.root.sectionResults.theme.state, 'working');
  f.appearance({state: 'committed', readback: 'Light',
    pendingApplications: [{app: 'Qt', action: 'login', reason: 'Sign out and back in.'}]});
  assert.equal(f.root.sectionResults.theme.state, 'pending'); assert.equal(f.root.sectionResults.fonts.state, 'working');
  f.fonts({transaction: 'fonts-saved', targetCount: 14});
  assert.equal(f.root.sectionResults.fonts.state, 'saved'); assert.equal(f.root.sectionResults.background.state, 'working');
  f.appearance({}, 1);
  assert.equal(f.root.sectionResults.background.state, 'error'); assert.equal(f.root.applyFailed, true);
  const attention = plain(f.root.collectAttention());
  assert(attention.some(item => item.app === 'Qt' && item.action === 'login'));
  assert(attention.some(item => item.app === 'Background' && item.action === 'error'));
  assert.equal(f.root.actionTitle('login'), 'Sign out and back in');
  assert.equal(f.root.actionTitle('apply-when-closed'), 'Close, then Apply again');
});

test('attention merges reconciliation results and clears resolved section pending work', () => {
  const f = fixture(); const pending = {app: 'Brave', action: 'apply-when-closed', reason: 'Close Brave.'};
  f.root.updatePending('fonts', {pendingApplications: [pending]});
  f.root.hostWidget = {reconciliationPending: [pending], reconciliationFailed: false};
  assert.equal(f.root.collectAttention().filter(item => item.app === 'Brave').length, 1);
  f.root.updatePending('fonts', {pendingApplications: []});
  f.root.hostWidget = {reconciliationPending: [], reconciliationFailed: true, reconciliationMessage: 'Fixture reconciliation failed'};
  const attention = f.root.collectAttention();
  assert.equal(attention.length, 1); assert.equal(attention[0].app, 'Appearance check');
});

test('PCManFM restart notices follow current observation without stale section entries', () => {
  const f = fixture();
  const notice = {app: 'PCManFM', action: 'reopen', reason: 'Fully quit and reopen PCManFM.'};
  f.root.hostWidget = {reconciliationPending: [], restartApplications: []};
  f.root.updatePending('fonts', {pendingApplications: [], restartApplications: [notice]});
  assert.equal(f.root.collectAttention().filter(item => item.app === 'PCManFM').length, 1);
  assert.equal(f.root.pendingBySection.fonts.length, 0);
  f.root.updateRestartApplications({}); // A failed observation preserves the notice.
  assert.equal(f.root.collectAttention().filter(item => item.app === 'PCManFM').length, 1);
  f.root.hostWidget.restartApplications = []; // Successful reconciliation after exit.
  assert.equal(f.root.collectAttention().filter(item => item.app === 'PCManFM').length, 0);
  f.root.hostWidget = null;
  f.root.updateRestartApplications({restartApplications: []});
  assert.equal(f.root.collectAttention().length, 0);
});

test('preview file URLs escape path data and contrast helper preserves readable text', () => {
  const f = fixture(); assert.equal(f.root.fileUrl(''), '');
  assert.equal(f.root.fileUrl('/fixture/a #1%/猫.png'), 'file:///fixture/a%20%231%25/%E7%8C%AB.png');
  const luminance = color => [color.r, color.g, color.b].map(value => value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4)
    .reduce((total, value, index) => total + value * [0.2126, 0.7152, 0.0722][index], 0);
  for (const [background, foreground] of [['#eff1f5', '#4c4f69'], ['#1e1e2e', '#cdd6f4']]) {
    f.root.popupBackground = f.context.Qt.color(background); f.root.popupForeground = f.context.Qt.color(foreground);
    for (const candidate of [background, foreground, '#eeeeee', '#111111', '#8899aa', '#ee8833']) {
      const actual = f.root.readable(candidate), a = luminance(actual), b = luminance(f.root.popupBackground);
      assert((Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05) >= 4.5);
    }
  }
});

test('Fonts Undo refreshes fonts without discarding other sections unsaved drafts', () => {
  const f = fixture();
  Object.assign(f.root, {selectedThemeMode: 'dark', selectedLightThemeId: 'theme:draft',
    selectedDarkThemeId: 'theme:draft', selectedBackgroundId: 'background:two', selectedIconId: 'icon:two'});
  const before = draft(f.root);
  f.root.undoGlobalFonts(); f.fonts({rolledBack: 'fonts-test'});
  const updated = inventory(); updated.preferences.systemFontSizePt = 10;
  f.root.adoptInventory(JSON.stringify(updated));
  assert.equal(f.root.selectedSystemSize, 10);
  for (const key of ['selectedThemeMode', 'selectedLightThemeId', 'selectedDarkThemeId', 'selectedBackgroundId', 'selectedIconId'])
    assert.equal(f.root[key], before[key], key);
});

test('observed current theme follows readback and file updates while preserving unsaved drafts', () => {
  const f = fixture();
  f.root.selectedThemeMode = 'light';
  f.root.applySelectedTheme();
  f.appearance({state: 'committed', readback: 'Light'});
  assert.equal(f.root.observedTheme, 'Light');
  assert.equal(f.root.lastAppliedThemeSetThisSession, true);
  Object.assign(f.root, {selectedLightThemeId: 'theme:draft', selectedBackgroundId: 'background:two', selectedSystemSize: 20});
  const before = draft(f.root);
  const data = inventory();
  data.catalog_entries.themes[1].preview = {background: '#111111'};
  data.appearance_action_status.theme.observedValue = 'Dark';
  data.appearance_action_status.theme.expectedValue = 'Light';
  f.root.adoptInventory(JSON.stringify(data));
  assert.equal(f.root.observedTheme, 'Dark');
  assert.equal(f.root.lastAppliedTheme, 'Light');
  assert.deepStrictEqual(draft(f.root), before);
  const active = /^  readonly property var activePreview:\s*([^\n]+)/m.exec(panel);
  const badge = /text: "Active now"; visible: ([^;]+);/.exec(panel);
  assert(active && badge, 'Missing production current-theme bindings');
  assert.equal(vm.runInContext(active[1], f.context).background, '#111111');
  f.context.choice = {entry: {name: 'Dark'}};
  assert.equal(vm.runInContext(badge[1], f.context), true);
  for (const observed of ['unknown-theme', undefined]) {
    data.appearance_action_status.theme.observedValue = observed;
    f.root.adoptInventory(JSON.stringify(data));
    assert.equal(vm.runInContext(badge[1], f.context), false);
    assert.deepStrictEqual(plain(vm.runInContext(active[1], f.context)), {});
    assert.deepStrictEqual(draft(f.root), before);
  }
  for (const [raw, expected] of [[' Catppuccin-Latte\n', 'catppuccin-latte'], ['../invalid', ''], ['', ''], [null, '']]) {
    const count = f.commands.length;
    f.root.adoptObservedThemeName(raw);
    assert.equal(f.root.observedTheme, expected);
    assert.deepStrictEqual(draft(f.root), before);
    assert.equal(f.commands.length, count, 'Observed file update launched a command');
  }
  f.root.undoAppearanceAction('theme');
  f.appearance({rolledBack: 'theme-test', readback: 'Dark', restored: 'Dark'});
  assert.equal(f.root.observedTheme, 'Dark');
});

test('boot actions require capability and use the normal checked process', () => {
  const f = fixture(); f.root.selectedUnlockId = 'unlock:preview';
  assert.equal(f.root.applySelectedUnlock(false), false);
  f.root.unlockApplyAvailable = true;
  assert.equal(f.root.applySelectedUnlock(false), true);
  assert.deepStrictEqual(plain(f.context.appearanceActionProcess.command.slice(3)), ['apply-catalog-action', 'unlock', 'unlock:preview']);
  f.appearance({state: 'committed', readback: 'preview'});
  f.root.undoAppearanceAction('unlock');
  assert.deepStrictEqual(plain(f.context.appearanceActionProcess.command.slice(3)), ['rollback-appearance', 'unlock']);
  assert(!panel.includes('omarchy-launch-floating-terminal-with-presentation'));
});

test('global Apply includes explicitly changed boot artwork last', () => {
  const f = fixture(); f.root.unlockApplyAvailable = true;
  f.root.selectedUnlockId = 'unlock:preview'; f.root.unlockSelectionChanged = true;
  f.root.applyAllSelectedSettings(); f.flush(); finishAll(f);
  assert.deepStrictEqual(actionSteps(f), ['theme', 'fonts', 'background', 'icons', 'unlock']);
  assert.equal(f.root.unlockSelectionChanged, false);
});

test('audit message describes the current finding, not cumulative registrations', () => {
  const f = fixture();
  assert.equal(f.root.auditResultMessage({status: 'launcher-found', findings: [{fontStatus: 'registered'}], unsupportedCount: 1}), 'Shared font control detected. The rendered font has not been verified.');
  assert.equal(f.root.auditResultMessage({status: 'launcher-found', findings: [{fontStatus: 'unsupported'}], registeredCount: 1}), 'No supported shared font control was identified. The rendered font has not been verified.');
  assert.equal(f.root.auditResultMessage({status: 'not-found', findings: []}), 'No matching installed application was found. Try a different name.');
  const ambiguous = [{framework: 'ambiguous or package-only result', fontStatus: 'unsupported'}];
  assert.equal(f.root.auditResultMessage({status: 'launcher-found', findings: ambiguous}), 'Multiple applications matched. Search for a specific launcher to audit one application.');
  assert.equal(f.root.auditResultMessage({status: 'installed-item-found-no-launcher', findings: ambiguous}), 'An installed item was found, but its application font control could not be identified. Try a specific launcher.');
});

test('clearing audit attention preserves unrelated pending actions', () => {
  const f = fixture();
  const audit = {app: 'Audited applications', action: 'review', reason: 'unresolved'};
  const oldAudit = {app: 'Fonts', action: 'manual-audit', reason: 'old'};
  const mail = {app: 'Betterbird', action: 'close', reason: 'close first'};
  f.root.pendingBySection = {fonts: [audit, mail], theme: []};
  f.root.hostWidget = {reconciliationPending: [oldAudit, mail], restartApplications: []};
  f.root.clearAuditAttention();
  assert.deepStrictEqual(plain(f.root.pendingBySection.fonts), [mail]);
  assert.deepStrictEqual(plain(f.root.hostWidget.reconciliationPending), [mail]);
});

test('clearing an audit updates font status without hiding other pending work', () => {
  const audit = {app: 'Audited applications', action: 'review', reason: 'unresolved'};
  const mail = {app: 'Betterbird', action: 'close', reason: 'close first'};
  for (const other of [[], [mail]]) {
    const f = fixture();
    const result = {transaction: 't1', targetCount: 2, pendingApplications: [audit, ...other], terminalReload: {requested: [], failed: []}};
    f.context.globalFontProcess.outputText = JSON.stringify(result);
    f.context.globalFontProcess.resultExitCode = 0;
    f.root.pendingBySection.fonts = result.pendingApplications;
    f.root.fontActionNeedsAttention = true;
    f.root.globalApplyStatus = 'Settings saved. Some applications need attention; see Applications.';
    f.root.clearAuditAttention();
    assert.equal(f.root.fontActionNeedsAttention, !!other.length);
    assert(!f.root.fontActionStatus.includes('unresolved'));
    assert.equal(f.root.sectionResults.fonts.state, other.length ? 'pending' : 'saved');
    if (other.length) assert(f.root.fontActionStatus.includes('Betterbird'));
    else assert.equal(f.root.globalApplyStatus, 'Settings saved.');
  }
});

test('clearing audits removes only the old audit-blocked error', () => {
  const f = fixture();
  f.context.globalFontProcess.outputText = JSON.stringify({blocked: true, unsupportedManualCount: 1});
  f.root.sectionResults.fonts = {state: 'error', detail: 'Font Apply stopped'};
  f.root.globalApplyCurrentStep = 'fonts';
  f.root.globalApplyStatus = 'Apply stopped at Fonts. Font Apply stopped';
  f.root.applyFailed = true;
  f.root.clearAuditAttention();
  assert.equal(f.root.sectionResults.fonts.state, '');
  assert.equal(f.root.applyFailed, false);
  assert(f.root.globalApplyStatus.includes('Apply changes again'));
});

test('successful re-audit retains previous attention until reconciliation confirms it', () => {
  const f = fixture(), p = f.context.manualAppProcess;
  const audit = {app: 'Audited applications', action: 'review', reason: 'unresolved'};
  const other = {app: 'Betterbird', action: 'close', reason: 'close first'};
  let refreshes = 0;
  f.root.pendingBySection = {fonts: [audit, other]};
  f.root.hostWidget = {reconciliationPending: [audit, other], restartApplications: [],
    auditRegistryChanged: () => refreshes++};
  f.root.manualAppActionRunning = true;
  Object.assign(p, {outputText: JSON.stringify({status: 'not-found', findings: []}),
    stdoutFinished: true, stderrFinished: true, exitSeen: true, resultExitCode: 0});
  f.root.finishManualAuditProcess(p, false);
  assert.deepStrictEqual(plain(f.root.pendingBySection.fonts), [audit, other]);
  assert.deepStrictEqual(plain(f.root.hostWidget.reconciliationPending), [audit, other]);
  assert.equal(refreshes, 1);
  assert.equal(f.root.manualAppStatus, 'No matching installed application was found. Try a different name.');
});

test('audit completion waits for exit and both streams in every order', () => {
  for (const order of ['ose', 'oes', 'soe', 'seo', 'eos', 'eso']) {
    for (const code of [0, 1]) {
      const f = fixture(); const p = f.context.manualAuditClearProcess;
      f.root.manualAppQuery = 'test input'; f.root.manualAuditClearRunning = true;
      for (const [index, event] of Array.from(order).entries()) {
        if (event === 'o') { p.outputText = '{"cleared":true}'; p.stdoutFinished = true; }
        if (event === 's') p.stderrFinished = true;
        if (event === 'e') { p.exitSeen = true; p.resultExitCode = code; }
        f.root.finishManualAuditProcess(p, true);
        if (index < 2) assert.equal(f.root.manualAppQuery, 'test input');
      }
      assert.equal(f.root.manualAppQuery, code ? 'test input' : '');
      assert.equal(f.root.manualAppStatus, code ? 'Saved audits could not be cleared safely.' : 'Saved audits cleared.');
      assert.equal(f.root.manualAuditClearRunning, false);
    }
  }
  for (const code of [0, 1]) {
    const f = fixture(), p = f.context.manualAppProcess;
    Object.assign(p, {outputText: JSON.stringify({status: 'launcher-found', findings: [{fontStatus: 'registered'}]}),
      stdoutFinished: true, stderrFinished: true, exitSeen: true, resultExitCode: code});
    f.root.manualAppActionRunning = true;
    f.root.finishManualAuditProcess(p, false);
    assert.equal(f.root.manualAppStatus, code ? 'The app audit could not be completed.' : 'Shared font control detected. The rendered font has not been verified.');
    assert.equal(f.root.manualAppActionRunning, false);
  }
});

let failures = 0;
for (const [name, body] of tests) {
  try { body(); console.log('PASS ' + name); }
  catch (error) { failures++; console.error('FAIL ' + name + '\n' + error.stack); }
}
if (failures) process.exitCode = 1;
else console.log('Production panel interaction regression passed (' + tests.length + ' cases; inert I/O).');
