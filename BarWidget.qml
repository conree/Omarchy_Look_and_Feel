import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui
import "." as Local

BarWidget {
  id: root
  moduleName: "si.omarchy-look-and-feel"

  readonly property bool opened: panelLoader.item ? panelLoader.item.opened === true : false
  property bool openRequested: false
  property string reconciliationMessage: ""
  property var reconciliationPending: []
  property var restartApplications: []
  property bool reconciliationFailed: false
  readonly property string appearanceConfigDir: {
    var configured = Quickshell.env("XDG_CONFIG_HOME")
    return (configured && configured.charAt(0) === "/" ? configured : Quickshell.env("HOME") + "/.config") + "/omarchy-look-and-feel/"
  }
  property bool shellFontOwned: false
  property string savedShellFont: ""

  // Omarchy defaults to its monospace alias. Bind the shared shell interface
  // directly while this plugin owns fonts; no optional font plugin is needed.
  // Restore the pre-existing binding/value when Fonts is undone or unloaded.
  onShellFontOwnedChanged: Local.ShellFontBridge.refresh()
  onSavedShellFontChanged: Local.ShellFontBridge.refresh()
  Component.onCompleted: Local.ShellFontBridge.acquire(root)
  Component.onDestruction: Local.ShellFontBridge.release(root)

  function readShellFontPolicy() {
    try {
      var desired = JSON.parse(desiredFontPolicy.text())
      var saved = JSON.parse(savedFontSelection.text())
      root.savedShellFont = saved.schemaVersion === 1 && typeof saved.systemFontFamily === "string" ? saved.systemFontFamily : ""
      root.shellFontOwned = desired.schemaVersion === 1 && !!desired.fonts
    } catch (e) { root.shellFontOwned = false }
  }

  FileView {
    id: desiredFontPolicy
    path: root.appearanceConfigDir + "policy.json"
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
    onLoaded: root.readShellFontPolicy()
    onLoadFailed: root.shellFontOwned = false
  }
  FileView {
    id: savedFontSelection
    path: root.appearanceConfigDir + "font-selection.json"
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
    onLoaded: root.readShellFontPolicy()
    onLoadFailed: root.shellFontOwned = false
  }

  Timer {
    interval: 15000
    running: true
    repeat: true
    triggeredOnStart: true
    onTriggered: {
      var panel = panelLoader.item
      if (reconcileProcess.running || (panel && (panel.globalApplyRunning || panel.appearanceActionRunning || panel.fontActionRunning))) return
      reconcileProcess.running = true
    }
  }

  function finishReconciliation() {
    if (reconcileProcess.handled || !reconcileProcess.exitSeen
        || !reconcileProcess.stdoutFinished || !reconcileProcess.stderrFinished) return
    reconcileProcess.handled = true
    if (reconcileProcess.resultExitCode !== 0) {
      root.reconciliationFailed = true
      root.reconciliationMessage = reconcileProcess.errorText.trim() || "The appearance check failed."
      return
    }
    try {
      var result = JSON.parse(reconcileProcess.outputText)
      if (result.schemaVersion === 1 && result.skipped === "busy") return
      if (result.schemaVersion !== 1 || !Array.isArray(result.pendingApplications)) throw new Error("Invalid reconciliation result")
      root.reconciliationFailed = false
      root.reconciliationPending = result.pendingApplications
      if (Array.isArray(result.restartApplications)) root.restartApplications = result.restartApplications
      root.reconciliationMessage = result.pendingApplications.map(function(item) { return item.app + ": " + item.reason }).join("\n")
    } catch (e) { root.reconciliationFailed = true; root.reconciliationMessage = "The appearance check returned an unreadable result." }
  }

  Process {
    id: reconcileProcess
    property string outputText: ""
    property string errorText: ""
    property int resultExitCode: -1
    property bool stdoutFinished: false
    property bool stderrFinished: false
    property bool exitSeen: false
    property bool handled: false
    command: ["/usr/bin/python3", "-B", decodeURIComponent(String(Qt.resolvedUrl("controller.py")).replace(/^file:\/\//, "")), "reconcile"]
    onRunningChanged: if (running) {
      outputText = ""
      errorText = ""
      resultExitCode = -1
      stdoutFinished = false
      stderrFinished = false
      exitSeen = false
      handled = false
    }
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: {
      reconcileProcess.outputText = String(text || "")
      reconcileProcess.stdoutFinished = true
      root.finishReconciliation()
    } }
    stderr: StdioCollector { waitForEnd: true; onStreamFinished: {
      reconcileProcess.errorText = String(text || "")
      reconcileProcess.stderrFinished = true
      root.finishReconciliation()
    } }
    onExited: function(code) {
      reconcileProcess.resultExitCode = code
      reconcileProcess.exitSeen = true
      root.finishReconciliation()
    }
  }

  function open() {
    root.openRequested = true
    var alreadyLoaded = !!panelLoader.item
    panelLoader.active = true
    if (alreadyLoaded && panelLoader.item) {
      root.injectPanel()
      panelLoader.item.open()
    }
  }

  function close() {
    root.openRequested = false
    if (panelLoader.item) panelLoader.item.close()
  }

  function closeForPopoutSwitch() {
    root.close()
  }

  function togglePanel() {
    if (root.opened) root.close()
    else root.open()
  }

  function injectPanel() {
    var target = panelLoader.item
    if (!target) return
    if ("bar" in target) target.bar = root.bar
    if ("settings" in target) target.settings = root.settings
    if ("anchorItem" in target) target.anchorItem = button
    if ("hostWidget" in target) target.hostWidget = root
  }

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  onBarChanged: injectPanel()
  onSettingsChanged: injectPanel()

  Loader {
    id: panelLoader
    // Prepare the catalog and decode static example images before the first
    // click. The panel remains closed until explicitly requested.
    active: true
    source: Qt.resolvedUrl("Panel.qml")
    visible: false
    onLoaded: {
      root.injectPanel()
      Qt.callLater(root.injectPanel)
      if (root.openRequested) item.open()
    }
  }

  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: "󰏘"
    labelVisible: true
    hasVisualContent: true
    horizontalMargin: 8.75
    verticalPadding: 8.75
    tooltipText: "Look & Feel" + (root.reconciliationMessage ? "\n" + root.reconciliationMessage : "")
    onPressed: function(buttonCode) {
      if (buttonCode === Qt.LeftButton) root.togglePanel()
    }
  }
}
