pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

Panel {
  id: root
  moduleName: "si.omarchy-look-and-feel"
  ipcTarget: ""
  manageIpc: false

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
  property var appearanceActionMessages: ({ theme: "", background: "", unlock: "" })

  function runAppearanceAction(kind, args, fromGlobalApply) {
    if (root.appearanceActionRunning || root.fontActionRunning || root.manualAppActionRunning || root.manualAuditClearRunning
        || (root.globalApplyRunning && !fromGlobalApply)) return false
    root.appearanceActionKind = kind
    var messages = Object.assign({}, root.appearanceActionMessages)
    messages[kind] = "Applying selected " + kind + "…"
    root.appearanceActionMessages = messages
    root.appearanceActionRunning = true
    appearanceActionProcess.command = ["/usr/bin/python3", localPath(Qt.resolvedUrl("controller.py"))].concat(args)
    appearanceActionProcess.running = true
    return true
  }

  function applySelectedTheme(fromGlobalApply) {
    if (!root.selectedLightThemeId || !root.selectedDarkThemeId) return false
    return root.runAppearanceAction("theme", ["apply-theme", root.selectedThemeMode,
      root.catalogName(root.themes, root.selectedLightThemeId),
      root.catalogName(root.themes, root.selectedDarkThemeId)], fromGlobalApply)
  }

  function applySelectedBackground(fromGlobalApply) {
    if (!root.selectedBackgroundId) return false
    return root.runAppearanceAction("background", ["apply-catalog-action", "background", root.selectedBackgroundId], fromGlobalApply)
  }

  function launchUnlockCommand(args, expectedSlug, operation, fromGlobalApply) {
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
    unlockApplyProcess.command = ["/usr/bin/omarchy-launch-floating-terminal-with-presentation", "/usr/bin/python3",
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
    inventoryProcess.command = ["/usr/bin/python3", localPath(Qt.resolvedUrl("controller.py")), "inventory"]
    inventoryProcess.running = true
  }

  function applyGlobalFonts(fromGlobalApply) {
    if (root.fontActionRunning || root.appearanceActionRunning || root.manualAppActionRunning || root.manualAuditClearRunning
        || (root.globalApplyRunning && !fromGlobalApply) || !root.selectedSystemFontId || !root.selectedTerminalFontId) return false
    root.fontActionStatus = "Applying the selected global font settings…"
    root.fontActionRunning = true
    globalFontProcess.command = ["/usr/bin/python3", localPath(Qt.resolvedUrl("controller.py")),
      "apply-global-fonts", root.selectedSystemFontId, String(root.selectedSystemSize),
      root.selectedTerminalFontId, String(root.selectedTerminalSize)]
    globalFontProcess.running = true
    return true
  }

  function globalApplyStepName(step) {
    if (step === "fonts") return "Fonts"
    if (step === "theme") return "Theme"
    if (step === "background") return "Background"
    if (step === "unlock") return "Boot unlock"
    return "Settings"
  }

  function applyAllSelectedSettings() {
    if (root.globalApplyRunning || root.appearanceActionRunning || root.fontActionRunning
        || root.manualAppActionRunning || root.manualAuditClearRunning) return
    if (!root.selectedSystemFontId || !root.selectedTerminalFontId
        || !root.selectedLightThemeId || !root.selectedDarkThemeId || !root.selectedBackgroundId) {
      root.globalApplyStatus = "Select both fonts, both themes, and a background before applying."
      return
    }
    root.globalApplySteps = ["theme", "fonts", "background"]
    if (root.unlockSelectionChanged && root.selectedUnlockId) root.globalApplySteps.push("unlock")
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
        : "Theme, fonts, and background were applied. Boot unlock was left unchanged."
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
    else if (step === "unlock") started = root.applySelectedUnlock(true)
    if (!started) root.finishGlobalApplyStep(false, "The selected settings could not be applied.")
  }

  function finishGlobalApplyStep(succeeded, detail) {
    if (!root.globalApplyRunning) return
    var step = root.globalApplyCurrentStep
    if (!succeeded) {
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
    root.fontActionStatus = "Restoring the previous global font settings…"
    root.fontActionRunning = true
    globalFontProcess.command = ["/usr/bin/python3", localPath(Qt.resolvedUrl("controller.py")), "rollback-global-fonts"]
    globalFontProcess.running = true
  }

  function inspectManualApp() {
    if (root.manualAppActionRunning || root.fontActionRunning || root.appearanceActionRunning || root.globalApplyRunning || root.manualAppQuery.trim().length < 2) return
    manualAppStatus = "Auditing the entered app and checking verified shared font controls…"
    manualAppActionRunning = true
    manualAppProcess.command = ["/usr/bin/python3", localPath(Qt.resolvedUrl("controller.py")), "audit-app", root.manualAppQuery.trim()]
    manualAppProcess.running = true
  }

  function clearManualAudit() {
    if (root.manualAuditClearRunning || root.manualAppActionRunning || root.fontActionRunning || root.appearanceActionRunning || root.globalApplyRunning) return
    root.manualAuditClearRunning = true
    manualAuditClearProcess.command = ["/usr/bin/python3", localPath(Qt.resolvedUrl("controller.py")), "clear-manual-app-audit"]
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
    appearanceAuditProcess.command = ["/usr/bin/python3", localPath(Qt.resolvedUrl("controller.py")), "audit-appearance", JSON.stringify(expected)]
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
      var entries = data.catalog_entries || ({})
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
      icons = entries.icons || []
      appearanceActionStatuses = data.appearance_action_status || ({})
      fontUndoAvailable = data.global_font_undo_available === true
      if (!lastAppliedThemeSetThisSession && appearanceActionStatuses.theme && appearanceActionStatuses.theme.expectedValue)
        lastAppliedTheme = String(appearanceActionStatuses.theme.expectedValue)

      function idFor(records, name) {
        var entry = records.find(function(item) { return item.name === name })
        return entry ? entry.id : ""
      }

      if (!inventoryLoaded) {
        selectedSystemFontId = (data.preferences && data.preferences.systemFontId) || idFor(fonts, "Aileron")
        selectedTerminalFontId = (data.preferences && data.preferences.terminalFontId)
          || idFor(fonts, "Office Code Pro")
        if (data.preferences && Number.isInteger(data.preferences.systemFontSizePt)
            && data.preferences.systemFontSizePt >= 6 && data.preferences.systemFontSizePt <= 48)
          selectedSystemSize = data.preferences.systemFontSizePt
        if (data.preferences && Number.isInteger(data.preferences.terminalFontSizePt)
            && data.preferences.terminalFontSizePt >= 6 && data.preferences.terminalFontSizePt <= 48)
          selectedTerminalSize = data.preferences.terminalFontSizePt
        selectedThemeMode = "automatic"
        selectedLightThemeId = idFor(themes, "dracula-pro-alucard")
        selectedDarkThemeId = idFor(themes, "dracula-pro-van-helsing")
        var preferredUnlock = unlockDesigns.find(function(entry) { return entry.name === "dracula-pro-van-helsing" })
        selectedUnlockId = preferredUnlock ? preferredUnlock.id : ""
        selectedUnlockPreview = preferredUnlock ? preferredUnlock.preview : ""
        var preferredBackground = backgrounds.find(function(entry) {
          return String(entry.source).endsWith("/Documents/Fonts_Icons_Wallpaper/Backgrounds/1333929.jpeg")
        })
        selectedBackgroundId = preferredBackground ? preferredBackground.id : idFor(backgrounds, "1333929.jpeg")
        selectedIconId = idFor(icons, "Tela-circle-dracula-dark-van-helsing")
        inventoryLoaded = true
      }
    } catch (e) {
      fonts = []
      themes = []
      unlockDesigns = []
      backgrounds = []
      icons = []
      selectedSystemFontId = ""
      selectedTerminalFontId = ""
      selectedLightThemeId = ""
      selectedDarkThemeId = ""
      selectedUnlockId = ""
      selectedUnlockPreview = ""
      selectedBackgroundId = ""
      selectedIconId = ""
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
    contentWidth: panel.fittedContentWidth(760)
    contentHeight: panel.fittedContentHeight(content.implicitHeight)

    PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      onCloseRequested: root.close()

      Flickable {
        anchors.fill: parent
        contentWidth: width
        contentHeight: content.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        interactive: contentHeight > height

        Column {
          id: content
          x: 16
          width: parent.width - 32
          spacing: 12

          Item { width: 1; height: 4 }

          RowLayout {
            width: content.width
            Text {
              Layout.fillWidth: true
              text: "Set your system-wide look and feel in one location"
              color: root.barForeground
              font.family: root.fontFamily
              font.pixelSize: Math.round(Style.font.heading * 1.25)
              font.weight: Font.DemiBold
              wrapMode: Text.Wrap
            }
            Controls.Button {
              text: "Help"
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              onClicked: helpDialog.open()
            }
          }

          GridLayout {
            id: settingsGrid
            width: content.width
            columns: 2
            uniformCellWidths: true
            enabled: !root.globalApplyRunning
            columnSpacing: 18
            rowSpacing: 10

            PanelSectionHeader { text: "FONTS"; fontFamily: root.fontFamily; Layout.columnSpan: 2 }
            ColumnLayout {
              Layout.fillWidth: true
              Text { text: "System font family"; color: root.barForeground; font.family: root.fontFamily; font.pixelSize: root.controlFontPixelSize }
              Controls.ComboBox {
                Layout.fillWidth: true
                Layout.preferredHeight: root.selectorHeight
                model: root.fonts; textRole: "name"; valueRole: "id"
                currentIndex: root.fonts.findIndex(function(entry) { return entry.id === root.selectedSystemFontId })
                displayText: currentIndex >= 0 ? currentText : "Select font"
                font.family: root.fontFamily
                onActivated: function(index) { root.selectedSystemFontId = root.fonts[index].id }
                font.pixelSize: root.controlFontPixelSize
              }
            }
            ColumnLayout {
              Layout.fillWidth: true
              Text { text: "System font size"; color: root.barForeground; font.family: root.fontFamily; font.pixelSize: root.controlFontPixelSize }
              Controls.ComboBox {
                Layout.fillWidth: true
                Layout.preferredHeight: root.selectorHeight
                model: root.fontSizes; textRole: "name"; valueRole: "id"
                currentIndex: root.fontSizes.findIndex(function(entry) { return entry.id === root.selectedSystemSize })
                font.family: root.fontFamily
                onActivated: function(index) { root.selectedSystemSize = root.fontSizes[index].id }
                font.pixelSize: root.controlFontPixelSize
              }
            }
            ColumnLayout {
              Layout.fillWidth: true
              Text { text: "Terminal font family"; color: root.barForeground; font.family: root.fontFamily; font.pixelSize: root.controlFontPixelSize }
              Controls.ComboBox {
                id: terminalFontCombo
                Layout.fillWidth: true
                Layout.preferredHeight: root.selectorHeight
                model: root.terminalFonts; textRole: "name"; valueRole: "id"
                currentIndex: root.terminalFonts.findIndex(function(entry) { return entry.id === root.selectedTerminalFontId })
                displayText: root.catalogName(root.fonts, root.selectedTerminalFontId) || "Select font"
                font.family: root.fontFamily
                onActivated: function(index) { root.selectedTerminalFontId = root.terminalFonts[index].id }
                font.pixelSize: root.controlFontPixelSize
              }
            }
            ColumnLayout {
              Layout.fillWidth: true
              Text { text: "Terminal font size"; color: root.barForeground; font.family: root.fontFamily; font.pixelSize: root.controlFontPixelSize }
              Controls.ComboBox {
                Layout.fillWidth: true
                Layout.preferredHeight: root.selectorHeight
                model: root.fontSizes; textRole: "name"; valueRole: "id"
                currentIndex: root.fontSizes.findIndex(function(entry) { return entry.id === root.selectedTerminalSize })
                font.family: root.fontFamily
                onActivated: function(index) { root.selectedTerminalSize = root.fontSizes[index].id }
                font.pixelSize: root.controlFontPixelSize
              }
            }
            Controls.CheckBox {
              id: terminalMonospaceCheck
              Layout.columnSpan: 2
              text: "Only show monospaced fonts"
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              palette.windowText: root.barForeground
              checked: root.onlyMonospacedTerminalFonts
              onToggled: root.onlyMonospacedTerminalFonts = checked
            }
            RowLayout {
              Layout.columnSpan: 2
              Layout.fillWidth: true
              Controls.Button {
                text: "Undo font change"
                font.family: root.fontFamily
                font.pixelSize: root.controlFontPixelSize
                enabled: !root.fontActionRunning && !root.appearanceActionRunning && !root.globalApplyRunning && root.fontUndoAvailable
                onClicked: root.undoGlobalFonts()
              }
            }
            Text {
              Layout.columnSpan: 2
              Layout.fillWidth: true
              visible: root.fontActionStatus !== ""
              text: root.fontActionStatus
              color: root.barForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              wrapMode: Text.Wrap
            }

            PanelSectionHeader { text: "THEME"; fontFamily: root.fontFamily; Layout.columnSpan: 2 }
            ColumnLayout {
              Layout.fillWidth: true
              Text { text: "Light theme"; color: root.barForeground; font.family: root.fontFamily; font.pixelSize: root.controlFontPixelSize }
              Controls.ComboBox {
                Layout.fillWidth: true
                Layout.preferredHeight: root.selectorHeight
                model: root.themes; textRole: "displayName"; valueRole: "id"
                currentIndex: root.themes.findIndex(function(entry) { return entry.id === root.selectedLightThemeId })
                displayText: currentIndex >= 0 ? currentText : "Select light theme"
                font.family: root.fontFamily
                onActivated: function(index) { root.selectedLightThemeId = root.themes[index].id }
                font.pixelSize: root.controlFontPixelSize
              }
            }
            ColumnLayout {
              Layout.fillWidth: true
              Text { text: "Mode"; color: root.barForeground; font.family: root.fontFamily; font.pixelSize: root.controlFontPixelSize }
              Controls.ComboBox {
                Layout.fillWidth: true
                Layout.preferredHeight: root.selectorHeight
                model: root.themeModes; textRole: "name"; valueRole: "id"
                currentIndex: root.themeModes.findIndex(function(entry) { return entry.id === root.selectedThemeMode })
                font.family: root.fontFamily
                onActivated: function(index) { root.selectedThemeMode = root.themeModes[index].id }
                font.pixelSize: root.controlFontPixelSize
              }
            }
            ColumnLayout {
              Layout.fillWidth: true
              Text { text: "Dark theme"; color: root.barForeground; font.family: root.fontFamily; font.pixelSize: root.controlFontPixelSize }
              Controls.ComboBox {
                Layout.fillWidth: true
                Layout.preferredHeight: root.selectorHeight
                model: root.themes; textRole: "displayName"; valueRole: "id"
                currentIndex: root.themes.findIndex(function(entry) { return entry.id === root.selectedDarkThemeId })
                displayText: currentIndex >= 0 ? currentText : "Select dark theme"
                font.family: root.fontFamily
                onActivated: function(index) { root.selectedDarkThemeId = root.themes[index].id }
                font.pixelSize: root.controlFontPixelSize
              }
            }
            ColumnLayout {
              Layout.fillWidth: true
              Text { text: "Boot unlock design"; color: root.barForeground; font.family: root.fontFamily; font.pixelSize: root.controlFontPixelSize }
              Controls.ComboBox {
                id: unlockCombo
                Layout.fillWidth: true
                Layout.preferredHeight: root.selectorHeight
                model: root.unlockDesigns; textRole: "displayName"; valueRole: "id"
                currentIndex: root.unlockDesigns.findIndex(function(entry) { return entry.id === root.selectedUnlockId })
                displayText: currentIndex >= 0 ? currentText : "Select unlock design"
                font.family: root.fontFamily
                onActivated: function(index) {
                  var entry = root.unlockDesigns[index]
                  if (entry.id !== root.selectedUnlockId) root.unlockSelectionChanged = true
                  root.selectedUnlockId = entry.id
                  root.selectedUnlockPreview = entry.preview || ""
                  if (root.selectedUnlockPreview !== "") unlockPreviewDialog.open()
                }
                font.pixelSize: root.controlFontPixelSize
              }
            }
            RowLayout {
              Layout.columnSpan: 2
              Layout.fillWidth: true
              Controls.Button {
                text: "Undo theme change"
                font.family: root.fontFamily
                font.pixelSize: root.controlFontPixelSize
                enabled: !root.appearanceActionRunning && !root.fontActionRunning && !root.globalApplyRunning && !!(root.appearanceActionStatuses.theme && root.appearanceActionStatuses.theme.undoAvailable)
                onClicked: root.undoAppearanceAction("theme")
              }
            }
            Text {
              Layout.columnSpan: 2
              Layout.fillWidth: true
              visible: root.appearanceActionMessages.theme !== ""
              text: root.appearanceActionMessages.theme
              color: root.barForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              wrapMode: Text.Wrap
            }
            RowLayout {
              Layout.columnSpan: 2
              Layout.fillWidth: true
              Controls.Button {
                text: "Undo unlock change"
                font.family: root.fontFamily
                font.pixelSize: root.controlFontPixelSize
                enabled: !root.appearanceActionRunning && !root.fontActionRunning && !root.globalApplyRunning && !!(root.appearanceActionStatuses.unlock && root.appearanceActionStatuses.unlock.undoAvailable)
                onClicked: root.undoAppearanceAction("unlock")
              }
            }
            Text {
              Layout.columnSpan: 2
              Layout.fillWidth: true
              visible: root.appearanceActionMessages.unlock !== ""
              text: root.appearanceActionMessages.unlock
              color: root.barForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              wrapMode: Text.Wrap
            }
            ColumnLayout {
              Layout.fillWidth: true
              Text { text: "Icon theme"; color: root.barForeground; font.family: root.fontFamily; font.pixelSize: root.controlFontPixelSize }
              Controls.ComboBox {
                Layout.fillWidth: true
                Layout.preferredHeight: root.selectorHeight
                model: root.icons; textRole: "displayName"; valueRole: "id"
                currentIndex: root.icons.findIndex(function(entry) { return entry.id === root.selectedIconId })
                displayText: currentIndex >= 0 ? currentText : "Select icon theme"
                font.family: root.fontFamily
                onActivated: function(index) { root.selectedIconId = root.icons[index].id }
                font.pixelSize: root.controlFontPixelSize
              }
            }
            PanelSectionHeader { text: "DESKTOP APPEARANCE"; fontFamily: root.fontFamily; Layout.columnSpan: 2 }
            ColumnLayout {
              Layout.fillWidth: true
              Text { text: "Background"; color: root.barForeground; font.family: root.fontFamily; font.pixelSize: root.controlFontPixelSize }
              Controls.ComboBox {
                Layout.fillWidth: true
                Layout.preferredHeight: root.selectorHeight
                model: root.backgrounds; textRole: "label"; valueRole: "id"
                currentIndex: root.backgrounds.findIndex(function(entry) { return entry.id === root.selectedBackgroundId })
                displayText: currentIndex >= 0 ? currentText : "Select background"
                font.family: root.fontFamily
                onActivated: function(index) { root.selectedBackgroundId = root.backgrounds[index].id }
                font.pixelSize: root.controlFontPixelSize
              }
            }
            RowLayout {
              Layout.columnSpan: 2
              Layout.fillWidth: true
              Controls.Button {
                text: "Undo background change"
                font.family: root.fontFamily
                font.pixelSize: root.controlFontPixelSize
                enabled: !root.appearanceActionRunning && !root.fontActionRunning && !root.globalApplyRunning && !!(root.appearanceActionStatuses.background && root.appearanceActionStatuses.background.undoAvailable)
                onClicked: root.undoAppearanceAction("background")
              }
            }
            Text {
              Layout.columnSpan: 2
              Layout.fillWidth: true
              visible: root.appearanceActionMessages.background !== ""
              text: root.appearanceActionMessages.background
              color: root.barForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              wrapMode: Text.Wrap
            }

            PanelSectionHeader { text: "APPLICATION AUDIT"; fontFamily: root.fontFamily; Layout.columnSpan: 2 }
            Text {
              Layout.columnSpan: 2
              Layout.fillWidth: true
              text: "Being Linux we cannot guarantee that every application will be identified and added for Look_and_Feel changes. If you have a particular application you want added please entery it in the Audit app window and press RETURN."
              color: root.barForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              wrapMode: Text.Wrap
            }
            RowLayout {
              Layout.columnSpan: 2
              Layout.fillWidth: true
              Controls.TextField {
                id: manualAppField
                Layout.fillWidth: true
                placeholderText: "Enter app name, launcher, or package"
                text: root.manualAppQuery
                font.family: root.fontFamily
                font.pixelSize: root.controlFontPixelSize
                onTextEdited: root.manualAppQuery = text
                onAccepted: root.inspectManualApp()
              }
              Controls.Button {
                text: root.manualAppActionRunning ? "Auditing…" : "Audit app"
                font.family: root.fontFamily
                font.pixelSize: root.controlFontPixelSize
                enabled: !root.manualAppActionRunning && root.manualAppQuery.trim().length >= 2
                onClicked: root.inspectManualApp()
              }
              Controls.Button {
                text: root.manualAuditClearRunning ? "Clearing…" : "Clear registrations"
                font.family: root.fontFamily
                font.pixelSize: root.controlFontPixelSize
                enabled: !root.manualAuditClearRunning && !root.manualAppActionRunning
                onClicked: root.clearManualAudit()
              }
            }
            Text {
              Layout.columnSpan: 2
              Layout.fillWidth: true
              visible: root.manualAppStatus !== ""
              text: root.manualAppStatus
              color: root.barForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              wrapMode: Text.Wrap
            }

            Text {
              Layout.columnSpan: 2
              Layout.fillWidth: true
              visible: root.globalApplyStatus !== ""
              text: root.globalApplyStatus
              color: root.barForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              wrapMode: Text.Wrap
            }
            RowLayout {
              Layout.columnSpan: 2
              Layout.fillWidth: true
              Item { Layout.fillWidth: true }
              Controls.Button {
                text: root.globalApplyRunning ? "APPLYING…" : "APPLY"
                font.family: root.fontFamily
                font.pixelSize: root.controlFontPixelSize
                enabled: !root.globalApplyRunning && !root.appearanceActionRunning && !root.fontActionRunning
                  && !root.manualAppActionRunning && !root.manualAuditClearRunning
                onClicked: root.applyAllSelectedSettings()
              }
            }

          }

          Item { width: 1; height: 8 }
        }
      }

      Controls.Dialog {
        id: unlockPreviewDialog
        title: "Boot unlock preview"
        modal: true
        anchors.centerIn: parent
        width: Math.min(640, panel.availableCardWidth - 40)
        height: Math.min(440, panel.availableCardHeight - 40)
        standardButtons: Controls.Dialog.Close
        contentItem: Image {
          source: root.selectedUnlockPreview ? "file://" + root.selectedUnlockPreview : ""
          fillMode: Image.PreserveAspectFit
          asynchronous: true
          cache: false
        }
      }

      Controls.Dialog {
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
              text: "APPLY"
              color: root.barForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              font.weight: Font.DemiBold
            }
            Text {
              width: parent.width
              text: "The APPLY button at the bottom applies theme, fonts, and background in that order, followed by boot unlock only if you deliberately choose a design during this panel session. If a step fails, later steps stop; completed steps remain applied and can be undone with their section's Undo control. Icon theme selection is not applied."
              color: root.barForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              wrapMode: Text.Wrap
            }
            Text {
              width: parent.width
              text: "FONTS"
              color: root.barForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              font.weight: Font.DemiBold
            }
            Text {
              width: parent.width
              text: "System font family and size set the shared GTK and Omarchy shell font targets. Terminal font family and size set detected terminal configurations with verified adapters; discovery is not exhaustive. Only show monospaced fonts filters the terminal menu using installed font spacing metadata. It starts unchecked and keeps your current font selected until you choose another, even if that font is absent from the filtered menu. The global APPLY uses both selections; Undo font change restores the previous plugin font transaction. Some applications need to be restarted. An unresolved or unsupported manual audit registration blocks font Apply until it is resolved or cleared."
              color: root.barForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              wrapMode: Text.Wrap
            }
            Text {
              width: parent.width
              text: "THEME"
              color: root.barForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              font.weight: Font.DemiBold
            }
            Text {
              width: parent.width
              text: "Choose Automatic, Light all day, or Dark all day. When you press the global APPLY button in Automatic mode, the plugin chooses the Light or Dark theme for the current solar phase. Choose the Light and Dark themes, then apply. Undo theme change restores the previous detected theme."
              color: root.barForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              wrapMode: Text.Wrap
            }
            Text {
              width: parent.width
              text: "BOOT UNLOCK DESIGN"
              color: root.barForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              font.weight: Font.DemiBold
            }
            Text {
              width: parent.width
              text: "Choose a design to preview it. Global APPLY includes the design only after you deliberately change this selection during the panel session. Applying it updates Omarchy's Plymouth/SDDM artwork and rebuilds the initramfs; on systems using Limine integration it can also update boot entries. Undo unlock change reapplies the previous detected design, without guaranteeing restoration of boot files or entries."
              color: root.barForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              wrapMode: Text.Wrap
            }
            Text {
              width: parent.width
              text: "BACKGROUND"
              color: root.barForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              font.weight: Font.DemiBold
            }
            Text {
              width: parent.width
              text: "Choose a background. The global APPLY button applies the selection; Undo background change restores the previous background."
              color: root.barForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              wrapMode: Text.Wrap
            }
            Text {
              width: parent.width
              text: "ICON THEME"
              color: root.barForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              font.weight: Font.DemiBold
            }
            Text {
              width: parent.width
              text: "Icon theme changes are not applied yet."
              color: root.barForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              wrapMode: Text.Wrap
            }
            Text {
              width: parent.width
              text: "APPLICATION AUDIT"
              color: root.barForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              font.weight: Font.DemiBold
            }
            Text {
              width: parent.width
              text: "Enter an application name, launcher, or package and press Return or select Audit app. The lookup searches separately from the automatic inventory. It can register verified shared GTK or supported terminal font surfaces for global font Apply; app-specific theme controls are not registered. Ambiguous or unsupported results block font Apply. Clear registrations deletes the saved manual audit registrations. Audit results omit application names."
              color: root.barForeground
              font.family: root.fontFamily
              font.pixelSize: root.controlFontPixelSize
              wrapMode: Text.Wrap
            }
          }
        }
      }
    }
  }

  Process {
    id: inventoryProcess
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: root.adoptInventory(text)
    }
    onExited: function(code) {
      if (code !== 0) {
        root.fonts = []
        root.themes = []
        root.unlockDesigns = []
        root.backgrounds = []
        root.icons = []
      }
    }
  }

  Process {
    id: appearanceActionProcess
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: {
      var kind = root.appearanceActionKind
      try {
        var result = JSON.parse(String(text || "{}"))
        root.globalApplyStepSucceeded = !!result.rolledBack || result.state === "already-current"
          || (result.state === "committed" && !!result.readback)
        var message
        if (result.rolledBack) {
          if (kind === "theme") {
            root.lastAppliedTheme = String(result.restored || "")
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
          } else {
            var restoredUnlock = root.unlockDesigns.find(function(entry) { return String(entry.name).toLowerCase().replace(/_/g, "-") === String(result.restored || "").toLowerCase().replace(/_/g, "-") })
            if (restoredUnlock) root.selectedUnlockId = restoredUnlock.id
          }
        } else if (result.state === "already-current") {
          if (kind === "theme") {
            root.lastAppliedTheme = String(result.after || "")
            root.lastAppliedThemeSetThisSession = true
          }
          message = "The selected " + kind + " is already active; no change was needed."
        } else if (kind === "theme") {
          root.lastAppliedTheme = String(result.readback || "")
          root.lastAppliedThemeSetThisSession = true
          message = "Applied and verified the selected theme."
        } else if (kind === "background") {
          message = "Applied and verified the selected background."
        } else {
          message = "Applied and verified the selected boot unlock design."
        }
        var messages = Object.assign({}, root.appearanceActionMessages)
        messages[kind] = message
        root.appearanceActionMessages = messages
        root.appearanceAuditStatus = ""
        root.refreshInventory()
        Qt.callLater(root.runAppearanceAudit)
      } catch (e) {
        root.globalApplyStepSucceeded = false
        var errors = Object.assign({}, root.appearanceActionMessages)
        errors[kind] = "Appearance action completed, but its result could not be read."
        root.appearanceActionMessages = errors
      }
    } }
    stderr: StdioCollector { waitForEnd: true; onStreamFinished: {
      if (String(text || "").trim()) {
        root.globalApplyStepSucceeded = false
        var errors = Object.assign({}, root.appearanceActionMessages)
        errors[root.appearanceActionKind] = "The appearance action could not be completed."
        root.appearanceActionMessages = errors
      }
    } }
    onExited: function(code) {
      root.appearanceActionRunning = false
      if (code !== 0) {
        var kind = root.appearanceActionKind
        var messages = Object.assign({}, root.appearanceActionMessages)
        if (!messages[kind] || messages[kind].indexOf("failed") < 0)
          messages[kind] = "Appearance action failed; see the plugin log for details."
        root.appearanceActionMessages = messages
      }
      if (root.globalApplyRunning && root.globalApplyCurrentStep === root.appearanceActionKind) {
        var stepSucceeded = code === 0 && root.globalApplyStepSucceeded
        var stepDetail = root.appearanceActionMessages[root.appearanceActionKind]
        Qt.callLater(function() { root.finishGlobalApplyStep(stepSucceeded, stepDetail) })
      }
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
      unlockStatusProcess.command = ["/usr/bin/python3", localPath(Qt.resolvedUrl("controller.py")),
        "appearance-action-status", "unlock"]
      unlockStatusProcess.running = true
    }
  }

  Process {
    id: globalFontProcess
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: {
      try {
        var result = JSON.parse(String(text || "{}"))
        if (result.blocked) {
          root.globalApplyStepSucceeded = false
          root.fontActionStatus = "Font Apply stopped: " + Number(result.unsupportedManualCount || 0)
            + " manually audited control surface(s) lack a verified reversible adapter. Re-audit with a specific entry or clear the manual audit registry."
        } else if (result.transaction) {
          root.globalApplyStepSucceeded = true
          root.fontUndoAvailable = true
          root.fontActionStatus = "Applied the selected system font to GTK settings and Omarchy shell files, plus the terminal font to "
            + result.terminalCount + " detected terminal configuration(s). Registered manual font surfaces included: "
            + Number(result.registeredManualCount || 0) + ". Restart applications that do not reload fonts automatically."
        } else if (result.rolledBack) {
          root.globalApplyStepSucceeded = true
          root.fontUndoAvailable = false
          root.inventoryLoaded = false
          root.refreshInventory()
          root.fontActionStatus = "Restored the previous global font settings."
        } else {
          root.globalApplyStepSucceeded = false
          root.fontActionStatus = "The global font action returned no result."
        }
      } catch (e) {
        root.globalApplyStepSucceeded = false
        root.fontActionStatus = "The global font action completed, but its result could not be read."
      }
    } }
    stderr: StdioCollector { waitForEnd: true; onStreamFinished: {
      if (String(text || "").trim()) {
        root.globalApplyStepSucceeded = false
        root.fontActionStatus = "The global font action could not be completed."
      }
    } }
    onRunningChanged: if (!running) root.fontActionRunning = false
    onExited: function(code) {
      root.fontActionRunning = false
      if (root.globalApplyRunning && root.globalApplyCurrentStep === "fonts") {
        var stepSucceeded = code === 0 && root.globalApplyStepSucceeded
        var stepDetail = root.fontActionStatus
        Qt.callLater(function() { root.finishGlobalApplyStep(stepSucceeded, stepDetail) })
      }
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
