# AI Coding Efficiency Kit

A cross-platform installer that provisions a vetted set of **token-saving tools, local MCP servers, and agent skills** for AI coding agents — and wires them into the agents you already use.

It makes agents cheaper and faster to run by routing work to the right tool (semantic code retrieval instead of whole-file reads, compressed command output, terse prose, minimal code generation) instead of letting them burn context on brute force.

> **This kit does not install coding agents.** It installs the *tools* and *skills* they use, then integrates into detected agents (Claude Code, Codex, Cursor, OpenCode, OpenClaw, and others). Every third-party component has been security-reviewed — see [VETTING.md](VETTING.md).

> ⚠️ **Corporate / organization users: check with your internal security or IT office first.** Before installing, confirm these tools are approved for use in your organization. This kit runs third-party installers, registers MCP servers and agent hooks, and includes components that send data off-machine (see [PRIVACY.md](PRIVACY.md)) and components whose licenses restrict commercial use (serena-agent is GPL-3.0-or-later; jCodeMunch/jDocMunch require a paid commercial license; Context Mode is under the Elastic License 2.0 — see [Acknowledgements & licenses](#acknowledgements--licenses)). Your security team's guidance and your organization's software, licensing, and data-handling policies take precedence over anything in this README.

## Contents

- [What it is / isn't](#what-it-is--isnt)
- [Requirements](#requirements)
- [Quick start](#quick-start)
- [Configuration flags](#configuration-flags)
- [What gets installed](#what-gets-installed)
- [Agent integration](#agent-integration)
- [Making agents actually use the tools](#making-agents-actually-use-the-token-saving-tools)
- [Security & vetting](#security--vetting)
- [Privacy — what leaves your machine](#privacy--what-leaves-your-machine)
- [Verifying the install](#verifying-the-install)
- [Uninstalling](#uninstalling)
- [Repository layout](#repository-layout)
- [Troubleshooting](#troubleshooting)
- [Acknowledgements & licenses](#acknowledgements--licenses)
- [License](#license)

## What it is / isn't

**It is:** OS CLI utilities, local coding MCP servers (serena, jCodeMunch, jDocMunch, and complementary tools), agent skills (concise-response, code-minimalism, context-management, tool routing), a version-pinned installer, a security-vetting gate, and optional runtime guard/enforcement hooks.

**It isn't:** a coding agent, a model, or an API-key manager. It integrates into *existing* agents and never fabricates config for agents that aren't installed.

## Requirements

- **Linux / WSL2:** one of `apt-get`, `dnf`, `pacman`, `zypper`, `apk`. `sudo` for system packages. No preinstalled Python or `uv` required — the installer bootstraps them.
- **macOS:** Homebrew (bootstrapped automatically; may prompt for administrator approval and Xcode command-line tools).
- **Windows:** WinGet (App Installer). The installer attempts to bootstrap it if missing; see [Troubleshooting](#native-windows-winget--read-this-first).
- Internet access at install time. Some steps need administrator/root privileges.

**Run the installer from the account that runs your coding agents.** WSL agents use the WSL Linux home directory, not the Windows host home; native Windows agents need the Windows installer separately.

## Quick start

From the extracted `ai-efficiency-kit` folder:

```bash
# Linux / WSL2  — auto-detects apt / dnf / pacman / zypper / apk
./install-unix

# macOS         — bootstraps Homebrew if needed
./install-unix
```

```powershell
# Native Windows
powershell -ExecutionPolicy Bypass -File .\install-windows.ps1
```

Core tools (`git`, `curl`, `python3`, `ripgrep`, `fd`, `jq`, `bat`, `fzf`, `ctags`) install strictly; optional extras (`shellcheck`, `sd`, `git-delta`, `hyperfine`, `watchexec`) are best-effort per distro and fall back to `cargo install` where a package is missing. `uv` installs via the Astral script when no distro package exists; Node is upgraded to ≥22 via NodeSource on apt/dnf, otherwise the distro Node is kept with a warning.

After installation, verify it:

```bash
uv run --no-project --python 3.13 python verify.py
```

## Configuration flags

| Flag (Unix / `install.py`) | Windows switch | Effect |
|---|---|---|
| *(default)* | *(default)* | Install tools, skills, MCP registrations, and the always-on routing instruction |
| `--no-context7` | `-SkipContext7` | Skip Context7 remote-MCP registration |
| `--no-extras` | `-SkipExtras` | Skip the complementary tools (Roam, Headroom, Context Mode) |
| `--guard` | `-Guard` | Install the PreToolUse **safety-net** hook (blocks destructive/exfil actions) |
| `--enforce` | `-Enforce` | Install the PreToolUse **efficiency** hook (routes verbose Bash to `rtk`) |

Environment variables:

- `AIKIT_ENFORCE=block|warn|off` — behavior of the efficiency hook (default `block`; auto-downgrades to `warn` if `rtk` is absent).
- `SNYK_TOKEN` — enables the Snyk Agent Scan step in the vetting gate / CI.

## What gets installed

- **CLI tools:** Git, ripgrep, fd, jq, bat, fzf, Universal Ctags, Tree-sitter CLI, ast-grep, Repomix, RTK, plus platform-available ShellCheck, sd, git-delta, hyperfine, watchexec, yq.
- **Local MCP servers:** serena (semantic code retrieval + edits), jCodeMunch (indexed code extraction), jDocMunch (indexed docs). Source navigation also uses Tree-sitter, Ctags, and ast-grep.
- **Agent skills & instructions:** caveman (terse replies), Ponytail (minimal/YAGNI code), token-saviour (tool routing — kit ships a sanitized fork), Context Canary + Loop Factory, Benjamin-Plus (efficient-investigation ruleset injected into existing agent instruction files).
- **Complementary tools (`--no-extras` to skip):** Roam, Headroom, Context Mode. Installed but **not all enabled at once** — overlapping context proxies can conflict and cost more than they save.
- **Remote:** Context7 (`https://mcp.context7.com/mcp`) registered last; authentication happens inside your agent when prompted.

All packages are **pinned to reviewed versions** (see [VETTING.md](VETTING.md)); re-vet and bump on upstream updates.

## Agent integration

- **Caveman** uses its upstream detected-agent installer (Claude Code, Codex, Cursor, OpenCode, OpenClaw, and more when detected).
- **jCodeMunch / jDocMunch** use their own multi-client initializers (Claude Code, Codex, OpenCode, Cursor, Cline, Gemini, Continue, …).
- **serena** is registered for Claude Code and Codex when their CLIs exist, via native Cursor JSON where present, and via the OpenCode CLI when detected. Registration results are recorded, not assumed.
- **Benjamin-Plus** and the **token-routing instruction** are injected only into *existing* agent instruction files, under removable `ai-kit:*` markers.
- **Context7** is registered as a **remote Streamable-HTTP MCP** (`https://mcp.context7.com/mcp`). The installer never runs an interactive `ctx7 setup`, preserves existing configuration, and registers the endpoint with detected Claude Code, Codex, Cursor, and OpenCode clients in their documented formats. Authentication is performed inside the client when requested. `--no-context7` skips it.

Client support varies by release; per-client failures are recorded in `install-report.json`. **A downloaded skill or MCP binary is not proof of connection** — restart the client and check its MCP list. An agent in a remote/cloud sandbox needs these tools installed **inside that environment**.

## Making agents actually use the token-saving tools

Getting an agent to *always* reach for serena/rtk/caveman/ponytail is a spectrum from soft (instructions it may ignore) to hard (enforcement it cannot bypass). The kit ships both layers:

- **Always-on routing instruction (default, soft).** `configs/efficiency-policy.md` is injected into each agent's standing-instructions file (`~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, opencode/openclaw `AGENTS.md`) under an `ai-kit:efficiency-routing` marker. It routes code-reads→serena, command-output→rtk, prose→caveman, codegen→ponytail. Raises tool use; does not force it.
- **Efficiency enforcement hook (opt-in, hard — Claude Code).** Install with `--enforce` (`-Enforce` on Windows). `hooks/efficiency-pretooluse.py` is a PreToolUse hook that **blocks** raw verbose test commands (`pytest`, `go test`, …) with a redirect to `rtk`, and warns on `grep`/`find`/`git log`. Tunable via `AIKIT_ENFORCE=block|warn|off` (default `block`); it auto-downgrades to a warning if `rtk` isn't installed, and never touches `Read` (code-read routing stays advisory). This is the only mechanism that yields true "always."
- **Coverage reality.** Hard enforcement works where the agent supports PreToolUse hooks (**Claude Code** fully; **Cursor**/**OpenCode** partially via their hook/plugin systems; **Codex** and others are instruction-only). You get "always" on Claude Code, "usually" elsewhere.
- **Measure it.** token-saviour prints a `🪙 token-saviour: …` tag naming the tools it actually used, so you can see real adherence rather than assume it.

## Security & vetting

Every third-party skill, MCP server, CLI tool, and install script this kit pulls in was reviewed for prompt injection, malicious code, data exfiltration, and supply-chain risk. The method, per-component verdicts, known CVEs, pinned versions, and evidence are recorded in **[VETTING.md](VETTING.md)**. That record is point-in-time and must be re-checked on every version bump — scanners are bypassable and upstream code can change. Mainstream OS packages from official distro/Homebrew/WinGet channels are out of scope.

- **Runtime guard hook (opt-in):** `--guard` adds a PreToolUse safety net (`hooks/guard-pretooluse.py`) that blocks a high-confidence set of destructive/exfiltration actions — `curl … | bash`, `rm -rf ~`, reads of SSH/AWS keys, shell-profile persistence. It is a deny-list net, **not a sandbox**, appended to `~/.claude/settings.json` without clobbering existing hooks.
- **Vetting gate:** `vet-skills` (+ `.github/workflows/vet.yml`) runs the automated layer — remote-installer check, secret scan, Semgrep, and Snyk Agent Scan when `SNYK_TOKEN` is set.
- **Secret-scanning for your own repos:** copy [templates/.pre-commit-config.yaml](templates/.pre-commit-config.yaml) into a repo and run `pre-commit install` (gitleaks + detect-private-key).

## Privacy — what leaves your machine

A few components send data off-machine at install time or, if enabled, at runtime. **[PRIVACY.md](PRIVACY.md)** lists each one (Context7 queries, jCodeMunch's anonymous counter, the Headroom proxy, Context Mode, Snyk Agent Scan, …) and exactly how to disable it. For zero outbound at runtime, install with `--no-context7 --no-extras`, don't enable the Headroom proxy, and disable the jCodeMunch counter.

## Verifying the install

`verify.py` checks that required executables are present **and** that the MCP servers actually respond:

```bash
uv run --no-project --python 3.13 python verify.py
```

It performs a real JSON-RPC `initialize` handshake against serena, jCodeMunch, and jDocMunch, and a liveness check on the rest. Missing required executables fail the run (exit 1); MCP connectivity issues are reported as warnings (a server may legitimately need a project or config). Also inspect `install-report.json` for per-step results.

## Uninstalling

```bash
python3 uninstall.py            # dry-run: prints what it would remove
python3 uninstall.py --yes      # actually remove
python3 uninstall.py --yes --purge-state   # also delete ~/.local/share/ai-efficiency-kit
```

It reverses the MCP servers, pinned packages, MCP registrations, injected instruction blocks, and the guard/efficiency hooks, backing up each edited config. **It does not remove shared OS tools** (git, ripgrep, fd, …) — remove those with your package manager if desired.

## Repository layout

| Path | Purpose |
|---|---|
| `install-unix` | Linux/macOS bootstrap + installer entry (auto-detects package manager) |
| `install-windows.ps1` | Windows (WinGet) bootstrap + installer entry |
| `install.py` | Cross-platform installer logic (pinned versions, registrations, injections) |
| `verify.py` | Post-install check (executables + MCP handshake) |
| `uninstall.py` | Reversal (dry-run by default) |
| `vet-skills` | Automated security-vetting gate |
| `hooks/` | `guard-pretooluse.py` (safety net), `efficiency-pretooluse.py` (rtk routing) |
| `configs/` | MCP config templates, `efficiency-policy.md`, `settings.guard.json` |
| `skills/token-saviour/` | Kit-vetted, sanitized fork of token-saviour |
| `templates/` | `.pre-commit-config.yaml` secret-scanning baseline |
| `VETTING.md` | Security-vetting record, method, evidence, pinned versions |
| `PRIVACY.md` | What each component sends off-machine, and how to disable it |
| `policy.md` | The efficiency policy agents follow |

## Troubleshooting

Each entry below is a real, recently-reported failure with a copy-paste remedy. Check `install-report.json` and `verify.py` output first to see which step failed.

### All platforms

- **`uv: command not found` right after install.** The installer updated your shell profile, but the current shell has not re-read it. Open a new terminal, or run `source "$HOME/.local/bin/env"`. If the binary is genuinely missing, confirm `~/.local/bin/uv` exists (uv < 0.5.0 used `~/.cargo/bin`); if two copies shadow each other, `which -a uv` and remove the unwanted one. Never install uv with `sudo`; if you did, `chown -R "$USER" ~/.local/bin` and re-run.
- **`npm install -g` fails with `EACCES: permission denied`.** The global prefix points at a root-owned directory such as `/usr/local/lib/node_modules`. Do **not** fix it with `sudo`. Point npm at a directory you own: `npm config set prefix ~/.local` then ensure `~/.local/bin` is on `PATH`. Verify with `npm config get prefix`; a system `/etc/npmrc` can override it. The NodeSource/distro node the script installs usually avoids this.
- **`tree-sitter`, `ast-grep` or `repomix` installed but broken on Alpine/musl.** The npm packages ship **glibc** binaries that pass install but die at runtime with `symbol not found` (e.g. `fcntl64`, `__res_init`). `gcompat` does not reliably fix it. Remedy: use Alpine's own package where it exists (`apk add tree-sitter-cli`), or build from source: `apk add build-base clang musl-dev pkgconf cargo && cargo install --locked tree-sitter-cli`. This affects musl systems only.
- **Context7 MCP returns HTTP 401.** A rejected or empty `Authorization` header is a hard failure — Claude Code will not fall back to OAuth. If you have no key, make sure **no** Authorization header is sent and sign in via `/mcp`. If you have a key, it must start with `ctx7sk` and match the dashboard; the remote header is `Authorization: Bearer <key>`. Stale key: `claude mcp remove context7` then re-add, and restart the client. HTTP 429: add a free key from context7.com/dashboard. `--no-context7` skips the whole step.
- **A coding agent does not see the new MCP servers.** Restart the client fully after install — most agents read MCP config only at startup. Then check the client's MCP list (`claude mcp list`, `codex mcp list`, or the client UI). A downloaded executable is **not** proof of connection.

### Ubuntu / Debian / WSL (apt)

- **`fd` or `bat` "not found" though apt installed them.** Debian/Ubuntu ship the binaries as `fdfind` and `batcat` to avoid name clashes. The installer symlinks canonical names into `~/.local/bin`; if that is not on `PATH`, add it, or call `fdfind`/`batcat` directly.
- **NodeSource `setup_22.x` fails with `Conflicting values set for option Signed-By`.** A leftover `nodesource.list` conflicts with a newer `nodesource.sources` pointing at a different keyring. Remove the stale files and re-run: `sudo rm -f /etc/apt/sources.list.d/nodesource.list /usr/share/keyrings/nodesource.gpg` then re-run the installer. On Debian 13 / newer Ubuntu a SHA-1 signing-key rejection (effective Feb 2026) may need NodeSource's current key fetched manually.
- **`git-delta` breaks an existing `delta` package.** The apt `git-delta` package declares `Provides: delta`, which collides with the unrelated Debian `delta` package. If you need both, skip the distro package and use the cargo build the installer falls back to (`cargo install --locked git-delta`, binary `delta`).
- **WSL confusion.** WSL is a separate Linux filesystem and `PATH`. Tools installed on the Windows host never appear in WSL and vice-versa. Run the installer from the **account that runs your agent**, inside the right environment.

### Fedora / RHEL / Rocky / Alma (dnf)

- **`No match for argument: ripgrep` / `fd-find`.** These live in EPEL on RHEL-family systems. Enable it first: RHEL/Rocky/Alma 8+: `sudo dnf install epel-release`. RHEL 9/10 also needs CodeReady Builder: `sudo subscription-manager repos --enable codeready-builder-for-rhel-$(rpm -E %rhel)-$(arch)-rpms`, then install the EPEL release RPM.
- **`sd` is unavailable on Fedora.** It was dropped from the repos; the installer marks it a warning and the cargo fallback builds it (`cargo install --locked sd`). Needs a Rust toolchain (`sudo dnf install cargo rust`).
- **`ShellCheck` casing.** The Fedora package is capitalized `ShellCheck`; the installer uses that exact name. `shellcheck` (lowercase) is the binary.

### Arch / Manjaro (pacman)

- **`invalid or corrupted package (PGP signature)`.** Refresh the keyring **before** upgrading: `sudo pacman -Sy --needed archlinux-keyring && sudo pacman -Su`. If it persists: check the system clock (`timedatectl`) — a wrong clock makes keys look expired; then clear the bad cached file in `/var/cache/pacman/pkg/`. Last resort: reset `/etc/pacman.d/gnupg` with `pacman-key --init && pacman-key --populate archlinux` (back it up first).
- **Partial-upgrade warning.** Do not run a bare `pacman -Sy <pkg>` afterward; refreshing the database without a full upgrade leaves a partial upgrade. The installer runs `pacman -Syu` (full upgrade) before installing, as Arch requires.

### openSUSE (zypper) / Alpine (apk)

- **A best-effort package name is rejected.** Names such as `ShellCheck`, `sd`, `git-delta` drift across these repos. The installer wraps each in `|| warn`, so a wrong name warns rather than aborting; the cargo fallback then builds the Rust tools. Confirm a name with `zypper se <name>` or `apk search <name>`.
- **Alpine `apk add delta` is the wrong `delta`.** It is **not** the git diff pager. The installer omits it on Alpine and builds `git-delta` via cargo instead.

### macOS (Homebrew)

- **`zsh: command not found: brew` after install (Apple Silicon).** Homebrew lives in `/opt/homebrew`, which may not be on `PATH`. Run `eval "$(/opt/homebrew/bin/brew shellenv)"` now, and add that line to `~/.zprofile` (bash: `~/.bash_profile`) so it persists. If `uname -m` reports `x86_64` on an Apple Silicon Mac, your terminal is under Rosetta and will find the wrong Homebrew.
- **Homebrew bootstrap needs admin.** First-time install may prompt for administrator approval and the Xcode command-line tools (`xcode-select --install`). Run `brew doctor` to confirm a healthy setup.

### Native Windows (WinGet) — read this first

Windows is the most failure-prone platform here. The installer now bootstraps WinGet, runs fully non-interactively (`--disable-interactivity`), and treats "already installed" as success. The remaining issues below are environmental.

- **`running scripts is disabled on this system` / the `.ps1` won't start.** PowerShell's execution policy, or the downloaded-file "blocked" mark, stops it. Run it without changing any global setting:
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\install-windows.ps1
  ```
  If it still refuses, the file is marked as downloaded — **unblock the ZIP before extracting** (or the script after): `Unblock-File .\install-windows.ps1`. Diagnose scope with `Get-ExecutionPolicy -List`; a Group Policy setting cannot be overridden by `Set-ExecutionPolicy`. PowerShell 7 and Windows PowerShell 5.1 keep **separate** policies — set it in the one you run.
- **`winget` is missing (fresh image, Windows Server, Enterprise LTSC).** The script auto-attempts a bootstrap:
  ```powershell
  Install-Module Microsoft.WinGet.Client -Scope CurrentUser
  Repair-WinGetPackageManager -AllUsers
  ```
  If that fails: WinGet ships only on **Windows Server 2025 with Desktop Experience** — Server 2022, Server Core, and Nano are unsupported (use Chocolatey or MSIs). On Windows 10/11, install **App Installer** from the Microsoft Store. See [Microsoft WinGet docs](https://learn.microsoft.com/windows/package-manager/winget/).
- **`winget` "not recognized" on a fresh/service account even though it is installed.** WinGet registers per-user at **first interactive sign-in**. Sign in once as that account, or verify the machine has it: `Get-AppxPackage -AllUsers Microsoft.DesktopAppInstaller`. If present but unregistered, run `Repair-WinGetPackageManager`.
- **Non-interactive run fails with `0x8A150042` (`PROMPT_INPUT_ERROR`).** WinGet's `msstore` source has never had its agreement accepted for this profile and blocked on a prompt. Fix once: `winget source reset --force`, then re-run. The script already passes `--accept-source-agreements --accept-package-agreements --disable-interactivity --source winget`.
- **`0x8A150077` (`AUTHENTICATION_CANCELLED_BY_USER`).** A private/enterprise WinGet source needs sign-in that was dismissed. Authenticate to that source, or remove it if unneeded.
- **"Nothing to do" codes are not failures.** `0x8A15002B` (already current), `0x8A15010D` (a different version already installed), `0x8A15010E` (a higher version already installed) all mean success. The script classifies these as benign and continues; only other codes are collected as real failures.
- **`node`/`npm`/`uv` "not recognized" right after install.** The running shell kept the pre-install environment. **Close every terminal and VS Code, open a new PowerShell window, and re-run.** The script refreshes `PATH` in-process (including `C:\Program Files\nodejs` and `%APPDATA%\npm`), but a fresh session is the reliable fix. If it persists, run `where.exe node` / `where.exe npm`: a stale **nvm-windows**, Scoop, or Chocolatey Node whose `PATH` entry points at a missing directory will shadow the WinGet install — uninstall the conflicting one.
- **Admin vs per-user.** Writing to `C:\Program Files` or machine `PATH` needs an elevated PowerShell. If machine-scope installs fail, run the terminal **as Administrator**, or accept the per-user installs WinGet falls back to.
- **MSI sub-code `3010`.** A package installed but requests a reboot. Reboot and re-run `verify.py`.
- **Corporate proxy / TLS.** Behind a proxy, WinGet and the uv/NodeSource downloads may fail to reach their CDNs. Configure the system proxy (`netsh winhttp set proxy ...`) or set `HTTPS_PROXY` before running.

## Acknowledgements & licenses

This kit stands on the work of the projects below. It installs them from their official distribution channels (and, for token-saviour, ships a sanitized fork — see note). All credit to their authors. **Verify current license terms at each source before redistributing**; the SPDX identifiers below were captured on 2026-11-11.

### Skills & agent instructions

| Component | Source | License |
|---|---|---|
| caveman | [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) | Apache-2.0 |
| Ponytail | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) | MIT |
| token-saviour *(sanitized fork shipped in `skills/`)* | [vagkaratzas/token-saviour](https://github.com/vagkaratzas/token-saviour) | MIT |
| Context Canary & Loop Factory | [JuliusBrussee/skills](https://github.com/JuliusBrussee/skills) | MIT |
| Benjamin-Plus | [JetBrains/benjamin-plus-skill](https://github.com/JetBrains/benjamin-plus-skill) | MIT |

### MCP servers & agent tools

| Component | Source | License |
|---|---|---|
| serena (`serena-agent`) | [oraios/serena](https://github.com/oraios/serena) | **GPL-3.0-or-later** (combined package; SolidLSP component is MIT) |
| jCodeMunch (`jcodemunch-mcp`) | [jgravelle/jcodemunch-mcp](https://github.com/jgravelle/jcodemunch-mcp) | **Custom "Dual-Use License" (jMunch, LLC)** — free for non-commercial use; commercial use requires a paid license |
| jDocMunch (`jdocmunch-mcp`) | [jgravelle/jdocmunch-mcp](https://github.com/jgravelle/jdocmunch-mcp) | **Custom "Dual-Use License" (jMunch, LLC)** — same terms as above |
| Roam (`roam-code`) | [Cranot/roam-code](https://github.com/Cranot/roam-code) | Apache-2.0 |
| Headroom (`headroom-ai`) | [headroomlabs-ai/headroom](https://github.com/headroomlabs-ai/headroom) | Apache-2.0 |
| Context Mode (`context-mode`) | [mksglu/context-mode](https://github.com/mksglu/context-mode) | **Elastic License 2.0** (source-available, not OSI-approved; usage restrictions apply) |
| RTK (`rtk`) | [rtk-ai/rtk](https://github.com/rtk-ai/rtk) | Apache-2.0 |
| ast-grep | [ast-grep/ast-grep](https://github.com/ast-grep/ast-grep) | MIT |
| Repomix | [yamadashy/repomix](https://github.com/yamadashy/repomix) | MIT |
| Tree-sitter | [tree-sitter/tree-sitter](https://github.com/tree-sitter/tree-sitter) | MIT |
| Context7 (remote MCP) | [upstash/context7](https://github.com/upstash/context7) · [context7.com](https://context7.com) | MIT client; the hosted service has its own terms |

### CLI tools (installed from your OS package manager / Homebrew / WinGet)

| Tool | Source | License |
|---|---|---|
| ripgrep | [BurntSushi/ripgrep](https://github.com/BurntSushi/ripgrep) | Unlicense OR MIT |
| fd | [sharkdp/fd](https://github.com/sharkdp/fd) | MIT OR Apache-2.0 |
| bat | [sharkdp/bat](https://github.com/sharkdp/bat) | MIT OR Apache-2.0 |
| jq | [jqlang/jq](https://github.com/jqlang/jq) | MIT (with bundled components) |
| fzf | [junegunn/fzf](https://github.com/junegunn/fzf) | MIT |
| Universal Ctags | [universal-ctags/ctags](https://github.com/universal-ctags/ctags) | GPL-2.0 |
| sd | [chmln/sd](https://github.com/chmln/sd) | MIT |
| git-delta | [dandavison/delta](https://github.com/dandavison/delta) | MIT |
| hyperfine | [sharkdp/hyperfine](https://github.com/sharkdp/hyperfine) | MIT OR Apache-2.0 |
| ShellCheck | [koalaman/shellcheck](https://github.com/koalaman/shellcheck) | GPL-3.0 |
| watchexec | [watchexec/watchexec](https://github.com/watchexec/watchexec) | Apache-2.0 |
| yq | [mikefarah/yq](https://github.com/mikefarah/yq) | MIT |
| Semgrep *(used by the vetting gate)* | [semgrep/semgrep](https://github.com/semgrep/semgrep) | LGPL-2.1 |
| Snyk Agent Scan *(optional vetting)* | [snyk/agent-scan](https://github.com/invariantlabs-ai/mcp-scan) | see repo |

> **License compliance notes.** `serena-agent` is **GPL-3.0-or-later** as a combined package. `jcodemunch-mcp` / `jdocmunch-mcp` are **not free for commercial use** — obtain a license from jMunch, LLC for commercial deployments. `context-mode` is under the **Elastic License 2.0** (source-available; you may not provide it as a managed service or circumvent the license). Universal Ctags (GPL-2.0) and ShellCheck (GPL-3.0) are invoked as separate binaries, not linked. These components are installed from upstream, **not redistributed by this repository**.

## License

The ai-efficiency-kit's own code (installer scripts, hooks, `verify.py`, `uninstall.py`, templates, and documentation) is released under the **MIT License** — see [LICENSE](LICENSE). This covers only the kit's own files; each third-party component remains under its own license as listed above. The sanitized token-saviour fork in `skills/token-saviour/` retains its upstream MIT license and attribution in `skills/token-saviour/LICENSE`.

> If you intend to redistribute this kit, review the compliance notes above — particularly the GPL, Dual-Use, and Elastic-licensed components, which the kit *installs* but does not *bundle*.
