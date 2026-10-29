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
  property int selectedOpacity: -1
  property string selectedBlur: "keep"
  property var blurChoices: [{ id: "keep", name: "Keep current settings" },
    { id: "off", name: "Off" }, { id: "on", name: "On" }]
  property var opacityChoices: [{ id: -1, name: "Keep current settings" }].concat(
    Array.from({ length: 21 }, function(_, index) {
      var percent = index * 5
      return { id: percent, name: percent + "%" + (percent === 100 ? " (opaque)" : "") }
    }))
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
  property bool previewCacheLoaded: false
  readonly property string previewCachePath: {
    var configured = Quickshell.env("XDG_CACHE_HOME")
    return (configured && configured.charAt(0) === "/" ? configured : Quickshell.env("HOME") + "/.cache")
      + "/omarchy-look-and-feel/panel-previews.json"
  }
  property string manualAppQuery: ""
  property string manualAppStatus: ""
  property bool manualAppActionRunning: false
  property bool manualAuditClearRunning: false
  property string fontActionStatus: ""
  property bool fontActionRunning: false
  property bool fontUndoAvailable: false
  property bool fontActionNeedsAttention: false
  property bool themeActionNeedsAttention: false
  property bool opacityActionNeedsAttention: false
  readonly property bool unlockApplyAvailable: root.inventoryLoaded && !!(root.appearanceActionStatuses.unlock || {}).applyAvailable
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
  property var appearanceActionStatuses: ({})
  property var appearanceActionMessages: ({ theme: "", background: "", icons: "", unlock: "" })

  property int activeTab: 0
  property string inventoryError: ""
  property bool refreshFontSelection: false
  property bool applyFailed: false
  property var sectionResults: ({})
  property var pendingBySection: ({ fonts: [], theme: [], opacity: [] })
  property var restartApplications: []
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
    root.updateRestartApplications(data)
    var pending = (data.pendingApplications || []).slice()
    var reload = data.terminalReload || ((data.runtimeRefresh || {}).terminalReload) || ({})
    ;(reload.failed || []).forEach(function(app) { pending.push({ app: app, action: "reload", reason: "Settings saved. Reopen the application to see the changes." }) })
    var groups = Object.assign({}, root.pendingBySection)
    groups[kind] = pending
    root.pendingBySection = groups
  }

  function updateRestartApplications(data) {
    if (!Array.isArray(data.restartApplications)) return
    root.restartApplications = data.restartApplications
    if (root.hostWidget) root.hostWidget.restartApplications = data.restartApplications
  }

  function collectAttention() {
    var items = [], seen = ({})
    var pending = (root.pendingBySection.fonts || []).concat(root.pendingBySection.theme || [], root.pendingBySection.opacity || [])
    if (root.hostWidget) pending = pending.concat(root.hostWidget.reconciliationPending || [])
    pending = pending.concat((root.hostWidget ? root.hostWidget.restartApplications : root.restartApplications) || [])
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

  function auditResultMessage(result) {
    if (result.status === "not-found")
      return "Font support not detected. No matching installed application was found."
    var findings = Array.isArray(result.findings) ? result.findings : []
    return findings.length === 1 && findings[0].fontStatus === "registered"
      ? "Font support detected" : "Font support not detected"
  }

  function runAppearanceAction(kind, args, fromGlobalApply) {
    if (!root.inventoryLoaded || root.appearanceActionRunning || root.fontActionRunning || root.manualAppActionRunning || root.manualAuditClearRunning
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

  function applySelectedOpacity(fromGlobalApply) {
    return root.runAppearanceAction("opacity", ["apply-opacity", String(root.selectedOpacity)], fromGlobalApply)
  }

  function applySelectedBlur(fromGlobalApply) {
    return root.runAppearanceAction("blur", ["apply-blur", root.selectedBlur], fromGlobalApply)
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
    if (!root.unlockApplyAvailable) return false
    return root.runAppearanceAction("unlock", args, fromGlobalApply)
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
    if (inventoryProcess.running) return
    inventoryProcess.command = ["/usr/bin/python3", "-B", localPath(Qt.resolvedUrl("controller.py")), "panel-inventory"]
    inventoryProcess.running = true
  }

  function applyGlobalFonts(fromGlobalApply) {
    if (!root.inventoryLoaded || root.fontActionRunning || root.appearanceActionRunning || root.manualAppActionRunning || root.manualAuditClearRunning
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
    if (step === "opacity") return "Terminal opacity"
    if (step === "blur") return "Terminal blur"
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
    if (!root.inventoryLoaded || root.globalApplyRunning || root.appearanceActionRunning || root.fontActionRunning
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
    if (root.selectedOpacity >= 0) root.globalApplySteps.splice(1, 0, "opacity")
    if (root.selectedBlur && root.selectedBlur !== "keep")
      root.globalApplySteps.splice(root.globalApplySteps.indexOf("fonts"), 0, "blur")
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
      root.globalApplyStatus = (root.fontActionNeedsAttention || root.themeActionNeedsAttention || root.opacityActionNeedsAttention)
        ? "Settings saved. Some applications need attention; see Applications."
        : (includedUnlock ? "Settings saved, including verified boot artwork." : "Settings saved.")
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
    else if (step === "opacity") started = root.applySelectedOpacity(true)
    else if (step === "blur") started = root.applySelectedBlur(true)
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

  function undoGlobalFonts() {
    if (!root.inventoryLoaded || root.fontActionRunning || root.appearanceActionRunning || root.manualAppActionRunning || root.manualAuditClearRunning || root.globalApplyRunning) return
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

  function adoptPreviewCache(raw) {
    if (root.inventoryLoaded || root.previewCacheLoaded || String(raw).length > 8 * 1024 * 1024) return
    try {
      var cached = JSON.parse(String(raw || "{}"))
      if (cached.schemaVersion !== 1 || !cached.inventory) return
      root.adoptInventory(JSON.stringify(cached.inventory), true)
    } catch (e) {} // Missing/obsolete cache falls back to live discovery.
  }

  function adoptInventory(raw, previewOnly) {
    if (previewOnly && root.inventoryLoaded) return
    try {
      var data = JSON.parse(String(raw || "{}"))
      if (!data || !data.catalog_entries || !Array.isArray(data.catalog_entries.fonts) || !Array.isArray(data.catalog_entries.themes)) throw new Error("Invalid inventory")
      var entries = data.catalog_entries
      if (!["unlocks", "backgrounds", "icons"].every(function(kind) { return !entries[kind] || Array.isArray(entries[kind]) })) throw new Error("Invalid catalog")
      var statuses = data.appearance_action_status || ({})
      if (!previewOnly) {
        root.inventoryError = ""
      }
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
      if (!previewOnly) {
        appearanceActionStatuses = statuses
        root.observedTheme = String((statuses.theme || {}).observedValue || "")
        fontUndoAvailable = data.global_font_undo_available === true
        if (!lastAppliedThemeSetThisSession && statuses.theme && statuses.theme.expectedValue)
          lastAppliedTheme = String(statuses.theme.expectedValue)
      }

      function idFor(records, name) {
        var entry = records.find(function(item) { return item.name === name })
        return entry ? entry.id : ""
      }

      if (!inventoryLoaded) {
        selectedSystemFontId = (data.preferences && data.preferences.systemFontId) || (fonts.length ? fonts[0].id : "")
        selectedTerminalFontId = (data.preferences && data.preferences.terminalFontId)
          || (fonts.length ? fonts[0].id : "")
        selectedSystemSize = 12
        selectedTerminalSize = 12
        if (data.preferences && Number.isInteger(data.preferences.systemFontSizePt)
            && data.preferences.systemFontSizePt >= 6 && data.preferences.systemFontSizePt <= 48)
          selectedSystemSize = data.preferences.systemFontSizePt
        if (data.preferences && Number.isInteger(data.preferences.terminalFontSizePt)
            && data.preferences.terminalFontSizePt >= 6 && data.preferences.terminalFontSizePt <= 48)
          selectedTerminalSize = data.preferences.terminalFontSizePt
        selectedThemeMode = "automatic"
        selectedOpacity = data.desiredAppearance && Number.isInteger(data.desiredAppearance.opacity)
          ? data.desiredAppearance.opacity : -1
        var savedBlur = data.desiredAppearance && data.desiredAppearance.blur
        selectedBlur = typeof savedBlur === "boolean" ? (savedBlur ? "on" : "off") : "keep"
        var savedTheme = data.desiredAppearance && data.desiredAppearance.theme
        if (savedTheme) {
          selectedThemeMode = savedTheme.mode
          selectedLightThemeId = idFor(themes, savedTheme.light)
          selectedDarkThemeId = idFor(themes, savedTheme.dark)
        } else {
          var activeTheme = (statuses.theme || {}).observedValue
          selectedLightThemeId = idFor(themes, activeTheme) || (themes.length ? themes[0].id : "")
          selectedDarkThemeId = selectedLightThemeId
        }
        var activeUnlock = (statuses.unlock || {}).observedValue
        var initialUnlock = unlockDesigns.find(function(entry) { return entry.name === activeUnlock }) || unlockDesigns[0]
        selectedUnlockId = initialUnlock ? initialUnlock.id : ""
        selectedUnlockPreview = initialUnlock ? initialUnlock.preview || "" : ""
        var activeBackground = (statuses.background || {}).observedValue
        var preferredBackground = backgrounds.find(function(entry) { return entry.source === activeBackground })
        selectedBackgroundId = preferredBackground ? preferredBackground.id : (backgrounds.length ? backgrounds[0].id : "")
        if (!previewOnly) inventoryLoaded = true
      }
      if (!previewOnly && root.refreshFontSelection) {
        selectedSystemFontId = (data.preferences || {}).systemFontId || selectedSystemFontId
        selectedTerminalFontId = (data.preferences || {}).terminalFontId || selectedTerminalFontId
        selectedSystemSize = (data.preferences || {}).systemFontSizePt || selectedSystemSize
        selectedTerminalSize = (data.preferences || {}).terminalFontSizePt || selectedTerminalSize
        root.refreshFontSelection = false
      }
      root.adoptIconSelection(data.desiredAppearance && data.desiredAppearance.icons,
        (statuses.icons || {}).observedValue, resetIconSelection)
      if (previewOnly) root.previewCacheLoaded = true
    } catch (e) {
      if (!previewOnly) root.inventoryError = "Could not refresh the catalog. Your selections are kept; try opening the panel again."
    }
  }

  component Caption: Text {
    color: root.popupForeground
    font.family: root.fontFamily
    font.pixelSize: root.controlFontPixelSize
    wrapMode: Text.Wrap
    textFormat: Text.PlainText
  }
  component FieldLabel: Caption { color: root.labelColor; font.weight: Font.Medium; font.pixelSize: root.controlFontPixelSize + 2 }
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
    visible: !!result.state && result.state !== "saved"
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
  component ThemeSampleText: Text {
    required property var sample
    color: sample.foreground
    font.family: sample.systemFamily
    font.pixelSize: sample.sampleSize
    textFormat: Text.PlainText
    elide: Text.ElideRight
  }
  component ThemeExample: Rectangle {
    id: example
    property bool terminal: false
    property var preview: ({})
    readonly property color foreground: preview.foreground || root.popupForeground
    readonly property color background: preview.background || root.surfaceColor
    readonly property color accent: preview.accent || foreground
    readonly property color chrome: Qt.tint(background, Qt.rgba(foreground.r, foreground.g, foreground.b, 0.07))
    readonly property color rule: Qt.tint(background, Qt.rgba(foreground.r, foreground.g, foreground.b, 0.18))
    readonly property int sampleSize: Math.max(11, Math.round(root.controlFontPixelSize * 0.8))
    readonly property string systemFamily: root.entryFor(root.fonts, root.selectedSystemFontId).name || root.fontFamily
    readonly property string terminalFamily: root.entryFor(root.fonts, root.selectedTerminalFontId).name || "monospace"
    Layout.fillWidth: true
    implicitHeight: exampleContent.implicitHeight + 2
    color: background; border.color: rule; radius: 3; clip: true
    Accessible.role: Accessible.Graphic
    Accessible.name: terminal ? "Terminal theme example" : "Application theme example"

    ColumnLayout {
      id: exampleContent
      anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
      anchors.margins: 1; spacing: 0
      Rectangle {
        Layout.fillWidth: true; implicitHeight: example.sampleSize + 16
        color: example.chrome
        RowLayout {
          anchors.fill: parent; anchors.leftMargin: 10; anchors.rightMargin: 10; spacing: 8
          ThemeSampleText { sample: example; Layout.fillWidth: true; text: example.terminal ? "Terminal" : "Application"; font.weight: Font.Medium }
          ThemeSampleText { sample: example; text: "−  □  ×" }
        }
      }
      ColumnLayout {
        Layout.fillWidth: true; spacing: 0; visible: !example.terminal && !!example.preview.background
        ThemeSampleText { sample: example; Layout.fillWidth: true; Layout.margins: 8; text: "File    Edit    View    Go    Help" }
        Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: example.rule }
        RowLayout {
          Layout.fillWidth: true; Layout.leftMargin: 8; Layout.rightMargin: 8; Layout.topMargin: 6; Layout.bottomMargin: 6; spacing: 10
          Rectangle {
            implicitWidth: tabLabel.implicitWidth + 18; implicitHeight: tabLabel.implicitHeight + 10
            color: example.chrome; radius: 2
            ThemeSampleText { id: tabLabel; sample: example; anchors.centerIn: parent; text: "Projects  ×" }
            Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; height: 2; color: example.accent }
          }
          ThemeSampleText { sample: example; Layout.fillWidth: true; text: "‹  ›    ~/Projects" }
        }
        Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: example.rule }
        RowLayout {
          Layout.fillWidth: true; spacing: 0
          ColumnLayout {
            Layout.preferredWidth: example.width * 0.35; Layout.margins: 8; spacing: 5
            ThemeSampleText { sample: example; Layout.fillWidth: true; text: "Places"; font.weight: Font.DemiBold }
            ThemeSampleText { sample: example; Layout.fillWidth: true; text: "Home Folder" }
            ThemeSampleText { sample: example; Layout.fillWidth: true; text: "Documents" }
          }
          Rectangle { Layout.fillHeight: true; implicitWidth: 1; color: example.rule }
          ColumnLayout {
            Layout.fillWidth: true; Layout.margins: 8; spacing: 5
            ThemeSampleText { sample: example; Layout.fillWidth: true; text: "Name"; font.weight: Font.DemiBold }
            ThemeSampleText { sample: example; Layout.fillWidth: true; text: "src/" }
            ThemeSampleText { sample: example; Layout.fillWidth: true; text: "preview.py" }
          }
        }
      }
      Text {
        Layout.fillWidth: true; Layout.margins: 10
        visible: example.terminal && !!example.preview.background
        font.family: example.terminalFamily; font.pixelSize: example.sampleSize
        color: example.foreground; textFormat: Text.RichText
        wrapMode: Text.NoWrap; clip: true
        text: "<font color='" + example.accent + "'>~/Projects</font> $ python"
          + "<br>&gt;&gt;&gt; theme = <font color='" + ((example.preview.swatches || [])[2] || example.foreground) + "'>&quot;My desktop&quot;</font>"
          + "<br>&gt;&gt;&gt; <font color='" + ((example.preview.swatches || [])[4] || example.foreground) + "'>preview</font>(theme)"
          + "<br>My desktop"
          + "<br>&gt;&gt;&gt; ▌"
      }
      ThemeSampleText {
        sample: example
        Layout.fillWidth: true; Layout.margins: 10
        visible: !example.preview.background; text: "Preview unavailable"
      }
    }
  }
  component ThemeChoice: ColumnLayout {
    id: choice
    property string heading: ""
    property bool light: false
    property string selectedId: light ? root.selectedLightThemeId : root.selectedDarkThemeId
    readonly property var entry: root.entryFor(root.themes, selectedId)
    readonly property var preview: entry.preview || ({})
    Layout.fillWidth: true
    Layout.alignment: Qt.AlignTop
    spacing: 8
    RowLayout {
      Layout.fillWidth: true
      FieldLabel { text: choice.heading; Layout.fillWidth: true }
      Caption { objectName: choice.light ? "lightThemeActiveBadge" : "darkThemeActiveBadge"; text: "Active now"; visible: !!choice.entry.name && choice.entry.name === root.observedTheme; color: root.mutedColor; font.pixelSize: Math.max(11, root.controlFontPixelSize - 2) }
    }
    Picker {
      accessibleLabel: choice.heading; model: root.themes; textRole: "displayName"
      currentIndex: root.themes.findIndex(function(entry) { return entry.id === choice.selectedId })
      displayText: currentIndex >= 0 ? currentText : "Select theme"
      onActivated: function(index) { if (choice.light) root.selectedLightThemeId = root.themes[index].id; else root.selectedDarkThemeId = root.themes[index].id }
    }
    ColumnLayout {
      objectName: choice.light ? "lightThemePreview" : "darkThemePreview"
      Layout.fillWidth: true; spacing: 8
      ThemeExample {
        objectName: choice.light ? "lightApplicationThemePreview" : "darkApplicationThemePreview"
        preview: choice.preview
      }
      ThemeExample {
        objectName: choice.light ? "lightTerminalThemePreview" : "darkTerminalThemePreview"
        terminal: true; preview: choice.preview
      }
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
        Caption { Layout.fillWidth: true; text: choice.selectedFamily ? choice.selectedFamily + " · " + choice.selectedSize + " pt" : "Choose a font"; color: root.mutedColor; font.pixelSize: Math.max(11, root.controlFontPixelSize - 2); elide: Text.ElideRight; maximumLineCount: 1 }
      }
    }
    RowLayout {
      Layout.fillWidth: true; visible: choice.terminal
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
      Item { Layout.fillWidth: true }
      ActionButton { objectName: "undoFontsButton"; text: "Undo fonts"; quiet: true; visible: root.fontUndoAvailable; onClicked: root.undoGlobalFonts() }
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
              Caption { text: "v0.2.0"; color: root.mutedColor; font.pixelSize: root.controlFontPixelSize - 2; Layout.alignment: Qt.AlignBottom; Layout.bottomMargin: 3 }
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
              enabled: root.inventoryLoaded && !root.busy; spacing: 16
              RowLayout {
                Layout.fillWidth: true; spacing: 6
                ActionButton { objectName: "undoThemeButton"; text: contentViewport.width < 620 ? "Undo" : "Undo theme"; Accessible.name: "Undo theme"; quiet: true; visible: !!(root.appearanceActionStatuses.theme || {}).undoAvailable; onClicked: root.undoAppearanceAction("theme") }
                Item { Layout.fillWidth: true }
                FieldLabel { text: "Mode"; Layout.rightMargin: 8 }
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
              ColumnLayout {
                Layout.fillWidth: true; spacing: 8
                GridLayout {
                  id: terminalControlsGrid
                  Layout.fillWidth: true; Layout.maximumWidth: 492; Layout.alignment: Qt.AlignLeft
                  columns: width < 480 ? 1 : 2; columnSpacing: 12; rowSpacing: 12
                  ColumnLayout {
                    Layout.fillWidth: true; spacing: 8
                    RowLayout {
                      Layout.fillWidth: true
                      FieldLabel { text: "Terminal opacity"; Layout.fillWidth: true }
                      ActionButton { objectName: "undoOpacityButton"; text: "Undo"; Accessible.name: "Undo opacity"; quiet: true; visible: !!(root.appearanceActionStatuses.opacity || {}).undoAvailable; onClicked: root.undoAppearanceAction("opacity") }
                    }
                    Picker {
                      id: terminalOpacityPicker
                      objectName: "terminalOpacityPicker"
                      Layout.fillWidth: true; Layout.minimumWidth: 0; Layout.maximumWidth: 240
                      accessibleLabel: "Terminal opacity"
                      model: root.opacityChoices
                      currentIndex: root.opacityChoices.findIndex(function(entry) { return entry.id === root.selectedOpacity })
                      onActivated: function(index) { root.selectedOpacity = root.opacityChoices[index].id }
                    }
                  }
                  ColumnLayout {
                    id: terminalBlurColumn
                    Layout.fillWidth: true; spacing: 8
                    RowLayout {
                      Layout.fillWidth: true
                      FieldLabel { text: "Terminal blur"; Layout.fillWidth: true }
                      ActionButton { objectName: "undoBlurButton"; text: "Undo"; Accessible.name: "Undo blur"; quiet: true; visible: !!(root.appearanceActionStatuses.blur || {}).undoAvailable; onClicked: root.undoAppearanceAction("blur") }
                    }
                    Picker {
                      id: terminalBlurPicker
                      objectName: "terminalBlurPicker"
                      Layout.fillWidth: true; Layout.minimumWidth: 0; Layout.maximumWidth: 240
                      accessibleLabel: "Terminal blur"
                      model: root.blurChoices
                      currentIndex: root.blurChoices.findIndex(function(entry) { return entry.id === root.selectedBlur })
                      onActivated: function(index) { root.selectedBlur = root.blurChoices[index].id }
                    }
                  }
                }
                Caption {
                  Layout.fillWidth: true
                  Layout.maximumWidth: terminalBlurColumn.x + terminalBlurPicker.width
                  Layout.alignment: Qt.AlignLeft
                  color: root.mutedColor; font.pixelSize: root.controlFontPixelSize - 2
                  text: "70% opacity means 30% transparency. Blur softens the background behind terminals. Coloured prompt backgrounds stay opaque."
                }
                ResultNotice { Layout.fillWidth: true; kind: "opacity" }
                ResultNotice { Layout.fillWidth: true; kind: "blur" }
              }
              ResultNotice { Layout.fillWidth: true; kind: "theme" }
              Divider {}
              GridLayout {
                Layout.fillWidth: true; columns: width < 620 ? 1 : 2
                columnSpacing: 20; rowSpacing: 18; uniformCellWidths: true
                ColumnLayout {
                  Layout.fillWidth: true; spacing: 8
                  RowLayout { Layout.fillWidth: true; FieldLabel { text: "Background"; Layout.fillWidth: true } ActionButton { text: "Undo"; quiet: true; visible: !!(root.appearanceActionStatuses.background || {}).undoAvailable; Accessible.name: "Undo background"; onClicked: root.undoAppearanceAction("background") } }
                  Picker { accessibleLabel: "Background"; model: root.backgrounds; textRole: "label"; currentIndex: root.backgrounds.findIndex(function(entry) { return entry.id === root.selectedBackgroundId }); displayText: currentIndex >= 0 ? currentText : "Select background"; onActivated: function(index) { root.selectedBackgroundId = root.backgrounds[index].id } }
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
                  ResultNotice { Layout.fillWidth: true; kind: "background" }
                }
                ColumnLayout {
                  Layout.fillWidth: true; Layout.alignment: Qt.AlignTop; spacing: 8
                  RowLayout { Layout.fillWidth: true; FieldLabel { text: "Icons"; Layout.fillWidth: true } ActionButton { text: "Undo"; quiet: true; visible: !!(root.appearanceActionStatuses.icons || {}).undoAvailable; Accessible.name: "Undo icons"; onClicked: root.undoAppearanceAction("icons") } }
                  Picker { accessibleLabel: "Icon theme"; model: root.icons; textRole: "displayName"; currentIndex: root.icons.findIndex(function(entry) { return entry.id === root.selectedIconId }); displayText: currentIndex >= 0 ? currentText : "Keep current icons"; onActivated: function(index) { root.selectedIconId = root.icons[index].id } }
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
                  ResultNotice { Layout.fillWidth: true; kind: "icons" }
                }
              }
              Divider {}
              RowLayout {
                Layout.fillWidth: true
                FieldLabel { text: "Boot unlock artwork"; Layout.fillWidth: true }
                ActionButton { objectName: "undoBootArtworkButton"; text: "Undo"; Accessible.name: "Undo boot artwork"; quiet: true; visible: !!(root.appearanceActionStatuses.unlock || {}).undoAvailable; onClicked: root.undoAppearanceAction("unlock") }
              }
              ColumnLayout {
                objectName: "unlockExamples"
                Layout.fillWidth: true; spacing: 8
                Picker {
                  objectName: "unlockDesignPicker"
                  accessibleLabel: "Boot unlock artwork"; model: root.unlockDesigns; textRole: "displayName"
                  currentIndex: root.unlockDesigns.findIndex(function(entry) { return entry.id === root.selectedUnlockId })
                  displayText: currentIndex >= 0 ? currentText : "No design selected"
                  enabled: root.unlockDesigns.length > 0
                  onActivated: function(index) { root.selectedUnlockId = root.unlockDesigns[index].id; root.selectedUnlockPreview = root.unlockDesigns[index].preview || ""; root.unlockSelectionChanged = true }
                }
                Rectangle {
                  objectName: "unlockPreviewCard"
                  Layout.fillWidth: true; implicitHeight: Math.max(140, Math.min(220, width * 9 / 16))
                  color: root.entryFor(root.unlockDesigns, root.selectedUnlockId).backgroundColor || root.surfaceColor; border.color: root.lineColor; radius: 3; clip: true
                  Image {
                    id: unlockImage
                    objectName: "unlockDesignPreview"
                    anchors.centerIn: parent; width: parent.width * 0.72; height: parent.height * 0.65
                    source: root.fileUrl(root.selectedUnlockPreview)
                    sourceSize.width: 960; sourceSize.height: 540
                    fillMode: Image.PreserveAspectFit; asynchronous: true; cache: true
                    Accessible.role: Accessible.Graphic
                    Accessible.name: "Boot unlock artwork example"
                  }
                  Caption {
                    anchors.centerIn: parent; width: parent.width - 24
                    horizontalAlignment: Text.AlignHCenter; color: root.mutedColor
                    visible: unlockImage.status !== Image.Ready
                    text: !root.unlockDesigns.length ? "No unlock artwork available" : unlockImage.status === Image.Loading ? "Loading artwork…" : "Preview unavailable"
                  }
                }
                RowLayout {
                  Layout.fillWidth: true
                  visible: !!(root.appearanceActionStatuses.unlock || {}).recoveryAvailable
                  ActionButton { text: "Recover boot artwork"; quiet: true; visible: !!(root.appearanceActionStatuses.unlock || {}).recoveryAvailable; onClicked: root.runAppearanceAction("unlock", ["recover-unlock"]) }
                }
                ResultNotice { Layout.fillWidth: true; kind: "unlock" }
                Caption { Layout.fillWidth: true; text: "Applying or undoing boot artwork requires administrator approval."; color: root.mutedColor; font.pixelSize: root.controlFontPixelSize - 1 }
              }
            }
            ColumnLayout {
              objectName: "fontsPage"
              width: parent.width; visible: root.activeTab === 1; enabled: root.inventoryLoaded && !root.busy; spacing: 18
              Caption { Layout.fillWidth: true; text: "Two fonts. One consistent desktop."; color: root.mutedColor }
              GridLayout { Layout.fillWidth: true; columns: width < 620 ? 1 : 2; uniformCellWidths: true; columnSpacing: 24; rowSpacing: 24; FontChoice { terminal: false } FontChoice { terminal: true } }
              Divider {}
              Caption { Layout.fillWidth: true; text: "Font changes may require reopening applications."; color: root.mutedColor; font.pixelSize: root.controlFontPixelSize - 1 }
              ResultNotice { Layout.fillWidth: true; kind: "fonts" }
            }
            ColumnLayout {
              objectName: "applicationsPage"
              width: parent.width; visible: root.activeTab === 2; spacing: 16
              FieldLabel { Layout.fillWidth: true; text: "Audit Applications not Automatically Configured by the Plugin" }
              RowLayout {
                Layout.fillWidth: true
                SearchField { id: manualAppField; Layout.fillWidth: true; enabled: !root.busy; placeholderText: "App name, launcher, or package"; text: root.manualAppQuery; onTextEdited: root.manualAppQuery = text; onAccepted: root.inspectManualApp(); Accessible.name: "Application to audit" }
                ActionButton { text: root.manualAppActionRunning ? "Auditing…" : "Audit app"; enabled: !root.busy && root.manualAppQuery.trim().length >= 2; onClicked: root.inspectManualApp() }
              }
              Caption { Layout.fillWidth: true; visible: !!root.manualAppStatus; text: root.manualAppStatus; color: root.mutedColor; font.pixelSize: root.controlFontPixelSize - 1 }
              ActionButton { text: "Clear Audits"; quiet: true; enabled: !root.busy; onClicked: root.clearManualAudit() }
              Divider {}
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
              Caption { Layout.fillWidth: true; visible: !!root.globalApplyStatus; text: root.globalApplyStatus; color: root.applyFailed ? root.warningColor : root.mutedColor; font.pixelSize: root.controlFontPixelSize - 1 }
            }
          }
        }
        Divider {}
        Caption {
          Layout.fillWidth: true
          text: "Save your work in all open applications before applying changes. Some applications may need to be closed or restarted."
          color: root.mutedColor
          font.pixelSize: root.controlFontPixelSize - 2
        }
        RowLayout {
          id: footer
          objectName: "panelFooter"
          Layout.fillWidth: true; spacing: 12
          ColumnLayout {
            Layout.fillWidth: true; spacing: 4
            Caption {
              Layout.fillWidth: true
              text: !root.inventoryLoaded && !root.inventoryError ? "Loading settings…" : root.globalApplyRunning ? root.globalApplyStatus : root.applyFailed ? (root.globalApplyCurrentStep ? "Apply stopped at " + root.globalApplyStepName(root.globalApplyCurrentStep) : "Choose the missing settings") : root.attentionItems.length ? root.attentionItems.length + " action" + (root.attentionItems.length === 1 ? " needs" : "s need") + " attention" : root.globalApplyStatus ? "Last Apply: settings saved" : "Ready when you are"
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
              text: "Save your work in all open applications before applying changes. Some applications may need to be closed or restarted. Use Appearance, Fonts and Applications to review your choices. Switching tabs keeps your draft selections. The Apply changes button stays below the scrolling content and applies selections from every tab: theme, selected terminal opacity, fonts, background, then optional icons. A changed boot artwork selection is applied last and requests administrator approval. If a step fails, later steps stop; completed steps remain applied and can be undone with their section's Undo control. Section results describe the last action; Details expands the full message. Applications lists any remaining actions."
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
              text: "Choose Automatic, Light or Dark mode on the Appearance tab. Automatic follows local sunrise and sunset. Terminal opacity applies separately to installed Ghostty, Alacritty, Kitty, Foot and WezTerm. Choose a percentage, then Apply changes. 100% is opaque; 70% is 30% transparent. Coloured prompt backgrounds remain opaque. Foot and Kitty may need to be fully quit and reopened. Undo opacity restores previous opacity settings independently of fonts and themes. In every mode, the loaded plugin checks saved themes, fonts, icons and opacity on startup and every 15 seconds, even with the panel closed. Hand edits to managed settings can be replaced. Undo the relevant choices, or disable the plugin to stop repair. Undo theme restores the previous detected theme."
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
              text: "Boot unlock artwork is shown directly on the Appearance tab. Select a design to update the example. Changing the boot artwork requires administrator approval. Each current boot image is built and inspected before publication. Undo restores the saved boot files; it refuses if a system update or other change has replaced them. Boot colours are preserved. Signed/Secure Boot and custom boot layouts are currently unsupported."
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
              text: "Enter an application name, launcher, or package and select Audit app. The audit searches installed launchers and packages, then saves its result. Font support detected means the app matches an existing shared GTK, Qt, or supported terminal font control. It does not apply fonts, add a new adapter, verify the rendered font, or register app-specific theme controls. Font support not detected means the app was not found, the result was ambiguous, or its font control is unsupported. Ambiguous or unsupported matches are saved and block Fonts Apply and automatic font repair; earlier steps in Apply changes may already have completed. A more specific audit does not remove an earlier ambiguous result. Clear Audits removes all saved manual audit records, including supported ones, without undoing settings or removing automatic support. A search with no match saves no new record."
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

  Component.onCompleted: root.refreshInventory()

  FileView {
    id: cachedPreviews
    path: root.previewCachePath
    printErrors: false
    onLoaded: root.adoptPreviewCache(text())
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
          } else if (kind === "opacity") {
            root.selectedOpacity = Number.isInteger(result.savedPercent) ? result.savedPercent : -1
          } else if (kind === "blur") {
            root.selectedBlur = typeof result.savedBlur === "boolean" ? (result.savedBlur ? "on" : "off") : "keep"
          } else {
            var restoredUnlock = root.unlockDesigns.find(function(entry) { return String(entry.name).toLowerCase().replace(/_/g, "-") === String(result.restored || "").toLowerCase().replace(/_/g, "-") })
            if (restoredUnlock) { root.selectedUnlockId = restoredUnlock.id; root.selectedUnlockPreview = restoredUnlock.preview || "" }
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
        } else if (kind === "opacity") {
          message = "Terminal opacity saved at " + result.opacityPercent + "%."
        } else if (kind === "blur") {
          message = "Terminal blur is " + (result.blurEnabled ? "On" : "Off") + "."
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
        root.updateRestartApplications(result)
        if (kind === "theme") root.updatePending("theme", result)
        if (kind === "opacity") {
          root.updatePending("opacity", result)
          root.opacityActionNeedsAttention = (result.pendingApplications || []).length > 0
          if ((result.pendingApplications || []).length) message += " " + result.pendingApplications.map(function(item) { return item.app + ": " + item.reason }).join(" ")
        }
        root.setSectionResult(kind, (kind === "theme" && root.themeActionNeedsAttention) || (kind === "opacity" && root.opacityActionNeedsAttention) ? "pending" : "saved", message)
        if (kind === "unlock") root.unlockSelectionChanged = false
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
    if (!root.globalApplyStepSucceeded && root.appearanceActionKind === "unlock") root.refreshInventory()
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
        root.manualAppStatus = root.auditResultMessage(result)
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
        root.manualAppStatus = result.cleared ? "Saved audits cleared." : "Saved audits could not be cleared."
      } catch (e) {
        root.manualAppStatus = "Saved audits could not be cleared."
      }
    } }
    stderr: StdioCollector { waitForEnd: true; onStreamFinished: {
      if (String(text || "").trim()) root.manualAppStatus = "Saved audits could not be cleared safely."
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
