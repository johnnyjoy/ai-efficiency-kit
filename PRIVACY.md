# What Leaves Your Machine

This kit installs local tools, but a few components send data off-machine — at install
time, or at runtime if you enable them. This is the full list and how to turn each off.
(Your coding agent's own calls to its model provider are inherent and not listed here.)

## Runtime — sends data when used

| Component | What it sends, where | Default | How to disable |
|---|---|---|---|
| **Context7** (remote MCP) | Your library/doc lookup queries → `mcp.context7.com` | On (registered by installer) | `--no-context7` at install; or remove the `context7` MCP from your agent config |
| **jcodemunch-mcp** | Anonymous "savings counter" ping | On | Disable per its docs/env (`jcodemunch-mcp` config); it is designed to be disableable |
| **headroom-ai proxy** | If you enable the proxy, it sits in-path for OpenAI/Anthropic-compatible traffic and sees **every prompt, completion, and API key** | Installed but **proxy not auto-enabled** | Simply don't run `headroom proxy`; use only the local `headroom` MCP/library if at all |
| **codegraph** (optional runner-up; only if you install it) | Telemetry | On | `export CODEGRAPH_TELEMETRY=0`; and do not run `codegraph install` (auto-wires MCP) |
| **caveman-compress** (skill; not auto-run) | The full text of any file you compress → the configured model provider | Only when you invoke it | Don't invoke it on sensitive files; it refuses obvious secret filenames |
| **Snyk Agent Scan** (vetting gate; opt-in) | Tool/skill names, descriptions, MCP config, skill content (secrets redacted) → Snyk API | Only runs when `SNYK_TOKEN` is set | Leave `SNYK_TOKEN` unset to skip it |

Tools confirmed to have **no** telemetry / no auto-upload: **serena** (downloads language
servers only), **roam-code** (one checksum-verified parser-bundle download on first use),
**context-mode** (vendor states zero telemetry), and the plain CLIs (ripgrep, fd, jq, bat,
fzf, ctags, ast-grep, tree-sitter, rtk, repomix).

## Install time — standard package fetches

The installer downloads from these hosts (all HTTPS): your OS package manager's repos
(apt/dnf/pacman/zypper/apk mirrors, Homebrew, WinGet), `astral.sh` (uv), NodeSource
(Node), PyPI and npm (pinned packages), and GitHub (`oraios/serena` language servers,
`rtk-ai/rtk` release at tag `v1.1.0`, `JuliusBrussee/caveman`, `JetBrains/benjamin-plus-skill`).
Nothing from your machine is uploaded during install. See `VETTING.md` for provenance and
pinning of each.

## If you want zero outbound at runtime

Install with `--no-context7 --no-extras`, don't enable the headroom proxy, and disable the
jcodemunch savings counter. That leaves serena + the local CLIs, which do not phone home.
