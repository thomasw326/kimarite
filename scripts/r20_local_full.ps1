# Resumable R20 gauntlet launch for Windows PowerShell. Never invokes GitHub Actions.
param(
    [int] $ChunkSize = 216,
    [int] $MaxTurns = 30,
    [int] $Seed = 20261010,
    [switch] $SkipSmoke
)
$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ($ChunkSize -lt 1 -or $ChunkSize -gt 648) { throw "ChunkSize must be between 1 and 648." }
if ($MaxTurns -lt 1) { throw "MaxTurns must be positive." }

$root = Join-Path (Get-Location) "artifacts\r20_full"
New-Item -ItemType Directory -Force -Path $root | Out-Null

if (-not $SkipSmoke) {
    Write-Host "[R20] Smoke gate: running regression tests and 160 sample bouts..."
    & (Join-Path $PSScriptRoot "r20_local_smoke.ps1")
    if ($LASTEXITCODE -ne 0) { throw "R20 smoke failed: full run cancelled." }
}

# Read the authoritative frozen manifest, never rebuild the arm list from styles.
$manifest = Get-Content "data\r20_kimarite_arms.json" -Raw | ConvertFrom-Json
$arms = @($manifest.arms | ForEach-Object { $_.id })
if ($arms.Count -ne 70 -or @($arms | Sort-Object -Unique).Count -ne 70) {
    throw "Expected 70 distinct R20 variants; found $($arms.Count)."
}

$expected = $arms.Count * 2 * 648
$config = @{
    seed = $Seed
    max_turns = $MaxTurns
    chunk_size = $ChunkSize
    expected_bouts = $expected
    design_sha256 = (Get-FileHash "data\r20_kimarite_arms.json" -Algorithm SHA256).Hash
}
$configPath = Join-Path $root "run_config.json"
if (Test-Path $configPath) {
    $prior = Get-Content $configPath -Raw | ConvertFrom-Json
    foreach ($key in $config.Keys) {
        if ([string]$prior.$key -ne [string]$config[$key]) {
            throw "Checkpoint $configPath belongs to another schedule ($key differs). Move the old outputs before restarting."
        }
    }
}
else {
    $config | ConvertTo-Json | Set-Content -Encoding UTF8 $configPath
}
$done = 0
$skipped = 0
foreach ($arm in $arms) {
    foreach ($placement in @("starting", "shuffled")) {
        $placementOffset = if ($placement -eq "starting") { 0 } else { 648 }
        $part = 0
        for ($index = 0; $index -lt 648; $index += $ChunkSize) {
            $n = [Math]::Min($ChunkSize, 648 - $index)
            $offset = $placementOffset + $index
            $path = Join-Path $root ("{0}_{1}_{2:d4}_{3:d3}.csv" -f $arm, $placement, $index, $n)
            if (Test-Path $path) {
                $rows = @(Import-Csv $path)
                if ($rows.Count -ne $n) {
                    throw "Checkpoint contains $($rows.Count) rows rather than $n : $path"
                }
                if (@($rows | Where-Object { $_.arm_id -ne $arm -or $_.placement -ne $placement }).Count -gt 0) {
                    throw "Checkpoint arm/placement mismatch: $path"
                }
                $done += $n
                $skipped += $n
                continue
            }
            Write-Host ("[R20] {0}/{1} offset={2}, bouts={3}, overall={4}/{5}" -f $arm, $placement, $offset, $n, $done, $expected)
            $temp = "$path.partial"
            python -m kimarite.r20_gauntlet_bouts --arm $arm --seed $Seed --start $offset --count $n --max-turns $MaxTurns --output $temp
            if ($LASTEXITCODE -ne 0) {
                throw "R20 simulator exited nonzero on $arm/$placement offset $offset"
            }
            $rows = @(Import-Csv $temp)
            if ($rows.Count -ne $n) { throw "Batch has $($rows.Count) rows, expected $n: $temp" }
            if (@($rows | Where-Object { $_.error -ne "" -or $_.completed -ne "True" }).Count -gt 0) {
                # Preserve incomplete batch for inspection; never silently mark it complete.
                Write-Warning "R20 unresolved outcomes detected. Check $temp and investigate before continuing."
                throw "R20 interrupted at $arm/$placement offset $offset (unresolved results)."
            }
            Move-Item -Force $temp $path
            $done += $n
            $part += 1
        }
    }
}

if ($done -ne $expected) { throw "Only $done of $expected bouts were checkpointed." }
Write-Host "[R20] Full schedule complete: $done / $expected bouts ($skipped resumed)."
$all = @(Get-ChildItem $root -Filter "*.csv" | Select-Object -ExpandProperty FullName)
python -m kimarite.r20_gauntlet_report @all --output-dir (Join-Path $root "report")
if ($LASTEXITCODE -ne 0) { throw "R20 final report failed." }
Write-Host "[R20] Detailed report: artifacts\r20_full\report\variant_placement_summary.csv"
