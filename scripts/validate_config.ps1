param(
    [string]$ConfigPath = "shadowrocket-rules/nodnsleak-pk.ini"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
    throw "Config not found: $ConfigPath"
}

$text = [System.IO.File]::ReadAllText((Resolve-Path -LiteralPath $ConfigPath))
if ($text.Contains("`r")) {
    throw "Config must use LF line endings"
}

$expectedSections = @("General", "Rule", "Host", "URL Rewrite")
$sections = [regex]::Matches($text, '(?m)^\[([^]]+)]$') | ForEach-Object { $_.Groups[1].Value }
if (($sections -join "|") -ne ($expectedSections -join "|")) {
    throw "Expected sections $($expectedSections -join ', '); got $($sections -join ', ')"
}

$general = ($text -split '\[General\]', 2)[1] -split '\[Rule\]', 2 | Select-Object -First 1
$requiredKeys = @("dns-server", "fallback-dns-server", "dns-fallback-system", "dns-direct-system")
$keys = $general -split "`n" |
    Where-Object { $_ -match '=' -and $_ -notmatch '^\s*#' } |
    ForEach-Object { ($_ -split '=', 2)[0].Trim() }

foreach ($key in $requiredKeys) {
    if ($key -notin $keys) {
        throw "Missing General key: $key"
    }
}

if ($general -match '(?m)^dns-server\s*=\s*system\s*$') {
    throw "dns-server must not use the system resolver"
}
if ($general -notmatch '(?m)^dns-fallback-system\s*=\s*false\s*$') {
    throw "System DNS fallback must stay disabled"
}

$ruleSection = (($text -split '\[Rule\]', 2)[1] -split '\[Host\]', 2)[0]
$rules = $ruleSection -split "`n" |
    ForEach-Object { $_.Trim() } |
    Where-Object { $_ -and $_ -notmatch '^#' }

if ($rules.Count -eq 0 -or $rules[-1] -ne "FINAL,PROXY") {
    throw "FINAL,PROXY must be the last routing rule"
}

foreach ($rule in $rules | Where-Object { $_ -match '^RULE-SET,' }) {
    if (($rule.ToCharArray() | Where-Object { $_ -eq ',' }).Count -lt 2) {
        throw "Invalid RULE-SET entry: $rule"
    }
}

Write-Output "ok: $ConfigPath ($($rules.Count) rules)"
