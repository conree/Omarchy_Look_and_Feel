# Source of truth

The authoritative source and publication target is
`/home/si/Projects/Omarchy_Plugins/Look_and_Feel`, branch `main`, remote
`https://github.com/conree/Omarchy_Look_and_Feel.git`.
The owner's installed plugin at
`/home/si/.config/omarchy/plugins/si.omarchy-look-and-feel` is a symlink to this
repository. Other users receive their own plugin-manager checkout.

Git commits identify published source. [README.md](README.md) defines installation
and supported behavior; [PROJECT_STATUS.md](PROJECT_STATUS.md) records acceptance;
[RELEASE_VALIDATION.md](RELEASE_VALIDATION.md) records test scope and provenance.
The design brief contains owner requirements and explicitly dated history.
Handoffs record operational continuity and are not design authority.

The October 26 source adds separate application/terminal theme examples and
always-visible inline boot artwork to `Panel.qml`, removing preview buttons.
It also preloads examples and caches presentation data in `panel_preview_cache.py`,
with live readiness gates and bounded icon-lookup optimizations. These changes
are included in the current archive below; their validation is recorded in
`RELEASE_VALIDATION.md`. Version 0.2.0 also adds `boot_unlock.py` and the self-contained authenticated
`boot_unlock_helper.py`; desktop-setting writers retain their existing transactions.
The full-panel VM-tested runtime/test archive is
`c01b9ad40e7493a7990c3bb749c75e5de20d26e86b00cdcd6b8bb522459d1c43`
(61 files), with hashes in `Testing/Boot_VM_Lab/tools/finish-runtime-files.json`.
Boot acceptance is in `Testing/Boot_VM_Lab/results/finish-boot-acceptance.json`.
Application discovery and Qt manual-registration changes are included in that archive.
A later presentation-only change moves the terminal monospace checkbox below its
example. Only `Panel.qml` differs from that archive; current Git source and native
alignment evidence are authoritative for this refinement.

The October 25 EE Calc-inspired panel runtime/test archive contains 61 files:
`ea7774d1c2d4e853b90545b6a8cc9b17dd767d3d9207c9ba3763ef0fa9006ec3`.
Manifest: `Testing/Boot_VM_Lab/tools/design-release-runtime-files.json`.
It adds tabbed controls, previews, truthful current-theme and result state,
keyboard navigation, draft-preservation fixes and regressions. Backend appearance
writers remain unchanged. Earlier October 25 light/dark GUI evidence uses this archive;
earlier backend/sizing evidence is distinguished below and in the validation report.

The earlier October 25 Qt-safe runtime/test archive contains 57 files and has SHA-256
`d68c7bf132ec47801bbd8924f0cda7b30ef623a3105f32a0f2b7980ce87343ed`.
Its private manifest is `Testing/Boot_VM_Lab/tools/release-qt-safe-runtime-files.json`.
The rendered-size archive is
`6458b71d8f28e50fb2ba070c070a4bbd0d01dcf4595088149631278068bbf18b`.
Subsequent changes add reopening guidance, Fontconfig Undo ownership, native Qt
font validation/serialization, safe restore and activation guards. Non-Qt font
rendering paths are unchanged; native Qt metrics supplement the earlier matrix.
The preceding GUI archive is
`3cd67d0404fe267d66dabad01837179a9105342357a439791cdd89d2bd5b08a3`.
Earlier stock installer/login evidence used archive
`6e814d374623cd79b30542ced02da4e20bab6d068397aec58b891248856ccdbe`.
Use the validation report to distinguish those checks from final-runtime tests.

`Testing/` is ignored private VM evidence, images, keys, screenshots, baselines
and recovery material. It is not a release payload or alternate source tree.
Temporary preparation under `/tmp` is superseded by the reviewed repository
source after deployment. Do not substitute earlier October 24–25 attention
archives for this candidate.
