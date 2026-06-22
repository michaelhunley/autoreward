# Inject the autoreward validation-tiers policy into YOUR project's CLAUDE.md
# (or AGENTS.md). Idempotent. Usage:
#   powershell -File install.ps1 [C:\path\to\your\project] [CLAUDE.md|AGENTS.md]
param([string]$Target = $PWD, [string]$File = "CLAUDE.md")
$ErrorActionPreference = "Stop"
$Atlas = Split-Path -Parent $MyInvocation.MyCommand.Path
$Dst = Join-Path $Target $File
$Begin = "<!-- BEGIN autoreward validation-tiers (injected) -->"
$End = "<!-- END autoreward validation-tiers -->"

$policyRaw = Get-Content (Join-Path $Atlas "AGENT_POLICY.md") -Raw
$policy = [regex]::Match($policyRaw, '(?s)```markdown\r?\n(.*?)\r?\n```').Groups[1].Value

$block = @"
$Begin
$policy

autoreward reference (read when building a gauge):
- $Atlas\gauges\by-goal.md   - worked examples by workflow goal, copy & adapt
- $Atlas\models\index.json   - B-proxy models by domain + reliability ranking
- $Atlas\README.md           - the full method
$End
"@

New-Item -ItemType Directory -Force $Target | Out-Null
if ((Test-Path $Dst) -and (Select-String -Path $Dst -SimpleMatch $Begin -Quiet)) {
    $lines = Get-Content $Dst; $out = @(); $skip = $false
    foreach ($l in $lines) {
        if ($l -match [regex]::Escape($Begin)) { $skip = $true }
        if (-not $skip) { $out += $l }
        if ($l -match [regex]::Escape($End)) { $skip = $false }
    }
    Set-Content -Path $Dst -Value $out -Encoding utf8
    "updated existing autoreward block in $Dst"
} else { "adding autoreward block to $Dst" }
Add-Content -Path $Dst -Value "`n$block" -Encoding utf8
"done. Your agent now frames validation as A/B/C (C>B>A) and can consult the atlas."
