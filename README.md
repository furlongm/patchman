# beads

Backlog for patchman and patchman-client, tracked with
[bd (beads)](https://github.com/steveyegge/beads). Not part of the
patchman source tree, like `gh-pages`.

- `issues.jsonl` - `bd export` of the local beads database
- `describe.sh`, `add-missing.sh` - scripts used to seed the issues
- `bundles/` - git bundles of unpushed branches, as a backup

Restore a branch from a bundle (needs origin/main and origin/develop):

    git fetch bundles/patchman.bundle 'refs/heads/*:refs/heads/*'

Re-import the issues into a fresh bd database:

    bd init --setup-exclude --skip-hooks --skip-agents --non-interactive
    bd import issues.jsonl
