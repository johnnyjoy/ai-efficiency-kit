# Tool Links And Install Commands

Use this file when `SKILL.md` selects a tool that is missing locally. Install only the chosen
tool or smallest chosen stack, then verify it before using it.

> **Sanitized for ai-efficiency-kit (2026-11-03).** Every `curl … | sh/bash` and `irm … | iex`
> network-install one-liner and every hook/MCP auto-wiring step (`rtk init -g`,
> `codegraph install`) from the upstream `vagkaratzas/token-saviour` version was removed. Use
> only the package-manager commands below. If a tool needs a method not listed here, ask the
> user to install it out-of-band — do not pipe a remote script to a shell, and do not run a
> tool's config/hook auto-wiring from inside a task.

Prerequisites by installer: `serena` and `graphify` need `uv`; `codegraph` needs Node >=18
(`npm`); `rtk` needs Homebrew or Cargo; `caveman` and `ponytail` are installed by the
ai-efficiency-kit installer (Node >=18 for some agent targets).

## The chosen stack (one per layer)

| Tool | Layer | Vetted install | Verify | Notes |
|------|-------|----------------|--------|-------|
| [serena](https://github.com/oraios/serena) | code-read input — symbol comprehension **and edits** | `uv tool install -p 3.13 serena-agent` then `serena init` | `serena --help` | Requires `uv`; language-server deps may be needed per language. Configure the MCP client after install. The only code-read tool that also does semantic edits/renames. Pin `serena-agent>=2.0.0`. |
| [rtk](https://github.com/rtk-ai/rtk) | command-output input — compress verbose stdout | `brew install rtk`, otherwise `cargo install --git https://github.com/rtk-ai/rtk` | `rtk --help` | Installed by the ai-efficiency-kit installer. Do not run its `init -g` hook-wiring step from inside a task. |
| [caveman](https://github.com/juliusbrussee/caveman) | prose output — terse replies | Installed by the ai-efficiency-kit installer (`node installer --all`) | Start a new session and trigger `/caveman` | Installs agent skills/commands, not a dev CLI. Compresses prose; leaves code blocks ~unchanged. |
| [ponytail](https://github.com/DietrichGebert/ponytail) | code output — minimal/YAGNI code generation | Installed by the ai-efficiency-kit installer; or Claude Code `/plugin marketplace add DietrichGebert/ponytail` then `/plugin install ponytail@ponytail` | `/ponytail` in-session | Behavioural plugin (no dev CLI). Biases the agent toward minimal code; bites only when you generate/edit code, ~0 on prose. Levels `lite\|full\|ultra`. |

## Runner-ups per layer (benchmarked; install only if the chosen tool doesn't fit)

| Tool | Layer | Vetted install | Verify | When it beats the pick — and when it doesn't |
|------|-------|----------------|--------|-----------------------------------------------|
| [graphify](https://github.com/safishamsi/graphify) | code-read | `uv tool install graphifyy` (double `y`; CLI is `graphify`) | `graphify --help` | Best at call-path tracing (A3 −89% vs serena's −62%) and impact queries. Read-only; rebuild the graph (`graphify update`) after edits. Aggregate −65.6%, a hair behind serena, and no semantic edits. |
| [codegraph](https://github.com/colbymchenry/codegraph) | code-read | `npm i -g @colbymchenry/codegraph` then `codegraph init <path>` | `codegraph --help` | Best at pinpoint caller lookups (`callers`, A2 −78%). Zero-config single binary, local SQLite, no API key. Aggregate −54.1%: its `explore` returns verbatim source inline (heavier per call, saves follow-up reads). **Do not run `codegraph install`** (it auto-wires MCP into agent configs); set `CODEGRAPH_TELEMETRY=0`. |
| [archex](https://github.com/Mathews-Tom/archex) | code-read | `uv tool install archex` then `archex init && archex index` | `archex doctor` | **Measured worse than baseline (+15.5%) on our ~30-file repo** — every query ships a file tree + multi-chunk bundle designed to amortise on large codebases. Consider only on a monorepo too big to read, and measure before adopting. |
| [Pare](https://github.com/Dave-London/Pare) | command-output | `npx @paretools/init --client claude-code --preset web` (or run servers directly: `npx -y @paretools/python`, `npx -y @paretools/search`) | `npx @paretools/init doctor` | Structured MCP wrappers for pytest/rg/fd/git/docker (28 servers, 240 tools). Its `pytest` posted the single best command cell we measured (−72%; `pytest: 13 passed` = 5 tokens) — pick it for **test-run-dominated loops**. But `find`/`search` returned *more* tokens than terse Unix output (+32%/+11%), so rtk keeps the layer overall. Search server shells out to `rg`/`fd` (install via brew). |
| [lazy-cat](https://github.com/albertobarnabo/lazy-cat) | code output | `npx lazycat-skill` (or add its `think-twice`/`surgical` skills to the project) | skills appear in `/skills` | Same YAGNI territory as ponytail; under identical prompt framing it landed within noise of ponytail on our codegen artifact (−45% vs −41% output — single-sample LLM noise). Fine substitute; ponytail keeps the slot for intensity levels + don't-simplify guardrails. |

## Evaluated but out of scope for this stack

These attack token cost at layers this skill's artifact-level playbook can't measure or that
overlap with harness-native features — listed so you don't re-research them:

- [context-mode](https://github.com/mksglu/context-mode) — sandboxes big tool outputs behind
  MCP + hooks and returns summaries (claims 98%). Different mechanism (session-level output
  quarantine), heavier integration; overlaps with Claude Code's own sandboxing/summarisation.
- Headroom — API-proxy payload compression between agent and API. Transport-layer; orthogonal
  to everything here and invisible to a skill.
- Memory-layer tools (CBM "codebase memory", remindb) — trade re-reads for a persistent
  knowledge graph across sessions. Complementary, not a per-task routing decision.

## Optional variants

- `graphify`: install extras only when needed, e.g. `uv tool install "graphifyy[mcp]"`.
- `rtk`: on Linux/macOS, use `brew install rtk` or `cargo install --git https://github.com/rtk-ai/rtk`. It installs to `~/.local/bin`; add that to `PATH` only if verification can't find `rtk`.

## Selection rule

Do not install every tool. Take **serena** for the code-read layer (fall back to `graphify` for
navigation-heavy work or `codegraph` for a zero-config binary), then add `rtk` (command-heavy
work), `caveman` (chatty prose output), and/or `ponytail` (code-generation work) only when their
layer is the bottleneck. Never run two code-read tools side by side.
