import QtQuick
import Quickshell.Io

// Only the bounded supervisor writes to these collectors. The launch watchdog
// also completes when Python cannot start and Quickshell emits no exit signal.
Item {
  id: root
  visible: false
  property var command: []
  property bool running: false
  property int timeoutMs: 120000
  property int outputLimit: 8388608
  property string interpreter: "/usr/bin/python3"
  property string outputText: ""
  property string errorText: ""
  property int resultExitCode: -1
  property bool stdoutFinished: false
  property bool stderrFinished: false
  property bool exitSeen: false
  property bool handled: false
  property bool started: false
  property var worker: null
  signal completed()

  function finish() {
    if (!running || !exitSeen || !stdoutFinished || !stderrFinished) return
    startup.stop()
    watchdog.stop()
    var previous = worker
    worker = null
    if (previous) previous.retire()
    running = false
    completed()
  }
  function fail(message) {
    if (!running) return
    outputText = ""
    errorText = message
    resultExitCode = 125
    exitSeen = stdoutFinished = stderrFinished = true
    finish()
  }
  onRunningChanged: {
    if (!running) {
      startup.stop()
      watchdog.stop()
      var previous = worker
      worker = null
      if (previous) previous.retire()
      return
    }
    outputText = errorText = ""
    resultExitCode = -1
    stdoutFinished = stderrFinished = exitSeen = handled = false
    started = true
    // Fresh native processes keep late events from a cancelled request out of
    // an immediate retry, including a retry made inside completed().
    worker = workerFactory.createObject(root)
    worker.process.command = [interpreter, "-B", decodeURIComponent(String(Qt.resolvedUrl("process_supervisor.py")).replace(/^file:\/\//, "")),
                              String(timeoutMs / 1000), String(outputLimit)].concat(command)
    startup.start()
    watchdog.start()
    worker.process.running = true
  }
  Component.onDestruction: if (worker) worker.process.signal(15)
  Timer { id: startup; interval: 2000; onTriggered: root.fail("Could not start the appearance command.") }
  Timer { id: watchdog; interval: root.timeoutMs + 3000; onTriggered: root.fail("The appearance command did not finish within its time limit.") }
  Component {
    id: workerFactory
    Item {
      id: invocation
      property alias process: nativeProcess
      readonly property bool current: root.worker === invocation && root.running
      function retire() {
        nativeProcess.signal(15)
        cleanup.start()
      }
      // Give the supervisor time to reap its group before forcing a stuck
      // supervisor down. Old invocation callbacks cannot finish a new request.
      Timer { id: cleanup; interval: 1000; onTriggered: { nativeProcess.signal(9); invocation.destroy() } }
      Component.onDestruction: nativeProcess.signal(15)
      Process {
        id: nativeProcess
        onStarted: if (invocation.current) startup.stop()
        stdout: StdioCollector { waitForEnd: true; onStreamFinished: {
          if (!invocation.current) return
          root.outputText = text
          root.stdoutFinished = true
          root.finish()
        } }
        stderr: StdioCollector { waitForEnd: true; onStreamFinished: {
          if (!invocation.current) return
          root.errorText = text
          root.stderrFinished = true
          root.finish()
        } }
        onExited: function(code) {
          if (!invocation.current) return
          root.resultExitCode = code
          root.exitSeen = true
          root.finish()
        }
      }
    }
  }
}
