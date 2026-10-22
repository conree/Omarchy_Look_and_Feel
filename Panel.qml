pragma ComponentBehavior: Bound

import QtQuick
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
  property string inventorySummary: "Loading the Omarchy appearance inventory…"
  property var applications: []
  property string transactionSummary: "Checking transaction history…"
  property string transactionError: ""
  property string transactionNotice: ""
  property string transactionAction: "status"
  property var transactions: []
  property bool transactionBusy: false

  function open() {
    root.controller.show()
    refreshInventory()
    refreshTransactions()
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

  function refreshTransactions() {
    runTransaction("status")
  }

  function runTransaction(action) {
    if (transactionBusy) return
    transactionBusy = true
    transactionError = ""
    if (action !== "status") transactionNotice = ""
    transactionAction = action
    transactionProcess.command = ["/usr/bin/python3", localPath(Qt.resolvedUrl("controller.py")), "transaction", action]
    transactionProcess.running = true
  }

  function adoptTransactionOutput(raw) {
    try {
      var data = JSON.parse(String(raw || "{}"))
      if (transactionAction === "status") {
        transactions = data.transactions || []
        var pending = transactions.filter(function(item) {
          return ["prepared", "applying", "rolling_back", "recovery_required"].indexOf(item.state) >= 0
        })
        transactionSummary = pending.length
          ? String(pending.length) + " interrupted transaction(s) need recovery."
          : String(transactions.length) + " transaction(s); no recovery is pending."
      } else if (transactionAction === "recover") {
        var recovered = data.recovered || []
        transactionNotice = recovered.length
          ? "Recovered transaction(s): " + recovered.join(", ")
          : "No interrupted transactions needed recovery."
      } else if (transactionAction === "rollback") {
        transactionNotice = "Reverted transaction " + String(data.rolledBack || "") + "."
      }
    } catch (e) {
      transactionError = "Could not read transaction status output."
    }
  }

  function pendingTransactionCount() {
    return transactions.filter(function(item) {
      return ["prepared", "applying", "rolling_back", "recovery_required"].indexOf(item.state) >= 0
    }).length
  }

  function committedTransactionCount() {
    return transactions.filter(function(item) { return item.state === "committed" }).length
  }

  function adoptInventory(raw) {
    try {
      var data = JSON.parse(String(raw || "{}"))
      applications = data.applications || []
      inventorySummary = "Catalogs found: "
        + String((data.catalogs && data.catalogs.themes || []).length) + " themes, "
        + String((data.catalogs && data.catalogs.fonts || []).length) + " font families, "
        + String((data.catalogs && data.catalogs.icons || []).length) + " icon themes, "
        + String((data.catalogs && data.catalogs.backgrounds || []).length) + " backgrounds. "
        + String(Object.values(data.catalog_review || {}).reduce(function(sum, item) { return sum + Number(item.selectable || 0) }, 0))
        + " entries are selectable after provenance and license review."
    } catch (e) {
      inventorySummary = "Could not read the appearance inventory. Open the plugin's diagnostic output for details."
      applications = []
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
    contentWidth: panel.fittedContentWidth(520)
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
            text: "Look & Feel"
            color: root.barForeground
            font.family: root.fontFamily
            font.pixelSize: Style.font.heading
            font.weight: Font.DemiBold
          }

          PanelSectionHeader { text: "APPLY AND RECOVERY" }

          Text {
            width: parent.width
            text: "Apply is unavailable until a reviewed application adapter is enabled. No application settings can be changed by this build."
            color: root.barForeground
            opacity: 0.78
            wrapMode: Text.WordWrap
            font.family: root.fontFamily
            font.pixelSize: Style.font.body
          }

          Row {
            width: parent.width
            spacing: 8
            Rectangle {
              width: 116; height: 34; radius: 5
              color: "#363636"; opacity: 0.55
              Text { anchors.centerIn: parent; text: "Apply (unavailable)"; color: root.barForeground; font.family: root.fontFamily; font.pixelSize: Style.font.small }
            }
            Rectangle {
              width: 130; height: 34; radius: 5
              color: root.pendingTransactionCount() > 0 && !root.transactionBusy ? Color.accent : "#363636"
              opacity: root.pendingTransactionCount() > 0 && !root.transactionBusy ? 1 : 0.55
              Text { anchors.centerIn: parent; text: "Recover interrupted"; color: root.barForeground; font.family: root.fontFamily; font.pixelSize: Style.font.small }
              MouseArea { anchors.fill: parent; enabled: root.pendingTransactionCount() > 0 && !root.transactionBusy; onClicked: root.runTransaction("recover") }
            }
            Rectangle {
              width: 112; height: 34; radius: 5
              color: root.committedTransactionCount() > 0 && !root.transactionBusy ? Color.accent : "#363636"
              opacity: root.committedTransactionCount() > 0 && !root.transactionBusy ? 1 : 0.55
              Text { anchors.centerIn: parent; text: "Revert last Apply"; color: root.barForeground; font.family: root.fontFamily; font.pixelSize: Style.font.small }
              MouseArea { anchors.fill: parent; enabled: root.committedTransactionCount() > 0 && !root.transactionBusy; onClicked: root.runTransaction("rollback") }
            }
          }

          Text {
            width: parent.width
            text: root.transactionError || (root.transactionNotice
              ? root.transactionSummary + "\n" + root.transactionNotice
              : root.transactionSummary)
            color: root.transactionError ? "#ff7777" : root.barForeground
            opacity: 0.82
            wrapMode: Text.WordWrap
            font.family: root.fontFamily
            font.pixelSize: Style.font.small
          }

          Text {
            width: parent.width
            text: "One Omarchy appearance authority. This first build inventories the available sources and priority applications; setting application is not enabled yet."
            color: root.barForeground
            opacity: 0.78
            wrapMode: Text.WordWrap
            font.family: root.fontFamily
            font.pixelSize: Style.font.body
          }

          PanelSectionHeader { text: "APPLICATION COVERAGE" }

          Repeater {
            model: root.applications
            delegate: Row {
              required property var modelData
              width: content.width
              spacing: 8
              Text {
                text: modelData.available ? "●" : "○"
                color: modelData.available ? Color.accent : root.barForeground
                opacity: modelData.available ? 1 : 0.55
                font.family: root.fontFamily
                font.pixelSize: Style.font.body
              }
              Text {
                text: modelData.name + (modelData.available ? " — found" : " — not installed")
                color: root.barForeground
                opacity: 0.85
                font.family: root.fontFamily
                font.pixelSize: Style.font.body
              }
            }
          }

          PanelSectionHeader { text: "SOURCE CATALOGS" }
          Text {
            width: parent.width
            text: root.inventorySummary
            color: root.barForeground
            opacity: 0.78
            wrapMode: Text.WordWrap
            font.family: root.fontFamily
            font.pixelSize: Style.font.body
          }

          Item { width: 1; height: 4 }
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
        root.inventorySummary = "Inventory scan failed (exit " + String(code) + ")."
        root.applications = []
      }
    }
  }

  Process {
    id: transactionProcess
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: root.adoptTransactionOutput(text)
    }
    stderr: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        if (String(text || "").trim()) root.transactionError = String(text).trim()
      }
    }
    onExited: function(code) {
      root.transactionBusy = false
      if (code !== 0) {
        if (!root.transactionError) root.transactionError = "Transaction " + root.transactionAction + " failed (exit " + String(code) + ")."
      } else if (root.transactionAction !== "status") {
        root.refreshTransactions()
      }
    }
  }
}
