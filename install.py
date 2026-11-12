#!/usr/bin/env python3
"""AI efficiency kit: installs tools and configures detected coding agents.
No coding agents are installed. Requires platform bootstrap to provision uv/node.
"""
import argparse, json, os, pathlib, shutil, subprocess, sys, time
H=pathlib.Path.home(); ROOT=pathlib.Path(__file__).resolve().parent
STATE=H/'.local'/'share'/'ai-efficiency-kit'; STATE.mkdir(parents=True,exist_ok=True)
RESULT=[]
def cmd(name):
    p=shutil.which(name)
    if p: return p
    for base in (H/'.local'/'bin', H/'.cargo'/'bin'):
        for suffix in ('','.exe','.cmd'):
            q=base/(name+suffix)
            if q.is_file(): return str(q)
    return None
def noderun(name):
    """Runnable argv prefix for an npm-family CLI. Windows npm/npx are .cmd wrappers;
    CreateProcess cannot exec a .cmd directly, so route through cmd /c."""
    p=cmd(name)
    if not p: return None
    if sys.platform=='win32' and p.lower().endswith(('.cmd','.bat')): return ['cmd','/c',p]
    return [p]
# winget "already installed / no applicable upgrade / no newer version" exit codes (benign no-ops).
WINGET_BENIGN=(0x8A15002B,0x8A15010D,0x8A15010E)
def step(label, argv, timeout=900, cwd=None, ok_codes=(0,), env=None):
    print('>>',label,flush=True)
    try:
        # errors='replace': tool output is often not valid in the Windows ANSI code page (cp1252),
        # which would otherwise crash the capture reader thread and lose the result.
        p=subprocess.run([str(a) for a in argv], cwd=cwd, capture_output=True,
                         encoding='utf-8', errors='replace', timeout=timeout, env=env)
        detail=((p.stdout or '')+'\n'+(p.stderr or '')).strip()[-2200:]
        okset={c & 0xFFFFFFFF for c in ok_codes}; ok=(p.returncode & 0xFFFFFFFF) in okset
    except Exception as e: ok=False;detail=str(e)
    RESULT.append({'item':label,'status':'ok' if ok else 'failed','detail':detail})
    if not ok: print('FAILED:',label,detail[-400:],flush=True)
    return ok
def mark(label,status,detail=''):
    RESULT.append({'item':label,'status':status,'detail':detail});print(status.upper(),label,detail[:150],flush=True)
def backup(path):
    if path.exists(): shutil.copy2(path,path.with_name(path.name+'.bak-ai-kit-'+time.strftime('%Y%m%d%H%M%S')))
def json_merge(path, change):
    path.parent.mkdir(parents=True,exist_ok=True)
    try: base=json.loads(path.read_text(encoding='utf8')) if path.exists() else {}
    except Exception as e: mark('config '+str(path),'failed','JSON cannot be safely merged: '+str(e));return
    if not isinstance(base,dict):mark('config '+str(path),'failed','Expected JSON object');return
    def merge(dst,src):
        for k,v in src.items():
            if k in dst and isinstance(dst[k],dict) and isinstance(v,dict):merge(dst[k],v)
            else:dst[k]=v
    previous=json.dumps(base,sort_keys=True);merge(base,change)
    if json.dumps(base,sort_keys=True)!=previous:
        backup(path);path.write_text(json.dumps(base,indent=2)+'\n',encoding='utf8')
    mark('config '+str(path),'ok')
def inject(path,tag,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    old=path.read_text(encoding='utf8') if path.exists() else ''
    b=f'<!-- ai-kit:{tag}:start -->';e=f'<!-- ai-kit:{tag}:end -->'
    block=b+'\n'+data.strip()+'\n'+e
    if (b in old)!=(e in old):mark('inject '+str(path),'failed','Mismatched markers');return
    new=old.split(b)[0]+block+old.split(e,1)[1] if b in old else old.rstrip()+'\n\n'+block+'\n'
    if new!=old:backup(path);path.write_text(new,encoding='utf8')
    mark('inject '+str(path),'ok')
def install_hook(basename,matcher,label,detail):
    # Copy a PreToolUse hook to a stable path and APPEND it to ~/.claude/settings.json's
    # PreToolUse list without clobbering existing hooks.
    src=ROOT/'hooks'/basename
    if not src.is_file():mark(label,'failed','hooks/'+basename+' missing');return
    dest=STATE/basename
    try:shutil.copy2(src,dest)
    except Exception as e:mark(label,'failed','copy: '+str(e));return
    settings=H/'.claude'/'settings.json'
    cmdline='python3 -I "'+str(dest)+'"'
    try:base=json.loads(settings.read_text(encoding='utf8')) if settings.exists() else {}
    except Exception as e:mark(label,'failed','settings.json not valid JSON: '+str(e));return
    if not isinstance(base,dict):mark(label,'failed','settings.json is not an object');return
    hooks=base.setdefault('hooks',{});pre=hooks.setdefault('PreToolUse',[])
    if not isinstance(pre,list):mark(label,'failed','hooks.PreToolUse is not a list');return
    if any(isinstance(e,dict) and any(isinstance(h,dict) and basename in str(h.get('command','')) for h in e.get('hooks',[])) for e in pre):
        mark(label,'ok','Already installed');return
    pre.append({'matcher':matcher,'hooks':[{'type':'command','command':cmdline}]})
    settings.parent.mkdir(parents=True,exist_ok=True);backup(settings)
    settings.write_text(json.dumps(base,indent=2)+'\n',encoding='utf8')
    mark(label,'ok',detail)

def install_guard():
    install_hook('guard-pretooluse.py','Bash|Read|Edit|Write|NotebookEdit','guard hook',
                 'Installed PreToolUse safety net (deny-list; not a sandbox)')

def install_enforce():
    install_hook('efficiency-pretooluse.py','Bash','efficiency enforcement hook',
                 'Installed PreToolUse rtk routing (AIKIT_ENFORCE=block|warn|off; default block)')

def repo(slug):
    dest=STATE/slug.rsplit('/',1)[-1]
    if (dest/'.git').exists():step('update '+slug,['git','-C',dest,'pull','--ff-only'])
    elif not dest.exists():step('clone '+slug,['git','clone','--depth','1','https://github.com/'+slug+'.git',dest])
    else:mark('clone '+slug,'failed','Directory exists but is not Git checkout')
    return dest

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--no-context7',action='store_true');ap.add_argument('--no-extras',action='store_true');ap.add_argument('--guard',action='store_true',help='Install the PreToolUse safety-net guard hook into ~/.claude/settings.json');ap.add_argument('--enforce',action='store_true',help='Install the PreToolUse efficiency hook that routes verbose Bash commands to rtk'); args=ap.parse_args()
    try:
        for name in ('uv','node','npm','git'):
            if not cmd(name):mark('prerequisite '+name,'failed','Platform bootstrap did not provide executable')
        if not cmd('uv') or not cmd('npm'):return 2
        step('Python runtime',['uv','python','install','3.13'])
        # Pinned to reviewed versions (2026-11-03); re-vet on bump. serena==2.1.0 also closes CVE-2026-109965. See VETTING.md.
        for label,pkg in [('Serena','serena-agent==2.1.0'),('jCodeMunch','jcodemunch-mcp==1.108.411'),('jDocMunch','jdocmunch-mcp==1.150.1')]:
            step(label,['uv','tool','install','--python','3.13',pkg])
        for exe,flags in [('serena',['init'])]:
            if cmd(exe):step(exe+' initialization',[cmd(exe),*flags])
            else:mark(exe+' initialization','failed','Executable unavailable')
        # Pinned to reviewed versions (2026-11-03); re-vet on bump.
        npm_wanted=[('ast-grep','@ast-grep/cli@0.51.1'),('tree-sitter','tree-sitter-cli@0.27.1')]
        npm_missing=[spec for exe,spec in npm_wanted if not cmd(exe)]
        # repomix pinned ==1.18.1 (>=1.14.1 closes CVE-2026-49987, an 8.8 RCE) and ALWAYS installed
        # (not skip-if-present) so an older local copy is upgraded, not skipped. See VETTING.md.
        npm_missing.append('repomix@1.18.1')
        npm=noderun('npm');npx=noderun('npx')
        # On Unix, apt/dnf node sets npm's global prefix to /usr, so `npm -g` writes bins into
        # /usr/bin -- needs root and collides with system bins (e.g. @ast-grep/cli's `sg` vs
        # /usr/bin/sg). Install into ~/.local instead: no root, no collision, and ~/.local/bin
        # is already the path cmd()/verify.py resolve. Windows (%APPDATA%\npm) is left alone.
        npm_env=None
        if sys.platform!='win32':
            (H/'.local'/'bin').mkdir(parents=True,exist_ok=True)
            npm_env={**os.environ,'npm_config_prefix':str(H/'.local')}
        step('Node command-line utilities',[*npm,'install','-g',*npm_missing],timeout=1200,env=npm_env)
        if sys.platform=='win32':step('RTK Windows',['winget','install','--id','rtk-ai.rtk','--exact','--accept-source-agreements','--accept-package-agreements','--disable-interactivity'],ok_codes=(0,*WINGET_BENIGN))
        elif sys.platform=='darwin':step('RTK macOS',['brew','install','rtk-ai/tap/rtk'])
        else:
            # Pin the installer script to a release tag (not master) and pin the version it fetches. See VETTING.md.
            rtk_ref='v1.1.0'
            script=STATE/'rtk-install.sh'
            if step('RTK script download',['curl','-fsSL','https://raw.githubusercontent.com/rtk-ai/rtk/'+rtk_ref+'/install.sh','-o',script]):
                step('RTK Linux',['env','RTK_VERSION='+rtk_ref,'sh',script])
        if cmd('rtk'):step('RTK dashboard',[cmd('rtk'),'gain'])
        else:mark('RTK verification','failed','rtk executable missing')
        cav=repo('JuliusBrussee/caveman')
        installer=cav/'installer'/'install.js'
        if not installer.exists():installer=cav/'bin'/'install.js'
        if installer.exists():step('Caveman detected-agent integration',['node',installer,'--all','--non-interactive'],timeout=1200)
        else:mark('Caveman','failed','Upstream installer not found')
        for label,slug in [('Ponytail','DietrichGebert/ponytail'),('Context Canary and Loop Factory','JuliusBrussee/skills')]:
            step(label+' global skills',[*npx,'-y','skills','add',slug,'--global','--yes'],timeout=1200)
        # token-saviour: install the kit-vetted local fork (upstream curl|bash + hook-wiring removed). See VETTING.md.
        ts=ROOT/'skills'/'token-saviour'
        if (ts/'SKILL.md').exists():step('token-saviour (kit-vetted) global skill',[*npx,'-y','skills','add',str(ts),'--global','--yes'],timeout=1200)
        else:mark('token-saviour','failed','Kit-local skill missing at '+str(ts))
        ben=repo('JetBrains/benjamin-plus-skill')/'injected-instruction.md'
        if ben.exists():
            contents=ben.read_text(encoding='utf8')
            for path in (H/'.claude'/'CLAUDE.md',H/'.codex'/'AGENTS.md',H/'.config'/'opencode'/'AGENTS.md',H/'.openclaw'/'workspace'/'AGENTS.md'):
                # Don't create phantom agent homes for agents that aren't installed.
                if path.parent.exists():inject(path,'benjamin-plus',contents)
                else:mark('inject '+str(path),'skipped','Agent config directory absent')
        else:mark('Benjamin-Plus','failed','Source file missing')
        # Always-on token-routing instruction (soft: raises tool use; --enforce makes it hard for Bash).
        pol=ROOT/'configs'/'efficiency-policy.md'
        if pol.exists():
            poltext=pol.read_text(encoding='utf8')
            for path in (H/'.claude'/'CLAUDE.md',H/'.codex'/'AGENTS.md',H/'.config'/'opencode'/'AGENTS.md',H/'.openclaw'/'workspace'/'AGENTS.md'):
                if path.parent.exists():inject(path,'efficiency-routing',poltext)
                else:mark('inject '+str(path),'skipped','Agent config directory absent')
        else:mark('efficiency routing policy','failed','configs/efficiency-policy.md missing')
        # jCodeMunch owns a tested multi-client initializer. Avoid model-facing hook spam.
        if cmd('jcodemunch-mcp'):step('jCodeMunch agent auto-registration',[cmd('jcodemunch-mcp'),'init','--yes'],timeout=1200)
        else:mark('jCodeMunch registration','failed','Executable unavailable')
        if cmd('jdocmunch-mcp'):step('jDocMunch auto-registration',[cmd('jdocmunch-mcp'),'init','--yes'],timeout=1200)
        else:mark('jDocMunch registration','failed','Executable unavailable')
        # Serena: configure verified native JSON formats for detected IDEs.
        serena=[cmd('serena') or 'serena','start-mcp-server','--project-from-cwd']
        stdio={'command':serena[0],'args':serena[1:]}
        if (H/'.cursor').is_dir():json_merge(H/'.cursor'/'mcp.json',{'mcpServers':{'serena':stdio}})
        if (H/'.config'/'opencode').is_dir():
            cfg=H/'.config'/'opencode'/'opencode.json'
            # Don't touch JSONC; use agent CLI for v2 instead of writing incompatible config.
            if cmd('opencode'):
                # OpenCode v1 and v2 use different schemas; delegate to native registration.
                step('OpenCode Serena MCP registration',[cmd('opencode'),'mcp','add','serena','--',*serena])
            elif cfg.exists():mark('OpenCode MCP registration','skipped','OpenCode executable absent')
        if cmd('claude'):
            step('Claude Code Serena MCP registration',[cmd('claude'),'mcp','add','--scope','user','serena','--',*serena])
        if cmd('codex'):
            step('Codex Serena MCP registration',[cmd('codex'),'mcp','add','serena','--',*serena])
        # MCP extras: install locally; activation of overlapping proxies is deliberately distinct.
        if args.no_extras:
            mark('MCP extras','skipped','--no-extras set')
        else:
            # Pinned to reviewed versions (2026-11-03); re-vet on bump. See VETTING.md.
            step('Roam source indexer',['uv','tool','install','roam-code==14.1.0'])
            step('Headroom proxy',['uv','tool','install','headroom-ai[proxy,mcp]==0.42.0'])
            if cmd('context-mode'):mark('Context Mode','ok','Already present')
            else:step('Context Mode',[*noderun('npm'),'install','-g','context-mode@1.0.169'],env=npm_env)
        if not args.no_context7:
            # Context7 is a REMOTE MCP. Never run interactive ctx7 setup here.
            # An existing configuration is a successful no-op; do not touch authentication.
            url='https://mcp.context7.com/mcp'
            if (H/'.cursor').is_dir():
                json_merge(H/'.cursor'/'mcp.json',{'mcpServers':{'context7':{'url':url}}})
            if (H/'.config'/'opencode').is_dir():
                # OpenCode JSON config; don't parse or overwrite JSONC configs.
                op=H/'.config'/'opencode'/'opencode.json'
                if op.exists() or not (H/'.config'/'opencode'/'opencode.jsonc').exists():
                    json_merge(op,{'mcp':{'context7':{'type':'remote','url':url,'enabled':True}}})
                else: mark('OpenCode Context7','skipped','JSONC config detected; manual setup required')
            if (H/'.codex').is_dir():
                toml=H/'.codex'/'config.toml'
                existing=toml.read_text(encoding='utf8') if toml.exists() else ''
                if '[mcp_servers.context7]' in existing:
                    mark('Codex Context7','ok','Existing registration preserved')
                elif cmd('codex'):
                    step('Codex Context7 remote MCP',[cmd('codex'),'mcp','add','context7','--url',url],timeout=45)
                else:mark('Codex Context7','skipped','Codex executable not detected')
            if cmd('claude'):
                # Query first: avoid duplicate registration and auth prompts.
                try:
                    check=subprocess.run([cmd('claude'),'mcp','get','context7'],capture_output=True,text=True,timeout=15)
                    already=check.returncode==0
                except Exception:already=False
                if already:mark('Claude Context7','ok','Existing registration preserved')
                else:step('Claude Context7 remote MCP',[cmd('claude'),'mcp','add','--scope','user','--transport','http','context7',url],timeout=45)
            mark('Context7 authentication','manual','Existing auth untouched. Connect OAuth in your coding agent if requested: '+url)
        if args.guard:install_guard()
        else:mark('guard hook','skipped','Run with --guard to install the PreToolUse safety net')
        if args.enforce:install_enforce()
        else:mark('efficiency enforcement hook','skipped','Run with --enforce to route verbose Bash through rtk')
        versions={}
        for n in ('rg','fd','fdfind','jq','git','ctags','tree-sitter','ast-grep','repomix','rtk','bat','batcat','fzf','sd','delta','hyperfine','shellcheck','serena','jcodemunch-mcp','jdocmunch-mcp'):
            versions[n]=cmd(n) or None
        (ROOT/'install-report.json').write_text(json.dumps({'platform':sys.platform,'results':RESULT,'executables':versions},indent=2)+'\n',encoding='utf8')
        failures=sum(r['status']=='failed' for r in RESULT)
        print('FINISHED:',len(RESULT),'steps;',failures,'failures. See install-report.json')
        return 1 if failures else 0
    finally:
        if not (ROOT/'install-report.json').exists():
            (ROOT/'install-report.json').write_text(json.dumps({'results':RESULT},indent=2))
if __name__=='__main__':sys.exit(main())
