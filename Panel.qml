pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui
import "FontActionResult.js" as FontActionResult

Panel {
  id: root
  moduleName: "si.omarchy-look-and-feel"
  ipcTarget: ""
  manageIpc: false

  readonly property color popupForeground: Color.popups.text
  readonly property color popupBackground: Color.popups.background

  property var anchorItem: null
  property var hostWidget: null
  readonly property var barIdentity: hostWidget || root
  readonly property string fontFamily: bar ? bar.fontFamily : Style.font.family
  readonly property int selectorHeight: Math.round(Style.font.body * 1.95)
  // Style.font values are logical pixels throughout this panel. Using
  // pointSize here scaled controls larger than adjacent text and widened
  // the action rows enough to squeeze their explanatory text.
  readonly property int controlFontPixelSize: Math.round(Style.font.body)
  property var fonts: []
  property bool onlyMonospacedTerminalFonts: false
  readonly property var terminalFonts: onlyMonospacedTerminalFonts
    ? fonts.filter(function(entry) { return entry.monospace === true }) : fonts
  property var themes: []
  property var unlockDesigns: []
  property var backgrounds: []
  property var icons: []
  property var themeModes: [
    { id: "automatic", name: "Automatic" },
    { id: "light", name: "Light all day" },
    { id: "dark", name: "Dark all day" }
  ]
  property var fontSizes: [
    { id: 8, name: "8 pt" }, { id: 9, name: "9 pt" },
    { id: 10, name: "10 pt" }, { id: 11, name: "11 pt" },
    { id: 12, name: "12 pt" }, { id: 13, name: "13 pt" },
    { id: 14, name: "14 pt" }, { id: 16, name: "16 pt" },
    { id: 18, name: "18 pt" }, { id: 20, name: "20 pt" },
    { id: 24, name: "24 pt" }, { id: 28, name: "28 pt" },
    { id: 32, name: "32 pt" }, { id: 36, name: "36 pt" },
    { id: 48, name: "48 pt" }
  ]
  property string selectedSystemFontId: ""
  property string selectedTerminalFontId: ""
  property int selectedSystemSize: 12
  property int selectedTerminalSize: 12
  property string selectedThemeMode: "automatic"
  property string lastAppliedTheme: ""
  property string observedTheme: ""
  property bool lastAppliedThemeSetThisSession: false
  property string selectedLightThemeId: ""
  property string selectedDarkThemeId: ""
  property string selectedUnlockId: ""
  property string selectedUnlockPreview: ""
  property bool unlockSelectionChanged: false
  property string selectedBackgroundId: ""
  property string selectedIconId: ""
  property bool inventoryLoaded: false
  property string manualAppQuery: ""
  property string manualAppStatus: ""
  property bool manualAppActionRunning: false
  property bool manualAuditClearRunning: false
  property string fontActionStatus: ""
  property bool fontActionRunning: false
  property bool fontUndoAvailable: false
  property bool fontActionNeedsAttention: false
  property bool themeActionNeedsAttention: false
  readonly property bool unlockApplyAvailable: false
  property bool globalApplyRunning: false
  property string globalApplyStatus: ""
  property var globalApplySteps: []
  property int globalApplyStepIndex: 0
  property string globalApplyCurrentStep: ""
  property bool globalApplyStepSucceeded: false
  property string appearanceAuditStatus: ""
  property bool appearanceAuditRunning: false
  property bool appearanceActionRunning: false
  property string appearanceActionKind: ""
  property string unlockBaselineTransaction: ""
  property string unlockRequestedSlug: ""
  property string unlockOperation: "apply"
  property int unlockStatusPollCount: 0
  property int unlockStatusExitCode: 0
  property bool unlockStatusPollHandled: false
  property bool unlockStatusProcessExited: false
  property var appearanceActionStatuses: ({})
  property var appearanceActionMessages: ({ theme: "", background: "", icons: "", unlock: "" })

  property int activeTab: 0
  property bool unlockExpanded: false
  property string inventoryError: ""
  property bool refreshFontSelection: false
  property bool applyFailed: false
  property var sectionResults: ({})
  property var pendingBySection: ({ fonts: [], theme: [] })
  property var applicationRecords: []
  property string applicationSearch: ""
  readonly property bool busy: globalApplyRunning || appearanceActionRunning || fontActionRunning || manualAppActionRunning || manualAuditClearRunning
  readonly property var attentionItems: collectAttention()
  readonly property var activePreview: (themes.find(function(entry) { return entry.name === root.observedTheme }) || {}).preview || ({})
  readonly property color surfaceColor: Qt.tint(popupBackground, Qt.rgba(popupForeground.r, popupForeground.g, popupForeground.b, 0.035))
  readonly property color lineColor: Qt.tint(popupBackground, Qt.rgba(popupForeground.r, popupForeground.g, popupForeground.b, 0.24))
  readonly property color rawLabelColor: (activePreview.swatches || [])[5] || Color.accent
  readonly property color rawBrandColor: (activePreview.swatches || [])[4] || Color.accent
  readonly property color accentColor: readable(Color.accent)
  readonly property color labelColor: readable(rawLabelColor)
  readonly property color brandColor: readable(rawBrandColor)
  readonly property color mutedColor: readable(Qt.tint(popupBackground, Qt.rgba(popupForeground.r, popupForeground.g, popupForeground.b, 0.72)))
  readonly property color warningColor: readable(popupBackground.hslLightness < 0.5 ? "#f5c66a" : "#805200")

  function readable(candidate) {
    var c = Qt.color(candidate)
    function luminance(color) {
      function channel(v) { return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4) }
      return 0.2126 * channel(color.r) + 0.7152 * channel(color.g) + 0.0722 * channel(color.b)
    }
    var b = luminance(root.popupBackground)
    // Keep the theme's hue where possible instead of turning all light-theme
    // accents into the same gray. The extra margin covers lightly tinted rows.
    for (var step = 0; step <= 20; step++) {
      var amount = step / 20
      var adjusted = Qt.rgba(c.r + (root.popupForeground.r - c.r) * amount,
                             c.g + (root.popupForeground.g - c.g) * amount,
                             c.b + (root.popupForeground.b - c.b) * amount, 1)
      var a = luminance(adjusted)
      if ((Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05) >= 4.8) return adjusted
    }
    return root.popupForeground
  }

  function selectTab(index) {
    if (index < 0 || index > 2) return
    root.activeTab = index
    contentViewport.contentY = 0
  }

  function revealControl(control) {
    // Layout may settle after focus changes. Header/footer controls are outside
    // this content tree and must not move the scrolling page.
    Qt.callLater(function() {
      if (!control || !control.activeFocus) return
      var ancestor = control
      while (ancestor && ancestor !== content) ancestor = ancestor.parent
      if (!ancestor || contentViewport.height <= 0) return
      var top = control.mapToItem(content, 0, 0).y
      var bottom = top + control.height
      var position = contentViewport.contentY
      var padding = 8
      if (control.height + padding * 2 >= contentViewport.height || top - padding < position)
        position = top - padding
      else if (bottom + padding > position + contentViewport.height)
        position = bottom + padding - contentViewport.height
      contentViewport.contentY = Math.max(0, Math.min(position, Math.max(0, contentViewport.contentHeight - contentViewport.height)))
    })
  }

  function entryFor(records, id) { return records.find(function(entry) { return entry.id === id }) || ({}) }

  function fileUrl(path) { return path ? "file://" + String(path).split("/").map(encodeURIComponent).join("/") : "" }

  function adoptObservedThemeName(raw) {
    var name = String(raw || "").trim().toLowerCase()
    root.observedTheme = /^[a-z0-9][a-z0-9_-]*$/.test(name) ? name : ""
  }

  function setSectionResult(kind, state, detail) {
    var results = Object.assign({}, root.sectionResults)
    results[kind] = { state: state, detail: detail || "" }
    root.sectionResults = results
  }

  function updatePending(kind, data) {
    var pending = (data.pendingApplications || []).slice()
    var reload = data.terminalReload || ((data.runtimeRefresh || {}).terminalReload) || ({})
    ;(reload.failed || []).forEach(function(app) { pending.push({ app: app, action: "reload", reason: "Settings saved. Reopen the application to see the changes." }) })
    var groups = Object.assign({}, root.pendingBySection)
    groups[kind] = pending
    root.pendingBySection = groups
  }

  function collectAttention() {
    var items = [], seen = ({})
    var pending = (root.pendingBySection.fonts || []).concat(root.pendingBySection.theme || [])
    if (root.hostWidget) pending = pending.concat(root.hostWidget.reconciliationPending || [])
    pending.forEach(function(item) {
      var key = item.app + ":" + item.action + ":" + item.reason
      if (!seen[key]) { seen[key] = true; items.push(item) }
    })
    Object.keys(root.sectionResults).forEach(function(kind) {
      var result = root.sectionResults[kind]
      if (result.state === "error") items.push({ app: root.globalApplyStepName(kind), action: "error", reason: result.detail })
    })
    if (root.inventoryError) items.push({ app: "Catalog", action: "error", reason: root.inventoryError })
    if (root.hostWidget && root.hostWidget.reconciliationFailed)
      items.push({ app: "Appearance check", action: "error", reason: root.hostWidget.reconciliationMessage })
    return items
  }

  function actionTitle(action) {
    if (action === "login") return "Sign out and back in"
    if (action === "close-and-apply" || action === "apply-when-closed") return "Close, then Apply again"
    if (action === "reopen" || action === "reload") return "Reopen to see changes"
    if (action === "apply-integration") return "Apply to enable integration"
    return "Needs attention"
  }

  function filteredApplications() {
    var query = root.applicationSearch.trim().toLowerCase()
    return root.applicationRecords.filter(function(app) { return !query || (app.name + " " + app.id + " " + app.framework).toLowerCase().indexOf(query) >= 0 })
  }

  function runAppearanceAction(kind, args, fromGlobalApply) {
    if (root.appearanceActionRunning || root.fontActionRunning || root.manualAppActionRunning || root.manualAuditClearRunning
        || (root.globalApplyRunning && !fromGlobalApply)) return false
    root.appearanceActionKind = kind
    root.setSectionResult(kind, "working", "Saving settings…")
    var messages = Object.assign({}, root.appearanceActionMessages)
    messages[kind] = "Applying selected " + kind + "…"
    root.appearanceActionMessages = messages
    root.appearanceActionRunning = true
    appearanceActionProcess.command = ["/usr/bin/python3", "-B", localPath(Qt.resolvedUrl("controller.py"))].concat(args)
    appearanceActionProcess.running = true
    return true
  }

  function applySelectedTheme(fromGlobalApply) {
    if (!root.selectedLightThemeId || !root.selectedDarkThemeId) return false
    return root.runAppearanceAction("theme", ["apply-theme", root.selectedThemeMode,
      root.catalogName(root.themes, root.selectedLightThemeId),
      root.catalogName(root.themes, root.selectedDarkThemeId)], fromGlobalApply)
  }

  function applySelectedIcons(fromGlobalApply) {
    if (!root.selectedIconId) return false
    return root.runAppearanceAction("icons", ["apply-catalog-action", "icons", root.selectedIconId], fromGlobalApply)
  }

  function adoptIconSelection(savedId, observedName, resetSelection) {
    var requested = resetSelection ? String(savedId || "") : root.selectedIconId
    if (resetSelection && !requested) {
      var observed = root.icons.find(function(entry) { return entry.name === observedName })
      requested = observed ? observed.id : ""
    }
    if (requested && !root.icons.some(function(entry) { return entry.id === requested })) {
      root.selectedIconId = ""
      root.appearanceActionMessages = Object.assign({}, root.appearanceActionMessages,
        { icons: "The previous icon selection is unavailable. Choose an installed icon theme to include icons in Apply." })
    } else {
      root.selectedIconId = requested
    }
  }

  function applySelectedBackground(fromGlobalApply) {
    if (!root.selectedBackgroundId) return false
    return root.runAppearanceAction("background", ["apply-catalog-action", "background", root.selectedBackgroundId], fromGlobalApply)
  }

  function launchUnlockCommand(args, expectedSlug, operation, fromGlobalApply) {
    if (!root.unlockApplyAvailable) {
      root.appearanceActionMessages = Object.assign({}, root.appearanceActionMessages,
        { unlock: "Boot unlock is preview-only while boot rebuild verification is being repaired." })
      return false
    }
    if (root.appearanceActionRunning || root.fontActionRunning || root.manualAppActionRunning || root.manualAuditClearRunning
        || (root.globalApplyRunning && !fromGlobalApply)) return false
    root.appearanceActionKind = "unlock"
    root.unlockBaselineTransaction = String((root.appearanceActionStatuses.unlock || {}).transaction || "")
    root.unlockRequestedSlug = expectedSlug
    root.unlockOperation = operation
    root.unlockStatusPollCount = 0
    var messages = Object.assign({}, root.appearanceActionMessages)
    messages.unlock = "Applying boot unlock design…"
    root.appearanceActionMessages = messages
    root.appearanceActionRunning = true
    unlockApplyProcess.command = ["/usr/bin/omarchy-launch-floating-terminal-with-presentation", "/usr/bin/python3", "-B",
      localPath(Qt.resolvedUrl("controller.py"))].concat(args)
    unlockApplyProcess.running = true
    return true
  }

  function applySelectedUnlock(fromGlobalApply) {
    if (!root.selectedUnlockId) return false
    var slug = root.catalogName(root.unlockDesigns, root.selectedUnlockId).toLowerCase().replace(/ /g, "-")
    return root.launchUnlockCommand(["apply-catalog-action", "unlock", root.selectedUnlockId], slug, "apply", fromGlobalApply)
  }

  function undoAppearanceAction(kind) {
    if (kind === "unlock") {
      var previous = String((root.appearanceActionStatuses.unlock || {}).previousValue || "")
      if (!previous) return
      root.launchUnlockCommand(["rollback-appearance", "unlock"], previous, "undo")
      return
    }
    root.runAppearanceAction(kind, ["rollback-appearance", kind])
  }

  function open() {
    root.controller.show()
    refreshInventory()
  }

  function close() {
    root.controller.hide()
  }

  function toggle() {
    if (root.opened) root.close()
    else root.open()
  }

  function localPath(url) {
    var value = String(url)
    if (value.indexOf("file://") === 0) value = value.substring(7)
    return decodeURIComponent(value)
  }

  function refreshInventory() {
    inventoryProcess.command = ["/usr/bin/python3", "-B", localPath(Qt.resolvedUrl("controller.py")), "inventory"]
    inventoryProcess.running = true
  }

  function applyGlobalFonts(fromGlobalApply) {
    if (root.fontActionRunning || root.appearanceActionRunning || root.manualAppActionRunning || root.manualAuditClearRunning
        || (root.globalApplyRunning && !fromGlobalApply) || !root.selectedSystemFontId || !root.selectedTerminalFontId) return false
    root.setSectionResult("fonts", "working", "Saving font settings…")
    root.fontActionStatus = "Applying the selected global font settings…"
    root.fontActionRunning = true
    globalFontProcess.command = ["/usr/bin/python3", "-B", localPath(Qt.resolvedUrl("controller.py")),
      "apply-global-fonts", root.selectedSystemFontId, String(root.selectedSystemSize),
      root.selectedTerminalFontId, String(root.selectedTerminalSize)]
    globalFontProcess.running = true
    return true
  }

  function globalApplyStepName(step) {
    if (step === "fonts") return "Fonts"
    if (step === "theme") return "Theme"
    if (step === "background") return "Background"
    if (step === "icons") return "Icons"
    if (step === "unlock") return "Boot unlock"
    return "Settings"
  }

  function finishGlobalFontAction() {
    if (!globalFontProcess.exitSeen || !globalFontProcess.stdoutFinished
        || !globalFontProcess.stderrFinished || globalFontProcess.handled) return
    globalFontProcess.handled = true
    var result = FontActionResult.evaluate(globalFontProcess.outputText,
      globalFontProcess.errorText, globalFontProcess.resultExitCode)
    root.fontActionRunning = false
    root.globalApplyStepSucceeded = result.success
    root.fontActionStatus = result.message
    root.fontActionNeedsAttention = !!result.needsAction
    if (result.undoAvailable !== undefined) root.fontUndoAvailable = result.undoAvailable
    if (result.success) {
      root.updatePending("fonts", JSON.parse(globalFontProcess.outputText))
    }
    root.setSectionResult("fonts", result.success ? (result.needsAction ? "pending" : "saved") : "error", result.message)
    if (result.refreshInventory) { root.refreshFontSelection = true; root.refreshInventory() }
    if (root.globalApplyRunning && root.globalApplyCurrentStep === "fonts")
      Qt.callLater(function() { root.finishGlobalApplyStep(result.success, result.message) })
  }

  function applyAllSelectedSettings() {
    if (root.globalApplyRunning || root.appearanceActionRunning || root.fontActionRunning
        || root.manualAppActionRunning || root.manualAuditClearRunning) return
    if (!root.selectedSystemFontId || !root.selectedTerminalFontId
        || !root.selectedLightThemeId || !root.selectedDarkThemeId || !root.selectedBackgroundId) {
      root.applyFailed = true
      root.globalApplyCurrentStep = ""
      root.globalApplyStatus = "Select both fonts, both themes, and a background before applying."
      return
    }
    root.applyFailed = false
    root.globalApplySteps = ["theme", "fonts", "background"]
    if (root.selectedIconId) root.globalApplySteps.push("icons")
    if (root.unlockApplyAvailable && root.unlockSelectionChanged && root.selectedUnlockId) root.globalApplySteps.push("unlock")
    root.globalApplyStepIndex = 0
    root.globalApplyRunning = true
    root.globalApplyStatus = ""
    root.applyNextGlobalStep()
  }

  function applyNextGlobalStep() {
    if (!root.globalApplyRunning) return
    if (root.globalApplyStepIndex >= root.globalApplySteps.length) {
      var includedUnlock = root.globalApplySteps.indexOf("unlock") >= 0
      root.globalApplyRunning = false
      root.globalApplyStatus = includedUnlock
        ? "The selected theme, fonts, background, and boot unlock design were applied."
        : ((root.fontActionNeedsAttention || root.themeActionNeedsAttention)
            ? "Settings saved. Some applications need attention; see Applications. Boot unlock was not applied."
            : "Settings saved and configuration read back. Application rendering still needs checking. Boot unlock was not applied.")
      return
    }
    var step = root.globalApplySteps[root.globalApplyStepIndex]
    root.globalApplyCurrentStep = step
    root.globalApplyStepSucceeded = false
    root.globalApplyStatus = "Applying " + root.globalApplyStepName(step) + " ("
      + (root.globalApplyStepIndex + 1) + " of " + root.globalApplySteps.length + ")…"
    var started = false
    if (step === "fonts") started = root.applyGlobalFonts(true)
    else if (step === "theme") started = root.applySelectedTheme(true)
    else if (step === "background") started = root.applySelectedBackground(true)
    else if (step === "icons") started = root.applySelectedIcons(true)
    else if (step === "unlock") started = root.applySelectedUnlock(true)
    if (!started) root.finishGlobalApplyStep(false, "The selected settings could not be applied.")
  }

  function finishGlobalApplyStep(succeeded, detail) {
    if (!root.globalApplyRunning) return
    var step = root.globalApplyCurrentStep
    if (!succeeded) {
      root.applyFailed = true
      root.setSectionResult(step, "error", detail)
      root.globalApplyRunning = false
      root.globalApplyStatus = "Apply stopped at " + root.globalApplyStepName(step) + ". "
        + (detail || "The step failed.") + " Later steps were not run; completed steps remain applied."
      return
    }
    if (step === "unlock") root.unlockSelectionChanged = false
    root.globalApplyStepIndex += 1
    Qt.callLater(root.applyNextGlobalStep)
  }

  function handleUnlockStatusPoll() {
    if (unlockStatusProcess.running || !root.unlockStatusProcessExited || root.unlockStatusPollHandled) return
    if (!unlockStatusProcess.statusRead) {
      if (root.unlockStatusPollCount < 40) return
      root.unlockStatusPollHandled = true
      unlockStatusPoll.stop()
      root.appearanceActionRunning = false
      var missing = Object.assign({}, root.appearanceActionMessages)
      missing.unlock = "The selected boot unlock design was not verified."
      root.appearanceActionMessages = missing
      if (root.globalApplyRunning && root.globalApplyCurrentStep === "unlock")
        Qt.callLater(function() { root.finishGlobalApplyStep(false, missing.unlock) })
      return
    }

    var status = unlockStatusProcess.parsedStatus || ({})
    var observed = String(status.observedValue || "")
    if (root.unlockStatusExitCode === 0 && observed === root.unlockRequestedSlug) {
      root.unlockStatusPollHandled = true
      unlockStatusPoll.stop()
      root.appearanceActionRunning = false
      var messages = Object.assign({}, root.appearanceActionMessages)
      if (root.unlockOperation === "undo") {
        messages.unlock = "Restored the previous boot unlock design."
        root.unlockSelectionChanged = false
        var restoredUnlock = root.unlockDesigns.find(function(entry) { return String(entry.name).toLowerCase().replace(/ /g, "-") === observed })
        if (restoredUnlock) root.selectedUnlockId = restoredUnlock.id
      } else {
        messages.unlock = status.transaction && status.transaction !== root.unlockBaselineTransaction
          ? "Applied and verified the selected boot unlock design."
          : "The selected boot unlock design is already active."
      }
      root.appearanceActionMessages = messages
      root.refreshInventory()
      Qt.callLater(root.runAppearanceAudit)
      if (root.globalApplyRunning && root.globalApplyCurrentStep === "unlock")
        Qt.callLater(function() { root.finishGlobalApplyStep(true, messages.unlock) })
      return
    }

    root.unlockStatusPollHandled = true
    if (root.unlockStatusPollCount >= 40) {
      unlockStatusPoll.stop()
      root.appearanceActionRunning = false
      var pending = Object.assign({}, root.appearanceActionMessages)
      pending.unlock = "The selected boot unlock design was not verified."
      root.appearanceActionMessages = pending
      if (root.globalApplyRunning && root.globalApplyCurrentStep === "unlock")
        Qt.callLater(function() { root.finishGlobalApplyStep(false, pending.unlock) })
    }
  }

  function undoGlobalFonts() {
    if (root.fontActionRunning || root.appearanceActionRunning || root.manualAppActionRunning || root.manualAuditClearRunning || root.globalApplyRunning) return
    root.setSectionResult("fonts", "working", "Restoring font settings…")
    root.fontActionStatus = "Restoring the previous global font settings…"
    root.fontActionRunning = true
    globalFontProcess.command = ["/usr/bin/python3", "-B", localPath(Qt.resolvedUrl("controller.py")), "rollback-global-fonts"]
    globalFontProcess.running = true
  }

  function inspectManualApp() {
    if (root.manualAppActionRunning || root.fontActionRunning || root.appearanceActionRunning || root.globalApplyRunning || root.manualAppQuery.trim().length < 2) return
    manualAppStatus = "Auditing the entered app and checking verified shared font controls…"
    manualAppActionRunning = true
    manualAppProcess.command = ["/usr/bin/python3", "-B", localPath(Qt.resolvedUrl("controller.py")), "audit-app", root.manualAppQuery.trim()]
    manualAppProcess.running = true
  }

  function clearManualAudit() {
    if (root.manualAuditClearRunning || root.manualAppActionRunning || root.fontActionRunning || root.appearanceActionRunning || root.globalApplyRunning) return
    root.manualAuditClearRunning = true
    manualAuditClearProcess.command = ["/usr/bin/python3", "-B", localPath(Qt.resolvedUrl("controller.py")), "clear-manual-app-audit"]
    manualAuditClearProcess.running = true
  }

  function catalogName(records, id) {
    var entry = records.find(function(item) { return item.id === id })
    return entry ? entry.name : ""
  }

  function runAppearanceAudit() {
    if (root.appearanceAuditRunning) return
    var expected = {
      systemFont: root.catalogName(root.fonts, root.selectedSystemFontId),
      systemSizePt: root.selectedSystemSize,
      terminalFont: root.catalogName(root.fonts, root.selectedTerminalFontId),
      terminalSizePt: root.selectedTerminalSize,
      themeMode: root.selectedThemeMode,
      lightTheme: root.catalogName(root.themes, root.selectedLightThemeId),
      darkTheme: root.catalogName(root.themes, root.selectedDarkThemeId),
      appliedTheme: root.lastAppliedTheme,
      unlockTheme: root.catalogName(root.unlockDesigns, root.selectedUnlockId),
      background: (root.backgrounds.find(function(entry) { return entry.id === root.selectedBackgroundId }) || {}).source || ""
    }
    appearanceAuditStatus = "Reading current font settings, active theme, background, and Plymouth unlock image…"
    appearanceAuditRunning = true
    appearanceAuditProcess.command = ["/usr/bin/python3", "-B", localPath(Qt.resolvedUrl("controller.py")), "audit-appearance", JSON.stringify(expected)]
    appearanceAuditProcess.running = true
  }

  function adoptAppearanceAudit(raw) {
    try {
      var result = JSON.parse(String(raw || "{}"))
      var candidates = result.applicationCandidateCoverage || ({})
      var sources = candidates.sourceStatus || ({})
      var coverage = result.launcherFrameworkIdentification || ({})
      var lines = [
        "Overall readback: " + (result.overall || "unknown"),
        "Audit classification: " + (candidates.frameworkIdentified || 0) + "/" + (candidates.discovered || 0)
          + " discovered candidate records (" + Number(candidates.percent || 0).toFixed(1) + "%). This is toolkit classification coverage, not proof of font or theme control.",
        "Visible launcher classification: " + (coverage.identified || 0) + "/" + (coverage.denominator || 0)
          + " (" + Number(coverage.percent || 0).toFixed(1) + "%). Package-only and hidden app records use separate audit sources.",
        "Discovery sources — packages: " + (sources.pacman || "unknown") + "; package metadata: " + (sources.pacmanAppstream || "unknown")
          + "; Flatpak: " + (sources.flatpak || "unknown") + "; Snap: " + (sources.snap || "unknown") + "; AppImage: " + (sources.AppImage || "unknown") + ".",
        "Fonts: " + (result.summary.font || "not checked"),
        "Theme: " + (result.summary.theme || "not checked"),
        "Background: " + (result.summary.background || "not checked"),
        "Boot unlock: " + (result.summary.unlock || "not checked")
      ]
      var issues = (result.checks || []).filter(function(check) {
        return check.state === "mismatched" || check.state === "pending-restart" || check.state === "unobservable"
      })
      if (issues.length) {
        var byGroup = { font: 0, terminal: 0, theme: 0, background: 0, unlock: 0 }
        issues.forEach(function(check) {
          if (Object.prototype.hasOwnProperty.call(byGroup, check.group)) byGroup[check.group] += 1
        })
        lines.push(issues.length + " readback item(s) need attention: fonts " + byGroup.font + ", terminals " + byGroup.terminal
          + ", theme " + byGroup.theme + ", background " + byGroup.background + ", unlock " + byGroup.unlock + ".")
      }
      lines.push("Readback checks current settings and installed state; it does not prove rendered appearance or that the plugin caused those values.")
      appearanceAuditStatus = lines.filter(function(line) { return line !== "" }).join("\n")
    } catch (e) {
      appearanceAuditStatus = "The appearance audit returned an unreadable result."
    }
  }

  function adoptInventory(raw) {
    try {
      var data = JSON.parse(String(raw || "{}"))
      if (!data || !data.catalog_entries || !Array.isArray(data.catalog_entries.fonts) || !Array.isArray(data.catalog_entries.themes)) throw new Error("Invalid inventory")
      var entries = data.catalog_entries
      root.inventoryError = ""
      root.applicationRecords = ((data.font_application_inventory || {}).desktopApplications || []).filter(function(app) { return !app.hidden && !app.noDisplay && app.launchable !== false }).sort(function(a, b) { return a.name.localeCompare(b.name) })
      fonts = entries.fonts || []
      themes = (entries.themes || []).filter(function(entry) { return entry.selectable })
      unlockDesigns = (entries.unlocks || []).filter(function(entry) { return entry.selectable })
      backgrounds = (entries.backgrounds || []).filter(function(entry) { return entry.selectable }).map(function(entry) {
        var copy = Object.assign({}, entry)
        var source = String(entry.source || "")
        var themeName = source.match(/\/themes\/([^/]+)\/backgrounds\//)
        var userThemeName = source.match(/\/omarchy\/backgrounds\/([^/]+)\//)
        var collection = themeName ? themeName[1] : (userThemeName ? userThemeName[1] : "")
        if (collection) collection = collection.replace(/[-_]+/g, " ").replace(/\b\w/g, function(letter) { return letter.toUpperCase() })
        copy.label = entry.name + (collection ? " — " + collection : "")
        return copy
      })
      icons = (entries.icons || []).filter(function(entry) { return entry.selectable })
      var resetIconSelection = !inventoryLoaded
      appearanceActionStatuses = data.appearance_action_status || ({})
      root.observedTheme = String((appearanceActionStatuses.theme || {}).observedValue || "")
      fontUndoAvailable = data.global_font_undo_available === true
      if (!lastAppliedThemeSetThisSession && appearanceActionStatuses.theme && appearanceActionStatuses.theme.expectedValue)
        lastAppliedTheme = String(appearanceActionStatuses.theme.expectedValue)

      function idFor(records, name) {
        var entry = records.find(function(item) { return item.name === name })
        return entry ? entry.id : ""
      }

      if (!inventoryLoaded) {
        selectedSystemFontId = (data.preferences && data.preferences.systemFontId) || (fonts.length ? fonts[0].id : "")
        selectedTerminalFontId = (data.preferences && data.preferences.terminalFontId)
          || (fonts.length ? fonts[0].id : "")
        if (data.preferences && Number.isInteger(data.preferences.systemFontSizePt)
            && data.preferences.systemFontSizePt >= 6 && data.preferences.systemFontSizePt <= 48)
          selectedSystemSize = data.preferences.systemFontSizePt
        if (data.preferences && Number.isInteger(data.preferences.terminalFontSizePt)
            && data.preferences.terminalFontSizePt >= 6 && data.preferences.terminalFontSizePt <= 48)
          selectedTerminalSize = data.preferences.terminalFontSizePt
        selectedThemeMode = "automatic"
        var savedTheme = data.desiredAppearance && data.desiredAppearance.theme
        if (savedTheme) {
          selectedThemeMode = savedTheme.mode
          selectedLightThemeId = idFor(themes, savedTheme.light)
          selectedDarkThemeId = idFor(themes, savedTheme.dark)
        } else {
          var activeTheme = (appearanceActionStatuses.theme || {}).observedValue
          selectedLightThemeId = idFor(themes, activeTheme) || (themes.length ? themes[0].id : "")
          selectedDarkThemeId = selectedLightThemeId
        }
        selectedUnlockId = ""
        selectedUnlockPreview = ""
        var activeBackground = (appearanceActionStatuses.background || {}).observedValue
        var preferredBackground = backgrounds.find(function(entry) { return entry.source === activeBackground })
        selectedBackgroundId = preferredBackground ? preferredBackground.id : (backgrounds.length ? backgrounds[0].id : "")
        inventoryLoaded = true
      }
      if (root.refreshFontSelection) {
        selectedSystemFontId = (data.preferences || {}).systemFontId || selectedSystemFontId
        selectedTerminalFontId = (data.preferences || {}).terminalFontId || selectedTerminalFontId
        selectedSystemSize = (data.preferences || {}).systemFontSizePt || selectedSystemSize
        selectedTerminalSize = (data.preferences || {}).terminalFontSizePt || selectedTerminalSize
        root.refreshFontSelection = false
      }
      root.adoptIconSelection(data.desiredAppearance && data.desiredAppearance.icons,
        (appearanceActionStatuses.icons || {}).observedValue, resetIconSelection)
    } catch (e) {
      root.inventoryError = "Could not refresh the catalog. Your selections are kept; try opening the panel again."
    }
  }

  component Caption: Text {
    color: root.popupForeground
    font.family: root.fontFamily
    font.pixelSize: root.controlFontPixelSize
    wrapMode: Text.Wrap
    textFormat: Text.PlainText
  }
  component FieldLabel: Caption { color: root.labelColor; font.weight: Font.Medium }
  component Divider: Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: root.lineColor }
  component ActionButton: Controls.Button {
    id: action
    property bool selected: false
    property bool primary: false
    property bool quiet: false
    property bool round: false
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    onActiveFocusChanged: if (activeFocus) root.revealControl(action)
    implicitHeight: root.selectorHeight + 6
    implicitWidth: Math.max(round ? implicitHeight : 72, contentItem.implicitWidth + 24)
    leftPadding: 12; rightPadding: 12
    Accessible.name: text
    contentItem: Text {
      text: action.text; textFormat: Text.PlainText
      font.family: root.fontFamily; font.pixelSize: root.controlFontPixelSize
      font.weight: action.primary || action.selected ? Font.DemiBold : Font.Normal
      color: action.primary ? root.popupBackground : root.popupForeground
      opacity: action.enabled ? 1 : 0.5
      horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
      elide: Text.ElideRight
    }
    background: Rectangle {
      radius: action.round ? height / 2 : 3
      color: action.primary ? root.accentColor : (action.selected || action.hovered || action.down ? Qt.tint(root.popupBackground, Qt.rgba(root.popupForeground.r, root.popupForeground.g, root.popupForeground.b, 0.09)) : "transparent")
      border.width: action.activeFocus ? 2 : 1
      border.color: action.activeFocus || action.selected ? root.accentColor : (action.quiet && !action.hovered ? "transparent" : root.lineColor)
      opacity: action.enabled ? 1 : 0.45
    }
  }
  component Picker: Controls.ComboBox {
    id: picker
    Layout.fillWidth: true
    implicitHeight: root.selectorHeight + 6
    font.family: root.fontFamily; font.pixelSize: root.controlFontPixelSize
    textRole: "name"; valueRole: "id"
    focusPolicy: Qt.StrongFocus
    onActiveFocusChanged: if (activeFocus) root.revealControl(picker)
    hoverEnabled: true
    leftPadding: 12; rightPadding: 32
    Accessible.name: accessibleLabel
    property string accessibleLabel: "Selection"
    background: Rectangle {
      color: root.surfaceColor; radius: 3
      border.color: picker.activeFocus || picker.hovered ? root.accentColor : root.lineColor
      border.width: picker.activeFocus ? 2 : 1
      opacity: picker.enabled ? 1 : 0.45
    }
    contentItem: Text {
      text: picker.displayText; textFormat: Text.PlainText
      color: root.popupForeground; opacity: picker.enabled ? 1 : 0.5
      font: picker.font; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight
    }
    indicator: Text {
      x: picker.width - width - 12; y: (picker.height - height) / 2
      text: "⌄"; color: root.mutedColor; font.pixelSize: root.controlFontPixelSize
    }
    delegate: Controls.ItemDelegate {
      required property var modelData
      required property int index
      width: picker.width
      text: String(modelData[picker.textRole] || "")
      font: picker.font
      highlighted: picker.highlightedIndex === index
      contentItem: Text {
        text: parent.text; textFormat: Text.PlainText; font: picker.font
        color: root.popupForeground; elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter
      }
      background: Rectangle { color: parent.highlighted ? Qt.tint(root.popupBackground, Qt.rgba(root.popupForeground.r, root.popupForeground.g, root.popupForeground.b, 0.12)) : root.popupBackground }
    }
    popup: Controls.Popup {
      y: picker.height + 4; width: picker.width
      height: Math.min(contentItem.implicitHeight + 8, Math.max(100, Math.min(300, panel.availableCardHeight - 100)))
      padding: 4
      background: Rectangle { color: root.popupBackground; border.color: root.lineColor; radius: 3 }
      contentItem: ListView {
        implicitHeight: contentHeight
        clip: true; model: picker.popup.visible ? picker.delegateModel : null
        currentIndex: picker.highlightedIndex
        Controls.ScrollIndicator.vertical: Controls.ScrollIndicator {}
      }
    }
  }
  component SearchField: Controls.TextField {
    id: input
    onActiveFocusChanged: if (activeFocus) root.revealControl(input)
    implicitHeight: root.selectorHeight + 6
    font.family: root.fontFamily; font.pixelSize: root.controlFontPixelSize
    color: root.popupForeground; placeholderTextColor: root.mutedColor
    selectionColor: root.accentColor; selectedTextColor: root.popupBackground
    leftPadding: 12; rightPadding: 12
    background: Rectangle { color: root.surfaceColor; radius: 3; border.color: input.activeFocus ? root.accentColor : root.lineColor; border.width: input.activeFocus ? 2 : 1 }
  }
  component ResultNotice: ColumnLayout {
    id: notice
    property string kind: ""
    property var result: root.sectionResults[kind] || ({})
    property bool expanded: false
    visible: !!result.state
    spacing: 4
    RowLayout {
      Layout.fillWidth: true
      Caption {
        Layout.fillWidth: true
        text: notice.result.state === "working" ? "Saving settings…" : notice.result.state === "error" ? "Last action: could not complete" : notice.result.state === "pending" ? "Last action: saved · attention needed" : "Last action: settings saved"
        color: notice.result.state === "error" || notice.result.state === "pending" ? root.warningColor : root.mutedColor
        font.pixelSize: Math.max(11, root.controlFontPixelSize - 1)
      }
      ActionButton { quiet: true; text: notice.expanded ? "Hide details" : "Details"; onClicked: notice.expanded = !notice.expanded }
    }
    Caption { Layout.fillWidth: true; visible: notice.expanded; text: notice.result.detail || ""; color: root.mutedColor; font.pixelSize: Math.max(11, root.controlFontPixelSize - 1) }
  }
  component ThemeChoice: ColumnLayout {
    id: choice
    property string heading: ""
    property bool light: false
    property string selectedId: light ? root.selectedLightThemeId : root.selectedDarkThemeId
    readonly property var entry: root.entryFor(root.themes, selectedId)
    readonly property var preview: entry.preview || ({})
    Layout.fillWidth: true
    spacing: 8
    RowLayout {
      Layout.fillWidth: true
      FieldLabel { text: choice.heading; Layout.fillWidth: true }
      Caption { objectName: choice.light ? "lightThemeActiveBadge" : "darkThemeActiveBadge"; text: "Active now"; visible: !!choice.entry.name && choice.entry.name === root.observedTheme; color: root.mutedColor; font.pixelSize: Math.max(11, root.controlFontPixelSize - 2) }
    }
    Rectangle {
      objectName: choice.light ? "lightThemePreview" : "darkThemePreview"
      Layout.fillWidth: true; implicitHeight: 116
      color: choice.preview.background || root.surfaceColor
      border.color: root.lineColor; radius: 3; clip: true
      ColumnLayout {
        anchors.fill: parent; anchors.margins: 14; spacing: 9
        RowLayout {
          spacing: 5
          Repeater { model: 3; Rectangle { required property int index; width: 6; height: 6; radius: 3; color: choice.preview.foreground || root.mutedColor; opacity: 0.2 + index * 0.1 } }
          Item { Layout.fillWidth: true }
          Text { text: "Window preview"; color: choice.preview.foreground || root.mutedColor; font.family: root.fontFamily; font.pixelSize: 11 }
        }
        Text { Layout.fillWidth: true; text: choice.entry.preview ? "Make it feel like yours." : "Preview unavailable"; color: choice.preview.foreground || root.popupForeground; font.family: root.fontFamily; font.pixelSize: root.controlFontPixelSize + 1; elide: Text.ElideRight }
        Row {
          spacing: 6
          Repeater { model: choice.preview.swatches || []; Rectangle { required property var modelData; width: 19; height: 12; radius: 2; color: modelData } }
        }
      }
    }
    Picker {
      accessibleLabel: choice.heading; model: root.themes; textRole: "displayName"
      currentIndex: root.themes.findIndex(function(entry) { return entry.id === choice.selectedId })
      displayText: currentIndex >= 0 ? currentText : "Select theme"
      onActivated: function(index) { if (choice.light) root.selectedLightThemeId = root.themes[index].id; else root.selectedDarkThemeId = root.themes[index].id }
    }
  }
  component FontChoice: ColumnLayout {
    id: choice
    property bool terminal: false
    readonly property string selectedId: terminal ? root.selectedTerminalFontId : root.selectedSystemFontId
    readonly property int selectedSize: terminal ? root.selectedTerminalSize : root.selectedSystemSize
    readonly property string selectedFamily: root.catalogName(root.fonts, selectedId)
    Layout.fillWidth: true; Layout.alignment: Qt.AlignTop; spacing: 12
    FieldLabel { text: choice.terminal ? "Terminals" : "System applications" }
    Rectangle {
      Layout.fillWidth: true; implicitHeight: Math.max(158, choice.selectedSize * 96 / 72 * 2.6 + 48)
      color: root.surfaceColor; border.color: root.lineColor; radius: 3; clip: true
      ColumnLayout {
        anchors.fill: parent; anchors.margins: 16; spacing: 8
        Text {
          objectName: choice.terminal ? "terminalFontPreview" : "systemFontPreview"
          Layout.fillWidth: true
          text: choice.terminal ? "> Hello, world!\n0123456789  {} []" : "A place for everything.\nAa Bb Cc  0123456789"
          font.family: choice.selectedFamily || root.fontFamily
          font.pointSize: choice.selectedSize
          color: root.popupForeground; elide: Text.ElideRight
          maximumLineCount: 2; wrapMode: Text.Wrap
        }
        Item { Layout.fillHeight: true }
        Caption { Layout.fillWidth: true; text: choice.selectedFamily ? choice.selectedFamily + " · " + choice.selectedSize + " pt" : "Choose a font below"; color: root.mutedColor; font.pixelSize: Math.max(11, root.controlFontPixelSize - 2); elide: Text.ElideRight; maximumLineCount: 1 }
      }
    }
    Caption { text: "Font family"; color: root.mutedColor; font.pixelSize: root.controlFontPixelSize - 1 }
    Picker {
      objectName: choice.terminal ? "terminalFontPicker" : "systemFontPicker"
      accessibleLabel: choice.terminal ? "Terminal font family" : "System font family"
      model: choice.terminal ? root.terminalFonts : root.fonts
      currentIndex: model.findIndex(function(entry) { return entry.id === choice.selectedId })
      displayText: currentIndex >= 0 ? currentText : choice.selectedFamily || "Select font"
      onActivated: function(index) { if (choice.terminal) root.selectedTerminalFontId = model[index].id; else root.selectedSystemFontId = model[index].id }
    }
    RowLayout {
      Layout.fillWidth: true
      Caption { text: "Size"; color: root.mutedColor; Layout.fillWidth: true }
      Picker {
        objectName: choice.terminal ? "terminalSizePicker" : "systemSizePicker"
        accessibleLabel: choice.terminal ? "Terminal font size" : "System font size"
        Layout.fillWidth: false; Layout.preferredWidth: 110
        model: root.fontSizes
        currentIndex: root.fontSizes.findIndex(function(entry) { return entry.id === choice.selectedSize })
        displayText: choice.selectedSize + " pt"
        onActivated: function(index) { if (choice.terminal) root.selectedTerminalSize = root.fontSizes[index].id; else root.selectedSystemSize = root.fontSizes[index].id }
      }
    }
    Controls.CheckBox {
      id: monoFilter
      objectName: choice.terminal ? "monospaceFilter" : "systemMonospaceFilter"
      onActiveFocusChanged: if (activeFocus) root.revealControl(monoFilter)
      visible: choice.terminal
      text: "Only show monospaced fonts"
      checked: root.onlyMonospacedTerminalFonts
      onToggled: root.onlyMonospacedTerminalFonts = checked
      font.family: root.fontFamily; font.pixelSize: root.controlFontPixelSize - 1
      indicator: Rectangle {
        x: monoFilter.leftPadding
        y: (monoFilter.height - height) / 2
        width: 18; height: 18; radius: 2
        color: monoFilter.checked ? root.accentColor : root.surfaceColor
        border.color: monoFilter.activeFocus || monoFilter.checked ? root.accentColor : root.mutedColor
        border.width: monoFilter.activeFocus ? 2 : 1
        Text { anchors.centerIn: parent; text: "✓"; visible: monoFilter.checked; color: root.popupBackground; font.pixelSize: 14; font.bold: true }
      }
      contentItem: Text { text: parent.text; font: parent.font; color: root.popupForeground; leftPadding: parent.indicator.width + 8; verticalAlignment: Text.AlignVCenter }
    }
  }

  KeyboardPanel {
    id: panel
    anchorItem: root.anchorItem
    owner: root.barIdentity
    bar: root.bar
    open: root.opened
    centerOnBar: true
    focusTarget: keyCatcher
    contentWidth: panel.fittedContentWidth(840)
    contentHeight: panel.fittedContentHeight(Math.max(600, root.controlFontPixelSize * 45))

    PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      // This panel uses native controls, rather than the shell's cursor-driven
      // navigation signals. Leave Tab, arrows and typing to those controls.
      blocked: true
      Keys.onEscapePressed: function(event) { root.close(); event.accepted = true }

      Controls.Pane {
        anchors.fill: parent
        padding: 0
        background: null
        palette.window: root.popupBackground
        palette.base: root.popupBackground
        palette.alternateBase: Qt.tint(root.popupBackground, Qt.rgba(root.popupForeground.r, root.popupForeground.g, root.popupForeground.b, 0.06))
        palette.button: root.popupBackground
        palette.windowText: root.popupForeground
        palette.text: root.popupForeground
        palette.buttonText: root.popupForeground
        palette.placeholderText: Qt.tint(root.popupBackground, Qt.rgba(root.popupForeground.r, root.popupForeground.g, root.popupForeground.b, 0.75))
        palette.brightText: root.popupBackground
        palette.highlight: root.popupForeground
        palette.highlightedText: root.popupBackground
        palette.light: Qt.lighter(root.popupBackground, 1.1)
        palette.midlight: Qt.lighter(root.popupBackground, 1.05)
        palette.mid: Qt.tint(root.popupBackground, Qt.rgba(root.popupForeground.r, root.popupForeground.g, root.popupForeground.b, 0.3))
        palette.dark: Qt.tint(root.popupBackground, Qt.rgba(root.popupForeground.r, root.popupForeground.g, root.popupForeground.b, 0.5))
        palette.shadow: root.popupForeground
        palette.disabled.windowText: Qt.tint(root.popupBackground, Qt.rgba(root.popupForeground.r, root.popupForeground.g, root.popupForeground.b, 0.65))
        palette.disabled.text: Qt.tint(root.popupBackground, Qt.rgba(root.popupForeground.r, root.popupForeground.g, root.popupForeground.b, 0.65))
        palette.disabled.buttonText: Qt.tint(root.popupBackground, Qt.rgba(root.popupForeground.r, root.popupForeground.g, root.popupForeground.b, 0.65))

      ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 14
        RowLayout {
          Layout.fillWidth: true; spacing: 8
          ColumnLayout {
            spacing: 4
            RowLayout {
              spacing: 6
              Text { text: "Look"; color: root.brandColor; font.family: root.fontFamily; font.pixelSize: root.controlFontPixelSize * 1.65; font.weight: Font.DemiBold }
              Text { text: "& Feel"; color: root.accentColor; font.family: root.fontFamily; font.pixelSize: root.controlFontPixelSize * 1.65; font.weight: Font.DemiBold }
              Caption { text: "v0.1.0"; color: root.mutedColor; font.pixelSize: root.controlFontPixelSize - 2; Layout.alignment: Qt.AlignBottom; Layout.bottomMargin: 3 }
            }
            Caption { text: "Your desktop, in one place"; color: root.mutedColor; font.pixelSize: root.controlFontPixelSize - 1 }
          }
          Item { Layout.fillWidth: true }
          ActionButton { text: "?"; round: true; implicitWidth: implicitHeight; Accessible.name: "Look and Feel help"; onClicked: helpDialog.open() }
        }
        RowLayout {
          Layout.fillWidth: true; spacing: 8; uniformCellSizes: true
          ActionButton { objectName: "tabAppearance"; text: "Appearance"; selected: root.activeTab === 0; Layout.fillWidth: true; onClicked: root.selectTab(0) }
          ActionButton { objectName: "tabFonts"; text: "Fonts"; selected: root.activeTab === 1; Layout.fillWidth: true; onClicked: root.selectTab(1) }
          ActionButton { objectName: "tabApplications"; text: "Applications" + (root.attentionItems.length ? " · " + root.attentionItems.length : ""); selected: root.activeTab === 2; Layout.fillWidth: true; onClicked: root.selectTab(2) }
        }
        Divider {}
        Flickable {
          id: contentViewport
          objectName: "contentViewport"
          Layout.fillWidth: true; Layout.fillHeight: true
          contentWidth: width; contentHeight: content.implicitHeight
          clip: true; boundsBehavior: Flickable.StopAtBounds
          interactive: contentHeight > height
          Controls.ScrollBar.vertical: Controls.ScrollBar { policy: contentViewport.contentHeight > contentViewport.height ? Controls.ScrollBar.AlwaysOn : Controls.ScrollBar.AlwaysOff }
          Column {
            id: content
            width: contentViewport.width - 12
            spacing: 16
            ColumnLayout {
              objectName: "appearancePage"
              width: parent.width; visible: root.activeTab === 0
              enabled: !root.busy; spacing: 16
              RowLayout {
                Layout.fillWidth: true; spacing: 6
                FieldLabel { text: "Mode"; Layout.fillWidth: true }
                Repeater {
                  model: ["Automatic", "Light", "Dark"]
                  ActionButton {
                    required property int index; required property string modelData
                    text: modelData; selected: root.selectedThemeMode === ["automatic", "light", "dark"][index]
                    onClicked: root.selectedThemeMode = ["automatic", "light", "dark"][index]
                  }
                }
              }
              GridLayout {
                Layout.fillWidth: true; columns: width < 620 ? 1 : 2
                columnSpacing: 20; rowSpacing: 18; uniformCellWidths: true
                ThemeChoice { light: true; heading: "Light theme" }
                ThemeChoice { light: false; heading: "Dark theme" }
              }
              Caption { Layout.fillWidth: true; text: "Automatic follows local sunrise and sunset."; color: root.mutedColor; font.pixelSize: root.controlFontPixelSize - 2; visible: root.selectedThemeMode === "automatic" }
              RowLayout {
                Layout.fillWidth: true
                ResultNotice { Layout.fillWidth: true; kind: "theme" }
                Item { Layout.fillWidth: true; visible: !root.sectionResults.theme }
                ActionButton { text: "Undo theme"; quiet: true; visible: !!(root.appearanceActionStatuses.theme || {}).undoAvailable; onClicked: root.undoAppearanceAction("theme") }
              }
              Divider {}
              GridLayout {
                Layout.fillWidth: true; columns: width < 620 ? 1 : 2
                columnSpacing: 20; rowSpacing: 18; uniformCellWidths: true
                ColumnLayout {
                  Layout.fillWidth: true; spacing: 8
                  RowLayout { Layout.fillWidth: true; FieldLabel { text: "Background"; Layout.fillWidth: true } ActionButton { text: "Undo"; quiet: true; visible: !!(root.appearanceActionStatuses.background || {}).undoAvailable; Accessible.name: "Undo background"; onClicked: root.undoAppearanceAction("background") } }
                  Rectangle {
                    objectName: "wallpaperPreview"
                    Layout.fillWidth: true; implicitHeight: 110; color: root.surfaceColor; border.color: root.lineColor; radius: 3; clip: true
                    Image {
                      id: wallpaperImage
                      anchors.fill: parent; anchors.margins: 1
                      source: root.fileUrl(root.entryFor(root.backgrounds, root.selectedBackgroundId).source)
                      sourceSize.width: 600; sourceSize.height: 240
                      asynchronous: true; fillMode: Image.PreserveAspectCrop
                    }
                    Caption { anchors.centerIn: parent; text: "Preview unavailable"; visible: wallpaperImage.status === Image.Error || wallpaperImage.status === Image.Null; color: root.mutedColor }
                  }
                  Picker { accessibleLabel: "Background"; model: root.backgrounds; textRole: "label"; currentIndex: root.backgrounds.findIndex(function(entry) { return entry.id === root.selectedBackgroundId }); displayText: currentIndex >= 0 ? currentText : "Select background"; onActivated: function(index) { root.selectedBackgroundId = root.backgrounds[index].id } }
                  ResultNotice { Layout.fillWidth: true; kind: "background" }
                }
                ColumnLayout {
                  Layout.fillWidth: true; Layout.alignment: Qt.AlignTop; spacing: 8
                  RowLayout { Layout.fillWidth: true; FieldLabel { text: "Icons"; Layout.fillWidth: true } ActionButton { text: "Undo"; quiet: true; visible: !!(root.appearanceActionStatuses.icons || {}).undoAvailable; Accessible.name: "Undo icons"; onClicked: root.undoAppearanceAction("icons") } }
                  Rectangle {
                    objectName: "iconPreview"
                    Layout.fillWidth: true; implicitHeight: 110; color: root.surfaceColor; border.color: root.lineColor; radius: 3
                    readonly property var samples: root.entryFor(root.icons, root.selectedIconId).previewIcons || []
                    Row {
                      anchors.centerIn: parent; spacing: 24
                      Repeater { model: parent.parent.samples; Image { required property var modelData; width: 40; height: 40; sourceSize.width: 64; sourceSize.height: 64; source: root.fileUrl(modelData.source); fillMode: Image.PreserveAspectFit; asynchronous: true } }
                    }
                    Caption { anchors.centerIn: parent; text: "No icon samples available"; visible: parent.samples.length === 0; color: root.mutedColor; font.pixelSize: root.controlFontPixelSize - 1 }
                  }
                  Picker { accessibleLabel: "Icon theme"; model: root.icons; textRole: "displayName"; currentIndex: root.icons.findIndex(function(entry) { return entry.id === root.selectedIconId }); displayText: currentIndex >= 0 ? currentText : "Keep current icons"; onActivated: function(index) { root.selectedIconId = root.icons[index].id } }
                  ResultNotice { Layout.fillWidth: true; kind: "icons" }
                }
              }
              Divider {}
              RowLayout {
                Layout.fillWidth: true
                ActionButton { objectName: "unlockPreviewToggle"; quiet: true; text: (root.unlockExpanded ? "▾ " : "▸ ") + "Boot unlock designs"; onClicked: root.unlockExpanded = !root.unlockExpanded }
                Item { Layout.fillWidth: true }
                Caption { text: "Preview only"; color: root.mutedColor; font.pixelSize: root.controlFontPixelSize - 2 }
              }
              ColumnLayout {
                visible: root.unlockExpanded; Layout.fillWidth: true; spacing: 8
                Caption { Layout.fillWidth: true; text: "Preview artwork here. Boot unlock changes are unavailable and are not included in Apply."; color: root.mutedColor; font.pixelSize: root.controlFontPixelSize - 1 }
                RowLayout {
                  Layout.fillWidth: true
                  Picker {
                    objectName: "unlockDesignPicker"
                    accessibleLabel: "Boot unlock preview"; model: root.unlockDesigns; textRole: "displayName"
                    currentIndex: root.unlockDesigns.findIndex(function(entry) { return entry.id === root.selectedUnlockId })
                    displayText: currentIndex >= 0 ? currentText : "Select a design to preview"
                    onActivated: function(index) { root.selectedUnlockId = root.unlockDesigns[index].id; root.selectedUnlockPreview = root.unlockDesigns[index].preview || ""; root.unlockSelectionChanged = true }
                  }
                  ActionButton { objectName: "openUnlockPreviewButton"; text: "Preview"; enabled: !!root.selectedUnlockPreview; onClicked: unlockPreviewDialog.open() }
                }
              }
            }
            ColumnLayout {
              objectName: "fontsPage"
              width: parent.width; visible: root.activeTab === 1; enabled: !root.busy; spacing: 18
              Caption { Layout.fillWidth: true; text: "Two fonts. One consistent desktop."; color: root.mutedColor }
              GridLayout { Layout.fillWidth: true; columns: width < 620 ? 1 : 2; uniformCellWidths: true; columnSpacing: 24; rowSpacing: 24; FontChoice { terminal: false } FontChoice { terminal: true } }
              Divider {}
              RowLayout { Layout.fillWidth: true; Caption { Layout.fillWidth: true; text: "Samples show your selections here. Application rendering may differ until settings are applied and the application is reopened."; color: root.mutedColor; font.pixelSize: root.controlFontPixelSize - 1 } ActionButton { text: "Undo fonts"; quiet: true; visible: root.fontUndoAvailable; onClicked: root.undoGlobalFonts() } }
              ResultNotice { Layout.fillWidth: true; kind: "fonts" }
            }
            ColumnLayout {
              objectName: "applicationsPage"
              width: parent.width; visible: root.activeTab === 2; spacing: 16
              FieldLabel { text: root.attentionItems.length ? "Needs your attention" : "Application settings" }
              Caption { Layout.fillWidth: true; visible: !root.attentionItems.length; text: "No pending actions reported. Saved settings do not verify each application's appearance."; color: root.mutedColor }
              Repeater {
                model: root.attentionItems
                Rectangle {
                  required property var modelData
                  Layout.fillWidth: true; implicitHeight: attentionRow.implicitHeight + 20
                  color: root.surfaceColor; border.color: root.lineColor; radius: 3
                  ColumnLayout {
                    id: attentionRow; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 10; spacing: 5
                    Caption { Layout.fillWidth: true; text: modelData.app + " · " + root.actionTitle(modelData.action); color: root.warningColor; font.weight: Font.Medium }
                    Caption { Layout.fillWidth: true; text: modelData.reason; color: root.mutedColor; font.pixelSize: root.controlFontPixelSize - 1 }
                  }
                }
              }
              Divider {}
              RowLayout { Layout.fillWidth: true; FieldLabel { text: "Detected applications"; Layout.fillWidth: true } Caption { text: root.applicationRecords.length + " found"; color: root.mutedColor; font.pixelSize: root.controlFontPixelSize - 2 } }
              SearchField { Layout.fillWidth: true; placeholderText: "Find an installed application…"; text: root.applicationSearch; onTextEdited: root.applicationSearch = text; Accessible.name: "Search detected applications" }
              ListView {
                id: applicationList
                Layout.fillWidth: true; implicitHeight: Math.min(260, contentHeight)
                clip: true; model: root.filteredApplications(); spacing: 1
                Controls.ScrollBar.vertical: Controls.ScrollBar {}
                delegate: Rectangle {
                  required property var modelData
                  width: applicationList.width; height: root.controlFontPixelSize * 3.5
                  color: root.surfaceColor
                  Column {
                    anchors.fill: parent; anchors.margins: 10; spacing: 3
                    Caption { width: parent.width; text: modelData.name; elide: Text.ElideRight; maximumLineCount: 1 }
                    Caption { width: parent.width; text: modelData.framework || "Toolkit not identified"; color: root.mutedColor; font.pixelSize: root.controlFontPixelSize - 2; elide: Text.ElideRight; maximumLineCount: 1 }
                  }
                }
              }
              Caption { Layout.fillWidth: true; visible: applicationList.count === 0; text: root.applicationSearch ? "No matching applications. Audit it below." : "No applications found in the current inventory."; color: root.mutedColor }
              Caption { Layout.fillWidth: true; text: "Detection identifies applications and toolkits, not verified appearance."; color: root.mutedColor; font.pixelSize: root.controlFontPixelSize - 2 }
              Divider {}
              FieldLabel { text: "Audit another application" }
              RowLayout {
                Layout.fillWidth: true
                SearchField { id: manualAppField; Layout.fillWidth: true; enabled: !root.busy; placeholderText: "App name, launcher, or package"; text: root.manualAppQuery; onTextEdited: root.manualAppQuery = text; onAccepted: root.inspectManualApp(); Accessible.name: "Application to audit" }
                ActionButton { text: root.manualAppActionRunning ? "Auditing…" : "Audit app"; enabled: !root.busy && root.manualAppQuery.trim().length >= 2; onClicked: root.inspectManualApp() }
              }
              Caption { Layout.fillWidth: true; visible: !!root.manualAppStatus; text: root.manualAppStatus; color: root.mutedColor; font.pixelSize: root.controlFontPixelSize - 1 }
              ActionButton { text: "Clear registrations"; quiet: true; enabled: !root.busy; onClicked: root.clearManualAudit() }
              Caption { Layout.fillWidth: true; visible: !!root.globalApplyStatus; text: root.globalApplyStatus; color: root.applyFailed ? root.warningColor : root.mutedColor; font.pixelSize: root.controlFontPixelSize - 1 }
            }
          }
        }
        Divider {}
        RowLayout {
          id: footer
          objectName: "panelFooter"
          Layout.fillWidth: true; spacing: 12
          ColumnLayout {
            Layout.fillWidth: true; spacing: 4
            Caption {
              Layout.fillWidth: true
              text: root.globalApplyRunning ? root.globalApplyStatus : root.applyFailed ? (root.globalApplyCurrentStep ? "Apply stopped at " + root.globalApplyStepName(root.globalApplyCurrentStep) : "Choose the missing settings") : root.attentionItems.length ? root.attentionItems.length + " action" + (root.attentionItems.length === 1 ? " needs" : "s need") + " attention" : root.globalApplyStatus ? "Last Apply: settings saved" : "Ready when you are"
              color: root.applyFailed || root.attentionItems.length ? root.warningColor : root.popupForeground
              font.pixelSize: root.controlFontPixelSize - 1
            }
            Caption { Layout.fillWidth: true; text: root.globalApplyRunning ? "Completed steps remain saved if a later step stops." : "Apply saves choices across all three tabs."; color: root.mutedColor; font.pixelSize: root.controlFontPixelSize - 2 }
          }
          ActionButton { text: "Review"; quiet: true; visible: root.attentionItems.length > 0 || root.applyFailed; onClicked: root.selectTab(2) }
          ActionButton { objectName: "applyChangesButton"; text: root.globalApplyRunning ? "Applying…" : "Apply changes"; primary: true; enabled: !root.busy && root.inventoryLoaded; onClicked: root.applyAllSelectedSettings() }
        }
      }

      Controls.Dialog {
        palette.window: root.popupBackground
        palette.base: root.popupBackground
        palette.alternateBase: Qt.tint(root.popupBackground, Qt.rgba(root.popupForeground.r, root.popupForeground.g, root.popupForeground.b, 0.06))
        palette.button: root.popupBackground
        palette.windowText: root.popupForeground
        palette.text: root.popupForeground
        palette.buttonText: root.popupForeground
        palette.placeholderText: Qt.tint(root.popupBackground, Qt.rgba(root.popupForeground.r, root.popupForeground.g, root.popupForeground.b, 0.75))
        palette.brightText: root.popupBackground
        palette.highlight: root.popupForeground
        palette.highlightedText: root.popupBackground
        palette.light: Qt.lighter(root.popupBackground, 1.1)
        palette.midlight: Qt.lighter(root.popupBackground, 1.05)
        palette.mid: Qt.tint(root.popupBackground, Qt.rgba(root.popupForeground.r, root.popupForeground.g, root.popupForeground.b, 0.3))
        palette.dark: Qt.tint(root.popupBackground, Qt.rgba(root.popupForeground.r, root.popupForeground.g, root.popupForeground.b, 0.5))
        palette.shadow: root.popupForeground
        palette.disabled.windowText: Qt.tint(root.popupBackground, Qt.rgba(root.popupForeground.r, root.popupForeground.g, root.popupForeground.b, 0.65))
        palette.disabled.text: Qt.tint(root.popupBackground, Qt.rgba(root.popupForeground.r, root.popupForeground.g, root.popupForeground.b, 0.65))
        palette.disabled.buttonText: Qt.tint(root.popupBackground, Qt.rgba(root.popupForeground.r, root.popupForeground.g, root.popupForeground.b, 0.65))

        id: unlockPreviewDialog
        title: "Boot unlock preview"
        modal: true
        anchors.centerIn: parent
        width: Math.min(640, panel.availableCardWidth - 40)
        height: Math.min(440, panel.availableCardHeight - 40)
        standardButtons: Controls.Dialog.Close
        contentItem: Image {
          objectName: "unlockDesignPreview"
          source: root.fileUrl(root.selectedUnlockPreview)
          fillMode: Image.PreserveAspectFit
          asynchronous: true
          cache: false
        }
      }

      Controls.Dialog {
        palette.window: root.popupBackground
        palette.base: root.popupBackground
        palette.alternateBase: Qt.tint(root.popupBackground, Qt.rgba(root.popupForeground.r, root.popupForeground.g, root.popupForeground.b, 0.06))
        palette.button: root.popupBackground
        palette.windowText: root.popupForeground
        palette.text: root.popupForeground
        palette.buttonText: root.popupForeground
        palette.placeholderText: Qt.tint(root.popupBackground, Qt.rgba(root.popupForeground.r, root.popupForeground.g, root.popupForeground.b, 0.75))
        palette.brightText: root.popupBackground
        palette.highlight: root.popupForeground
        palette.highlightedText: root.popupBackground
        palette.light: Qt.lighter(root.popupBackground, 1.1)
        palette.midlight: Qt.lighter(root.popupBackground, 1.05)
        palette.mid: Qt.tint(root.popupBackground, Qt.rgba(root.popupForeground.r, root.popupForeground.g, root.popupForeground.b, 0.3))
        palette.dark: Qt.tint(root.popupBackground, Qt.rgba(root.popupForeground.r, root.popupForeground.g, root.popupForeground.b, 0.5))
        palette.shadow: root.popupForeground
        palette.disabled.windowText: Qt.tint(root.popupBackground, Qt.rgba(root.popupForeground.r, root.popupForeground.g, root.popupForeground.b, 0.65))
        palette.disabled.text: Qt.tint(root.popupBackground, Qt.rgba(root.popupForeground.r, root.popupForeground.g, root.popupForeground.b, 0.65))
        palette.disabled.buttonText: Qt.tint(root.popupBackground, Qt.rgba(root.popupForeground.r, root.popupForeground.g, root.popupForeground.b, 0.65))

        id: helpDialog
        title: "Look & Feel help"
        modal: true
        anchors.centerIn: parent
        width: Math.min(660, panel.availableCardWidth - 40)
        height: Math.min(620, panel.availableCardHeight - 40)
        standardButtons: Controls.Dialog.Close
        contentItem: Controls.ScrollView {
          clip: true
          Column {
            width: parent.width
            spacing: 12
            Text {
              width: parent.width
              text: "APPLY CHANGES"
              color: root.popupForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              font.weight: Font.DemiBold
            }
            Text {
              width: parent.width
              text: "Use Appearance, Fonts and Applications to review your choices. Switching tabs keeps your draft selections. The Apply changes button stays below the scrolling content and applies selections from every tab: theme, fonts, background, then optional icons. Boot unlock is currently preview-only and is not applied. If a step fails, later steps stop; completed steps remain applied and can be undone with their section's Undo control. Section results describe the last action; Details expands the full message. Applications lists any remaining actions."
              color: root.popupForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              wrapMode: Text.Wrap
            }
            Text {
              width: parent.width
              text: "FONTS"
              color: root.popupForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              font.weight: Font.DemiBold
            }
            Text {
              width: parent.width
              text: "System font family and size set the shared GTK and Omarchy shell font targets. Terminal font family and size set detected terminal configurations with verified adapters; discovery is not exhaustive. Only show monospaced fonts filters the terminal menu using installed font spacing metadata. It starts unchecked and keeps your current font selected until you choose another, even if that font is absent from the filtered menu. Apply changes uses both selections; Undo fonts restores the previous plugin font transaction. Supported running terminals receive a reload request. Some applications need to be reopened; pending actions are listed in the result. Saving configuration does not verify every application's rendered fonts. An unresolved or unsupported manual audit registration blocks font Apply until it is resolved or cleared."
              color: root.popupForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              wrapMode: Text.Wrap
            }
            Text {
              width: parent.width
              text: "THEME"
              color: root.popupForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              font.weight: Font.DemiBold
            }
            Text {
              width: parent.width
              text: "Choose Automatic, Light or Dark mode on the Appearance tab. While the plugin is loaded, Automatic follows the current solar phase and checks saved appearance settings every 15 seconds. Choose the Light and Dark themes, then apply. Undo theme restores the previous detected theme."
              color: root.popupForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              wrapMode: Text.Wrap
            }
            Text {
              width: parent.width
              text: "BOOT UNLOCK PREVIEW"
              color: root.popupForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              font.weight: Font.DemiBold
            }
            Text {
              width: parent.width
              text: "Expand Boot unlock designs on the Appearance tab to preview installed artwork. Boot unlock changes are unavailable and are never included in Apply changes. Previous unlock journals are preserved."
              color: root.popupForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              wrapMode: Text.Wrap
            }
            Text {
              width: parent.width
              text: "BACKGROUND"
              color: root.popupForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              font.weight: Font.DemiBold
            }
            Text {
              width: parent.width
              text: "Choose a background on the Appearance tab. Apply changes applies the selection; its Undo control restores the previous background."
              color: root.popupForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              wrapMode: Text.Wrap
            }
            Text {
              width: parent.width
              text: "ICON THEME"
              color: root.popupForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              font.weight: Font.DemiBold
            }
            Text {
              width: parent.width
              text: "Icons use the selected installed theme across desktop, GTK and available Qt integrations. Undo icons restores the previous managed icon settings; unrelated font and palette edits are preserved. Applications with their own icon sets may not inherit desktop icons."
              color: root.popupForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              wrapMode: Text.Wrap
            }
            Text {
              width: parent.width
              text: "APPLICATION AUDIT"
              color: root.popupForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              font.weight: Font.DemiBold
            }
            Text {
              width: parent.width
              text: "Enter an application name, launcher, or package and press Return or select Audit app. The lookup searches separately from the automatic inventory. It can register verified shared GTK or supported terminal font surfaces for global font Apply; app-specific theme controls are not registered. Ambiguous or unsupported results block font Apply. Clear registrations deletes the saved manual audit registrations. Audit results omit application names."
              color: root.popupForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              wrapMode: Text.Wrap
            }
          }
        }
      }
      }
    }
  }

  // The current theme can change through Automatic mode or outside this panel.
  // Watch the same readback file as appearance_actions; never infer current
  // state from the saved draft or the last transaction's expected value.
  FileView {
    id: observedThemeName
    path: Quickshell.env("HOME") + "/.local/state/omarchy/current/theme.name"
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
    onLoaded: root.adoptObservedThemeName(text())
    onLoadFailed: root.observedTheme = ""
  }

  Process {
    id: inventoryProcess
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: root.adoptInventory(text)
    }
    onExited: function(code) {
      if (code !== 0) {
        root.inventoryError = "Could not refresh the catalog. Your selections are kept; try again."
      }
    }
  }

  function finishAppearanceAction() {
    if (appearanceActionProcess.handled || !appearanceActionProcess.exitSeen
        || !appearanceActionProcess.stdoutFinished || !appearanceActionProcess.stderrFinished) return
    appearanceActionProcess.handled = true
    var code = appearanceActionProcess.resultExitCode
    if (code === 0) {
      var kind = root.appearanceActionKind
      try {
        var result = JSON.parse(String(appearanceActionProcess.outputText || "{}"))
        root.globalApplyStepSucceeded = (typeof result.rolledBack === "string" && result.rolledBack.length > 0)
          || (result.state === "already-current" && typeof result.after === "string" && result.after.length > 0)
          || (result.state === "committed" && typeof result.readback === "string" && result.readback.length > 0)
        if (!root.globalApplyStepSucceeded) throw new Error("Unrecognized appearance result")
        var message
        if (result.rolledBack) {
          if (kind === "theme") {
            root.lastAppliedTheme = String(result.restored || "")
            root.observedTheme = String(result.readback || result.restored || "")
            root.lastAppliedThemeSetThisSession = true
          }
          message = "Restored the previous " + kind + " setting."
          if (kind === "theme") {
            var restoredTheme = String(result.restored || "").toLowerCase().replace(/_/g, "-")
            var restoredThemeEntry = root.themes.find(function(entry) { return String(entry.name).toLowerCase().replace(/_/g, "-") === restoredTheme })
            if (restoredThemeEntry) {
              root.selectedLightThemeId = restoredThemeEntry.id
              root.selectedDarkThemeId = restoredThemeEntry.id
            }
          } else if (kind === "background") {
            var restoredBackground = root.backgrounds.find(function(entry) { return entry.source === result.restored })
            if (restoredBackground) root.selectedBackgroundId = restoredBackground.id
          } else if (kind === "icons") {
            var restoredIcon = root.icons.find(function(entry) { return entry.name === result.restored })
            root.selectedIconId = restoredIcon ? restoredIcon.id : ""
          } else {
            var restoredUnlock = root.unlockDesigns.find(function(entry) { return String(entry.name).toLowerCase().replace(/_/g, "-") === String(result.restored || "").toLowerCase().replace(/_/g, "-") })
            if (restoredUnlock) root.selectedUnlockId = restoredUnlock.id
          }
        } else if (result.state === "already-current") {
          if (kind === "theme") {
            root.lastAppliedTheme = String(result.after || "")
            root.observedTheme = String(result.after || "")
            root.lastAppliedThemeSetThisSession = true
          }
          message = kind === "theme" && result.applicationTransaction
            ? "The desktop theme was already active; application settings were reconciled."
            : "The selected " + kind + " is already active; no change was needed."
        } else if (kind === "theme") {
          root.lastAppliedTheme = String(result.readback || "")
          root.observedTheme = String(result.readback || "")
          root.lastAppliedThemeSetThisSession = true
          message = "Desktop theme changed; application configuration was saved and read back."
        } else if (kind === "icons") {
          message = "Icon settings saved and read back for desktop, GTK and available Qt integrations."
        } else if (kind === "background") {
          message = "Applied and verified the selected background."
        } else {
          message = "Applied and verified the selected boot unlock design."
        }
        if (kind === "theme") {
          var pending = (result.pendingApplications || []).slice()
          var failedReloads = ((result.runtimeRefresh || {}).terminalReload || {}).failed || []
          failedReloads.forEach(function(name) {
            if (!pending.some(function(item) { return item.app === name && item.action === "reload" }))
              pending.push({ app: name, action: "reload", reason: "Settings saved, but its running window could not be refreshed; reopen it." })
          })
          root.themeActionNeedsAttention = pending.length > 0
          if (pending.length) message += " " + pending.map(function(item) { return item.app + ": " + item.reason }).join(" ")
        }
        var messages = Object.assign({}, root.appearanceActionMessages)
        messages[kind] = message
        root.appearanceActionMessages = messages
        if (kind === "theme") root.updatePending("theme", result)
        root.setSectionResult(kind, kind === "theme" && root.themeActionNeedsAttention ? "pending" : "saved", message)
        root.appearanceAuditStatus = ""
        root.refreshInventory()
        Qt.callLater(root.runAppearanceAudit)
      } catch (e) {
        root.globalApplyStepSucceeded = false
        var errors = Object.assign({}, root.appearanceActionMessages)
        errors[kind] = "Appearance action completed, but its result could not be read."
        root.appearanceActionMessages = errors
      }
    } else {
      root.globalApplyStepSucceeded = false
      var errors = Object.assign({}, root.appearanceActionMessages)
      errors[root.appearanceActionKind] = appearanceActionProcess.errorText.trim()
        || "Appearance action failed."
      root.appearanceActionMessages = errors
    }
    if (code !== 0 || !root.globalApplyStepSucceeded)
      root.setSectionResult(root.appearanceActionKind, "error", root.appearanceActionMessages[root.appearanceActionKind])
    root.appearanceActionRunning = false
    if (root.globalApplyRunning && root.globalApplyCurrentStep === root.appearanceActionKind) {
      var succeeded = code === 0 && root.globalApplyStepSucceeded
      var detail = root.appearanceActionMessages[root.appearanceActionKind]
      Qt.callLater(function() { root.finishGlobalApplyStep(succeeded, detail) })
    }
  }

  Process {
    id: appearanceActionProcess
    property string outputText: ""
    property string errorText: ""
    property int resultExitCode: -1
    property bool stdoutFinished: false
    property bool stderrFinished: false
    property bool exitSeen: false
    property bool handled: false
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
      appearanceActionProcess.outputText = String(text || "")
      appearanceActionProcess.stdoutFinished = true
      root.finishAppearanceAction()
    } }
    stderr: StdioCollector { waitForEnd: true; onStreamFinished: {
      appearanceActionProcess.errorText = String(text || "")
      appearanceActionProcess.stderrFinished = true
      root.finishAppearanceAction()
    } }
    onExited: function(code) {
      appearanceActionProcess.resultExitCode = code
      appearanceActionProcess.exitSeen = true
      root.finishAppearanceAction()
    }
  }

  Process {
    id: unlockApplyProcess
    onExited: function(code) {
      if (code !== 0) {
        root.appearanceActionRunning = false
        var errors = Object.assign({}, root.appearanceActionMessages)
        errors.unlock = "Could not start the boot unlock action."
        root.appearanceActionMessages = errors
        if (root.globalApplyRunning && root.globalApplyCurrentStep === "unlock")
          Qt.callLater(function() { root.finishGlobalApplyStep(false, errors.unlock) })
      } else {
        unlockStatusPoll.start()
      }
    }
  }

  Process {
    id: unlockStatusProcess
    property var parsedStatus: null
    property bool statusRead: false
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: {
      try {
        unlockStatusProcess.parsedStatus = JSON.parse(String(text || "{}"))
        unlockStatusProcess.statusRead = true
      } catch (e) {
        unlockStatusProcess.parsedStatus = null
        unlockStatusProcess.statusRead = false
      }
      root.handleUnlockStatusPoll()
    } }
    onExited: function(code) {
      root.unlockStatusExitCode = code
      root.unlockStatusProcessExited = true
      root.handleUnlockStatusPoll()
    }
  }

  Timer {
    id: unlockStatusPoll
    interval: 1500
    repeat: true
    onTriggered: {
      if (unlockStatusProcess.running) return
      root.unlockStatusPollCount += 1
      unlockStatusProcess.parsedStatus = null
      unlockStatusProcess.statusRead = false
      root.unlockStatusExitCode = 0
      root.unlockStatusPollHandled = false
      root.unlockStatusProcessExited = false
      unlockStatusProcess.command = ["/usr/bin/python3", "-B", localPath(Qt.resolvedUrl("controller.py")),
        "appearance-action-status", "unlock"]
      unlockStatusProcess.running = true
    }
  }

  Process {
    id: globalFontProcess
    property string outputText: ""
    property string errorText: ""
    property int resultExitCode: -1
    property bool stdoutFinished: false
    property bool stderrFinished: false
    property bool exitSeen: false
    property bool handled: false
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
      globalFontProcess.outputText = String(text || "")
      globalFontProcess.stdoutFinished = true
      root.finishGlobalFontAction()
    } }
    stderr: StdioCollector { waitForEnd: true; onStreamFinished: {
      globalFontProcess.errorText = String(text || "")
      globalFontProcess.stderrFinished = true
      if (globalFontProcess.errorText.trim()) console.warn("Look and Feel font command:", globalFontProcess.errorText)
      root.finishGlobalFontAction()
    } }
    onExited: function(code) {
      globalFontProcess.resultExitCode = code
      globalFontProcess.exitSeen = true
      root.finishGlobalFontAction()
    }
  }

  Process {
    id: manualAppProcess
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: {
      try {
        var result = JSON.parse(String(text || "{}"))
        if (result.status === "launcher-found" || result.status === "installed-item-found-no-launcher") {
          root.manualAppStatus = "Audit complete: " + Number(result.matchCount || 0) + " matching record(s). Registered font surfaces: "
            + Number(result.registeredCount || 0) + "; unsupported or unresolved surfaces: " + Number(result.unsupportedCount || 0)
            + ". App-specific theme surfaces not registered: " + Number(result.themeUnsupportedCount || 0) + ". "
            + (result.findings || []).slice(0, 4).map(function(item, index) {
              return "Finding " + (index + 1) + ": " + (item.framework || "framework unknown") + "; "
                + (item.roles || "control surface unknown") + "; font " + (item.fontStatus || "unsupported") + "."
            }).join(" ")
        } else
          root.manualAppStatus = "No matching installed record was found. Check the entry and try again."
      } catch (e) {
        root.manualAppStatus = "The app audit could not read its result."
      }
    } }
    stderr: StdioCollector { waitForEnd: true; onStreamFinished: {
      if (String(text || "").trim()) root.manualAppStatus = "The app audit could not be completed."
    } }
    onRunningChanged: if (!running) root.manualAppActionRunning = false
  }

  Process {
    id: manualAuditClearProcess
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: {
      try {
        var result = JSON.parse(String(text || "{}"))
        root.manualAppStatus = result.cleared ? "Manual audit registrations cleared." : "The audit registry could not be cleared."
      } catch (e) {
        root.manualAppStatus = "The audit registry could not be cleared."
      }
    } }
    stderr: StdioCollector { waitForEnd: true; onStreamFinished: {
      if (String(text || "").trim()) root.manualAppStatus = "The audit registry could not be cleared safely."
    } }
    onRunningChanged: if (!running) root.manualAuditClearRunning = false
  }

  Process {
    id: appearanceAuditProcess
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: root.adoptAppearanceAudit(text) }
    stderr: StdioCollector { waitForEnd: true; onStreamFinished: {
          if (String(text || "").trim()) root.appearanceAuditStatus = "The appearance audit could not be completed."
    } }
    onRunningChanged: if (!running) root.appearanceAuditRunning = false
  }
}
