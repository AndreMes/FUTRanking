$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if (-not $env:FOOTBALL_DATA_TOKEN) {
    throw "FOOTBALL_DATA_TOKEN não está disponível. Defina-a como variável de ambiente persistente antes de automatizar."
}

$env:PYTHONPATH = "src"
python -m glicko_br.cli sync-football-data --database data/rankings.sqlite3 --season 2026
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m glicko_br.cli rebuild --database data/rankings.sqlite3
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m glicko_br.export_site_data --database data/rankings.sqlite3 --output dist/data/ranking.json
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Output "Atualização da Série A concluída."
