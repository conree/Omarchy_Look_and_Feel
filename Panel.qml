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
  property string selectedBackgroundId: ""
  property string selectedIconId: ""
  property bool inventoryLoaded: false
  property bool ghosttyActionRunning: false
  property string ghosttyStatus: ""
  property bool mailFontActionRunning: false
  property string mailFontStatus: ""
  property string manualAppQuery: ""
  property string manualAppStatus: ""
  property bool manualAppActionRunning: false
  property string appearanceAuditStatus: ""
  property bool appearanceAuditRunning: false
  property bool appearanceActionRunning: false
  property string appearanceActionKind: ""
  property string unlockBaselineTransaction: ""
  property string unlockRequestedSlug: ""
  property string unlockOperation: "apply"
  property int unlockStatusPollCount: 0
  property var appearanceActionStatuses: ({})
  property var appearanceActionMessages: ({ theme: "", background: "", unlock: "" })

  function runAppearanceAction(kind, args) {
    if (root.appearanceActionRunning) return
    root.appearanceActionKind = kind
    var messages = Object.assign({}, root.appearanceActionMessages)
    messages[kind] = "Applying selected " + kind + "…"
    root.appearanceActionMessages = messages
    root.appearanceActionRunning = true
    appearanceActionProcess.command = ["/usr/bin/python3", localPath(Qt.resolvedUrl("controller.py"))].concat(args)
    appearanceActionProcess.running = true
  }

  function applySelectedTheme() {
    if (!root.selectedLightThemeId || !root.selectedDarkThemeId) return
    root.runAppearanceAction("theme", ["apply-theme", root.selectedThemeMode,
      root.catalogName(root.themes, root.selectedLightThemeId),
      root.catalogName(root.themes, root.selectedDarkThemeId)])
  }

  function applySelectedBackground() {
    if (!root.selectedBackgroundId) return
    root.runAppearanceAction("background", ["apply-catalog-action", "background", root.selectedBackgroundId])
  }

  function launchUnlockCommand(args, expectedSlug, operation) {
    if (root.appearanceActionRunning) return
    root.appearanceActionKind = "unlock"
    root.unlockBaselineTransaction = String((root.appearanceActionStatuses.unlock || {}).transaction || "")
    root.unlockRequestedSlug = expectedSlug
    root.unlockOperation = operation
    root.unlockStatusPollCount = 0
    var messages = Object.assign({}, root.appearanceActionMessages)
    messages.unlock = "Opening an Omarchy terminal for the unlock change and administrator authorization…"
    root.appearanceActionMessages = messages
    root.appearanceActionRunning = true
    unlockApplyProcess.command = ["/usr/bin/omarchy-launch-floating-terminal-with-presentation", "/usr/bin/python3",
      localPath(Qt.resolvedUrl("controller.py"))].concat(args)
    unlockApplyProcess.running = true
  }

  function applySelectedUnlock() {
    if (!root.selectedUnlockId) return
    var slug = root.catalogName(root.unlockDesigns, root.selectedUnlockId).toLowerCase().replace(/ /g, "-")
    root.launchUnlockCommand(["apply-catalog-action", "unlock", root.selectedUnlockId], slug, "apply")
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

  function applyGhosttyFont() {
    if (!root.selectedTerminalFontId || root.ghosttyActionRunning) return
    ghosttyStatus = "Applying selected font and size to Ghostty…"
    ghosttyActionRunning = true
    ghosttyProcess.command = ["/usr/bin/python3", localPath(Qt.resolvedUrl("controller.py")), "apply-ghostty-font", root.selectedTerminalFontId, String(root.selectedTerminalSize)]
    ghosttyProcess.running = true
  }

  function applyMailSystemFont() {
    if (!root.selectedSystemFontId || root.mailFontActionRunning) return
    mailFontStatus = "Applying the selected system font to Betterbird…"
    mailFontActionRunning = true
    mailFontProcess.command = ["/usr/bin/python3", localPath(Qt.resolvedUrl("controller.py")), "apply-mail-system-font", root.selectedSystemFontId, String(root.selectedSystemSize)]
    mailFontProcess.running = true
  }

  function rollbackMailSystemFont() {
    if (root.mailFontActionRunning) return
    mailFontStatus = "Restoring the previous mail-client font settings…"
    mailFontActionRunning = true
    mailFontProcess.command = ["/usr/bin/python3", localPath(Qt.resolvedUrl("controller.py")), "rollback-mail-system-font"]
    mailFontProcess.running = true
  }

  function inspectManualApp() {
    if (root.manualAppActionRunning || root.manualAppQuery.trim().length < 2) return
    manualAppStatus = "Looking up the requested application separately from the startup census…"
    manualAppActionRunning = true
    manualAppProcess.command = ["/usr/bin/python3", localPath(Qt.resolvedUrl("controller.py")), "inspect-app", root.manualAppQuery.trim()]
    manualAppProcess.running = true
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
      var coverage = result.launcherFrameworkIdentification || ({})
      var candidates = result.applicationCandidateCoverage || ({})
      var sources = candidates.sourceStatus || ({})
      var lines = [
        "Overall readback: " + (result.overall || "unknown"),
        "Framework identified: " + (candidates.frameworkIdentified || 0) + "/" + (candidates.discovered || 0)
          + " discovered app candidate records (" + Number(candidates.percent || 0).toFixed(1) + "%). This is not the share of every installed app or proof a font was applied.",
        "Scope: " + (candidates.scope || coverage.scope || "not available"),
        "Source scans — pacman: " + (sources.pacman || "unknown") + "; pacman app metadata: " + (sources.pacmanAppstream || "unknown")
          + "; Flatpak: " + (sources.flatpak || "unknown") + "; Snap: " + (sources.snap || "unknown") + "; AppImage: " + (sources.AppImage || "unknown") + ".",
        "Visible launchers: " + (coverage.identified || 0) + "/" + (coverage.denominator || 0)
          + " labeled (" + (coverage.inferredSharedSurface || 0) + " inferred, " + (coverage.unidentified || 0) + " unidentified).",
        "Fonts: " + (result.summary.font || "not checked"),
        "Theme: " + (result.summary.theme || "not checked"),
        "Background: " + (result.summary.background || "not checked"),
        "Boot unlock: " + (result.summary.unlock || "not checked")
      ]
      var issues = (result.checks || []).filter(function(check) {
        return check.state === "mismatched" || check.state === "pending-restart" || check.state === "unobservable"
      })
      issues.forEach(function(check) {
        lines.push(check.surface + ": " + (check.stateDetail || check.state) + " (expected " + JSON.stringify(check.expected)
          + "; observed " + JSON.stringify(check.actual) + ")")
      })
      lines.push(result.caveat || "")
      appearanceAuditStatus = lines.filter(function(line) { return line !== "" }).join("\n")
    } catch (e) {
      appearanceAuditStatus = "The appearance audit returned an unreadable result."
    }
  }

  function rollbackGhosttyFont() {
    if (root.ghosttyActionRunning) return
    ghosttyStatus = "Restoring the previous Ghostty font…"
    ghosttyActionRunning = true
    ghosttyProcess.command = ["/usr/bin/python3", localPath(Qt.resolvedUrl("controller.py")), "rollback-ghostty-font"]
    ghosttyProcess.running = true
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
      if (!lastAppliedThemeSetThisSession && appearanceActionStatuses.theme && appearanceActionStatuses.theme.expectedValue)
        lastAppliedTheme = String(appearanceActionStatuses.theme.expectedValue)

      function idFor(records, name) {
        var entry = records.find(function(item) { return item.name === name })
        return entry ? entry.id : ""
      }

      if (!inventoryLoaded) {
        selectedSystemFontId = idFor(fonts, "Aileron")
        selectedTerminalFontId = (data.preferences && data.preferences.terminalFontId)
          || idFor(fonts, "Office Code Pro")
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

          Text {
            text: "Set your system-wide look and feel in one location"
            color: root.barForeground
            font.family: root.fontFamily
            font.pixelSize: Math.round(Style.font.heading * 1.25)
            font.weight: Font.DemiBold
          }

          GridLayout {
            id: settingsGrid
            width: content.width
            columns: 2
            columnSpacing: 18
            rowSpacing: 10

            PanelSectionHeader { text: "TYPOGRAPHY"; Layout.columnSpan: 2 }

            ColumnLayout {
              Layout.fillWidth: true
              Text { text: "System font"; color: root.barForeground; font.family: root.fontFamily; font.pixelSize: Math.round(Style.font.bodySmall * 1.3) }
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
              Text { text: "System size"; color: root.barForeground; font.family: root.fontFamily; font.pixelSize: Math.round(Style.font.bodySmall * 1.3) }
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
              Text { text: "Terminal font"; color: root.barForeground; font.family: root.fontFamily; font.pixelSize: Math.round(Style.font.bodySmall * 1.3) }
              Controls.ComboBox {
                Layout.fillWidth: true
                Layout.preferredHeight: root.selectorHeight
                model: root.fonts; textRole: "name"; valueRole: "id"
                currentIndex: root.fonts.findIndex(function(entry) { return entry.id === root.selectedTerminalFontId })
                displayText: currentIndex >= 0 ? currentText : "Select font"
                font.family: root.fontFamily
                onActivated: function(index) {
                  root.selectedTerminalFontId = root.fonts[index].id
                  Qt.callLater(root.applyGhosttyFont)
                }
                font.pixelSize: root.controlFontPixelSize
              }
            }
            ColumnLayout {
              Layout.fillWidth: true
              Text { text: "Terminal size"; color: root.barForeground; font.family: root.fontFamily; font.pixelSize: Math.round(Style.font.bodySmall * 1.3) }
              Controls.ComboBox {
                Layout.fillWidth: true
                Layout.preferredHeight: root.selectorHeight
                model: root.fontSizes; textRole: "name"; valueRole: "id"
                currentIndex: root.fontSizes.findIndex(function(entry) { return entry.id === root.selectedTerminalSize })
                font.family: root.fontFamily
                onActivated: function(index) {
                  root.selectedTerminalSize = root.fontSizes[index].id
                  Qt.callLater(root.applyGhosttyFont)
                }
                font.pixelSize: root.controlFontPixelSize
              }
            }

            ColumnLayout {
              Layout.columnSpan: 2
              Layout.fillWidth: true
              spacing: 6
              RowLayout {
                Layout.fillWidth: true
                Text {
                  Layout.fillWidth: true
                  text: "This app-specific action updates Betterbird. GTK mail clients inherit the shared GTK font settings."
                  color: root.barForeground
                  font.family: root.fontFamily
                  font.pixelSize: Math.round(Style.font.bodySmall * 1.2)
                  wrapMode: Text.Wrap
                }
                Controls.Button {
                  text: "Apply to Betterbird"
                  font.family: root.fontFamily
                  font.pixelSize: root.controlFontPixelSize
                  enabled: !root.mailFontActionRunning && !!root.selectedSystemFontId
                  onClicked: root.applyMailSystemFont()
                }
                Controls.Button {
                  text: "Undo Betterbird font change"
                  font.family: root.fontFamily
                  font.pixelSize: root.controlFontPixelSize
                  enabled: !root.mailFontActionRunning
                  onClicked: root.rollbackMailSystemFont()
                }
              }
              Text {
                Layout.fillWidth: true
                visible: root.mailFontStatus !== ""
                text: root.mailFontStatus
                color: root.barForeground
                font.family: root.fontFamily
                font.pixelSize: Math.round(Style.font.bodySmall * 1.2)
                wrapMode: Text.Wrap
              }
              RowLayout {
                Layout.fillWidth: true
                Text {
                  Layout.fillWidth: true
                  text: "Changing Terminal font applies it to Ghostty."
                  color: root.barForeground
                  font.family: root.fontFamily
                  font.pixelSize: Math.round(Style.font.bodySmall * 1.2)
                }
                Controls.Button {
                  text: "Undo Ghostty font change"
                  font.family: root.fontFamily
                  font.pixelSize: root.controlFontPixelSize
                  enabled: !root.ghosttyActionRunning
                  onClicked: root.rollbackGhosttyFont()
                }
              }
              Text {
                Layout.fillWidth: true
                visible: root.ghosttyStatus !== ""
                text: root.ghosttyStatus
                color: root.barForeground
                font.family: root.fontFamily
                font.pixelSize: Math.round(Style.font.bodySmall * 1.2)
                wrapMode: Text.Wrap
              }
            }

            PanelSectionHeader { text: "THEME"; Layout.columnSpan: 2 }
            ColumnLayout {
              Layout.columnSpan: 2
              Layout.fillWidth: true
              Text { text: "Mode"; color: root.barForeground; font.family: root.fontFamily; font.pixelSize: Math.round(Style.font.bodySmall * 1.3) }
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
              Text { text: "Light theme"; color: root.barForeground; font.family: root.fontFamily; font.pixelSize: Math.round(Style.font.bodySmall * 1.3) }
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
              Text { text: "Dark theme"; color: root.barForeground; font.family: root.fontFamily; font.pixelSize: Math.round(Style.font.bodySmall * 1.3) }
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
            RowLayout {
              Layout.columnSpan: 2
              Layout.fillWidth: true
              Controls.Button {
                text: root.appearanceActionRunning && root.appearanceActionKind === "theme" ? "Applying…" : "Apply selected theme"
                font.family: root.fontFamily
                font.pixelSize: root.controlFontPixelSize
                enabled: !root.appearanceActionRunning && !!root.selectedLightThemeId && !!root.selectedDarkThemeId
                onClicked: root.applySelectedTheme()
              }
              Controls.Button {
                text: "Undo theme change"
                font.family: root.fontFamily
                font.pixelSize: root.controlFontPixelSize
                enabled: !root.appearanceActionRunning && !!(root.appearanceActionStatuses.theme && root.appearanceActionStatuses.theme.undoAvailable)
                onClicked: root.undoAppearanceAction("theme")
              }
              Text {
                Layout.fillWidth: true
                text: "Each Apply is one-time. Automatic chooses by the current solar phase; future theme transitions are not scheduled."
                color: root.barForeground
                font.family: root.fontFamily
                font.pixelSize: Math.round(Style.font.bodySmall * 1.05)
                wrapMode: Text.Wrap
              }
            }
            Text {
              Layout.columnSpan: 2
              Layout.fillWidth: true
              visible: root.appearanceActionMessages.theme !== ""
              text: root.appearanceActionMessages.theme
              color: root.barForeground
              font.family: root.fontFamily
              font.pixelSize: Math.round(Style.font.bodySmall * 1.05)
              wrapMode: Text.Wrap
            }
            ColumnLayout {
              Layout.fillWidth: true
              Text { text: "Boot unlock design"; color: root.barForeground; font.family: root.fontFamily; font.pixelSize: Math.round(Style.font.bodySmall * 1.3) }
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
                text: root.appearanceActionRunning && root.appearanceActionKind === "unlock" ? "Applying…" : "Apply boot unlock design"
                font.family: root.fontFamily
                font.pixelSize: root.controlFontPixelSize
                enabled: !root.appearanceActionRunning && !!root.selectedUnlockId
                onClicked: root.applySelectedUnlock()
              }
              Controls.Button {
                text: "Undo unlock change"
                font.family: root.fontFamily
                font.pixelSize: root.controlFontPixelSize
                enabled: !root.appearanceActionRunning && !!(root.appearanceActionStatuses.unlock && root.appearanceActionStatuses.unlock.undoAvailable)
                onClicked: root.undoAppearanceAction("unlock")
              }
              Text {
                Layout.fillWidth: true
                text: "Apply and Undo open an Omarchy terminal for administrator authorization. Omarchy updates Plymouth and SDDM assets and rebuilds the initramfs."
                color: root.barForeground
                font.family: root.fontFamily
                font.pixelSize: Math.round(Style.font.bodySmall * 1.05)
                wrapMode: Text.Wrap
              }
            }
            Text {
              Layout.columnSpan: 2
              Layout.fillWidth: true
              visible: root.appearanceActionMessages.unlock !== ""
              text: root.appearanceActionMessages.unlock
              color: root.barForeground
              font.family: root.fontFamily
              font.pixelSize: Math.round(Style.font.bodySmall * 1.05)
              wrapMode: Text.Wrap
            }
            ColumnLayout {
              Layout.fillWidth: true
              Text { text: "Icon theme"; color: root.barForeground; font.family: root.fontFamily; font.pixelSize: Math.round(Style.font.bodySmall * 1.3) }
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

            PanelSectionHeader { text: "DESKTOP APPEARANCE"; Layout.columnSpan: 2 }
            ColumnLayout {
              Layout.columnSpan: 2
              Layout.fillWidth: true
              Text { text: "Background"; color: root.barForeground; font.family: root.fontFamily; font.pixelSize: Math.round(Style.font.bodySmall * 1.3) }
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
                text: root.appearanceActionRunning && root.appearanceActionKind === "background" ? "Applying…" : "Apply background"
                font.family: root.fontFamily
                font.pixelSize: root.controlFontPixelSize
                enabled: !root.appearanceActionRunning && !!root.selectedBackgroundId
                onClicked: root.applySelectedBackground()
              }
              Controls.Button {
                text: "Undo background change"
                font.family: root.fontFamily
                font.pixelSize: root.controlFontPixelSize
                enabled: !root.appearanceActionRunning && !!(root.appearanceActionStatuses.background && root.appearanceActionStatuses.background.undoAvailable)
                onClicked: root.undoAppearanceAction("background")
              }
              Text {
                Layout.fillWidth: true
                text: "The saved background is applied independently of theme changes."
                color: root.barForeground
                font.family: root.fontFamily
                font.pixelSize: Math.round(Style.font.bodySmall * 1.05)
                wrapMode: Text.Wrap
              }
            }
            Text {
              Layout.columnSpan: 2
              Layout.fillWidth: true
              visible: root.appearanceActionMessages.background !== ""
              text: root.appearanceActionMessages.background
              color: root.barForeground
              font.family: root.fontFamily
              font.pixelSize: Math.round(Style.font.bodySmall * 1.05)
              wrapMode: Text.Wrap
            }

            PanelSectionHeader { text: "MANUAL APP REVIEW"; Layout.columnSpan: 2 }
            Text {
              Layout.columnSpan: 2
              Layout.fillWidth: true
              text: "For an app missed by the automatic inventory or not changed by a font action, enter its name for a separate review."
              color: root.barForeground
              font.family: root.fontFamily
              font.pixelSize: Math.round(Style.font.bodySmall * 1.1)
              wrapMode: Text.Wrap
            }
            RowLayout {
              Layout.columnSpan: 2
              Layout.fillWidth: true
              Controls.TextField {
                id: manualAppField
                Layout.fillWidth: true
                placeholderText: "Application name, launcher, or package"
                text: root.manualAppQuery
                font.family: root.fontFamily
                font.pixelSize: root.controlFontPixelSize
                onTextEdited: root.manualAppQuery = text
                onAccepted: root.inspectManualApp()
              }
              Controls.Button {
                text: root.manualAppActionRunning ? "Reviewing…" : "Review app"
                font.family: root.fontFamily
                font.pixelSize: root.controlFontPixelSize
                enabled: !root.manualAppActionRunning && root.manualAppQuery.trim().length >= 2
                onClicked: root.inspectManualApp()
              }
            }
            Text {
              Layout.columnSpan: 2
              Layout.fillWidth: true
              visible: root.manualAppStatus !== ""
              text: root.manualAppStatus
              color: root.barForeground
              font.family: root.fontFamily
              font.pixelSize: Math.round(Style.font.bodySmall * 1.05)
              wrapMode: Text.Wrap
            }

            PanelSectionHeader { text: "VERIFY FONT, THEME, BACKGROUND & BOOT UNLOCK"; Layout.columnSpan: 2 }
            RowLayout {
              Layout.columnSpan: 2
              Layout.fillWidth: true
              Text {
                Layout.fillWidth: true
                text: "Compare current selections (draft) with saved font configuration, Omarchy's active theme, background image, and installed Plymouth unlock assets. This does not mean the plugin applied them."
                color: root.barForeground
                font.family: root.fontFamily
                font.pixelSize: Math.round(Style.font.bodySmall * 1.1)
                wrapMode: Text.Wrap
              }
              Controls.Button {
                text: root.appearanceAuditRunning ? "Auditing…" : "Audit current state"
                font.family: root.fontFamily
                font.pixelSize: root.controlFontPixelSize
                enabled: !root.appearanceAuditRunning && !!root.selectedSystemFontId && !!root.selectedTerminalFontId
                onClicked: root.runAppearanceAudit()
              }
            }
            Text {
              Layout.columnSpan: 2
              Layout.fillWidth: true
              visible: root.appearanceAuditStatus !== ""
              text: root.appearanceAuditStatus
              color: root.barForeground
              font.family: root.fontFamily
              font.pixelSize: Math.round(Style.font.bodySmall * 1.05)
              wrapMode: Text.Wrap
            }

            Text {
              Layout.columnSpan: 2
              Layout.fillWidth: true
              text: "Font coverage is best effort. Linux apps may use private, bundled, sandboxed, or hard-coded font settings; verify each app's font controls before applying changes."
              color: root.barForeground
              font.family: root.fontFamily
              font.pixelSize: Math.round(Style.font.bodySmall * 1.05)
              wrapMode: Text.Wrap
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
        var message
        if (result.rolledBack) {
          if (kind === "theme") {
            root.lastAppliedTheme = String(result.restored || "")
            root.lastAppliedThemeSetThisSession = true
          }
          message = "Restored the previous active " + kind + " setting and verified " + JSON.stringify(result.readback) + "."
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
          message = "Applied and verified Omarchy theme " + JSON.stringify(result.readback) + ". Undo re-applies the previous detected Omarchy theme; theme hooks may have their own effects."
          message += " The independent background was preserved and read back as " + JSON.stringify(result.backgroundReadback) + ". This applies once; future theme transitions are not scheduled."
        } else if (kind === "background") {
          message = "Applied and verified background " + JSON.stringify(result.readback) + ". Undo restores the previous background path."
        } else {
          message = "Applied and verified unlock design " + JSON.stringify(result.readback) + ". Omarchy also updates SDDM/Plymouth assets and rebuilds initramfs; readback does not inspect the boot image."
        }
        var messages = Object.assign({}, root.appearanceActionMessages)
        messages[kind] = message
        root.appearanceActionMessages = messages
        root.appearanceAuditStatus = ""
        root.refreshInventory()
        Qt.callLater(root.runAppearanceAudit)
      } catch (e) {
        var errors = Object.assign({}, root.appearanceActionMessages)
        errors[kind] = "Appearance action completed, but its result could not be read."
        root.appearanceActionMessages = errors
      }
    } }
    stderr: StdioCollector { waitForEnd: true; onStreamFinished: {
      var message = String(text || "").trim()
      if (message) {
        var errors = Object.assign({}, root.appearanceActionMessages)
        errors[root.appearanceActionKind] = message
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
    }
  }

  Process {
    id: unlockApplyProcess
    onExited: function(code) {
      if (code !== 0) {
        root.appearanceActionRunning = false
        var errors = Object.assign({}, root.appearanceActionMessages)
        errors.unlock = "Could not open the Omarchy terminal for the unlock action."
        root.appearanceActionMessages = errors
      } else {
        unlockStatusPoll.start()
      }
    }
  }

  Process {
    id: unlockStatusProcess
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: {
      try {
        var status = JSON.parse(String(text || "{}"))
        var observed = String(status.observedValue || "")
        var matched = observed === root.unlockRequestedSlug
        if (matched) {
          unlockStatusPoll.stop()
          root.appearanceActionRunning = false
          var messages = Object.assign({}, root.appearanceActionMessages)
          if (root.unlockOperation === "undo") {
            messages.unlock = "Restored the previous active unlock setting and verified " + JSON.stringify(observed) + ". Omarchy updated Plymouth/SDDM assets and rebuilt initramfs; readback does not inspect the boot image."
            var restoredUnlock = root.unlockDesigns.find(function(entry) { return String(entry.name).toLowerCase().replace(/ /g, "-") === observed })
            if (restoredUnlock) root.selectedUnlockId = restoredUnlock.id
          } else {
            messages.unlock = status.transaction && status.transaction !== root.unlockBaselineTransaction
              ? "Applied and verified unlock design " + JSON.stringify(observed) + ". Omarchy updated Plymouth/SDDM assets and rebuilt initramfs; readback does not inspect the boot image."
              : "The selected unlock design is already active and its Omarchy readback matches."
          }
          root.appearanceActionMessages = messages
          root.refreshInventory()
          Qt.callLater(root.runAppearanceAudit)
        } else if (root.unlockStatusPollCount >= 40) {
          unlockStatusPoll.stop()
          root.appearanceActionRunning = false
          var pending = Object.assign({}, root.appearanceActionMessages)
          pending.unlock = "No matching unlock readback appeared. Check the Omarchy terminal for authorization or rebuild errors."
          root.appearanceActionMessages = pending
        }
      } catch (e) {
        // A transient status read is retried on the next poll.
      }
    } }
  }

  Timer {
    id: unlockStatusPoll
    interval: 1500
    repeat: true
    onTriggered: {
      if (unlockStatusProcess.running) return
      root.unlockStatusPollCount += 1
      unlockStatusProcess.command = ["/usr/bin/python3", localPath(Qt.resolvedUrl("controller.py")),
        "appearance-action-status", "unlock"]
      unlockStatusProcess.running = true
    }
  }

  Process {
    id: ghosttyProcess
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: {
      try {
        var result = JSON.parse(String(text || "{}"))
        if (result.font) {
          root.ghosttyStatus = "Applied and saved " + result.font + " " + result.sizePt + " pt for Ghostty. Reload its config or restart Ghostty to update open windows."
        } else if (result.rolledBack) {
          root.inventoryLoaded = false
          root.refreshInventory()
          root.ghosttyStatus = "Ghostty font change and saved selection rolled back. Reload its config or restart Ghostty to restore open windows."
        } else {
          root.ghosttyStatus = "Ghostty action completed."
        }
      } catch (e) {
        root.ghosttyStatus = "Ghostty action completed."
      }
    } }
    stderr: StdioCollector { waitForEnd: true; onStreamFinished: {
      var message = String(text || "").trim()
      if (message) root.ghosttyStatus = message
    } }
    onExited: function(code) {
      root.ghosttyActionRunning = false
      if (code !== 0 && root.ghosttyStatus.indexOf("failed") < 0) root.ghosttyStatus = "Ghostty font action failed. See the plugin log for details."
    }
  }

  Process {
    id: mailFontProcess
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: {
      try {
        var result = JSON.parse(String(text || "{}"))
        if (result.transaction) root.mailFontStatus = "Applied " + result.font + " " + result.sizePt + " pt to Betterbird's General and HTML composition fonts. Restart Betterbird to see it."
        else if (result.rolledBack) root.mailFontStatus = "Restored the previous Betterbird font settings. Restart Betterbird to see them."
      } catch (e) {
        var message = String(text || "").trim()
        if (message) root.mailFontStatus = message
      }
    } }
    stderr: StdioCollector { waitForEnd: true; onStreamFinished: {
      var message = String(text || "").trim()
      if (message) root.mailFontStatus = message
    } }
    onRunningChanged: if (!running) root.mailFontActionRunning = false
  }

  Process {
    id: manualAppProcess
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: {
      try {
        var result = JSON.parse(String(text || "{}"))
        var details = (result.matches || []).map(function(app) {
          return "\n\n" + app.name + " (" + app.execCommand + ") — " + app.framework + " [" + app.review + "]\n"
            + (app.controlPoints || []).slice(0, 3).join("\n")
        }).join("")
        var packages = (result.packageMatches || []).map(function(item) { return item.name + " (" + item.source + ")" }).join(", ")
        if (packages) details += "\n\nInstalled matches without a desktop launcher: " + packages
        root.manualAppStatus = result.message + details
      } catch (e) {
        root.manualAppStatus = "Application lookup returned an unreadable result."
      }
    } }
    stderr: StdioCollector { waitForEnd: true; onStreamFinished: {
      var message = String(text || "").trim()
      if (message) root.manualAppStatus = message
    } }
    onRunningChanged: if (!running) root.manualAppActionRunning = false
  }

  Process {
    id: appearanceAuditProcess
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: root.adoptAppearanceAudit(text) }
    stderr: StdioCollector { waitForEnd: true; onStreamFinished: {
      var message = String(text || "").trim()
      if (message) root.appearanceAuditStatus = message
    } }
    onRunningChanged: if (!running) root.appearanceAuditRunning = false
  }
}
