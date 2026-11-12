#!/usr/bin/env python3
"""Verify the kit: required executables present, and MCP servers actually respond.

Binary presence is a hard check (missing required tool -> exit 1). MCP connectivity
is a best-effort liveness/handshake check reported as info/WARN (a server may need a
project or config), so it never fails the run on its own.
"""
import json, pathlib, shutil, subprocess, sys, threading
root=pathlib.Path(__file__).resolve().parent
required={'git','rg','jq','ctags','tree-sitter','ast-grep','repomix','rtk','fzf','serena','jcodemunch-mcp','jdocmunch-mcp'}
missing=[]
for name in sorted(required):
    exe=shutil.which(name)
    if not exe: missing.append(name)
    print(('OK     ' if exe else 'MISSING'),name,exe or '')
if not (shutil.which('fd') or shutil.which('fdfind')):missing.append('fd/fdfind')

def which_any(*names):
    for n in names:
        p=shutil.which(n)
        if p:return p,n
    return None,names[0]

def mcp_ping(argv,timeout=25):
    """Spawn a stdio MCP server, send JSON-RPC initialize, wait for a response line."""
    try:
        p=subprocess.Popen([str(a) for a in argv],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL,text=True,bufsize=1)
    except Exception as e:return False,'spawn failed: '+str(e)
    req=json.dumps({"jsonrpc":"2.0","id":1,"method":"initialize","params":{
        "protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"verify","version":"0"}}})
    got={}
    def reader():
        try:
            for line in p.stdout:
                line=line.strip()
                if not line:continue
                try:obj=json.loads(line)
                except Exception:continue
                if isinstance(obj,dict) and (obj.get('jsonrpc') or 'result' in obj or 'error' in obj):
                    got['ok']=True;return
        except Exception:pass
    t=threading.Thread(target=reader,daemon=True);t.start()
    try:p.stdin.write(req+"\n");p.stdin.flush()
    except Exception:pass
    t.join(timeout)
    for fn in (p.terminate,p.kill):
        try:fn();p.wait(timeout=3);break
        except Exception:continue
    return (True,'responded to initialize') if got.get('ok') else (False,'no JSON-RPC response in %ds'%timeout)

def liveness(argv,timeout=20):
    """Fallback: process starts and exits/handles --help without crashing hard."""
    try:
        p=subprocess.run([str(a) for a in argv],capture_output=True,text=True,timeout=timeout)
        return (p.returncode in (0,1,2),'ran (exit %d)'%p.returncode)
    except Exception as e:return False,str(e)

print('\nMCP connectivity (best-effort; WARN is not a hard failure):')
mcp_warn=0
# Known stdio launch commands -> real initialize handshake.
for label,argv in [
    ('serena',[shutil.which('serena') or 'serena','start-mcp-server','--project-from-cwd']),
    ('jcodemunch-mcp',[shutil.which('jcodemunch-mcp') or 'jcodemunch-mcp']),
    ('jdocmunch-mcp',[shutil.which('jdocmunch-mcp') or 'jdocmunch-mcp']),
]:
    if not shutil.which(argv[0]) and not pathlib.Path(argv[0]).exists():
        print('  SKIP   %s (not installed)'%label);continue
    ok,detail=mcp_ping(argv)
    print(('  OK     ' if ok else '  WARN   ')+label+' — '+detail)
    if not ok:mcp_warn+=1
# Uncertain MCP invocation -> liveness only.
for label,names in [('roam-code',('roam-code','roam')),('headroom',('headroom',)),('context-mode',('context-mode',))]:
    exe,_=which_any(*names)
    if not exe:print('  SKIP   %s (not installed)'%label);continue
    ok,detail=liveness([exe,'--help'])
    print(('  OK     ' if ok else '  WARN   ')+label+' — liveness: '+detail)
    if not ok:mcp_warn+=1

report=root/'install-report.json'
if report.exists():
    data=json.loads(report.read_text())
    failed=[x for x in data.get('results',[]) if x.get('status')=='failed']
    print('\nInstaller-reported failures:',len(failed))
    for entry in failed:print(' -',entry['item'])
else:print('\nNo installation report found')
print('Missing required executables:',len(missing))
print('MCP connectivity warnings:',mcp_warn,'(informational)')
sys.exit(1 if missing else 0)
