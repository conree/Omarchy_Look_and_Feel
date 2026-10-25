# Source of truth

The authoritative working source is this Git repository:
`/home/si/Projects/Omarchy_Plugins/Look_and_Feel`.
The installed plugin is a symlink to this directory. Git commits identify
published source; README describes behavior and PROJECT_STATUS records state.
Handoffs are historical records, not alternate implementations.

Functional source in the October 24–25 validation is tied to local manifest
`Testing/Boot_VM_Lab/tools/attention-candidate-files.json` and archive SHA-256
`b9a35c8de98c2f7cac0fd53c1e2685f4c032ac2cfa562241ce506b02f27b0041`.
The archive also contains a headless-browser Typora CSS experiment excluded
from the final validation run and subsequently quarantined outside the source
tests; that experiment is not published.

`Testing/` contains ignored private VM evidence, snapshots, experiments and
recovery material. It is not a second editable source tree or a release payload.
Temporary staging directories under `/tmp` are superseded after deployment.
Reusable regression tests are in `tests/`. VM procedures are in local
`Testing/Boot_VM_Lab/tools`, separate from `Testing/Boot_VM_Lab/results`.
