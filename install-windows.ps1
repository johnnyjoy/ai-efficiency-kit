param([switch]$SkipContext7, [switch]$SkipExtras, [switch]$Guard, [switch]$Enforce)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$ProgressPreference = 'SilentlyContinue'  # speeds up any Invoke-WebRequest fallbacks

# --- WinGet availability + bootstrap (fresh images, Server, LTSC often lack it) ---
function Test-Winget { [bool](Get-Command winget -ErrorAction SilentlyContinue) }
if (-not (Test-Winget)) {
  Write-Warning 'WinGet not found. Attempting bootstrap via Microsoft.WinGet.Client (Repair-WinGetPackageManager).'
  try {
    if (-not (Get-Module -ListAvailable -Name Microsoft.WinGet.Client)) {
      Install-Module -Name Microsoft.WinGet.Client -Scope CurrentUser -Force -AllowClobber
    }
    Import-Module Microsoft.WinGet.Client -ErrorAction Stop
    Repair-WinGetPackageManager -AllUsers -ErrorAction Stop
  } catch {
    Write-Warning "WinGet bootstrap failed: $($_.Exception.Message)"
  }
}
if (-not (Test-Winget)) {
  throw @'
WinGet (App Installer) is required and could not be bootstrapped.
Remedies:
 - Windows 10/11: install "App Installer" from the Microsoft Store, or
   PowerShell: Install-Module Microsoft.WinGet.Client -Scope CurrentUser ; Repair-WinGetPackageManager -AllUsers
 - Windows Server 2025 (Desktop Experience) only; Server 2022/Core/Nano are unsupported — use Chocolatey or MSIs instead.
 - Fresh service account showing winget missing: sign in interactively once (winget registers per user at first sign-in),
   then verify with:  Get-AppxPackage -AllUsers Microsoft.DesktopAppInstaller
Docs: https://learn.microsoft.com/windows/package-manager/winget/
'@
}

# --- Package install with benign exit-code handling ---
# WinGet returns nonzero for "nothing to do". These are NOT failures:
#   0x8A15002B UPDATE_NOT_APPLICABLE (already current) ; 0x8A15010D INSTALL_ALREADY_INSTALLED (different version present) ; 0x8A15010E INSTALL_DOWNGRADE (higher version present)
$benign = @(0x8A15002B, 0x8A15010D, 0x8A15010E)
$promptInputError = 0x8A150042  # non-interactive run hit a prompt (msstore agreement)
$failed = @()
function Install-WingetPackage([string]$id) {
  & winget install --id $id --exact --source winget `
      --accept-source-agreements --accept-package-agreements `
      --disable-interactivity --silent
  $code = $LASTEXITCODE
  if ($code -eq 0) { return }
  $u = $code -band 0xFFFFFFFF  # normalize signed Int32 to unsigned for comparison
  if ($benign -contains $u) { Write-Host "WinGet ${id}: already present/current (0x$('{0:X}' -f $u))"; return }
  if ($u -eq $promptInputError) {
    Write-Warning "WinGet $id hit an interactive prompt (0x8A150042). Run 'winget source reset --force' once, then re-run this script."
  } else {
    Write-Warning "WinGet $id exited 0x$('{0:X}' -f $u); see install-report.json / Troubleshooting in README."
  }
  $script:failed += $id
}

$packages = @(
 'Git.Git','BurntSushi.ripgrep.MSVC','sharkdp.fd','jqlang.jq','astral-sh.uv','OpenJS.NodeJS.LTS',
 'sharkdp.bat','junegunn.fzf','chmln.sd','dandavison.delta','sharkdp.hyperfine','UniversalCtags.Ctags'
)
foreach ($id in $packages) { Install-WingetPackage $id }
if ($failed.Count) { Write-Warning "WinGet packages with non-benign exits: $($failed -join ', ')" }

# Refresh PATH in-process after WinGet installs; a new shell is the reliable fallback.
$machinePath = [Environment]::GetEnvironmentVariable('Path','Machine')
$userPath = [Environment]::GetEnvironmentVariable('Path','User')
$env:PATH = @("$HOME\.local\bin", "$HOME\.cargo\bin", "$env:ProgramFiles\Git\cmd", "$env:ProgramFiles\nodejs", "$HOME\AppData\Roaming\npm", "$env:LOCALAPPDATA\Microsoft\WinGet\Links", $machinePath, $userPath, $env:PATH) -join ';'
foreach ($n in @('uv','node','npm')) {
  if (-not (Get-Command $n -ErrorAction SilentlyContinue)) {
    throw "$n not on PATH after install. Close ALL terminals (and VS Code), open a new PowerShell window, and re-run this script. If it persists, check 'where.exe $n' and remove conflicting Node installs (nvm-windows/Scoop/Choco)."
  }
}
& uv python install 3.13
if ($LASTEXITCODE -ne 0) { throw 'uv Python install failed' }
$args2 = @('run','--no-project','--python','3.13','python','install.py')
if ($SkipContext7) {$args2 += '--no-context7'}
if ($SkipExtras) {$args2 += '--no-extras'}
if ($Guard) {$args2 += '--guard'}
if ($Enforce) {$args2 += '--enforce'}
& uv @args2
if ($LASTEXITCODE -ne 0) { throw 'Some installations failed: inspect install-report.json' }
