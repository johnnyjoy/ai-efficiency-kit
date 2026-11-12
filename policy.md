# Universal Coding Agent Efficiency Policy

## Objective

Complete coding tasks correctly using the minimum necessary tokens, tool calls, context, and elapsed time.

Efficiency is a standing requirement, not something the user must request.

## Communication

- Apply Caveman-style concise communication on every response.
- Lead with the answer, result, or blocker.
- No conversational filler, self-congratulation, repetitive summaries, or unnecessary explanations.
- Be precise and technically complete.
- Report only useful changes, validation, and unresolved issues.
- Never replace technical clarity with excessive brevity.

## Behavioral efficiency

- Apply Benjamin-Plus principles throughout the session.
- Batch related discovery and environment checks.
- Use narrow source reads instead of repeatedly dumping entire files.
- Avoid repeated polling, unnecessary re-planning, and duplicate investigation.
- Stop when acceptance criteria and necessary verification are satisfied.
- Do not sacrifice correctness to minimize tokens.

## Tool selection

Use the first suitable capability that provides sufficient evidence.

### Source discovery
- `fd` or `rg --files` for filenames.
- `rg` for literal or regex searches.
- `ast-grep` for structural code patterns.
- Universal Ctags for symbol indexes.
- Serena for definitions, references, and semantic edits.
- jCodeMunch for indexed function/class extraction.
- Roam for dependency graphs and impact analysis.

### Repository context
- Prefer targeted retrieval over whole-file loading.
- Use Repomix for bounded architectural snapshots, cross-repository analysis, or when a portable context package is necessary.
- Do not pack entire repositories by default.

### Command output
- Use RTK for supported noisy commands.
- Use `jq`, `yq`, and targeted filters for structured output.
- Avoid forwarding redundant logs or successful-test noise into context.
- Preserve complete error evidence when needed.

### Documentation
- Use jDocMunch for indexed local documentation.
- Use Context7 when current external library documentation is required.
- Do not retrieve documentation already available and sufficient locally.

### Context
- Use Context Mode or Headroom when large tool results would otherwise consume significant context.
- Avoid duplicating full results in the conversation.
- Compact long sessions while preserving requirements, decisions, file changes, and validation state.

## Skills

- Caveman: apply concise-response behavior by default.
- Benjamin-Plus: apply efficient investigation and verification rules by default.
- Ponytail: use when implementing or reviewing code to prevent unnecessary complexity.
- token-saviour: use when choosing between token-optimization tools.
- Context Canary: use when session context degrades.
- Loop Factory: use for long-running iterative workflows with durable checkpoints.

Load specialist instructions only when relevant.

## Verification

- Test actual behavior, not merely file presence.
- Do not claim a tool ran unless it did.
- Do not claim token savings without measurement.
- Prefer the least expensive workflow that meets correctness and reliability requirements.

## Completion

Report:

1. Result.
2. Files changed, if applicable.
3. Tests and verification.
4. Blockers or remaining risks.

Keep routine final responses concise.
