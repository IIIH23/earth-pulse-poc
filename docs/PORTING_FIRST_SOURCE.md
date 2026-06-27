# Porting: First Logic Source

Selected source: repository audit / file inventory generator (audit/FILE_INVENTORY.md)

Rationale
- The audit/file-inventory is already a reproducible artifact that provides value (inventory of files, missing manifests).
- It is small, self-contained, and its inputs and outputs are well-defined — a safe first target to port into code.
- Porting it to a lightweight Python CLI improves reproducibility, enables programmatic use in CI, and removes manual steps taken by autopilot.

Scope (what to implement first)
- A small Python script (tools/inventory.py) that walks the repository and emits audit/FILE_INVENTORY.md in the same markdown shape.
- Minimal dependencies (stdlib only: os, pathlib, argparse, json, datetime).
- CLI flags: --root (path, default='.'), --depth (int), --exclude (glob), --out (path, default='audit/FILE_INVENTORY.md').

Inputs
- root path (repository root) — files and directories to inspect.
- depth (how deep to recurse).
- exclude patterns (e.g. .git, node_modules).

Outputs
- Markdown file: audit/FILE_INVENTORY.md containing a summary (file counts, notable missing dev files) and file listing.
- Exit code 0 on success; non-zero on unexpected IO errors.

Verification
- Run tests/smoke_test.sh to ensure repository invariants still hold.
- Add a unit smoke script later that runs tools/inventory.py and diffs a golden output for a small test-tree.

Next steps
1. Implement tools/inventory.py (small, stdlib-only script).
2. Add a unit-style smoke test under tests/ that invokes the script on a small fixture.
3. Wire the script into .github/workflows/smoke.yml to run in CI.

Notes
- This change is a documentation specification only for the current autonomous cycle. Implementation will follow in a subsequent cycle and will use Codex CLI with sandbox workspace-write per project policy.
