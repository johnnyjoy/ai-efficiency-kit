#!/usr/bin/env python3
"""Reverse what install.py added. Dry-run by default; pass --yes to execute.

Removes the kit's MCP servers, CLI packages (installed via uv/npm), MCP
registrations, the injected Benjamin-Plus blocks, and the guard hook. It does NOT
remove OS packages (git, ripgrep, fd, jq, ...) — those are shared system tools and
may predate the kit. Config files are backed up before edits.
"""
import argparse, json, pathlib, shutil, subprocess, sys, time
H=pathlib.Path.home(); STATE=H/'.local'/'share'/'ai-efficiency-kit'
DRY=True
def cmd(name):
    p=shutil.which(name)
    if p:return p
    for base in (H/'.local'/'bin',H/'.cargo'/'bin'):
        for suf in ('','.exe','.cmd'):
            q=base/(name+suf)
            if q.is_file():return str(q)
    return None
def run(argv):
    print(('DRY  ' if DRY else 'RUN  ')+' '.join(str(a) for a in argv))
    if DRY:return
    try:
        p=subprocess.run([str(a) for a in argv],capture_output=True,text=True,timeout=600)
        if p.returncode!=0:print('   (exit %d) %s'%(p.returncode,(p.stderr or p.stdout).strip()[:200]))
    except Exception as e:print('   (error) '+str(e))
def backup(path):
    if path.exists() and not DRY:
        shutil.copy2(path,path.with_name(path.name+'.bak-ai-kit-uninstall-'+time.strftime('%Y%m%d%H%M%S')))
def strip_inject(path,tag='benjamin-plus'):
    if not path.exists():return
    old=path.read_text(encoding='utf8');b='<!-- ai-kit:%s:start -->'%tag;e='<!-- ai-kit:%s:end -->'%tag
    if b not in old or e not in old:return
    new=old.split(b)[0].rstrip()+'\n'+old.split(e,1)[1].lstrip()
    print(('DRY  ' if DRY else 'RUN  ')+'strip %s block from %s'%(tag,path))
    if not DRY:backup(path);path.write_text(new,encoding='utf8')
def remove_hooks():
    names=('guard-pretooluse.py','efficiency-pretooluse.py')
    settings=H/'.claude'/'settings.json'
    if settings.exists():
        try:base=json.loads(settings.read_text(encoding='utf8'))
        except Exception:base=None
        if isinstance(base,dict):
            pre=base.get('hooks',{}).get('PreToolUse',[])
            kept=[e for e in pre if not (isinstance(e,dict) and any(isinstance(h,dict) and any(n in str(h.get('command','')) for n in names) for h in e.get('hooks',[])))]
            if kept!=pre:
                print(('DRY  ' if DRY else 'RUN  ')+'remove ai-kit PreToolUse hooks from '+str(settings))
                if not DRY:
                    base['hooks']['PreToolUse']=kept;backup(settings)
                    settings.write_text(json.dumps(base,indent=2)+'\n',encoding='utf8')
    for n in names:
        g=STATE/n
        if g.exists():
            print(('DRY  ' if DRY else 'RUN  ')+'delete '+str(g))
            if not DRY:g.unlink()
def strip_json_mcp(path,keys=('serena','context7')):
    if not path.exists():return
    try:base=json.loads(path.read_text(encoding='utf8'))
    except Exception:return
    srv=base.get('mcpServers') if isinstance(base,dict) else None
    if not isinstance(srv,dict):return
    hit=[k for k in keys if k in srv]
    if hit:
        print(('DRY  ' if DRY else 'RUN  ')+'remove %s from %s'%(','.join(hit),path))
        if not DRY:
            for k in hit:srv.pop(k,None)
            backup(path);path.write_text(json.dumps(base,indent=2)+'\n',encoding='utf8')

def main():
    global DRY
    ap=argparse.ArgumentParser();ap.add_argument('--yes',action='store_true',help='actually perform removal (default: dry-run)')
    ap.add_argument('--purge-state',action='store_true',help='also delete '+str(STATE))
    args=ap.parse_args();DRY=not args.yes
    print('=== ai-efficiency-kit uninstall (%s) ===\n'%('EXECUTE' if args.yes else 'DRY-RUN — pass --yes to apply'))

    print('-- uv tools --')
    if cmd('uv'):
        for p in ('serena-agent','jcodemunch-mcp','jdocmunch-mcp','roam-code','headroom-ai'):
            run([cmd('uv'),'tool','uninstall',p])
    else:print('   uv not found; skip')

    print('-- npm global packages --')
    if cmd('npm'):
        run([cmd('npm'),'uninstall','-g','@ast-grep/cli','tree-sitter-cli','repomix','context-mode'])
    else:print('   npm not found; skip')

    print('-- MCP registrations --')
    for c in ('claude','codex'):
        if cmd(c):
            for s in ('serena','context7'):run([cmd(c),'mcp','remove',s])
    if cmd('opencode'):
        for s in ('serena','context7'):run([cmd('opencode'),'mcp','remove',s])
    strip_json_mcp(H/'.cursor'/'mcp.json')

    print('-- skills --')
    if cmd('npx') or shutil.which('npx'):
        for s in ('ponytail','token-saviour','context-canary','loop-factory'):
            run(['npx','-y','skills','remove',s,'--global','--yes'])
    print('-- caveman (upstream uninstaller) --')
    run(['npx','-y','github:JuliusBrussee/caveman','--','--uninstall'])

    print('-- injected instruction blocks (Benjamin-Plus + efficiency routing) --')
    for p in (H/'.claude'/'CLAUDE.md',H/'.codex'/'AGENTS.md',H/'.config'/'opencode'/'AGENTS.md',H/'.openclaw'/'workspace'/'AGENTS.md'):
        strip_inject(p,'benjamin-plus');strip_inject(p,'efficiency-routing')

    print('-- PreToolUse hooks (guard + efficiency) --')
    remove_hooks()

    if args.purge_state and STATE.exists():
        print('-- state dir --')
        print(('DRY  ' if DRY else 'RUN  ')+'rm -rf '+str(STATE))
        if not DRY:shutil.rmtree(STATE,ignore_errors=True)

    print('\nNote: OS packages (git, ripgrep, fd, jq, bat, fzf, ctags, ...) are NOT removed — '
          'they are shared system tools. Remove them with your package manager if desired.')
    print('Config backups were written next to each edited file as *.bak-ai-kit-uninstall-*.')
    if DRY:print('\nThis was a DRY-RUN. Re-run with --yes to apply.')
if __name__=='__main__':sys.exit(main())
