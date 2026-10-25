pragma Singleton
import QtQuick
import qs.Commons

QtObject {
  id: root
  property var clients: []
  property string wantedFamily: ""

  // This component lives for the QML engine's lifetime. Neither its parent
  // nor its binding context belongs to an individual monitor's widget.
  property Binding fontBinding: Binding {
    target: Style
    property: "fontFamily"
    value: root.wantedFamily
    when: root.wantedFamily.length > 0
    restoreMode: Binding.RestoreBindingOrValue
  }

  function acquire(client) {
    if (clients.indexOf(client) < 0) clients.push(client)
    refresh()
  }

  function refresh() {
    var owner = clients.find(function(client) { return client.shellFontOwned && client.savedShellFont.length > 0 })
    wantedFamily = owner ? owner.savedShellFont : ""
  }

  function release(client) {
    clients = clients.filter(function(item) { return item !== client })
    refresh()
  }
}
