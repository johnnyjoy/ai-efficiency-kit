#!/usr/bin/env python3
"""PreToolUse guard hook for coding agents (Claude Code format).

Blocks a small, high-confidence set of destructive / exfiltration actions before a
tool runs. Reads the hook JSON on stdin; exit code 2 blocks the call and feeds the
reason back to the agent. It is a SAFETY NET, not a sandbox — it is deny-list based
and bypassable; real isolation still needs least-privilege perms and a sandbox.

Run isolated: the installer wires this as `python3 -I <path>` so no stray local
module can hijack it.
"""
import json, re, sys

def deny(reason):
    sys.stderr.write("BLOCKED by ai-efficiency-kit guard: " + reason + "\n")
    sys.exit(2)  # exit 2 = block; stderr is shown to the agent

# High-confidence dangerous command patterns. Kept tight to avoid false positives
# (agents legitimately run `rm -rf build/`, read .env, etc.).
BASH_RULES = [
    (re.compile(r'(curl|wget|fetch)\b[^|]*\|\s*(sudo\s+)?(sh|bash|zsh|python3?)\b', re.I),
     "piping a downloaded script straight into a shell (curl|bash). Download to a file, review it, then run."),
    (re.compile(r'\b(irm|iwr|invoke-webrequest|wget)\b.*\|\s*iex\b', re.I),
     "piping a downloaded script into Invoke-Expression (irm|iex). Download, review, then run."),
    (re.compile(r'\brm\s+-[a-wyz]*[rf][a-wyz]*[rf]?[a-z]*\s+(-[a-z]+\s+)*(/|/\*|~|\$HOME|\$\{HOME\})(\s|/|$)'),
     "recursive force-delete of a root/home path (rm -rf / | ~ | $HOME)."),
    (re.compile(r':\s*\(\s*\)\s*\{\s*:\s*\|\s*:'),
     "fork bomb."),
    (re.compile(r'\bmkfs\b|\bdd\b[^\n]*\bof=/dev/|>\s*/dev/(sd|nvme|hd|vd)[a-z]'),
     "writing directly to a block device / filesystem creation."),
    (re.compile(r'\bchmod\s+(-R\s+)?0?777\s+(/|~|\$HOME)(\s|/|$)'),
     "world-writable chmod on a root/home path."),
    (re.compile(r'>>?\s*~?/?(\.(bashrc|zshrc|bash_profile|profile|zprofile|bash_login)|\.config/fish/)'),
     "writing to a shell startup file (persistence). Make the change explicit and reviewed instead."),
    (re.compile(r'\bcrontab\b|\bsystemctl\s+enable\b|\blaunchctl\s+load\b'),
     "installing a scheduled/startup job (persistence)."),
]
# Secret material that should not be read, copied, or edited.
SECRET_PATH = re.compile(r'(\bid_rsa\b|\bid_ed25519\b|/\.ssh/|/\.aws/credentials|/\.gnupg/|\.netrc\b|\.pgpass\b|/\.kube/config)')

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # can't parse → don't block (fail open; this is a net, not a gate)
    tool = data.get("tool_name") or data.get("tool") or ""
    ti = data.get("tool_input") or data.get("input") or {}
    if tool == "Bash":
        cmd = ti.get("command", "")
        if SECRET_PATH.search(cmd) and re.search(r'\b(cat|cp|scp|curl|wget|tar|zip|base64|xxd|dd|rsync|less|head|tail)\b', cmd):
            deny("command touches secret material (ssh/aws/gpg keys, .netrc, kubeconfig).")
        for rx, why in BASH_RULES:
            if rx.search(cmd):
                deny(why)
    elif tool in ("Read", "Edit", "Write", "NotebookEdit"):
        fp = ti.get("file_path") or ti.get("notebook_path") or ""
        if SECRET_PATH.search(fp):
            deny("accessing secret material: " + fp)
    sys.exit(0)

if __name__ == "__main__":
    main()
