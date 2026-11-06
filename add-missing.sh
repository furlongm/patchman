#!/bin/bash
# add the patchman backlog items missed in the first pass (run once)
set -euo pipefail
cd "$(dirname "$0")/.."

mk() { bd create "$1" --type task --priority "$2" -d "$3" --json \
  | jq -r '.id'; }

COMMON='Rules: Marcus pushes and opens PRs himself; agents never push or open PRs.
Commits: lower-case message, no Co-authored-by trailer, one logical change each.
Repos: server ~/src/patchman, client ~/src/patchman/patchman-client.'

a=$(mk 'backport client shellcheck + dry-run cleanup to in-repo client' 3 \
"The in-repo bash client (patchman repo client/patchman-client) lacks
patchman-client commit 6156bc1 (shellcheck cleanup, e.g. SC2004 ~line 826)
and the dry-run fix (call cleanup before exit 0 when -y). Port both on a
branch off fresh origin/main; check against later in-repo branches
(port-apt-parsing-client, fix-in-repo-client) for overlap first.
$COMMON")
echo "ok $a"

b=$(mk 'NVD cveIds curl check (Marcus)' 3 \
"Marcus runs a curl against the NVD API to confirm the cveIds response
shape/error behaviour that branch fix-cve-fetch-errors ('skip cve data on
error responses instead of crashing') relies on, before pushing it.
$COMMON")
echo "ok $b"

c=$(mk 'develop lint cleanup' 4 \
"develop has pre-existing ruff/flake8/isort (django profile) failures.
Fix on a branch off fresh origin/develop, lint-only commits, no behaviour
change. Run full test suite.
$COMMON")
echo "ok $c"

e=$(mk 'delete merged/stale local branches' 4 \
"Content already merged; safe to delete locally (git branch -D), Marcus's call:
client: fix/tag-parsing (both commits in main via PR #4 and jq dep),
fix/runtime-lock-dir-v4 and runtime-lock-dir (in main via PR #3; also
origin/runtime-lock-dir). server: fix/tag-parsing, fix/zstd-unknown-content-size
(merged), wip + origin/wip (content in develop/main).
Side note: client main lists jq in both Depends/Requires and Recommends
(debian/control, patchman-client.spec) - redundant, could drop Recommends.
$COMMON")
echo "ok $e"

f=$(mk 'python client dnf check' 4 \
"Offered earlier: verify the python client's dnf (dnf4) update/repo
collection matches bash. Probably covered by the dnf5 work on
fix-client-parity (repoquery for updates + repos); confirm and close,
or fix with a test.
$COMMON")
echo "ok $f"

bd update patchman-yuh --append-notes \
"Second reporter: Andreas (Rocky 9 hosts showing el10 updates, e.g.
bind-libs 9.16.23-40.el9_8.13 -> 9.18.33-15.el10_2.2, marked Security).
An earlier diagnostic was given for him; his output is also pending." \
  >/dev/null && echo "ok patchman-yuh notes"

bd update patchman-5sf --append-notes \
"Before pushing fix-cve-fetch-errors (server) see NVD curl check bead." \
  >/dev/null && echo "ok patchman-5sf notes"
