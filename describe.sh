#!/bin/bash
# add self-contained descriptions to the backlog beads (run once)
set -euo pipefail
cd "$(dirname "$0")/.."

d() { bd update "$1" --description "$2" >/dev/null && echo "ok $1"; }

COMMON='Rules: Marcus pushes and opens PRs himself; agents never push or open PRs.
Commits: lower-case message, no Co-authored-by trailer, one logical change each.
Repos: server ~/src/patchman (github furlongm/patchman), client
~/src/patchman/patchman-client (submodule, github furlongm/patchman-client).
Server lint: ruff, flake8 --max-line-length=120, isort --profile=django.
Local origin/* may be stale; fetch before trusting ahead/behind counts.
If a branch is missing locally, restore it from the git bundles in
~/src/patchman/.beads/bundles/ (needs origin/main + origin/develop fetched):
  git fetch .beads/bundles/patchman.bundle "refs/heads/*:refs/heads/*"
  (client: git -C patchman-client fetch ../.beads/bundles/patchman-client.bundle ...)'

d patchman-03x "Review branch gentoo-slot-field before it goes up as a PR.
Worktree ~/src/pm-slot, based on develop (not main). 6 commits:
7041de34 add slot field to packages for gentoo
6238ad91 store gentoo slot from reports in the slot field
c6425cc1 fix invalid plen argument to info_message in gentoo ingest
d0c84b41 read gentoo slots when ingesting repos
0a189bd8 match gentoo updates within the same slot
c620284a show gentoo slots in the ui and api
Design: report epoch carries SLOT for gentoo (old clients stay compatible);
repo ingest reads SLOT from md5-cache. Known caveats to check: overlays have
no md5-cache, variable SLOTs, sub-slot stripping, whether qlist %{SLOT}
includes the sub-slot. Check migration + data migration, serializer, tables,
update matching (pu_q). Run full develop test suite + lint.
$COMMON"

d patchman-5sf "Marcus pushes these server branches (all unpushed, local only):
off current origin/main: keep-client-updates, match-existing-non-http-mirrors,
fix-cve-fetch-errors, port-apt-parsing-client, fix-in-repo-client (worktree
~/src/pm-climod: %2b decode + dnf5 repos/updates in in-repo bash client),
accept-non-http-repo-urls (worktree ~/src/pm-rsync: gentoo rsync:// repo urls
400'd in protocol 2).
off STALE origin/main (rebase onto main first): fix-force-reprocess (-P option,
3 commits), fix-debian-sid-os, keep-client-reboot-required.
Already pushed but unmerged: fix-moving-mirrorlists (#858), fix-errata-dates,
fix-apt-mirror-slash, fix-host-update-counts, fix-all-errata, fix-tag-parsing,
zstd-fix, tagging-cleanup, 839-migrations (some may be squash-merged already).
$COMMON"

d patchman-cx0 "Marcus pushes the patchman-client branches (all off origin/main, unpushed):
fix-client-parity (worktree ~/src/pmc-parity, 25 commits: go client parity
fixes, %2b, gentoo r0, dnf5 repoquery updates + repos, zypper token strip,
conf.d sourcing, hooks -n, http exit codes), fix-lock-and-unit,
fix-apt-parsing-consistency, fix-gentoo-repo-consistency.
Expect test-file merge conflicts (tests/test_client_output.py) between apt,
gentoo and parity branches.
Before PR: go test ./... (go was only checked against local stubs, no module
download available), shellcheck bash/patchman-client, a real dnf5 host test.
$COMMON"

d patchman-yuh "Issue #881: RHEL9 hosts offered el10 updates after v4.0.22.
Trigger: v4.0.22 commit f870d654 fixed zstd multi-frame decoding, so el10 zstd
metadata/updateinfo is ingested fully for the first time. HOW el10 packages
reach el9 hosts is still unknown (repo ids are CPE-prefixed so no collision).
Waiting on nicehomerguy to run the read-only diagnostic (diag881.py, posted
as a heredoc to patchman-manage shell). Analyse its sections: HOSTREPO/MIRROR
el10 counts, EL10 PACKAGES REACHABLE, EL9->EL10 UPDATES, DUPLICATE
MIRRORPACKAGES, MIRRORS WITH EL10, REPORT flags.
Then decide branch fix-client-update-repo-lookup (worktree ~/src/pm-updrepo,
ca274f1b + 18e7b9c1, off develop): its MultipleObjectsReturned rationale was
refuted; keep only a get_or_create dedupe IF duplicate MirrorPackage rows are
proven, else drop it.
Side finding (not #881): bogus bind-libs 2: epochs come from Rocky Apollo
updateinfo (NEVRA_RE (\\d)+ bug); fixed upstream via resf/distro-tools PR
(branch fix-nevra-multidigit-epoch). No patchman change needed.
$COMMON"

d patchman-xym "Rebase fix-force-reprocess-develop (develop port of the -P option).
Only the top 3 commits are ours: 66f521a9 allow forced reprocessing,
67f907d5 never process older reports unless forced, 687bd3e7 add -P option.
The other 9 are pre-rebase develop duplicates (develop was rebased onto main).
Command: git rebase --onto develop 6524532e fix-force-reprocess-develop
Watch sbin/patchman vs management commands (main added -a errata, tags);
use patchman.* namespaced imports. Add --report <id> to
patchman/management/commands/process_reports.py with a test. Lint + full suite.
$COMMON"

d patchman-qkg "Port main-only fixes to develop (develop uses patchman.* app namespace):
#864 rpm reboot check outside the repo gate, #858 moving mirrorlists
(fix-moving-mirrorlists), apt mirror trailing-slash fix (fix-apt-mirror-slash),
errata dates fallback (fix-errata-dates), -P option (see patchman-xym).
Do each on its own branch off fresh origin/develop; lint + full suite.
$COMMON"

d patchman-slg "Fix remaining client parity audit items (bash vs python vs go clients).
Repo patchman-client; HIGH items already fixed on fix-client-parity.
Open MEDIUM (do M4 + M6 first, they create duplicate server data):
M1 defaults differ (bash protocol 1 + --insecure; py/go protocol 2 + TLS;
   py ignores protocol/hostname/curl_options keys)
M2 CLI: -h hostname vs help; -r bash only; go -d not verbose; go example.com
   check even with -y; go always prints success
M4 go 30s timeout + 3 retries -> duplicate reports
M5 py yum repo names differ (arch suffix); \$releasever -> '' breaks priorities
M6 go repo naming (zypper/pacman/apt) differs -> duplicate repos; pacman
   capped at 10 mirrors
M7 update gating differs (-n, CDN auto-enable, makecache, wrapped yum lines)
M9 pacman mirror var expansion (\$arch unset in bash, #Server lines)
M10 tags 'Default' handling differs
M11 py CPE suffix only for rpm distros
Unsure: py zypper -s11 split; go apt security detection; getfqdn vs hostname -f.
Each fix: test that fails before, one commit per logical change.
$COMMON"

d patchman-i0z "Issue replies owed:
#866 (client lock under hardened systemd unit): reply after Marcus tests on a
SELinux VM. #836 and #877: replies pending, re-read threads first.
$COMMON"

d patchman-777 "Triage untriaged issues on furlongm/patchman:
#861 #862 #863 #851 #852 #841 #838. Also previously offered, not accepted:
#842 kernel fallback hardening, #867 dedupe migration + non-null
epoch/release, #847 analysis, #810 ask cpoppema to rebase onto develop,
#872 ask mgedmin to test on Postgres.
$COMMON"

d patchman-p7f "Remove git worktrees once their branches are pushed/reviewed:
server (git -C ~/src/patchman worktree remove ...): ~/src/pm-climod,
~/src/pm-rsync, ~/src/pm-slot, ~/src/pm-updrepo; client
(git -C ~/src/patchman/patchman-client worktree remove ...): ~/src/pmc-parity.
Then git worktree prune. Branches stay. Blocked by 03x, 5sf, cx0.
$COMMON"
