#!/bin/bash
# add the 2026-11-17 backlog items: parity branches, ebuilds, reboot
# detection, #881 follow-ups (run once)
set -euo pipefail
cd "$(dirname "$0")/.."

mk() { bd create "$1" --type task --priority "$2" -d "$3" --json \
  | jq -r '.id'; }

COMMON='Rules: Marcus pushes and opens PRs himself; agents never push or open PRs.
Commits: lower-case message, no Co-authored-by trailer, one logical change each.
Target: main only (becomes stable-4.0); anything on main needs no develop port.
Repos: server ~/src/patchman, client ~/src/patchman/patchman-client.
Missing branches: restore from bundles/ on the beads branch.'

PC='patchman-client branch off origin/main 9a668e9, one commit. Tests:
python3 -m unittest discover -s tests -t . ; go only verified against
stub modules (lib/si TestGetOSInfo fails pre-existing), run go test ./...
for real before pushing.'

# policy change: no develop ports
bd close patchman-qkg patchman-xym \
  --reason 'main-only; main becomes stable-4.0, no develop ports'

m4=$(mk 'push fix-go-report-retries (parity M4)' 2 \
"Branch fix-go-report-retries @ 7aaeb82 'post the go client report once
without retries'. Go client no longer retries the POST (retries after a
server-side timeout created duplicate reports); timeout 30s -> 300s to
match python. Bash half of M4 is on fix-client-parity.
$PC
$COMMON")
echo "ok $m4"

m5=$(mk 'push fix-python-yum-repo-names (parity M5)' 2 \
"Branch fix-python-yum-repo-names @ 8adc3af 'collect python yum repos the
same way as the bash client': names always get arch appended, priorities
via real \$releasever, baseurl parsing copied from the bash awk, file://
and ftp:// urls now sent. On merge with fix-client-parity,
test_dnf5_repo_info (8fe96f4) breaks (mock rejects the new rpm call,
expects trailing slashes) and must be updated. Go still keeps trailing
slashes and matches priorities by id (not fixed).
$PC
$COMMON")
echo "ok $m5"

m6=$(mk 'push fix-go-repo-naming (parity M6)' 2 \
"Branch fix-go-repo-naming @ 543f5de 'name apt, zypper and arch repos in
the go client like bash'. apt: one repo per mirror, bash naming; zypper:
PRETTY_NAME naming; pacman: no 10-mirror cap, 'Arch Linux <repo> <arch>'.
CONFLICT with M9: this leaves \$arch empty (bash eval behaviour) while
fix-pacman-mirror-expansion expands \$arch to the machine arch in all
clients. Proposed: keep M9 and drop/adjust M6's pacman url expansion.
Needs b9534fe (fix-client-parity) for arch repos in protocol 2.
$PC
$COMMON")
echo "ok $m6"

m7=$(mk 'push fix-update-gating (parity M7)' 2 \
"Branch fix-update-gating @ a7148f2 'gate update collection in the python
and go clients as bash does': yum/zypper updates only with repos (no -n)
and -u or CDN/updates.suse.com match; apt only with -u; python runs yum
makecache. Trivial conflict with fix-client-parity in go/cmd/submit.go
(GetDNFUpdates line). Gap left: python/go still query all repos instead
of --disablerepo=* --enablerepo=<matched>.
$PC
$COMMON")
echo "ok $m7"

m9=$(mk 'push fix-pacman-mirror-expansion (parity M9)' 2 \
"Branch fix-pacman-mirror-expansion @ 7fee494 'expand \$repo and \$arch in
pacman server urls in all clients'. Bash dropped \$arch and sent '' for
#Server lines; python skipped mirrorlist expansion; go never expanded.
See M6 bead for the \$arch conflict. Small textual conflict with M6 in
GetPacmanRepos.
$PC
$COMMON")
echo "ok $m9"

m10=$(mk 'push fix-tags-default (parity M10)' 3 \
"Branch fix-tags-default @ f8435ff 'send no tags when tags is Default in
the python and go clients'. Matches bash: unset/''/Default -> []. Expect
a test-file conflict in tests/test_client_output.py with
fix-client-parity (no behaviour conflict).
$PC
$COMMON")
echo "ok $m10"

m11=$(mk 'push fix-python-cpe-suffix (parity M11)' 3 \
"Branch fix-python-cpe-suffix @ 7d4eafa 'append the cpe name to the os
string for every distro in the python client'. Edit is inside
_detect_os; check fix-client-parity python _detect_os overlap on merge.
Gap left: python rocky/almalinux branch sends PRETTY_NAME, bash sends
NAME VERSION.
$PC
$COMMON")
echo "ok $m11"

m12=$(mk 'decide parity M1/M2 (user-visible defaults + cli)' 4 \
"Deferred: M1 defaults differ (bash protocol 1 + --insecure vs python/go
protocol 2 + TLS verify); M2 cli option differences. User-visible, needs
a decision before changing. See client-parity-audit for detail.
$COMMON")
echo "ok $m12"

eb1=$(mk 'review gentoo ebuild for patchman-client' 3 \
"patchman-client branch add-gentoo-ebuild @ c20d1e8: gentoo/app-admin/
patchman-client/{-9999,-4.0.20 symlink,metadata.xml}, README section.
Installs bash client as /usr/sbin/patchman-client, conf, systemd units,
portage hook under /usr/share (user sources it from /etc/portage/bashrc).
Unverified: no emerge/pkgcheck/Manifest. Needs a real gentoo box.
$COMMON")
echo "ok $eb1"

eb2=$(mk 'review gentoo ebuild for patchman server' 3 \
"patchman branch add-gentoo-ebuild @ 1ec796c4: gentoo/www-apps/patchman/
{-9999,-4.0.22 symlink,metadata.xml}, INSTALL.md section. Blocker: not in
::gentoo: celery, django-celery-beat, django-extensions,
django-bootstrap3, djangorestframework-api-key, django-select2, cvss.
::gentoo only has django >=5.2 (patchman pins 4.2). Also v4.0.22 tag has
VERSION.txt 4.0.21 (ebuild patches it). Unverified: no emerge/pkgcheck.
$COMMON")
echo "ok $eb2"

svc=$(mk 'fix patchman-client.service /usr/bin path' 3 \
"patchman-client.service runs /usr/bin/patchman-client submit but every
package installs the client in /usr/sbin. Affects all distros. Found by
the client ebuild agent; not fixed.
$COMMON")
echo "ok $svc"

rb=$(mk 'push reboot detection fixes (PR 877 superseded)' 2 \
"PR 877 (bash dnf needs-restarting) is incomplete. Replacements:
- patchman fix-reboot-detection @ 8ab3e97e (in-repo bash client)
- patchman-client fix-reboot-detection @ 79aef86 (bash, python, go)
Both: dnf -C needs-restarting -r (rc0 False; rc1+'Reboot is required'
True), EL7 needs-restarting -r fallback, zypper needs-rebooting (102),
basename on /boot/vmlinuz readlink. Server half: keep-client-reboot-required
@ 3cae9fa9 (server wiped client True). Reply on PR 877 explaining.
Unverified on real dnf5/EL7/SUSE (stubs only).
$COMMON")
echo "ok $rb"

dup=$(mk 'fix MirrorPackage duplicate rows' 2 \
"reports/utils.py process_update does a blind MirrorPackage create on
every mirror of the repo for every client-reported update, every run,
every host, every -P reprocess; no unique constraint (849 dup pairs in
#881 diag). Also Repository.get(repo_id) can raise uncaught
MultipleObjectsReturned. Fix on a branch off origin/main: get_or_create,
OS-matching mirrors only, dedupe migration, UniqueConstraint(mirror,
package). fix-client-update-repo-lookup (develop-based, on hold) has
related work; redo off main if still wanted.
$COMMON")
echo "ok $dup"

key=$(mk 'normalized repo key (OS major + yum id)' 3 \
"Follow-up to #881 minimal fix (fix-repo-merge-by-name @ 3dbcc65d, which
splits same-named repos with different repo_id into 'name (repo_id)').
Better: key repos by OS major + yum id so RHEL 9 and Rocky 9 on different
urls don't split, and repo_id stops flapping (last writer wins). Main.
$COMMON")
echo "ok $key"

bd dep add "$dup" patchman-yuh
bd dep add "$key" patchman-yuh
