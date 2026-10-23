# Local-only R20 rule and combat smoke test.
$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
New-Item -ItemType Directory -Force -Path "artifacts\r20_smoke" | Out-Null

Write-Host "[R20] Running structural and variant regression tests..."
python -m pytest -q tests/test_r20_gauntlet.py tests/test_r20_variant_runtime.py tests/test_r20_gauntlet_report.py
if ($LASTEXITCODE -ne 0) {
    throw "R20 tests failed. No batch simulation was started."
}

# Each placement has 108 profiles x 6 opponents x 1 seat = 648 bouts.
# Half the subject fixtures use A and half use B; no seat-mirror rematches.
# Starting occupies offsets 0..647; Shuffled occupies 648..1295.
foreach ($arm in @("HIK-3", "OKD-1", "TSO-1", "KAT-1")) {
    foreach ($placement in @(
        @{ name = "starting"; offset = 0 },
        @{ name = "shuffled"; offset = 648 }
    )) {
        $target = "artifacts\r20_smoke\$arm-$($placement.name).csv"
        Write-Host "[R20] $arm in $($placement.name) placement..."
        python -m kimarite.r20_gauntlet_bouts --arm $arm --start $placement.offset --count 20 --max-turns 30 --output $target
        if ($LASTEXITCODE -ne 0) {
            throw "R20 smoke failed on $arm/$($placement.name). Inspect $target."
        }
        $rows = @(Import-Csv $target)
        if ($rows.Count -ne 20) {
            throw "R20 smoke produced $($rows.Count) rows instead of 20 for $arm/$($placement.name)."
        }
        $unresolved = @($rows | Where-Object { $_.error -ne "" -or $_.completed -ne "True" })
        if ($unresolved.Count -gt 0) {
            Write-Warning "$($unresolved.Count) unresolved smoke bouts in $target"
            throw "R20 smoke is not clean. Full run must not start."
        }
    }
}

Write-Host "[R20] Creating descriptive reports (no automatic variant ranking)..."
$files = @(Get-ChildItem "artifacts\r20_smoke\*.csv" | Select-Object -ExpandProperty FullName)
python -m kimarite.r20_gauntlet_report @files --output-dir "artifacts\r20_smoke\report"
if ($LASTEXITCODE -ne 0) {
    throw "R20 report generation failed."
}
Write-Host "[R20] Complete. Check artifacts\r20_smoke\report\variant_placement_summary.csv"
