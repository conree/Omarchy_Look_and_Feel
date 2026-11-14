"""Opt-in hostile-offer regression on actual Qt/Quickshell and isolated Wayland.

Start a separate compositor with temporary HOME/config and XDG_RUNTIME_DIR,
then run: python3 -B tests/check_wayland_clipboard.py --runtime-dir /tmp/.../runtime
The real desktop's clipboard must never be used. The old revision is a positive
control; its GUI is expected to stall until the test kills its process group.
Payloads are bounded by the fixture and each offer is observed for five seconds.
"""
from pathlib import Path
import subprocess, os, time, signal, json, argparse, tempfile, re, stat
# Requires a separate compositor. Never point this test at the desktop socket.
parser=argparse.ArgumentParser(description="Hostile clipboard regression; requires an isolated Wayland compositor under /tmp.")
parser.add_argument("--runtime-dir", required=True, type=Path)
parser.add_argument("--display", default="wayland-1")
args=parser.parse_args()
runtime=args.runtime_dir.resolve()
if not runtime.is_relative_to(Path("/tmp")) or "/" in args.display:
    raise ValueError("Use a separate compositor socket under /tmp.")
if not stat.S_ISSOCK((runtime/args.display).lstat().st_mode):
    raise ValueError("The isolated socket must be a real socket, not a symlink.")
repo=Path(__file__).resolve().parents[1]
base=Path(tempfile.mkdtemp(prefix="laf-hostile-clipboard-check-"))
(base/"home").mkdir()
protocol=Path("/usr/share/wlr-protocols/unstable/wlr-data-control-unstable-v1.xml")
subprocess.run(["wayland-scanner","client-header",str(protocol),str(base/"data-control.h")],check=True)
subprocess.run(["wayland-scanner","private-code",str(protocol),str(base/"data-control.c")],check=True)
subprocess.run(["cc","-O2","-Wall","-I",str(base),str(repo/"tests/hostile_clipboard_owner.c"),str(base/"data-control.c"),"-o",str(base/"owner"),"-lwayland-client","-lpthread"],check=True)
for name in ['Commons','Ui','services']:
 p=base/name
 if not p.exists():p.symlink_to('/usr/share/omarchy/shell/'+name)
old=base/'Old';old.mkdir(exist_ok=True)
for f in repo.iterdir():
 if f.is_file() and f.suffix in ['.py','.js','.qml'] and f.name not in ['BarWidget.qml','Panel.qml']:
  p=old/f.name
  if not p.exists():p.symlink_to(f)
for name in ['BarWidget.qml','Panel.qml','qmldir']:
 (old/name).write_bytes(subprocess.check_output(['git','show','4f0fb67bcac8b5470a9719086a0c595f3dda5235:'+name],cwd=repo))
p=base/'Plugin'
if not p.exists():p.symlink_to(repo)
config=base/'home/.config/omarchy-look-and-feel';config.mkdir(parents=True,exist_ok=True)
(config/'repair.json').write_text('{"enabled":false}')
env=dict(os.environ,HOME=str(base/'home'),XDG_CONFIG_HOME=str(base/'home/.config'),XDG_CACHE_HOME=str(base/'home/.cache'),XDG_STATE_HOME=str(base/'home/.local/state'),XDG_RUNTIME_DIR=str(runtime),WAYLAND_DISPLAY=args.display,QT_QPA_PLATFORM='wayland',QT_QUICK_BACKEND='software',WAYLAND_DEBUG='client')
for key in ['HYPRLAND_INSTANCE_SIGNATURE','SESSION_MANAGER']:
 env.pop(key,None)
results=[]

def stop(p):
 if p.poll() is None:
  os.killpg(p.pid,signal.SIGKILL)
 p.wait()

for name,old_version,mode,behavior in [('old_closed_slow',True,'slow','cold'),('fixed_closed_slow',False,'slow','cold'),('fixed_open_slow',False,'slow','open'),('fixed_reclosed_burst',False,'burst','warm')]:
 qml=base/(name+'.qml')
 qml.write_text('''import QtQuick
import Quickshell
import "./MODULE" as Local
ShellRoot {
  function findPanel(item) {
    if (typeof item.selectTab === "function") return item
    var children = item.children || []
    for (var i=0; i<children.length;i++) { var found=findPanel(children[i]); if (found) return found }
    if (item.item) return findPanel(item.item)
    return null
  }
  Window { id: host; width: 1000; height: 800; visible: true; title: "LAF isolated clipboard test"
    Local.BarWidget { id: widget; width: 40; height: 30 }
    Component.onCompleted: requestActivate()
  }
  Timer { interval: 100; running: true; repeat: true; onTriggered: console.log("HEARTBEAT", Date.now()) }
  Timer { interval: 500; running: BEHAVIOR !== "cold"; onTriggered: { widget.open(); var p=findPanel(widget); if(p) p.selectTab(2); console.log("PANEL_OPEN",widget.opened) } }
  Timer { interval: 1500; running: BEHAVIOR === "warm"; onTriggered: { widget.close(); host.requestActivate(); console.log("PANEL_RECLOSED",widget.opened) } }
}
'''.replace('MODULE','Old' if old_version else 'Plugin').replace('BEHAVIOR',json.dumps(behavior)))
 log=base/(name+'.log');ownerlog=base/(name+'.owner.log')
 with log.open('w') as output,ownerlog.open('w') as attackout:
  shell=subprocess.Popen(['quickshell','--path',str(qml),'--no-color'],env=env,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
  owner=None
  try:
   time.sleep(3)
   before=log.read_text().count('HEARTBEAT')
   assert shell.poll() is None and before>5,log.read_text()[-4000:]
   owner=subprocess.Popen([str(base/'owner'),mode],env=env,stdout=attackout,stderr=subprocess.STDOUT,start_new_session=True)
   time.sleep(5)
   after=log.read_text().count('HEARTBEAT')
   native=log.read_text(); hostile=ownerlog.read_text()
   result={'name':name,'heartbeats_before':before,'heartbeats_during_attack':after-before,'requests':hostile.count('SEND_REQUEST'),'offer_delivered':bool(re.search(r'wl_data_device#\d+\.selection\(wl_data_offer#\d+\)',native)),'shell_alive':shell.poll() is None,'panel_open':'PANEL_OPEN true' in native,'panel_reclosed':'PANEL_RECLOSED false' in native}
   results.append(result);print(json.dumps(result),flush=True)
  finally:
   if owner:stop(owner)
   stop(shell)
(base/'results.json').write_text(json.dumps(results,indent=2)+'\n')

assert all(r["offer_delivered"] and r["shell_alive"] for r in results), results
assert results[0]["requests"] > 0 and results[0]["heartbeats_during_attack"] < 5, results[0]
assert all(r["requests"] == 0 and r["heartbeats_during_attack"] >= 35 for r in results[1:]), results[1:]
assert results[2]["panel_open"] and results[3]["panel_reclosed"], results
print("PASS: reviewed closed panel stalls; fixed closed/open/reclosed panel receives offers without reading text and remains responsive.")
print("Test logs:", base)
