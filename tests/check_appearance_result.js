// Exercise the actual QML completion code, including all process event orders.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const panel=fs.readFileSync(path.join(__dirname,'../Panel.qml'),'utf8');
const start=panel.indexOf('  function finishAppearanceAction()');
const code=panel.slice(start,panel.indexOf('\n  Process {',start));
const permutations=[['out','err','exit'],['out','exit','err'],['err','out','exit'],['err','exit','out'],['exit','out','err'],['exit','err','out']];
function fixture(output) {
 const calls=[];
 const c={appearanceActionProcess:{handled:false,resultExitCode:0,outputText:JSON.stringify(output)},
 root:{appearanceActionKind:'theme',globalApplyRunning:true,globalApplyCurrentStep:'theme',appearanceActionMessages:{},
 themes:[],refreshInventory:()=>{},runAppearanceAudit:()=>{},finishGlobalApplyStep:(...args)=>calls.push(args)},Qt:{callLater:f=>f()}};
 vm.createContext(c);vm.runInContext(code,c);return [c,calls];
}
for (const events of permutations) {
 const [c,calls]=fixture({state:'committed',readback:'test',pendingApplications:[],runtimeRefresh:{terminalReload:{failed:['ghostty']}}});
 for(const [i,event] of events.entries()) {
  c.appearanceActionProcess[{out:'stdoutFinished',err:'stderrFinished',exit:'exitSeen'}[event]]=true;
  c.finishAppearanceAction();assert.equal(calls.length,i===2?1:0);
 }
 c.finishAppearanceAction();assert.equal(calls.length,1);assert(calls[0][0]);
 assert(c.root.themeActionNeedsAttention);assert(c.root.appearanceActionMessages.theme.includes('ghostty'));
}
for(const bad of [{},null,[],{state:'committed'},{state:'committed',readback:[]},{state:'already-current'}]) {
 const [c,calls]=fixture(bad);Object.assign(c.appearanceActionProcess,{stdoutFinished:true,stderrFinished:true,exitSeen:true});
 c.finishAppearanceAction();assert.equal(calls.length,1);assert(!calls[0][0]);
 assert(!c.root.appearanceActionMessages.theme.includes('Desktop theme changed'));
}
console.log('Appearance result handling passed: 6 event orders, malformed success refusal, terminal refresh attention.');
