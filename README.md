# FUTRanking

Ranking Glicko-2 de clubes brasileiros. A primeira versão publicada acompanha
o Campeonato Brasileiro Série A.

## Princípios do modelo

- O rating, RD e volatilidade de cada clube são guardados após cada semana com jogos.
- Todas as partidas da mesma semana são calculadas contra os ratings do início
  daquele período, evitando uma ordem artificial entre jogos simultâneos.
- Semanas sem partidas fazem o RD crescer; a confiança do rating cai durante a
  pausa entre temporadas.
- A vantagem de mando é configurável (55 pontos de rating por padrão) e não
  altera o rating publicado; ela afeta somente a expectativa pré-jogo.
- O banco conserva resultados brutos e recria os snapshots derivados sempre que
  uma correção for recebida. Assim, o ranking é reproduzível e auditável.

## Uso local

```powershell
python -m glicko_br.cli init --database data/rankings.sqlite3
python -m glicko_br.cli ingest --database data/rankings.sqlite3 --csv caminho\partidas.csv
python -m glicko_br.cli rebuild --database data/rankings.sqlite3
python -m glicko_br.cli ranking --database data/rankings.sqlite3
```

O CSV deve ter as colunas `external_id,played_at,competition,home_team,away_team,home_goals,away_goals`.
`played_at` usa ISO-8601; partidas só entram quando o placar final é conhecido.

## Sincronização automática

O adaptador da API-Football descobre os IDs brasileiros a cada temporada e
busca somente partidas concluídas. Sua chave fica apenas na variável de
ambiente `API_FOOTBALL_KEY` (nunca no código ou banco):

```powershell
$env:API_FOOTBALL_KEY = "sua-chave"
python -m glicko_br.cli sync-api-football --database data/rankings.sqlite3 --season 2026
python -m glicko_br.cli rebuild --database data/rankings.sqlite3
```

Para atualizar a temporada atual e o arquivo do site em uma única execução:

```powershell
.\scripts\update_series_a.ps1
```

Cada resposta bruta é registrada no banco para auditoria. Resultados decididos
nos pênaltis contam como empate para o Glicko-2; prorrogação conta no placar.

## Série A via football-data.org

Para a fonte gratuita e oficial da Série A, crie um token em
`football-data.org` e defina-o apenas na sessão local:

```powershell
$env:FOOTBALL_DATA_TOKEN = "seu-token"
python -m glicko_br.cli sync-football-data --database data/rankings.sqlite3 --season 2024
python -m glicko_br.cli rebuild --database data/rankings.sqlite3
```

## GitHub Pages e atualização automática

O workflow `.github/workflows/update-and-deploy.yml` é executado diariamente,
recria o ranking usando as temporadas disponíveis e publica `dist/` no GitHub
Pages. Crie o secret `FOOTBALL_DATA_TOKEN` em *Settings → Secrets and variables
→ Actions* do repositório. No GitHub Pages, selecione *GitHub Actions* como
fonte de publicação.

## Fonte Sofascore (uso local)

Também há um conector local, sem chave, para importar as competições brasileiras
do Sofascore. Como a fonte não oferece API pública, ele fica isolado do restante
do modelo e armazena as respostas originais. Use com moderação:

```powershell
python -m glicko_br.cli sync-sofascore --database data/rankings.sqlite3 --season 2024
python -m glicko_br.cli rebuild --database data/rankings.sqlite3
```
