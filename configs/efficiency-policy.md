## Token-efficient tool routing (ai-efficiency-kit)

Before acting, route the task to the tool that owns its cost layer:

- **Understand code** (symbols, callers, call paths, architecture) → **serena** MCP tools, not whole-file `Read`.
- **Run verbose commands** (tests, builds, grep, find, git log/diff) → **rtk** (e.g. `rtk test pytest`, `rtk grep …`), not the raw command.
- **Long prose replies** → **caveman** terse mode.
- **Generating or editing code** → **ponytail** (minimal / YAGNI).
- **Trivial one-off / one-line lookup** → plain `Read`/`Grep`/`Bash` (tool overhead isn't worth it).

Invoke the **token-saviour** skill when unsure which layer a task stresses. When these tools drive a task, announce them: `🪙 token-saviour: serena + rtk`. Never pretend a tool ran — if one is missing, fall back and say so.
