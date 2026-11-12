#!/usr/bin/env python3
"""PreToolUse efficiency enforcer (Claude Code format).

Routes wasteful Bash commands to the token-saving tools:
  - verbose TEST runners   -> `rtk test <cmd>`   (strong)
  - grep/find/ls/tree/git  -> `rtk <sub>`        (soft, warn only)

Modes via env AIKIT_ENFORCE: `block` (deny strong matches, exit 2 with a redirect),
`warn` (never block; print the suggestion), `off` (do nothing). Default: block.
Safety downgrades: if `rtk` is not on PATH, or the command already uses rtk, nothing
is blocked (never hard-break an agent by redirecting to a missing tool).

This complements, not replaces, the always-on routing instructions and the
token-saviour skill. It only shapes Bash; code-read routing to serena stays advisory
(blocking Read is too blunt).
"""
import json, os, re, shutil, sys

MODE = os.environ.get("AIKIT_ENFORCE", "block").lower()
HAVE_RTK = bool(shutil.which("rtk"))

# (regex, rtk suggestion, strong?) — strong items can be blocked in block mode.
RULES = [
    (re.compile(r'(?<!\w)(pytest|jest|vitest|mocha|phpunit)\b'), 'rtk test <cmd>', True),
    (re.compile(r'(?<!\w)(go|cargo)\s+test\b'),                   'rtk test <cmd>', True),
    (re.compile(r'(?<!\w)(npm|pnpm|yarn)\s+(run\s+)?test\b'),     'rtk test <cmd>', True),
    (re.compile(r'(?<!\w)(mvn|gradle|\./gradlew)\s+\w*test\b'),   'rtk test <cmd>', True),
    (re.compile(r'(?<!\w)(grep|rg| grep)\b'),                     'rtk grep <args>', False),
    (re.compile(r'(?<!\w)find\b'),                                'rtk find <args>', False),
    (re.compile(r'(?<!\w)(tree|ls\s+-[a-zA-Z]*R)\b'),            'rtk tree / rtk ls', False),
    (re.compile(r'(?<!\w)git\s+(log|diff|status)\b'),            'rtk git / rtk diff / rtk log', False),
]

def out(msg):
    sys.stderr.write("ai-efficiency-kit: " + msg + "\n")

def main():
    if MODE == "off":
        sys.exit(0)
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    if (data.get("tool_name") or data.get("tool")) != "Bash":
        sys.exit(0)
    cmd = (data.get("tool_input") or data.get("input") or {}).get("command", "")
    if not cmd or re.search(r'(?<!\w)rtk\b', cmd):   # already routed
        sys.exit(0)
    for rx, sugg, strong in RULES:
        if rx.search(cmd):
            if strong and MODE == "block" and HAVE_RTK:
                out("route this through rtk to save tokens: " + sugg +
                    "  (set AIKIT_ENFORCE=warn or off to relax)")
                sys.exit(2)  # block + redirect
            # warn mode, soft rule, or rtk missing -> non-blocking suggestion
            out("tip: " + sugg + " saves tokens vs the raw command.")
            sys.exit(0)
    sys.exit(0)

if __name__ == "__main__":
    main()
