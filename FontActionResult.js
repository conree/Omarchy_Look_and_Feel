// Consume stdout, stderr and exit status together, regardless of arrival order.
function evaluate(stdoutText, stderrText, exitCode) {
  if (exitCode !== 0) {
    var detail = String(stderrText || "").trim().replace(/\u001b\[[0-9;]*m/g, "")
    detail = detail.split("\n").filter(function(line) { return line.trim() !== "" }).pop() || ""
    detail = detail.replace(/\/(?:[^\s:;,]+)/g, "[settings path]").substring(0, 600)
    return { success: false, message: detail || "The font command failed (exit " + exitCode + ")." }
  }
  var result
  try { result = JSON.parse(String(stdoutText || "")) }
  catch (e) { return { success: false, message: "The font command returned an unreadable result." } }
  if (!result || typeof result !== "object")
    return { success: false, message: "The font command returned no verified transaction." }
  if (result.blocked)
    return { success: false, message: "Font Apply stopped: " + Number(result.unsupportedManualCount || 0)
      + " manually audited control surface(s) lack a verified reversible adapter. Re-audit with a specific entry or clear the manual audit registry." }
  var pending = result.pendingApplications || []
  var fontNotes = Array.isArray(result.fontNotes) ? result.fontNotes.filter(function(note) {
    return typeof note === "string"
  }) : []
  var information = fontNotes.length ? " " + fontNotes.join(" ") : ""
  var reload = result.terminalReload || { requested: [], failed: [] }
  var reloadNote = (reload.requested || []).length
    ? " Reload requested for " + reload.requested.length + " running terminal type(s)." : ""
  if ((reload.failed || []).length) reloadNote += " Some terminal reloads failed; reload those terminals manually."
  var pendingNote = pending.length ? " Pending: " + pending.map(function(item) {
    return item.app + ": " + item.reason
  }).join(" ") : ""
  if (typeof result.transaction === "string" && result.transaction)
    return { success: true, undoAvailable: true,
      needsAction: pending.length > 0 || (reload.failed || []).length > 0,
      message: "Font settings saved and checked in " + Number(result.targetCount || 0) + " configuration files"
        + (result.desktopFontsVerified ? " and the active desktop font settings." : ".")
        + reloadNote + pendingNote + information + " Individual applications' rendered fonts are not automatically verified. Reopen applications that retain the previous font." }
  if (typeof result.rolledBack === "string" && result.rolledBack)
    return { success: true, undoAvailable: false, refreshInventory: true,
      needsAction: (reload.failed || []).length > 0,
      message: "Previous font settings restored." + reloadNote + " Reopen applications that do not reload fonts automatically." }
  return { success: false, message: "The font command returned no verified transaction." }
}
