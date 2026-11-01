// Exercise the production reconciliation completion and audit-generation logic.
const fs = require('fs'), vm = require('vm'), assert = require('assert');
const source = fs.readFileSync(require('path').join(__dirname, '..', 'BarWidget.qml'), 'utf8');
function readFunction(name, sourceText = source) {
  const source = sourceText;
  const start = source.indexOf('  function ' + name + '(');
  assert(start >= 0);
  for (let end = source.indexOf('}', start); end >= 0; end = source.indexOf('}', end + 1)) {
    const candidate = source.slice(start, end + 1);
    try { new vm.Script('(' + candidate + ')'); return candidate; } catch (e) { if (!(e instanceof SyntaxError)) throw e; }
  }
  throw Error('Incomplete ' + name);
}
const queue = [];
const root = {repairSettingLoaded: true, repairEnabled: true, auditGeneration: 0, auditRefreshPending: false, reconciliationPending: [], reconciliationFailed: false, reconciliationMessage: '', sectionGeneration: {fonts: 0, theme: 0, opacity: 0, icons: 0, blur: 0}, reconciliationOwners: {}};
const processState = {running: false, started: true, handled: false, exitSeen: true, stdoutFinished: true, stderrFinished: true, resultExitCode: 0, errorText: '', auditGeneration: 0, sectionGeneration: {fonts: 0, theme: 0, opacity: 0, icons: 0, blur: 0}};
const context = {root, repairSettingProcess: {running: false}, reconcileProcess: processState, panelLoader: {item: null}, Qt: {callLater: fn => queue.push(fn)}};
vm.createContext(context);
const panelSource = fs.readFileSync(require('path').join(__dirname, '..', 'Panel.qml'), 'utf8');
function makePanel(extra = {}) {
  const panel = {pendingBySection: {}, sectionResults: {}, hostWidget: root,
    restartApplications: [], inventoryError: '', globalApplyStatus: '', ...extra};
  const panelContext = vm.createContext({root: panel});
  for (const name of ['updatePending', 'updateRestartApplications', 'collectAttention', 'setSectionResult', 'globalApplyStepName'])
    panel[name] = vm.runInContext('(' + readFunction(name, panelSource) + ')', panelContext);
  Object.defineProperty(panel, 'attentionItems', {get: () => panel.collectAttention()});
  return panel;
}
for (const name of ['tryReconcile', 'auditRegistryChanged', 'sectionApplied', 'isAuditAttention', 'finishReconciliation']) {
  root[name] = vm.runInContext('(' + readFunction(name) + ')', context);
}
const audit = {app: 'Audited applications', action: 'review', reason: 'old'};
const mail = {app: 'Betterbird', action: 'close', reason: 'close first'};
processState.outputText = JSON.stringify({schemaVersion: 1, pendingApplications: [audit, mail], results: {}});
root.auditRegistryChanged();
root.finishReconciliation();
assert.deepStrictEqual(JSON.parse(JSON.stringify(root.reconciliationPending)), [mail]);
assert(root.auditRefreshPending);
while (queue.length) queue.shift()();
assert(processState.running, 'stale result should schedule a new reconciliation');
// A later audit can legitimately produce a new warning; fresh results must not
// be suppressed even if an earlier clear had invalidated another process.
processState.running = false; processState.handled = false; processState.auditGeneration = root.auditGeneration;
processState.outputText = JSON.stringify({schemaVersion: 1, pendingApplications: [audit, mail], results: {}});
root.finishReconciliation();
assert.deepStrictEqual(JSON.parse(JSON.stringify(root.reconciliationPending)), [audit, mail]);
// While an audit is running, a refresh request waits for its completion.
processState.running = false; processState.handled = true;
context.panelLoader.item = makePanel({manualAppActionRunning: true});
root.auditRegistryChanged();
while (queue.length) queue.shift()();
assert(!processState.running && root.auditRefreshPending);
context.panelLoader.item.manualAppActionRunning = false;
root.tryReconcile();
assert(processState.running);
// A successful font apply removes the prior reconciliation font notice but
// preserves unrelated and shared notices. A delayed old result cannot restore it.
processState.running = false; processState.handled = false;
processState.auditGeneration = root.auditGeneration;
processState.sectionGeneration = {...root.sectionGeneration};
const brave = {app: 'Brave', action: 'close-and-apply', reason: 'close'};
const both = {app: 'Shared', action: 'review', reason: 'both sections'};
processState.outputText = JSON.stringify({schemaVersion: 1, pendingApplications: [brave, mail, both], results: {
  fonts: {pendingApplications: [brave, both]}, theme: {pendingApplications: [mail, both]}
}});
root.finishReconciliation();
root.sectionApplied('fonts');
assert.deepStrictEqual(JSON.parse(JSON.stringify(root.reconciliationPending)), [mail, both]);
processState.handled = false;
root.finishReconciliation();
assert.deepStrictEqual(JSON.parse(JSON.stringify(root.reconciliationPending)), [mail, both]);
assert(root.auditRefreshPending);
// Fresh reconciliation can report new font work after the successful apply.
processState.handled = false; processState.sectionGeneration = {...root.sectionGeneration};
root.finishReconciliation();
assert.deepStrictEqual(JSON.parse(JSON.stringify(root.reconciliationPending)), [brave, mail, both]);
// Retry and reload notices generated by reconciliation are attributed even
// when absent from a section's returned pendingApplications (or result).
const retry = {app: 'fonts', action: 'retry', reason: 'missing'};
const reload = {app: 'kitty', action: 'reload', reason: 'font reload failed'};
processState.handled = false;
processState.outputText = JSON.stringify({schemaVersion: 1, pendingApplications: [retry, reload, mail],
  pendingBySection: {fonts: [retry, reload], theme: [mail]}, results: {}});
root.finishReconciliation();
root.sectionApplied('fonts');
assert.deepStrictEqual(JSON.parse(JSON.stringify(root.reconciliationPending)), [mail]);
processState.handled = false;
root.finishReconciliation();
assert.deepStrictEqual(JSON.parse(JSON.stringify(root.reconciliationPending)), [mail]);
for (const section of ['icons', 'blur']) {
  processState.handled = false;
  processState.sectionGeneration = {...root.sectionGeneration};
  const own = {app: section, action: 'retry', reason: 'old error'};
  processState.outputText = JSON.stringify({schemaVersion: 1, pendingApplications: [own, mail],
    pendingBySection: {[section]: [own], theme: [mail]}, results: {}});
  root.finishReconciliation();
  root.sectionApplied(section);
  assert.deepStrictEqual(JSON.parse(JSON.stringify(root.reconciliationPending)), [mail]);
  processState.handled = false;
  root.finishReconciliation();
  assert.deepStrictEqual(JSON.parse(JSON.stringify(root.reconciliationPending)), [mail]);
}
// Re-auditing may leave other unresolved records. Only a successful current
// font reconciliation with no audit warning can clear the panel's old one.
let cleared = 0;
context.panelLoader.item = makePanel({clearAuditAttention: () => cleared++});
processState.running = false; processState.handled = false;
processState.auditGeneration = root.auditGeneration;
processState.sectionGeneration = {...root.sectionGeneration};
processState.outputText = JSON.stringify({schemaVersion: 1, pendingApplications: [audit, mail],
  pendingBySection: {fonts: [audit], theme: [mail]}, results: {fonts: {pendingApplications: [audit]}}});
root.finishReconciliation();
assert.equal(cleared, 0);
processState.handled = false; processState.resultExitCode = 1;
root.finishReconciliation();
assert.equal(cleared, 0);
processState.handled = false; processState.resultExitCode = 0;
processState.outputText = JSON.stringify({schemaVersion: 1, pendingApplications: [mail],
  pendingBySection: {fonts: [], theme: [mail]}, results: {fonts: {pendingApplications: []}}});
root.finishReconciliation();
assert.equal(cleared, 1);
assert.deepStrictEqual(JSON.parse(JSON.stringify(root.reconciliationPending)), [mail]);
// A legacy blocked Apply can have no saved font policy and hence no font
// reconciliation result. Unknown or unresolved registry evidence is not
// enough to clear its warning; a confirmed zero is.
for (const registry of [null, {unsupportedCount: 1}, {unsupportedCount: 0}]) {
  processState.handled = false;
  processState.outputText = JSON.stringify({schemaVersion: 1, pendingApplications: [mail],
    pendingBySection: {theme: [mail]}, results: {}, auditRegistryStatus: registry});
  root.finishReconciliation();
  assert.equal(cleared, registry && registry.unsupportedCount === 0 ? 2 : 1);
}
console.log('Reconciliation generation: stale warning filtered, unrelated notices retained, fresh audits and busy guard passed.');
processState.running = false; processState.handled = true;
root.repairEnabled = false;
root.tryReconcile();
assert(!processState.running, 'disabled repair must not start reconciliation');
processState.handled = false;
processState.outputText = JSON.stringify({schemaVersion: 1, skipped: 'disabled'});
root.reconciliationFailed = false;
root.finishReconciliation();
assert(!root.reconciliationFailed, 'disabled result must not be reported as an error');

// A current background font result replaces the Apply-time snapshot. A no-op
// reconciliation has transaction:null, but still verifies that no work remains.
const staleMail = {app: 'Betterbird', action: 'close-and-apply', reason: 'Close mail first.'};
function fontObservation(fontResult, attributed = fontResult && fontResult.pendingApplications) {
  root.reconciliationPending = [];
  root.reconciliationFailed = false;
  root.restartApplications = [];
  root.auditRefreshPending = false;
  context.panelLoader.item = makePanel({
    pendingBySection: {fonts: [staleMail]},
    sectionResults: {fonts: {state: 'pending', detail: staleMail.reason}},
    fontActionNeedsAttention: true, fontActionStatus: staleMail.reason,
    globalApplyStatus: 'Settings saved. Some applications need attention; see Applications.'
  });
  Object.assign(processState, {running: false, handled: false, resultExitCode: 0,
    auditGeneration: root.auditGeneration, sectionGeneration: {...root.sectionGeneration},
    outputText: JSON.stringify({schemaVersion: 1, pendingApplications: attributed || [],
      pendingBySection: {fonts: attributed || []}, results: fontResult ? {fonts: fontResult} : {}})});
  return context.panelLoader.item;
}
let panel = fontObservation({transaction: null, pendingApplications: []});
root.finishReconciliation();
assert.equal(panel.attentionItems.length, 0);
assert.equal(panel.fontActionNeedsAttention, false);
assert.equal(panel.sectionResults.fonts.state, 'saved');
assert.equal(panel.globalApplyStatus, 'Settings saved.');
assert(!panel.fontActionStatus.includes('Close mail'));

const currentMail = {...staleMail, reason: 'The mail profile is still open.'};
panel = fontObservation({transaction: null, pendingApplications: [currentMail]}, [currentMail, reload]);
root.finishReconciliation();
assert.deepStrictEqual(JSON.parse(JSON.stringify(panel.pendingBySection.fonts)), [currentMail, reload]);
assert.equal(panel.attentionItems.length, 2, 'Current font notices must replace old ones without duplicates');
assert(panel.fontActionNeedsAttention);
assert.equal(panel.sectionResults.fonts.state, 'pending');
assert(panel.fontActionStatus.includes(currentMail.reason));

for (const condition of ['stale-section', 'failed-command', 'blocked', 'stale-audit', 'missing-font-result']) {
  panel = fontObservation(condition === 'missing-font-result' ? null :
    {transaction: null, pendingApplications: [], blocked: condition === 'blocked'});
  if (condition === 'stale-section') processState.sectionGeneration.fonts -= 1;
  if (condition === 'failed-command') processState.resultExitCode = 1;
  if (condition === 'stale-audit') processState.auditGeneration -= 1;
  root.finishReconciliation();
  assert.deepStrictEqual(JSON.parse(JSON.stringify(panel.pendingBySection.fonts)), [staleMail], condition);
  assert(panel.fontActionNeedsAttention, condition);
  assert.equal(panel.sectionResults.fonts.state, 'pending', condition);
}
console.log('Font reconciliation: no-op success clears stale mail; current mail/reload work retained; stale, failed, blocked and missing results preserve warnings.');
