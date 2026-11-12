# Security Vetting Record

**What this is:** a record of how the third-party components this kit installs were vetted, what was found, and what remains unverified. It is evidence, not a guarantee. A static review proves what was true for the versions reviewed on the review date; it cannot prove future versions are safe. Re-vet on every version bump.

**Review date:** 2026-11-03
**Reviewed by:** ai-efficiency-kit maintainers (static, read-only review).

> **Corporate / organization users:** this review is the maintainers' own due diligence, not a substitute for your organization's. Check with your internal security or IT office before using these tools, and follow their guidance and your software/licensing/data-handling policies, which take precedence over this record.

## Scope

Vetted: the third-party skills, agent-instruction payloads, MCP servers, CLI tools, and install scripts that `install.py` / `install-unix` / `install-windows.ps1` pull in. **Not** vetted here: mainstream OS packages from official distro repos / Homebrew / WinGet (git, ripgrep, fd, jq, bat, fzf, ctags, etc.) — these come from trusted, signed distribution channels and are out of scope.

## Method

Vetting is layered because no single step is sufficient — automated scanners are bypassable (Trail of Bits bypassed the major skill scanners; Snyk's *ToxicSkills* study found prompt injection in 36% of agent skills), and human reading alone misses obfuscation. Each component was put through the layers that apply to it:

1. **Prompt-injection / instruction review (prose surface).** Every `SKILL.md` and referenced doc is read as *instructions the agent will obey*. Checked for: reading secrets/env, data exfiltration, network calls, modifying agent config/permissions/hooks, "ignore previous instructions" framing, deception, disabling verification/auto-approving destructive actions. Obfuscation swept for: zero-width/bidi chars, base64/hex blobs, absurd line widths (`grep -rnaE 'https?://|base64|[A-Za-z0-9+/]{120,}'`, `wc -L`).
2. **Code / install-script review (executable surface).** Installer JS, shell scripts, and the hooks they register are read in full. Danger grep for `curl|wget|nc|base64 -d|eval|exec|os.system|subprocess|child_process|fetch|rm -rf|chmod|crontab|>> ~/.bashrc|id_rsa|.ssh|AWS_|SECRET|TOKEN|postinstall`. Every network endpoint and the data it sends was enumerated; every hook's trigger→command recorded; integrity controls (checksums/signatures) verified.
3. **Provenance / supply chain.** Canonical source repo + publisher confirmed (typosquat check), distribution channel, version pinning, maintenance signal, known CVEs/advisories, runtime privilege.
4. **Automated gate (implemented — see "Automated gate" below).** `vet-skills` runs a shipped-skill installer check, a secrets scan, Semgrep on bundled scripts + the installer, and Snyk Agent Scan (when `SNYK_TOKEN` is set); `.github/workflows/vet.yml` runs it on every push/PR. Plus version-pinned installs.

**Verdict legend:** `benign` · `benign-with-notes` (safe, but has disclosed behavior worth awareness) · `needs-attention` (eyeball before unsupervised use) · `low-signal` (obscure/solo-maintainer; code reviewable but low external trust) · `cannot-verify`.

---

## Information sources used for vetting

Verdicts are built from these sources. None is trusted alone — scanners are bypassable and registry scores miss obfuscation (documented below), so they cross-check each other and feed the human review.

- **Package registries** — PyPI JSON API (`pypi.org/pypi/<pkg>/json`) and the npm registry (`registry.npmjs.org/<pkg>`) for current versions, maintainers, and release dates.
- **PyPI provenance attestations** — GitHub Actions/sigstore attestations shown on a package's PyPI "Provenance" panel, used to tie a published artifact to a specific source repo + workflow (e.g. headroom-ai → `headroomlabs-ai/headroom`).
- **GitHub REST API** — `/repos/<owner>/<repo>` for SPDX license (`.license.spdx_id`), stars/activity as a maintenance signal, and `/releases/latest` for release tags; raw `LICENSE`/`COPYING` files when the SPDX id is `NOASSERTION`.
- **Published CVE / advisory records** — for known vulnerabilities and their fixed-in versions (e.g. repomix CVE-2026-49987, serena CVE-2026-109965).
- **winget-pkgs manifests** — `github.com/microsoft/winget-pkgs/manifests/...` to confirm a WinGet package ID exists.
- **Vendor security research** — Invariant Labs tool-poisoning research, Snyk *ToxicSkills* study, Trail of Bits scanner-bypass findings, Cloud Security Alliance notes. These establish the threat model and the **limits** of automated scanning.
- **Skill-registry security scores** — Gen / Socket / Snyk passes shown on skills.sh, treated as a hint, not a verdict (they produced the token-saviour false-positive and have documented bypasses).
- **Automated scanners** — Semgrep (`--config auto`) on scripts; Snyk Agent Scan (`snyk-agent-scan`) on skills + MCP configs when a token is present.
- **First-hand source reading** — the actual `SKILL.md`, bundled scripts, installer code, and hooks on disk, plus targeted danger greps. This is the primary evidence; the above corroborate it.

Everything captured from these sources on the review date is recorded in the [Evidence appendix](#evidence-appendix-captured-2026-11-03), with the exact commands to reproduce it.

## Findings: skills & instruction payloads (prose surface)

| Component | Source | Verdict | Notes |
|---|---|---|---|
| caveman | JuliusBrussee/caveman | benign | Output-style skill. Drops to plain prose for security warnings & irreversible actions; preserves code/commands verbatim. No tool/network/config instruction. |
| context-canary | JuliusBrussee/skills | benign | Writes a local HANDOFF/notes checkpoint file only. URLs are research citations, not fetch instructions. |
| loop-factory | JuliusBrussee/skills | benign-with-notes | Can install a third-party CLI, optionally copy `.claude`/`.codex` hooks+settings into a repo, and set up unattended cron — **all opt-in and disclosed**. Strong safety posture (never archive without human acceptance; never weaken criteria). |
| ponytail | DietrichGebert/ponytail | benign | Code-minimalism skill. Explicitly never cuts validation/error-handling/security/accessibility. Reinforces verification. |
| token-saviour | **kit-vetted fork** of vagkaratzas/token-saviour (ships in `skills/token-saviour/`) | benign (rewritten) | Upstream was `needs-attention` (registry High/Critical — signature false-positive from `curl\|bash` / `irm\|iex` install lines + hook/MCP auto-wire references, all approval-gated). **Rewritten 2026-11-03:** every network-install one-liner and hook/MCP auto-wiring step removed from `references/tool_links.md`; routing guide + benchmark kept verbatim. The installer now ships this local copy instead of pulling upstream (`install.py`). |
| Benjamin-Plus | JetBrains/benjamin-plus-skill | benign | `injected-instruction.md` is a lookup-efficiency ruleset; insists efficiency never outranks correctness. Its `hooks/sessionstart.sh` only `cat`s that vetted markdown to re-inject it after /clear and /compact — reads/sends nothing else. |

No malicious prompt-injection, obfuscation, secret access, or exfiltration found in any skill.

### Plain-language note: what was wrong with token-saviour

token-saviour itself was not malicious — the danger was the *install instructions* it taught the agent. To add its helper tools, it told the agent to run commands like "download this script from a web address and run it immediately" (`curl … | bash`) and to switch on auto-running "hooks." The problem: whatever sits at that web address runs on your computer with your full permissions, and you never see it first. If that page is ever hijacked, swapped, or the link mistyped, you execute someone else's code. That is a classic way machines get compromised.

So it was teaching a risky habit, not hiding an attack. Security scanners flagged it High/Critical because `curl … | bash` and auto-hook patterns are exactly what malware install steps look like — a scanner cannot tell a careful use from a hostile one.

The fix: our rewritten copy installs the same tools the safe way — through package managers (`brew`, `npm`, `uv`, `cargo`) that fetch verified, signed packages — and never pipes a web script straight into a shell. Same benefit, no risky habit.

## Findings: executable & install surface

| Component | Verdict | Evidence |
|---|---|---|
| caveman installer (`installer/install.js`, install.sh/ps1, hooks) | benign-with-notes | Pinned `PINNED_REF='v4.0.1'`. Hook downloads are SHA-256-checked against a manifest and atomically applied only on full match (aborts otherwise). Optional Go MCP binaries are sigstore-signature-verified. No exfil, no obfuscation, no dotfile/crontab writes. **Notes:** checksum manifest is fetched from the same host as the payload (TOFU — a raw.githubusercontent compromise defeats it); env `CAVEMAN_REF` can repoint the pin; downloader follows redirects but content stays checksum-gated. |
| `rtk-install.sh` | benign-with-notes | Downloads tarball from `github.com/rtk-ai/rtk` releases, SHA-256-verifies against `checksums.txt`, path-traversal guard before extraction. No pipe-to-shell, no eval. **Notes:** checksums come from the same release (TOFU, no independent signature); `RTK_SKIP_CHECKSUM=1` disables verification; `set -e` only (no `set -u`). |
| `~/.claude/settings.json` hooks | benign | All four hook commands invoke the local `jdocmunch-mcp` binary with static args on Read/Edit/Write/PreCompact/SessionStart. No network, no shell interpolation. |
| `~/.cursor/hooks.json` | benign | Single `sklab _track-invocation` skill-tracking hook (local, fixed arg). |

## Findings: MCP servers & CLI packages (provenance)

| Package | Source | Verdict | Key finding / required action |
|---|---|---|---|
| serena-agent | oraios/serena (PyPI) | established / low-risk | **CVE-2026-109965** path traversal, fixed 2.0.0 → **pin ≥2.0.0**; never open an untrusted repo with it. |
| repomix | yamadashy/repomix (npm) | established / low-risk **only if pinned** | **CVE-2026-49987 (8.8, RCE via `--remote-branch`)**, CVE-2026-49988, CVE-2026-59702 (SSRF). Fixed ≥1.14.1 → **pin ≥1.14.1**. |
| @ast-grep/cli | ast-grep/ast-grep (npm) | established / low-risk | Popular, scoped org. Pin for reproducibility. |
| tree-sitter-cli | tree-sitter/tree-sitter (npm) | established / low-risk | Official org. Generating a parser compiles native C (expected). |
| jcodemunch-mcp | jgravelle/jcodemunch-mcp (PyPI) | low-signal / verify | Solo maintainer; odd license (forbids registry republish yet ships on PyPI); default anonymous "savings counter" phone-home (disableable). Reviewable on GitHub; pin. |
| jdocmunch-mcp | jgravelle/jdocmunch-mcp (PyPI) | low-signal / verify | Solo maintainer (sibling of above). Reviewable; pin. |
| roam-code | Cranot/roam-code (PyPI) | low-signal / verify | Obscure but Apache-2.0, clean privacy claims, `mutate` defaults to `--dry-run`. Best posture of the obscure group. Pin. |
| context-mode | mksglu/context-mode (npm) | low-signal / verify | Obscure, solo maintainer; runs agent commands in isolated subprocesses (executes commands as user). Not a network proxy. Reviewable; pin. |
| headroom-ai[proxy,mcp] | headroomlabs-ai/headroom (PyPI) | low-signal / provenance-resolved | **Provenance resolved 2026-11-03:** the PyPI artifact carries a GitHub Actions provenance attestation (PyPI-verified 2026-10-26) pointing to the `headroomlabs-ai/headroom` release workflow — cryptographic proof of source. The similarly-named `chopratejas/headroom` and `MindTouch/headroom-ai` repos are copies; the published package attests to headroomlabs-ai. **Still the highest runtime privilege in the kit** — its proxy sits in-path for OpenAI/Anthropic-compatible traffic and can see every prompt, completion, and API key. Treat as a credential-handling component; the installer installs but does **not** auto-enable the proxy. Pin a version as part of the kit-wide pinning work. |
| rtk | rtk-ai/rtk | low-signal / verify | Established-ish Rust binary, but the **Linux install is `curl … /master | sh`** (mutable branch, no release pin) — weakest delivery path. Pin a release tag + checksum instead of `master`. |

---

## Open action items (from this review)

Ordered by priority. None applied yet — tracked here for decision.

1. ~~Resolve `headroom-ai` provenance~~ **DONE 2026-11-03** — canonical source confirmed via PyPI GitHub-Actions provenance attestation (`headroomlabs-ai/headroom`). Kept, not dropped. Residual: highest runtime privilege (proxy sees LLM traffic + keys) — do not auto-enable the proxy; pin a version under item 2.
2. ~~Pin everything.~~ **DONE 2026-11-03.** All installed packages are pinned to reviewed versions in `install.py`: `serena-agent==2.1.0` (CVE-2026-109965), `repomix@1.18.1` (CVE-2026-49987, always-installed so an older local copy is upgraded), `jcodemunch-mcp==1.108.411`, `jdocmunch-mcp==1.150.1`, `roam-code==14.1.0`, `headroom-ai[proxy,mcp]==0.42.0`, `@ast-grep/cli@0.51.1`, `tree-sitter-cli@0.27.1`, `context-mode@1.0.169`. Re-vet and bump on update.
3. ~~Pin RTK's Linux install~~ **DONE 2026-11-03.** The installer script is now fetched from tag `v1.1.0` (not `master`) and runs with `RTK_VERSION=v1.1.0`; the script already SHA-256-verifies the binary. winget ID `rtk-ai.rtk` confirmed valid (manifests exist in winget-pkgs). (winget/brew left at channel-latest — signed channels, lower risk.)
4. ~~Human-review `token-saviour`~~ **DONE 2026-11-03** — replaced with a kit-vetted sanitized fork (`skills/token-saviour/`); installer no longer pulls upstream.
5. ~~Document the solo-maintainer / phone-home caveats~~ **DONE** — recorded in the package table above (jcodemunch, jdocmunch, roam-code, context-mode). jcodemunch's default anonymous "savings counter" is disableable; all are pinned.

**All items from this review are now closed.** Remaining standing work is operational, not a finding: re-vet + bump pins on each upstream update, and keep `vet-skills` green in CI.

## Automated gate

The automated layer of this process is wired up and runnable:

- **`vet-skills`** — checks shipped skills for remote-pipe-to-shell installers, scans for hardcoded secrets, runs Semgrep on bundled scripts + the installer, and runs **Snyk Agent Scan** (`uvx snyk-agent-scan`) when `SNYK_TOKEN` is set. Exits non-zero on any finding.
- **`.github/workflows/vet.yml`** — runs `vet-skills` and byte-compiles the installer on every push/PR. Add `SNYK_TOKEN` as a repo secret to enable the Snyk step.

The gate is the automated layer only — human review per the Method above is still required before adding or bumping a component.

**Runtime containment (opt-in):** `hooks/guard-pretooluse.py`, installed with `--guard`, is a PreToolUse deny-list net — it blocks `curl … | bash`, `rm -rf ~/$HOME`, reads of SSH/AWS/GPG keys, shell-profile persistence, fork bombs, and block-device writes before a tool runs (exit 2). It is a safety net, not a sandbox (deny-list, bypassable); real isolation still needs least-privilege perms and a sandbox. Removable via `uninstall.py`. This is the operational form of the runtime-containment layer.

**What leaves the machine** is documented separately in `PRIVACY.md` (per-component egress + how to disable).

**Documented accepted-risk (one suppressed finding):** `install-unix` bootstraps Homebrew on macOS with the official `NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL …/Homebrew/install/…)"` one-liner, which Semgrep flags as `curl-pipe-bash`. This is Homebrew's only supported bootstrap — there is no package-manager way to install the package manager itself — over HTTPS from Homebrew's canonical repo. It is suppressed with an inline `# nosemgrep` carrying this justification; the rule stays active everywhere else. The kit's other network bootstraps (uv, NodeSource) download to a file first, then run, rather than piping.

**token-saviour fork license:** upstream `vagkaratzas/token-saviour` is **MIT** (© 2026 Evangelos Karatzas); redistribution + modification are permitted. The notice is retained in `skills/token-saviour/LICENSE` with our modifications recorded.

## Vetting the kit's own code

The kit's own files (installer scripts, hooks, `verify.py`, `uninstall.py`, templates, the token-saviour fork) are first-party, not third-party pulls — here is how they were checked, so the standard is the same one we apply to upstream.

- **Automated gate over our own code.** `vet-skills` runs Semgrep (`--config auto`) and the secret scan over `skills/`, `hooks/`, `install.py`, `uninstall.py`, `verify.py`, and `install-unix`, plus the remote-pipe-to-shell check over `skills/`. It passes; the one Semgrep finding (`curl-pipe-bash`) is the official Homebrew bootstrap, suppressed with a documented inline `# nosemgrep` (see "Documented accepted-risk").
- **Hooks are unit-tested, not just read.** `guard-pretooluse.py` was tested against block/allow inputs (7 destructive patterns blocked: `curl|bash`, `rm -rf ~`, `rm -rf /`, SSH/AWS key reads, `>> ~/.bashrc`, `irm|iex`; 4 legitimate patterns allowed: `rm -rf build/`, reading `.env`, `curl -o file`, `git commit`). `efficiency-pretooluse.py` was tested across `AIKIT_ENFORCE=block|warn|off` (strong rules block, soft rules warn, already-`rtk`/off/safe pass).
- **Scripts are syntax- and lint-checked.** `install.py` / `uninstall.py` / `verify.py` via `python -m py_compile`; `install-unix` via `bash -n` and `shellcheck -S warning` (clean); `install-windows.ps1` via the PowerShell AST parser (parses on 5.1 and 7).
- **The token-saviour fork was diff-reviewed against upstream.** Every `curl … | sh/bash`, `irm … | iex`, and hook/MCP auto-wiring line was removed from `references/tool_links.md`; a grep for an executable remote-pipe-to-shell (`https?://… | sh/bash`, `irm … | iex`) over `skills/token-saviour/` confirms none remain. Upstream MIT license + attribution retained in `skills/token-saviour/LICENSE`.
- **Config edits are non-destructive.** The installer appends hooks to `~/.claude/settings.json` without clobbering existing entries, backs up every file before editing, and injects instruction blocks under removable `ai-kit:*` markers; `uninstall.py` reverses each.

**Honest limitation:** this is first-party self-review by the kit's authors, run through the same automated gate — it is **not** an independent third-party audit. Treat it accordingly, and re-run the gate on every change.

## Reproducing this review

Anyone can re-derive the facts below. Nothing here needs credentials except the optional Snyk step.

```bash
# Pinned versions — PyPI (.info.version) and npm (.version)
for p in serena-agent jcodemunch-mcp jdocmunch-mcp roam-code headroom-ai; do
  echo "$p = $(curl -s https://pypi.org/pypi/$p/json | jq -r .info.version)"; done
for p in repomix tree-sitter-cli context-mode; do
  echo "$p = $(curl -s https://registry.npmjs.org/$p/latest | jq -r .version)"; done
echo "@ast-grep/cli = $(curl -s 'https://registry.npmjs.org/@ast-grep%2Fcli/latest' | jq -r .version)"

# RTK release tag + that install.sh exists at that tag
curl -s https://api.github.com/repos/rtk-ai/rtk/releases/latest | jq -r .tag_name
curl -s -o /dev/null -w '%{http_code}\n' https://raw.githubusercontent.com/rtk-ai/rtk/v1.1.0/install.sh

# token-saviour upstream license
curl -s https://raw.githubusercontent.com/vagkaratzas/token-saviour/main/LICENSE | head -3

# rtk winget id exists
curl -s https://api.github.com/repos/microsoft/winget-pkgs/contents/manifests/r/rtk-ai/rtk | jq -r '.[].name'

# headroom-ai provenance attestation: pypi.org/project/headroom-ai/ → "Provenance" panel → headroomlabs-ai/headroom

# Run the automated gate (same as CI)
bash vet-skills
```

## Evidence appendix (captured 2026-11-03)

### Pinned versions and their source

| Package | Pinned | Registry source |
|---|---|---|
| serena-agent | 2.1.0 | `pypi.org/pypi/serena-agent/json` |
| jcodemunch-mcp | 1.108.411 | `pypi.org/pypi/jcodemunch-mcp/json` |
| jdocmunch-mcp | 1.150.1 | `pypi.org/pypi/jdocmunch-mcp/json` |
| roam-code | 14.1.0 | `pypi.org/pypi/roam-code/json` |
| headroom-ai | 0.42.0 | `pypi.org/pypi/headroom-ai/json` |
| @ast-grep/cli | 0.51.1 | `registry.npmjs.org/@ast-grep/cli` |
| tree-sitter-cli | 0.27.1 | `registry.npmjs.org/tree-sitter-cli` |
| repomix | 1.18.1 | `registry.npmjs.org/repomix` |
| context-mode | 1.0.169 | `registry.npmjs.org/context-mode` |
| rtk | v1.1.0 (Linux script + `RTK_VERSION`) | `api.github.com/repos/rtk-ai/rtk/releases/latest`; `install.sh` at tag `v1.1.0` → HTTP 200 |

### CVEs addressed (with fixed-in version)

- **serena-agent** — CVE-2026-109965 (path traversal via malicious repo), fixed 2.0.0 → pinned 2.1.0.
- **repomix** — CVE-2026-49987 (CVSS 8.8, RCE via `--remote-branch` argument injection), CVE-2026-49988 (MCP file-read bypasses secret-scanning), both fixed 1.14.1; CVE-2026-59702 (SSRF via `POST /api/pack`). Pinned 1.18.1 (> all fixes) and always-installed so an older local copy is upgraded.

### Provenance evidence

- **headroom-ai** — PyPI "Provenance" panel shows a GitHub Actions attestation, PyPI-verified 2026-10-26, tracing the artifact to the `headroomlabs-ai/headroom` release workflow. `chopratejas/headroom` and `MindTouch/headroom-ai` are same-name copies; the published artifact attests to headroomlabs-ai.
- **token-saviour** — upstream LICENSE is `MIT License` / `Copyright (c) 2026 Evangelos Karatzas`. Retained in `skills/token-saviour/LICENSE` with modifications recorded.
- **rtk** — `winget-pkgs/manifests/r/rtk-ai/rtk` exists (versions 0.36.0 … 0.44.0 listed), confirming winget ID `rtk-ai.rtk`. GitHub latest release `v1.1.0`; `install.sh` present at that tag (HTTP 200).

### Reviewers

Three independent static passes on 2026-11-03, each returning file:line evidence:
1. **Executable surface** — caveman installer JS/scripts, the hooks it writes, `rtk-install.sh`, `~/.claude/settings.json`, `~/.cursor/hooks.json`.
2. **Prose/injection surface** — all five skills + Benjamin-Plus `injected-instruction.md`.
3. **Provenance** — all MCP servers, npm CLIs, and RTK.

### Automated gate run (2026-11-03)

```
=== 1. Shipped skills must not contain remote-pipe-to-shell installers ===
ok: no curl|bash / irm|iex installers in skills/
=== 2. Secret scan (skills/, configs/, install scripts) ===
ok: no secret patterns
=== 3. Semgrep (bundled scripts + installers) ===
(no findings; the Homebrew bootstrap is suppressed with an inline # nosemgrep — see accepted-risk)
=== 4. Snyk Agent Scan (skills + MCP configs) ===
SKIP: set SNYK_TOKEN and install uv to run Snyk Agent Scan
=== Result ===
VET PASSED (automated layer). Human review per VETTING.md still required.
```

## Limitations of this review

- **Snyk Agent Scan was not run** in this review pass (no `SNYK_TOKEN` in the review environment), but it is now wired into `vet-skills` / CI for ongoing use.
- Semgrep ran via `vet-skills` over `skills/`, `install.py`, and `install-unix` (passed; one `curl-pipe-bash` finding, the Homebrew bootstrap, is a documented accepted-risk). It was not run against the full upstream source of each MCP/CLI dependency.
- MCP server / package *code* was assessed by provenance and public advisories, not a full line-by-line source audit of each dependency.
- Verdicts apply to the versions resolvable on the review date. **Scanners are bypassable and this review is point-in-time** — re-vet on every version bump, and treat any upstream change as unreviewed until re-checked.

## Ongoing policy

Before adding or bumping any component: run the layered method above, record the result in this file with the date and the reviewed version/commit, pin to a reviewed SHA/tag, and checksum it. Re-vet on update — a vetted skill can change under you (rug pull).
