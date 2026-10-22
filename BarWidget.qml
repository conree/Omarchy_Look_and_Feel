import QtQuick
import qs.Commons
import qs.Ui

BarWidget {
  id: root
  moduleName: "si.omarchy-look-and-feel"

  readonly property bool opened: panelLoader.item ? panelLoader.item.opened === true : false
  property bool openRequested: false

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
    active: false
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
    text: "Aa"
    labelVisible: true
    hasVisualContent: true
    horizontalMargin: 8.75
    verticalPadding: 8.75
    tooltipText: "Look & Feel"
    onPressed: function(buttonCode) {
      if (buttonCode === Qt.LeftButton) root.togglePanel()
    }
  }
}
