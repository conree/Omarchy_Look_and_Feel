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
  readonly property real selectorFontPointSize: Style.font.body * 0.99
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
  property string selectedLightThemeId: ""
  property string selectedDarkThemeId: ""
  property string selectedUnlockId: ""
  property string selectedUnlockPreview: ""
  property string selectedBackgroundId: ""
  property string selectedIconId: ""
  property bool inventoryLoaded: false

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

  function adoptInventory(raw) {
    try {
      var data = JSON.parse(String(raw || "{}"))
      var entries = data.catalog_entries || ({})
      fonts = entries.fonts || []
      themes = entries.themes || []
      unlockDesigns = entries.unlocks || []
      backgrounds = (entries.backgrounds || []).map(function(entry) {
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

      function idFor(records, name) {
        var entry = records.find(function(item) { return item.name === name })
        return entry ? entry.id : ""
      }

      if (!inventoryLoaded) {
        selectedSystemFontId = idFor(fonts, "Aileron")
        selectedTerminalFontId = idFor(fonts, "Office Code Pro")
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
                font.pointSize: root.selectorFontPointSize
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
                font.pointSize: root.selectorFontPointSize
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
                onActivated: function(index) { root.selectedTerminalFontId = root.fonts[index].id }
                font.pointSize: root.selectorFontPointSize
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
                onActivated: function(index) { root.selectedTerminalSize = root.fontSizes[index].id }
                font.pointSize: root.selectorFontPointSize
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
                font.pointSize: root.selectorFontPointSize
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
                font.pointSize: root.selectorFontPointSize
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
                font.pointSize: root.selectorFontPointSize
}
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
                font.pointSize: root.selectorFontPointSize
}
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
                font.pointSize: root.selectorFontPointSize
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
                font.pointSize: root.selectorFontPointSize
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
}
