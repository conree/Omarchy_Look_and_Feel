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
  property int auditGeneration: 0
  property bool auditRefreshPending: false
  property var sectionGeneration: ({ fonts: 0, theme: 0, opacity: 0, icons: 0, blur: 0 })
  property var reconciliationOwners: ({})
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
    onTriggered: root.tryReconcile()
  }

  function tryReconcile() {
    var panel = panelLoader.item
    if (reconcileProcess.running || (reconcileProcess.started && !reconcileProcess.handled)
        || (panel && (panel.globalApplyRunning || panel.appearanceActionRunning || panel.fontActionRunning
                      || panel.manualAppActionRunning || panel.manualAuditClearRunning))) return
    root.auditRefreshPending = false
    reconcileProcess.running = true
  }

  function auditRegistryChanged() {
    root.auditGeneration += 1
    root.auditRefreshPending = true
    Qt.callLater(root.tryReconcile)
  }

  function sectionApplied(section) {
    var generations = Object.assign({}, root.sectionGeneration)
    generations[section] = (generations[section] || 0) + 1
    root.sectionGeneration = generations
    var owners = Object.assign({}, root.reconciliationOwners)
    root.reconciliationPending = root.reconciliationPending.filter(function(item) {
      var key = JSON.stringify(item)
      var previous = owners[key] || []
      if (previous.indexOf(section) < 0) return true
      owners[key] = previous.filter(function(owner) { return owner !== section })
      return owners[key].length > 0
    })
    root.reconciliationOwners = owners
    root.auditRefreshPending = true
    Qt.callLater(root.tryReconcile)
  }

  function isAuditAttention(item) {
    return (item.app === "Audited applications" && item.action === "review")
        || (item.app === "Fonts" && item.action === "manual-audit")
  }

  function finishReconciliation() {
    if (reconcileProcess.handled || !reconcileProcess.exitSeen
        || !reconcileProcess.stdoutFinished || !reconcileProcess.stderrFinished) return
    reconcileProcess.handled = true
    if (reconcileProcess.resultExitCode !== 0) {
      root.reconciliationFailed = true
      root.reconciliationMessage = reconcileProcess.errorText.trim() || "The appearance check failed."
      if (root.auditRefreshPending) Qt.callLater(root.tryReconcile)
      return
    }
    try {
      var result = JSON.parse(reconcileProcess.outputText)
      if (result.schemaVersion === 1 && result.skipped === "busy") {
        if (root.auditRefreshPending) Qt.callLater(root.tryReconcile)
        return
      }
      if (result.schemaVersion !== 1 || !Array.isArray(result.pendingApplications)) throw new Error("Invalid reconciliation result")
      root.reconciliationFailed = false
      var owners = ({})
      var attributed = result.pendingBySection
      if (!attributed || typeof attributed !== "object" || Array.isArray(attributed)) {
        attributed = ({})
        Object.keys(result.results || {}).forEach(function(section) {
          attributed[section] = (result.results[section] || {}).pendingApplications || []
        })
      }
      Object.keys(attributed).forEach(function(section) {
        ;(attributed[section] || []).forEach(function(item) {
          var key = JSON.stringify(item)
          if (!owners[key]) owners[key] = []
          if (owners[key].indexOf(section) < 0) owners[key].push(section)
        })
      })
      var staleSections = Object.keys(root.sectionGeneration).filter(function(section) {
        return (root.sectionGeneration[section] || 0) !== ((reconcileProcess.sectionGeneration || {})[section] || 0)
      })
      if (staleSections.length) {
        result.pendingApplications = result.pendingApplications.filter(function(item) {
          var key = JSON.stringify(item), previous = owners[key] || []
          if (!previous.length) return true
          owners[key] = previous.filter(function(section) { return staleSections.indexOf(section) < 0 })
          return owners[key].length > 0
        })
        root.auditRefreshPending = true
      }
      // A result captured before an audit change cannot describe the current
      // registry. Keep unrelated notices and request a fresh audit read.
      if (reconcileProcess.auditGeneration !== root.auditGeneration) {
        result.pendingApplications = result.pendingApplications.filter(function(item) { return !root.isAuditAttention(item) })
        root.auditRefreshPending = true
      }
      // A successful, current font reconciliation is the evidence that an
      // old audit warning no longer applies. Failed or stale reads must leave
      // the panel's prior warning in place.
      var panel = panelLoader.item
      var fontResult = (result.results || {}).fonts
      var registry = result.auditRegistryStatus
      var fontAuditResolved = fontResult && Array.isArray(attributed.fonts)
        && !attributed.fonts.some(function(item) { return root.isAuditAttention(item) })
      var registryAuditResolved = !fontResult && registry && registry.unsupportedCount === 0
      if (panel && (fontAuditResolved || registryAuditResolved)
          && reconcileProcess.auditGeneration === root.auditGeneration && staleSections.indexOf("fonts") < 0
          && typeof panel.clearAuditAttention === "function") panel.clearAuditAttention(false)
      root.reconciliationPending = result.pendingApplications
      root.reconciliationOwners = owners
      var opacity = (result.results || {}).opacity
      if (panel && staleSections.indexOf("opacity") < 0 && opacity && Array.isArray(opacity.pendingApplications)) {
        panel.updatePending("opacity", opacity)
        panel.opacityActionNeedsAttention = opacity.pendingApplications.length > 0
        if (!panel.opacityActionNeedsAttention && (panel.sectionResults.opacity || {}).state === "pending")
          panel.setSectionResult("opacity", "saved", "No terminal reloads are pending.")
      }
      if (Array.isArray(result.restartApplications)) root.restartApplications = result.restartApplications
      root.reconciliationMessage = result.pendingApplications.map(function(item) { return item.app + ": " + item.reason }).join("\n")
    } catch (e) { root.reconciliationFailed = true; root.reconciliationMessage = "The appearance check returned an unreadable result." }
    if (root.auditRefreshPending) Qt.callLater(root.tryReconcile)
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
    property bool started: false
    property int auditGeneration: 0
    property var sectionGeneration: ({})
    command: ["/usr/bin/python3", "-B", decodeURIComponent(String(Qt.resolvedUrl("controller.py")).replace(/^file:\/\//, "")), "reconcile"]
    onRunningChanged: if (running) {
      started = true
      auditGeneration = root.auditGeneration
      sectionGeneration = Object.assign({}, root.sectionGeneration)
      outputText = ""
      errorText = ""
      resultExitCode = -1
      stdoutFinished = false
      stderrFinished = false
      exitSeen = false
      handled = false
    } else if (root.auditRefreshPending && handled) Qt.callLater(root.tryReconcile)
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
