const q = new URLSearchParams(location.search), page = document.body.dataset.page, el = s => document.querySelector(s);
const dataUrl = document.body.dataset.dataUrl || './data/ranking.json';
const freshDataUrl = `${dataUrl}${dataUrl.includes('?') ? '&' : '?'}v=${Date.now()}`;
const date = v => new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium' }).format(new Date(`${v}T12:00:00`));
const time = v => new Intl.DateTimeFormat('pt-BR', { timeZone: 'America/Sao_Paulo', dateStyle: 'short', timeStyle: 'short' }).format(new Date(v));
const matchTime = v => v.includes('T') ? time(v) : date(v);
const crest = (url, name) => url ? `<img class="crest" src="${url}" alt="Brasão do ${name}" loading="lazy" referrerpolicy="no-referrer">` : '';
const club = (name, url, link = false, newTab = false) => {
  const content = `${crest(url, name)}${name}`;
  return link ? `<a class="club club-link" href="clube.html?time=${encodeURIComponent(name)}"${newTab ? ' target="_blank" rel="noopener"' : ''}>${content}</a>` : `<span class="club">${content}</span>`;
};
const countryLabel = country => String(country || '').replace(/^[A-Z]{2}\s+/, '').trim() || 'País não informado';
const countryCode = country => ({ Argentina: 'ar', Bolívia: 'bo', Bolivia: 'bo', Brasil: 'br', Brazil: 'br', Chile: 'cl', Colômbia: 'co', Colombia: 'co', Equador: 'ec', Ecuador: 'ec', Paraguai: 'py', Paraguay: 'py', Peru: 'pe', Perú: 'pe', Uruguai: 'uy', Uruguay: 'uy', Venezuela: 've' }[countryLabel(country)] || (String(country || '').match(/^([A-Z]{2})\b/) || [])[1]?.toLowerCase());
const countryFlag = country => { const code = countryCode(country), label = countryLabel(country); return code ? `<img class="country-flag" src="https://flagcdn.com/w40/${code}.png" srcset="https://flagcdn.com/w80/${code}.png 2x" width="20" height="15" alt="Bandeira do ${label}">` : ''; };
const impact = value => `<span class="impact ${value >= 0 ? 'positive' : 'negative'}">${value >= 0 ? '+' : ''}${value?.toFixed(1) ?? '—'}</span>`;
const navigation = `<a href="ranking.html">Ranking</a><a href="resultados.html">Resultados</a><a href="proximos-jogos.html">Próximos jogos</a><a href="comparar.html">Comparar</a><a href="odds.html">Odds</a><a href="simulacoes.html">Simulações</a>`;
const shell = (title, kicker = 'Brasil · CONMEBOL') => `<header class="top"><div class="wrap"><a class="brand" href="index.html"><span class="mark">↗</span>FUTRanking</a><nav>${navigation}</nav><span class="pill">${kicker}</span></div></header><main class="wrap page"><div class="eyebrow">${kicker}</div><h1>${title}</h1><div id="content"></div></main><footer class="foot"><div class="wrap footer-wrap"><span>FUTRanking · Glicko-2 para o futebol sul-americano</span><span class="footer-links"><a href="dados.html">Dados</a><a href="metodo.html">Método</a></span></div></footer>`;
const stageName = stage => ({LAST_16: 'Oitavas de final', QUARTER_FINALS: 'Quartas de final', SEMI_FINALS: 'Semifinal', FINAL: 'Final', THIRD_PLACE: 'Disputa do 3º lugar'}[stage] || stage?.replaceAll('_', ' '));
function matchContext(m) { const date = m.played_at || m.scheduled_at; const season = m.season || (date ? String(date).slice(0, 4) : ''); const parts = [[m.competition, season].filter(Boolean).join(' ')]; if (m.stage && m.stage !== 'REGULAR_SEASON') parts.push(stageName(m.stage)); else if (m.matchday) parts.push(`Rodada ${m.matchday}`); if (m.group_name) parts.push(m.group_name); if (m.neutral_site) parts.push('Campo neutro'); else if (Number(m.home_advantage) < 0) parts.push('Mando visitante'); return parts.filter(Boolean).join(' · '); }
const contextStyle = document.createElement('style');
contextStyle.textContent = '.competition{display:block;margin-top:4px;color:#006b54;font-size:.68rem;font-weight:800;line-height:1.25}.club-meta{margin:-7px 0 23px;color:#5b6f68;font-size:.92rem}.club-meta strong{color:#075c42}.list-tools{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:24px 0 12px}.list-search,.list-filter{padding:11px 13px;border:1px solid #d8d0c1;border-radius:9px;background:#fffdf8;color:#10231d;font:inherit}.list-search{width:min(100%,420px)}.list-filter{min-width:175px}.pager{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:14px 0 4px;color:#5b6f68;font-size:.88rem}.pager-actions{display:flex;gap:8px}.pager button{border:1px solid #d8d0c1;border-radius:7px;background:#fffdf8;color:#10231d;padding:7px 10px;font:inherit;font-weight:700;cursor:pointer}.pager button:disabled{opacity:.45;cursor:not-allowed}.empty-list{padding:22px;text-align:center;color:#5b6f68}.chart-card{margin:30px 0 34px;padding:24px;border:1px solid #d8d0c1;border-radius:16px;background:#fffdf8}.chart-card h2{margin:0 0 6px}.chart-card p{margin:0 0 16px;color:#5b6f68}.rating-chart{display:block;width:100%;height:auto;overflow:visible}.rating-chart .grid{stroke:#e5ddd0;stroke-width:1}.rating-chart .axis-label{fill:#687a73;font-size:11px}.rating-chart .line{fill:none;stroke:#006b54;stroke-width:3;stroke-linecap:round;stroke-linejoin:round}.rating-chart .point{fill:#f4b942;stroke:#006b54;stroke-width:2}.chart-summary{display:flex;gap:20px;margin-top:12px;color:#5b6f68;font-size:.88rem}.chart-summary strong{color:#10231d}.footer-wrap{display:flex;align-items:center;justify-content:space-between;gap:18px}.footer-links{display:flex;gap:16px}.footer-links a{color:#d5e7d9;text-decoration:none}.footer-links a:hover,.footer-links a:focus-visible{color:#b6e851;text-decoration:underline}@media(max-width:650px){.list-tools{margin-top:18px}.pager{align-items:flex-start;flex-direction:column}.chart-card{padding:16px}.chart-summary{gap:12px;flex-wrap:wrap}.footer-wrap{align-items:flex-start;flex-direction:column;gap:10px}}';
document.head.append(contextStyle);
const chartControlsStyle = document.createElement('style');
chartControlsStyle.textContent = '.chart-controls{display:flex;align-items:end;gap:10px;flex-wrap:wrap;margin:18px 0}.chart-presets{display:flex;gap:6px;flex-wrap:wrap}.chart-periods{margin-left:auto}.chart-presets button{border:1px solid #d8d0c1;border-radius:99px;background:#fffdf8;color:#10231d;padding:7px 10px;font:inherit;font-size:.8rem;font-weight:750;cursor:pointer}.chart-presets button.active{background:#075c42;border-color:#075c42;color:#fff}.chart-date{display:grid;gap:4px;color:#5b6f68;font-size:.72rem;font-weight:750}.chart-date input{border:1px solid #d8d0c1;border-radius:7px;background:#fffdf8;color:#10231d;padding:7px;font:inherit}@media(max-width:700px){.chart-periods{margin-left:0}}';
document.head.append(chartControlsStyle);
const countryFlagStyle = document.createElement('style');
countryFlagStyle.textContent = '.country-flag{width:20px;height:15px;object-fit:cover;margin-right:6px;border-radius:2px;vertical-align:-2px;box-shadow:0 0 0 1px rgba(7,92,66,.14)}';
document.head.append(countryFlagStyle);
const chartDynamicStyle = document.createElement('style');
chartDynamicStyle.textContent = '.chart-canvas{position:relative}.rating-chart{touch-action:pan-y;cursor:crosshair}.rating-chart .area{fill:url(#rating-area);opacity:.32}.rating-chart .crosshair{stroke:#6d7e77;stroke-width:1;stroke-dasharray:4 4;pointer-events:none}.rating-chart .focus{fill:#fffdf8;stroke:#075c42;stroke-width:3;pointer-events:none}.rating-chart .hitbox{fill:transparent}.chart-tooltip{position:absolute;z-index:2;min-width:155px;max-width:220px;pointer-events:none;border:1px solid #d8d0c1;border-radius:10px;background:#10231d;color:#fffdf8;box-shadow:0 10px 24px rgba(16,35,29,.18);padding:10px 12px;font-size:.8rem;line-height:1.35;transform:translate(-50%,calc(-100% - 12px));transition:opacity .12s ease}.chart-tooltip[hidden]{display:none}.chart-tooltip strong{display:block;margin-top:2px;font-size:1rem}.chart-tooltip::after{content:"";position:absolute;left:50%;bottom:-6px;width:10px;height:10px;background:#10231d;transform:translateX(-50%) rotate(45deg)}.chart-tip-date{color:#cfdbd5;font-size:.74rem}';
document.head.append(chartDynamicStyle);
const simulationStyle = document.createElement('style');
simulationStyle.textContent = '.simulation-note{max-width:760px;margin-bottom:20px}.simulation-tabs{display:flex;gap:8px;flex-wrap:wrap;margin:18px 0 26px}.simulation-tabs button{border:1px solid #d8d0c1;border-radius:999px;background:#fffdf8;color:#10231d;padding:8px 13px;font:inherit;font-size:.85rem;font-weight:800;cursor:pointer}.simulation-tabs button.active{background:#075c42;border-color:#075c42;color:#fff}.simulation-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:22px}.simulation-grid h2{margin-top:0}.simulation-row{grid-template-columns:40px 1fr 66px 82px}.simulation-row strong{text-align:right}.simulation-method{max-width:820px;margin-top:42px;padding:24px;border-left:4px solid #075c42;background:#e9f0e8}.simulation-method h2{margin-top:0}.simulation-method p{color:#34473f}.simulation-unavailable{padding:26px}@media(max-width:780px){.simulation-grid{grid-template-columns:1fr}.simulation-row{grid-template-columns:32px 1fr 54px 72px;font-size:.82rem}}';
document.head.append(simulationStyle);
const simulationVisibilityStyle = document.createElement('style');
simulationVisibilityStyle.textContent = '.simulation-grid{grid-template-columns:repeat(3,minmax(0,1fr));align-items:start;gap:26px}.simulation-grid>div{display:flex;min-width:0;flex-direction:column}.simulation-grid h2{min-height:2.4em;margin:0;font-size:clamp(1.25rem,2vw,1.55rem);line-height:1.2}.simulation-grid>div>p{min-height:7.4em;margin:0}.simulation-grid .panel{width:100%;margin-top:18px}.simulation-row{grid-template-columns:32px minmax(0,1fr) 48px 74px;gap:8px;padding:14px 12px}.simulation-row b{min-width:0;overflow:hidden}.simulation-row .club{min-width:0;max-width:100%;gap:6px;white-space:normal}.simulation-row .club-link{overflow-wrap:anywhere}.simulation-row strong{white-space:nowrap;font-size:.92rem}.simulation-row.table-head{font-size:.66rem}@media(max-width:1040px){.simulation-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:680px){.simulation-grid{grid-template-columns:1fr;gap:32px}.simulation-grid h2,.simulation-grid>div>p{min-height:0}.simulation-row{grid-template-columns:30px minmax(0,1fr) 46px 72px;padding:13px 11px}.simulation-row .club{font-size:.84rem}.simulation-row strong{font-size:.86rem}}';
document.head.append(simulationVisibilityStyle);
const comparisonStyle = document.createElement('style');
comparisonStyle.textContent = '.compare-tools{display:grid;grid-template-columns:1fr 1fr;gap:12px;max-width:760px;margin:22px 0}.compare-tools label,.venue-control{display:grid;gap:6px;color:#5b6f68;font-size:.76rem;font-weight:800}.compare-tools select,.venue-control select{border:1px solid #d8d0c1;border-radius:9px;background:#fffdf8;color:#10231d;padding:11px 12px;font:inherit}.compare-card{overflow:hidden;border:1px solid #d8d0c1;border-radius:16px;background:#fffdf8}.compare-teams{display:grid;grid-template-columns:1fr auto 1fr;align-items:stretch}.compare-team{padding:24px;text-align:center}.compare-team:last-child{border-left:1px solid #d8d0c1}.compare-team .club{font-size:1.05rem;font-weight:850}.compare-team strong{display:block;margin-top:13px;font-size:2.3rem;letter-spacing:-.06em}.compare-team small{display:block;margin-top:3px;color:#5b6f68}.compare-vs{display:grid;place-items:center;padding:0 20px;background:#075c42;color:#b6e851;font-weight:900;font-size:1.1rem}.matchup{display:grid;grid-template-columns:1fr auto;gap:16px;align-items:center;padding:18px 24px;border-top:1px solid #d8d0c1;background:#eef3ea}.matchup h2{margin:0 0 5px;font-size:1rem}.matchup p{margin:0;font-size:.84rem}.matchup-probability{font-size:1.28rem;font-weight:900;white-space:nowrap}.compare-chart{margin-top:30px;padding:22px;border:1px solid #d8d0c1;border-radius:16px;background:#fffdf8}.compare-chart h2{margin:0 0 5px}.compare-chart p{margin:0 0 16px}.comparison-chart{display:block;width:100%;height:auto}.comparison-chart .grid{stroke:#e5ddd0}.comparison-chart .axis{fill:#687a73;font-size:11px}.comparison-chart .line-a{fill:none;stroke:#075c42;stroke-width:3}.comparison-chart .line-b{fill:none;stroke:#d0782a;stroke-width:3}.compare-legend{display:flex;gap:16px;flex-wrap:wrap;margin-top:12px;font-size:.84rem;font-weight:750}.compare-legend span::before{content:"";display:inline-block;width:10px;height:10px;margin-right:6px;border-radius:99px;background:#075c42}.compare-legend span:last-child::before{background:#d0782a}@media(max-width:650px){.compare-tools{grid-template-columns:1fr}.compare-team{padding:17px 10px}.compare-team .club{font-size:.85rem}.compare-team strong{font-size:1.8rem}.compare-vs{padding:0 9px}.matchup{grid-template-columns:1fr;padding:17px}.matchup-probability{font-size:1.12rem}.venue-control{width:100%}}';
document.head.append(comparisonStyle);
const comparisonInteractionStyle = document.createElement('style');
comparisonInteractionStyle.textContent = '.compare-tools input{width:100%;border:1px solid #d8d0c1;border-radius:9px;background:#fffdf8;color:#10231d;padding:11px 12px;font:inherit}.head-to-head{display:flex;align-items:center;justify-content:space-between;gap:22px;margin-top:26px;padding:20px 22px;border:1px solid #d8d0c1;border-radius:16px;background:#eef3ea}.head-to-head h2{margin:0 0 4px;font-size:1.1rem}.head-to-head p{margin:0;font-size:.84rem}.h2h-stats{display:flex;gap:18px;align-items:stretch}.h2h-stats span{display:grid;gap:4px;max-width:120px;color:#5b6f68;font-size:.72rem;line-height:1.2;text-align:center}.h2h-stats strong{color:#10231d;font-size:1.55rem}.compare-canvas{position:relative}.comparison-chart{touch-action:pan-y;cursor:crosshair}.comparison-chart .compare-crosshair{stroke:#6d7e77;stroke-width:1;stroke-dasharray:4 4;pointer-events:none}.comparison-chart .compare-focus{pointer-events:none;stroke:#fffdf8;stroke-width:2}.comparison-chart .focus-a{fill:#075c42}.comparison-chart .focus-b{fill:#d0782a}.comparison-chart .compare-hitbox{fill:transparent}.compare-tooltip{position:absolute;z-index:2;min-width:205px;pointer-events:none;border:1px solid #d8d0c1;border-radius:10px;background:#10231d;color:#fffdf8;box-shadow:0 10px 24px rgba(16,35,29,.18);padding:10px 12px;font-size:.8rem;line-height:1.35;transform:translate(-50%,calc(-100% - 12px))}.compare-tooltip[hidden]{display:none}.compare-tooltip::after{content:"";position:absolute;left:50%;bottom:-6px;width:10px;height:10px;background:#10231d;transform:translateX(-50%) rotate(45deg)}@media(max-width:650px){.head-to-head{align-items:flex-start;flex-direction:column}.h2h-stats{width:100%;justify-content:space-between;gap:8px}.h2h-stats span{max-width:31%}}';
document.head.append(comparisonInteractionStyle);
const rankingFilterStyle = document.createElement('style');
rankingFilterStyle.textContent = '.ranking-filters{display:flex;align-items:center;flex-wrap:wrap;gap:8px;margin:22px 0 14px}.ranking-filters button{border:1px solid #d8d0c1;border-radius:999px;background:#fffdf8;color:#10231d;padding:8px 13px;font:inherit;font-size:.85rem;font-weight:800;cursor:pointer}.ranking-filters button.active{background:#075c42;border-color:#075c42;color:#fff}.country-filter{margin-left:auto;min-width:190px;padding:8px 11px;border:1px solid #d8d0c1;border-radius:9px;background:#fffdf8;color:#10231d;font:inherit;font-size:.85rem;font-weight:750}.ranking-summary{margin:0 0 12px;color:#5b6f68;font-size:.9rem}@media(max-width:620px){.country-filter{width:100%;margin-left:0}}';
document.head.append(rankingFilterStyle);
const clubLinkStyle = document.createElement('style');
clubLinkStyle.textContent = '.club-link{color:inherit;text-decoration:none}.club-link:hover,.club-link:focus-visible{color:#075c42;text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:3px}';
document.head.append(clubLinkStyle);
const backtestStyle = document.createElement('style');
backtestStyle.textContent = '.backtest-tools{margin:24px 0 4px}.backtest-tools select{min-width:250px;padding:10px 12px;border:1px solid #d8d0c1;border-radius:9px;background:#fffdf8;color:#10231d;font:inherit}.backtest-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:22px 0}.backtest-stat{padding:16px;border:1px solid #d8d0c1;border-radius:12px;background:#fffdf8}.backtest-stat b{display:block;font-size:1.35rem}.backtest-stat span{display:block;margin-top:4px;color:#5b6f68;font-size:.7rem;font-weight:800;letter-spacing:.06em;text-transform:uppercase}.backtest-row{grid-template-columns:1fr 85px 115px 115px 90px}.backtest-row strong{text-align:right}.backtest-note{max-width:830px;margin-top:30px}.backtest-note h2{margin-bottom:8px}.model-selection{margin-top:42px}.model-selection-panel{margin-top:16px}.model-selection-row{grid-template-columns:1fr 1fr 1fr minmax(130px,1.4fr)}.model-window-row{grid-template-columns:1fr minmax(160px,1.4fr) 90px 90px minmax(110px,1fr)}.model-selection-row strong,.model-window-row strong{text-align:right}.model-selection-row.winner{background:#e9f0e8;font-weight:850}@media(max-width:700px){.backtest-stats{grid-template-columns:repeat(2,1fr)}.backtest-panel,.model-selection-panel{overflow-x:auto}.backtest-panel #content .row.backtest-row,.backtest-panel .row.backtest-row{display:grid;min-width:570px;grid-template-columns:1fr 85px 115px 115px 90px;padding:12px}.model-selection-panel .row.model-selection-row{display:grid;min-width:440px;grid-template-columns:1fr 1fr 1fr 1.4fr;padding:12px}.model-selection-panel .row.model-window-row{display:grid;min-width:590px;grid-template-columns:1fr 1.4fr 90px 90px 1fr;padding:12px}.backtest-tools select{width:100%;min-width:0}}';
document.head.append(backtestStyle);
const oddsStyle = document.createElement('style');
oddsStyle.textContent = '.odds-intro{max-width:820px}.odds-toolbar{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;margin:24px 0 12px}.odds-status{color:#5b6f68;font-size:.86rem}.odds-refresh{border:1px solid #075c42;border-radius:9px;background:#075c42;color:#fff;padding:10px 13px;font:inherit;font-size:.84rem;font-weight:850;cursor:pointer}.odds-refresh:disabled{opacity:.6;cursor:wait}.odds-panel{margin-top:0}.odds-row{grid-template-columns:minmax(190px,1.35fr) minmax(105px,.75fr) 90px 102px 92px;gap:14px}.odds-row>span,.odds-row>strong{min-width:0}.odds-game{display:grid;gap:4px}.odds-game strong{font-size:.9rem}.odds-game small{color:#5b6f68;font-size:.72rem}.odds-selection{font-weight:800}.odds-model,.odds-market,.odds-alpha{text-align:right;font-variant-numeric:tabular-nums}.odds-alpha{color:#075c42;font-weight:900}.odds-link{color:#075c42;font-weight:800;font-size:.78rem;text-decoration:none}.odds-link:hover{text-decoration:underline}.odds-note{max-width:850px;margin-top:28px;padding:17px 19px;border-left:4px solid #b6e851;background:#e9f0e8;color:#34473f;font-size:.86rem;line-height:1.55}.odds-warning{margin-top:20px;padding:17px;border:1px solid #e3c7c0;border-radius:12px;background:#fff7f4;color:#7d4037}.odds-warning p{margin:0;color:inherit}.brazil-odds-row{grid-template-columns:minmax(240px,1.4fr) repeat(3,minmax(115px,.8fr));gap:14px}.brazil-odds-row strong:not(:first-child){text-align:right;font-variant-numeric:tabular-nums}.brazil-odds-row small{display:block;margin-top:3px;color:#5b6f68;font-size:.72rem}@media(max-width:700px){.odds-panel{overflow-x:auto}.odds-row{display:grid!important;min-width:670px;grid-template-columns:250px 115px 85px 100px 80px;padding:12px}.brazil-odds-row{display:grid!important;min-width:640px;grid-template-columns:260px repeat(3,125px);padding:12px}.odds-row.table-head{font-size:.65rem}.odds-toolbar{align-items:flex-start;flex-direction:column}.odds-refresh{width:100%}}';
document.head.append(oddsStyle);
const oddsTeamsStyle = document.createElement('style');
oddsTeamsStyle.textContent = '.odds-teams{display:flex;align-items:center;gap:8px;font-weight:850}.odds-teams .crest{width:27px;height:27px;object-fit:contain}.odds-vs{color:#5b6f68;font-size:.75rem;font-weight:800}';
document.head.append(oddsTeamsStyle);
const oddsLayoutStyle = document.createElement('style');
oddsLayoutStyle.textContent = '.odds-panel .brazil-odds-row{grid-template-columns:minmax(300px,420px) repeat(3,120px);justify-content:center;gap:28px}.odds-panel .kelly-row{grid-template-columns:minmax(250px,360px) 145px 86px 100px 90px 76px;justify-content:center;gap:18px}.kelly-control{display:flex;gap:5px;padding:4px;border:1px solid #d8d0c1;border-radius:10px;background:#fffdf8}.kelly-control button{border:0;border-radius:6px;background:transparent;color:#34473f;padding:7px 9px;font:inherit;font-size:.76rem;font-weight:850;cursor:pointer}.kelly-control button.active{background:#075c42;color:#fff}@media(max-width:700px){.odds-panel .brazil-odds-row{grid-template-columns:260px repeat(3,125px);justify-content:start;gap:14px}.odds-panel .kelly-row{grid-template-columns:245px 115px 82px 96px 80px 92px;justify-content:start;gap:14px}.kelly-control{width:100%;justify-content:space-between}.kelly-control button{flex:1}}';
document.head.append(oddsLayoutStyle);
const oddsComparisonStyle = document.createElement('style');
oddsComparisonStyle.textContent = '.odds-mode{border:1px solid #075c42;border-radius:9px;background:#075c42;color:#fff;padding:10px 13px;font:inherit;font-size:.84rem;font-weight:850;cursor:pointer}.odds-mode:hover{background:#064b36}.odds-mode:disabled{opacity:.55;cursor:wait}.kelly-row{grid-template-columns:minmax(190px,1.35fr) minmax(105px,.75fr) 82px 96px 80px 92px}.odds-alpha.negative{color:#a13d34}.odds-alpha.positive{color:#075c42}.odds-kelly{text-align:right;font-variant-numeric:tabular-nums;color:#075c42}.odds-mode-note{margin-top:7px;color:#5b6f68;font-size:.78rem}@media(max-width:700px){.odds-mode{width:100%}.odds-row.kelly-row{min-width:760px!important;grid-template-columns:245px 115px 82px 96px 80px 92px!important}}';
document.head.append(oddsComparisonStyle);
const adminStyle = document.createElement('style');
adminStyle.textContent = '.admin-login{max-width:430px;margin:42px auto;padding:26px;border:1px solid #d8d0c1;border-radius:16px;background:#fffdf8}.admin-login h1{font-size:2rem}.admin-login label{display:grid;gap:6px;margin:14px 0;color:#5b6f68;font-size:.8rem;font-weight:800}.admin-login input,.manual-merge input{padding:11px 12px;border:1px solid #d8d0c1;border-radius:9px;background:#fffdf8;color:#10231d;font:inherit}.admin-login button,.admin-action{border:0;border-radius:9px;background:#075c42;color:#fff;padding:10px 13px;font:inherit;font-weight:850;cursor:pointer}.admin-action.secondary{background:#fffdf8;color:#10231d;border:1px solid #d8d0c1}.admin-action.warn{background:#7c5400}.admin-note{padding:15px 17px;border-left:4px solid #b6e851;background:#e9f0e8;color:#34473f;font-size:.88rem}.admin-toolbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:22px 0}.admin-toolbar span{color:#5b6f68;font-size:.85rem}.identity-card,.manual-merge{margin:14px 0;padding:18px;border:1px solid #d8d0c1;border-radius:14px;background:#fffdf8}.identity-card header{display:flex;align-items:center;justify-content:space-between;gap:12px}.identity-card h2,.manual-merge h2{margin:0;font-size:1.08rem}.identity-clubs{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px;margin:15px 0}.identity-club{display:flex;align-items:center;gap:9px;padding:11px;border:1px solid #e6dfd2;border-radius:10px}.identity-club .crest{width:34px;height:34px;flex-basis:34px}.identity-club small{display:block;color:#5b6f68;margin-top:2px}.identity-actions{display:flex;gap:8px;flex-wrap:wrap}.identity-status,.identity-impact{padding:5px 8px;border-radius:99px;background:#eef3ea;color:#075c42;font-size:.74rem;font-weight:850}.identity-status.pending{background:#f5ead0;color:#7c5400}.identity-impact{background:#edf2eb;color:#34473f;white-space:nowrap}.manual-merge form{display:grid;grid-template-columns:1fr 1fr auto;gap:10px;margin-top:14px}.manual-merge .manual-feedback{grid-column:1/-1;margin:0;color:#7c5400;font-size:.84rem}.manual-merge-list{margin:14px 0 0;padding-left:20px;color:#34473f}.manual-merge-list button{margin-left:8px;border:0;background:none;color:#9a352d;font:inherit;font-weight:800;cursor:pointer}@media(max-width:650px){.admin-login{margin:24px 0;padding:20px}.identity-card{padding:15px}.manual-merge form{grid-template-columns:1fr}.manual-merge .admin-action{width:max-content}}';
document.head.append(adminStyle);

function game(m, fixture = false) {
  const labels = { IN_PLAY: 'Em andamento', PAUSED: 'Intervalo', POSTPONED: 'Adiado', SUSPENDED: 'Suspenso', CANCELLED: 'Cancelado', FINISHED: 'Aguardando placar' };
  const pending = fixture && (labels[m.status] || (new Date(m.scheduled_at).getTime() <= Date.now() ? 'Aguardando resultado' : null));
  const safeColor = (color, fallback) => /^#[0-9a-f]{6}$/i.test(String(color)) ? color : fallback;
  const oneXTwo = `<span class="fixture-market"><span class="score forecast forecast-1x2" aria-label="Mandante ${m.home_favoritism}%, empate ${m.draw_probability}%, visitante ${m.away_favoritism}%"><span>1 <b>${m.home_favoritism}%</b></span><span>X <b>${m.draw_probability}%</b></span><span>2 <b>${m.away_favoritism}%</b></span></span><span class="probability-bar" role="img" aria-label="Barra de probabilidades: mandante ${m.home_favoritism}%, empate ${m.draw_probability}%, visitante ${m.away_favoritism}%"><i style="width:${m.home_favoritism}%;background:${safeColor(m.home_color, '#075c42')}"></i><i style="width:${m.draw_probability}%;background:#d5d8d5"></i><i style="width:${m.away_favoritism}%;background:${safeColor(m.away_color, '#466f9c')}"></i></span></span>`;
  const score = fixture ? (pending ? `<span class="score forecast">${pending}</span>` : oneXTwo) : `<span class="score">${m.home_goals}–${m.away_goals}</span>`;
  const homeMeta = fixture ? `Rating ${Math.round(m.home_rating)}` : `Rating ${m.home_rating_after?.toFixed(1) ?? '—'} · impacto ${impact(m.home_rating_effect)}`;
  const awayMeta = fixture ? `Rating ${Math.round(m.away_rating)}` : `Rating ${m.away_rating_after?.toFixed(1) ?? '—'} · impacto ${impact(m.away_rating_effect)}`;
  return `<article class="row"><span class="date">${fixture ? time(m.scheduled_at) : matchTime(m.played_at)}<small class="competition">${matchContext(m)}</small></span><span class="home">${club(m.home_team, m.home_crest, true)}<small class="rating">${homeMeta}</small></span>${score}<span class="away">${club(m.away_team, m.away_crest, true)}<small class="rating">${awayMeta}</small></span></article>`;
}

const searchableText = m => [m.home_team, m.away_team, m.competition, m.matchday && `rodada ${m.matchday}`, stageName(m.stage), m.group_name, m.played_at, m.scheduled_at].filter(Boolean).join(' ').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

function mountPagedList(host, games, renderGame, options = {}) {
  const pageSize = options.pageSize || 15, canSearch = Boolean(options.search), canFilterCompetition = Boolean(options.competitionFilter), emptyText = options.emptyText || 'Nenhuma partida encontrada.';
  const competitions = [...new Set(games.map(game => game.competition).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'pt-BR'));
  const tools = canSearch || canFilterCompetition ? `<div class="list-tools">${canSearch ? `<input class="list-search" type="search" placeholder="${options.placeholder || 'Buscar partida'}" aria-label="Buscar partida">` : ''}${canFilterCompetition ? `<select class="list-filter" aria-label="Filtrar competição"><option value="">Todas as competições</option>${competitions.map(competition => `<option value="${competition}">${competition}</option>`).join('')}</select>` : ''}</div>` : '';
  host.innerHTML = `${tools}<section class="panel"></section><div class="pager" aria-live="polite"></div>`;
  const input = host.querySelector('.list-search'), select = host.querySelector('.list-filter'), panel = host.querySelector('.panel'), pager = host.querySelector('.pager');
  let filtered = games, currentPage = 1;
  const render = () => {
    const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
    currentPage = Math.min(currentPage, totalPages);
    const start = (currentPage - 1) * pageSize, visible = filtered.slice(start, start + pageSize);
    panel.innerHTML = visible.length ? visible.map(renderGame).join('') : `<p class="empty-list">${emptyText}</p>`;
    pager.innerHTML = filtered.length ? `<span>Página ${currentPage} de ${totalPages} · ${filtered.length} partida${filtered.length === 1 ? '' : 's'}</span><span class="pager-actions"><button type="button" data-page="previous" ${currentPage === 1 ? 'disabled' : ''}>Anterior</button><button type="button" data-page="next" ${currentPage === totalPages ? 'disabled' : ''}>Próxima</button></span>` : '';
    pager.querySelector('[data-page="previous"]')?.addEventListener('click', () => { currentPage -= 1; render(); host.scrollIntoView({ block: 'start', behavior: 'smooth' }); });
    pager.querySelector('[data-page="next"]')?.addEventListener('click', () => { currentPage += 1; render(); host.scrollIntoView({ block: 'start', behavior: 'smooth' }); });
  };
  const applyFilters = () => { const query = input?.value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim() || ''; const competition = select?.value || ''; filtered = games.filter(game => (!query || searchableText(game).includes(query)) && (!competition || game.competition === competition)); currentPage = 1; render(); };
  input?.addEventListener('input', applyFilters);
  select?.addEventListener('change', applyFilters);
  render();
}

function teamRatingHistory(matches, team) {
  return matches.filter(m => m.home_team === team || m.away_team === team).map(m => ({
    at: m.played_at,
    rating: m.home_team === team ? m.home_rating_after : m.away_rating_after,
  })).filter(point => Number.isFinite(point.rating)).sort((a, b) => new Date(a.at) - new Date(b.at));
}

function teamPositionHistory(matches, team) {
  const ordered = [...matches].filter(match => Number.isFinite(match.home_rating_after) && Number.isFinite(match.away_rating_after)).sort((a, b) => new Date(a.played_at) - new Date(b.played_at));
  const ratings = new Map(), history = [];
  for (let index = 0; index < ordered.length;) {
    const at = ordered[index].played_at, group = [];
    while (index < ordered.length && ordered[index].played_at === at) group.push(ordered[index++]);
    group.forEach(match => { ratings.set(match.home_team, match.home_rating_after); ratings.set(match.away_team, match.away_rating_after); });
    if (group.some(match => match.home_team === team || match.away_team === team)) {
      const ranking = [...ratings.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'pt-BR'));
      history.push({ at, position: ranking.findIndex(([name]) => name === team) + 1 });
    }
  }
  return history;
}

function ratingChartSvg(history, team, metric = 'rating') {
  if (!history.length) return `<p class="empty-list">Não há partidas no intervalo selecionado.</p>`;
  const width = 800, height = 260, padding = { top: 20, right: 24, bottom: 42, left: 52 };
  const dates = history.map(point => new Date(point.at).getTime()), ratings = history.map(point => point[metric]);
  const minDate = Math.min(...dates), maxDate = Math.max(...dates), minRating = Math.min(...ratings), maxRating = Math.max(...ratings);
  const ratingPad = metric === 'position' ? 0 : Math.max(12, (maxRating - minRating) * 0.15), low = metric === 'position' ? maxRating : minRating - ratingPad, high = metric === 'position' ? minRating : maxRating + ratingPad;
  const x = value => padding.left + (maxDate === minDate ? (width - padding.left - padding.right) / 2 : (value - minDate) / (maxDate - minDate) * (width - padding.left - padding.right));
  const y = value => padding.top + (high - value) / (high - low) * (height - padding.top - padding.bottom);
  const line = history.map(point => `${x(new Date(point.at).getTime()).toFixed(1)},${y(point[metric]).toFixed(1)}`).join(' ');
  const baseline = height - padding.bottom;
  const area = `${padding.left},${baseline} ${line} ${width - padding.right},${baseline}`;
  const tickValues = [0, 0.5, 1].map(fraction => low + (high - low) * fraction);
  const dateLabel = value => new Intl.DateTimeFormat('pt-BR', { timeZone: 'America/Sao_Paulo', month: 'short', year: '2-digit' }).format(new Date(value));
  const dateTicks = [0, .25, .5, .75, 1].map(fraction => minDate + (maxDate - minDate) * fraction);
  const grid = tickValues.map(value => `<line class="grid" x1="${padding.left}" x2="${width - padding.right}" y1="${y(value)}" y2="${y(value)}"/><text class="axis-label" x="${padding.left - 8}" y="${y(value) + 4}" text-anchor="end">${metric === 'position' ? `${Math.round(value)}º` : value.toFixed(0)}</text>`).join('');
  const xLabels = dateTicks.map(value => `<text class="axis-label" x="${x(value)}" y="${height - 14}" text-anchor="middle">${dateLabel(value)}</text>`).join('');
  const points = history.map(point => `<circle class="point" cx="${x(new Date(point.at).getTime())}" cy="${y(point[metric])}" r="3.5"/>`).join('');
  const change = history.at(-1)[metric] - history[0][metric], label = metric === 'position' ? 'Posição' : 'Rating';
  return `<svg class="rating-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Trajetória interativa de ${label.toLowerCase()} de ${team}"><defs><linearGradient id="rating-area" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#159b78"/><stop offset="1" stop-color="#159b78" stop-opacity="0"/></linearGradient></defs>${grid}<polygon class="area" points="${area}"/><polyline class="line" points="${line}"/>${points}<line class="crosshair" hidden/><circle class="focus" r="6" hidden/><rect class="hitbox" x="${padding.left}" y="${padding.top}" width="${width - padding.left - padding.right}" height="${height - padding.top - padding.bottom}"/>${xLabels}</svg><div class="chart-tooltip" hidden></div><div class="chart-summary"><span>Primeiro ponto: <strong>${metric === 'position' ? `${history[0][metric]}º` : history[0][metric].toFixed(1)}</strong></span><span>Variação: <strong>${change >= 0 ? '+' : ''}${metric === 'position' ? `${change} posições` : change.toFixed(1)}</strong></span><span>Partidas: <strong>${history.length}</strong></span></div>`;
}

function mountRatingChart(host, matches, team) {
  const history = teamRatingHistory(matches, team);
  const positionHistory = teamPositionHistory(matches, team);
  if (!history.length) { host.innerHTML = `<section class="chart-card"><h2>Trajetória do rating</h2><p>Ainda não há resultados suficientes para desenhar a trajetória deste clube.</p></section>`; return; }
  const toInputDate = value => new Date(value).toISOString().slice(0, 10);
  const first = new Date(history[0].at).getTime(), last = new Date(history.at(-1).at).getTime();
  host.innerHTML = `<section class="chart-card"><h2>Histórico do clube</h2><p>Escolha rating ou posição. A posição é reconstruída com os ratings disponíveis em cada data; 1º fica no topo do gráfico.</p><div class="chart-controls"><div class="chart-presets" aria-label="Métrica"><button type="button" data-metric="rating" class="active">Rating</button><button type="button" data-metric="position">Posição</button></div><div class="chart-presets chart-periods" aria-label="Período do gráfico"><button type="button" data-months="all" class="active">Tudo</button><button type="button" data-months="ytd">YTD</button><button type="button" data-months="24">24 meses</button><button type="button" data-months="12">12 meses</button><button type="button" data-months="6">6 meses</button><button type="button" data-months="3">3 meses</button></div><label class="chart-date">De<input type="date" data-range="start" min="${toInputDate(first)}" max="${toInputDate(last)}" value="${toInputDate(first)}"></label><label class="chart-date">Até<input type="date" data-range="end" min="${toInputDate(first)}" max="${toInputDate(last)}" value="${toInputDate(last)}"></label></div><div class="chart-canvas"></div></section>`;
  const canvas = host.querySelector('.chart-canvas'), startInput = host.querySelector('[data-range="start"]'), endInput = host.querySelector('[data-range="end"]'), buttons = [...host.querySelectorAll('[data-months]')], metricButtons = [...host.querySelectorAll('[data-metric]')]; let metric = 'rating';
  const bindInteraction = (visible, selectedMetric = 'rating') => {
    const svg = canvas.querySelector('.rating-chart');
    if (!svg || !visible.length) return;
    const tooltip = canvas.querySelector('.chart-tooltip'), crosshair = svg.querySelector('.crosshair'), focus = svg.querySelector('.focus');
    const width = 800, height = 260, padding = { top: 20, right: 24, bottom: 42, left: 52 };
    const dates = visible.map(point => new Date(point.at).getTime()), ratings = visible.map(point => point[selectedMetric]);
    const minDate = Math.min(...dates), maxDate = Math.max(...dates), minRating = Math.min(...ratings), maxRating = Math.max(...ratings);
    const ratingPad = selectedMetric === 'position' ? 0 : Math.max(12, (maxRating - minRating) * 0.15), low = selectedMetric === 'position' ? maxRating : minRating - ratingPad, high = selectedMetric === 'position' ? minRating : maxRating + ratingPad;
    const x = value => padding.left + (maxDate === minDate ? (width - padding.left - padding.right) / 2 : (value - minDate) / (maxDate - minDate) * (width - padding.left - padding.right));
    const y = value => padding.top + (high - value) / (high - low) * (height - padding.top - padding.bottom);
    const show = event => {
      const rect = svg.getBoundingClientRect(), chartX = (event.clientX - rect.left) / rect.width * width;
      let index = 0, distance = Infinity;
      visible.forEach((point, candidate) => { const nextDistance = Math.abs(x(new Date(point.at).getTime()) - chartX); if (nextDistance < distance) { index = candidate; distance = nextDistance; } });
      const point = visible[index], pointX = x(new Date(point.at).getTime()), pointY = y(point[selectedMetric]);
      crosshair.setAttribute('x1', pointX); crosshair.setAttribute('x2', pointX); crosshair.setAttribute('y1', padding.top); crosshair.setAttribute('y2', height - padding.bottom); crosshair.hidden = false;
      focus.setAttribute('cx', pointX); focus.setAttribute('cy', pointY); focus.hidden = false;
      tooltip.innerHTML = `<span class="chart-tip-date">${time(point.at)}</span><strong>${selectedMetric === 'position' ? `${point.position}º lugar` : `Rating ${Math.round(point.rating)}`}</strong>`;
      tooltip.style.left = `${pointX / width * 100}%`; tooltip.style.top = `${pointY / height * 100}%`; tooltip.hidden = false;
    };
    const hide = event => { if (event.pointerType !== 'touch') { tooltip.hidden = true; crosshair.hidden = true; focus.hidden = true; } };
    svg.addEventListener('pointermove', show); svg.addEventListener('pointerdown', show); svg.addEventListener('pointerleave', hide);
  };
  const render = () => {
    const start = new Date(`${startInput.value}T00:00:00-03:00`).getTime(), end = new Date(`${endInput.value}T23:59:59-03:00`).getTime();
    const selectedHistory = metric === 'position' ? positionHistory : history;
    const visible = selectedHistory.filter(point => { const at = new Date(point.at).getTime(); return at >= start && at <= end; });
    canvas.innerHTML = start <= end ? ratingChartSvg(visible, team, metric) : '<p class="empty-list">A data inicial deve ser anterior à data final.</p>';
    if (start <= end) bindInteraction(visible, metric);
  };
  const setPeriod = months => {
    let start = first;
    if (months === 'ytd') { const cutoff = new Date(last); cutoff.setUTCMonth(0, 1); start = Math.max(first, cutoff.getTime()); }
    else if (months !== 'all') { const cutoff = new Date(last); cutoff.setUTCMonth(cutoff.getUTCMonth() - Number(months)); start = Math.max(first, cutoff.getTime()); }
    startInput.value = toInputDate(start); endInput.value = toInputDate(last);
    buttons.forEach(button => button.classList.toggle('active', button.dataset.months === String(months)));
    render();
  };
  buttons.forEach(button => button.addEventListener('click', () => setPeriod(button.dataset.months)));
  metricButtons.forEach(button => button.addEventListener('click', () => { metric = button.dataset.metric; metricButtons.forEach(item => item.classList.toggle('active', item === button)); render(); }));
  [startInput, endInput].forEach(input => input.addEventListener('change', () => { buttons.forEach(button => button.classList.remove('active')); render(); }));
  render();
}

const percentage = value => `${(value * 100).toFixed(2)}%`;
const ratingConfidence = rd => {
  if (!Number.isFinite(rd)) return { label: 'Confiança indisponível', tone: 'limited', description: 'Ainda não há informação suficiente para qualificar a incerteza deste rating.' };
  if (rd <= 75) return { label: 'Alta confiança', tone: 'high', description: 'Para os dados disponíveis, o rating está bem sustentado pelos jogos rastreados; pequenas oscilações são esperadas.' };
  if (rd <= 100) return { label: 'Confiança moderada', tone: 'medium', description: 'A estimativa é útil, mas ainda pode variar de forma relevante com os próximos jogos.' };
  return { label: 'Confiança limitada', tone: 'limited', description: 'Há maior incerteza por poucos dados recentes ou por um intervalo sem partidas rastreadas.' };
};

function simulationTable(teams, field, title, detail, orderByPoints = false) {
  const rows = teams.filter(team => Number((team[field] * 100).toFixed(2)) > 0).sort((a, b) => orderByPoints ? b.points - a.points || a.position - b.position : b[field] - a[field] || a.position - b.position);
  return `<div><h2>${title}</h2><p>${detail}</p><section class="panel"><div class="row simulation-row table-head"><span>Pos.</span><span>Clube</span><span>Pontos</span><span>Prob.</span></div>${rows.map(team => `<div class="row simulation-row"><span>${team.position}º</span><b>${club(team.name, team.crest, true)}</b><span>${team.points}</span><strong>${percentage(team[field])}</strong></div>`).join('')}</section></div>`;
}

function simulations(data) {
  document.body.innerHTML = shell('Reta final', 'Simulações');
  const all = data.simulation?.competitions || (data.simulation ? [data.simulation] : []);
  if (!all.length) {
    el('#content').innerHTML = `<section class="panel simulation-unavailable"><p>As simulações ficam disponíveis quando houver resultados e fixtures restantes de uma competição na fonte de dados.</p></section>`;
    return;
  }
  el('#content').innerHTML = `<p class="simulation-note">Projeções da reta final a partir de ratings Glicko-2 e do mando de campo. Cada competição recebe <strong>1.000.000</strong> de cenários independentes.</p><div class="simulation-tabs">${all.map((simulation, index) => `<button type="button" data-competition="${simulation.competition}" class="${index === 0 ? 'active' : ''}">${simulation.competition}</button>`).join('')}</div><div class="simulation-host"></div>`;
  const host = el('.simulation-host');
  const render = simulation => {
    if (!simulation.available) {
      host.innerHTML = `<section class="panel simulation-unavailable"><h2>${simulation.competition} ${simulation.season}</h2><p>${simulation.unavailable_reason || 'A simulação desta competição será exibida quando houver resultados e fixtures restantes disponíveis.'}</p><p>A aba permanece acessível para deixar clara a cobertura atual. A próxima carga completa do banco revisará a temporada antes de calcular os <strong>1.000.000</strong> cenários.</p></section>`;
      return;
    }
    const playoffSlots = Number(simulation.playoff_promotion_slots || 0), directSlots = Number(simulation.promotion_slots || 0) - playoffSlots;
    const accessDetail = playoffSlots ? `Chance de acesso: os ${directSlots} primeiros sobem direto; 3º–6º disputam ${playoffSlots} vagas em ida e volta, com vantagem da melhor campanha no empate agregado.` : `Chance de terminar entre os ${simulation.promotion_slots} primeiros e subir de divisão.`;
    const access = simulation.promotion_slots ? simulationTable(simulation.teams, 'promotion_probability', 'Probabilidade de acesso', accessDetail) : '';
    const playoffMethod = playoffSlots ? `<p><strong>Playoff de acesso da Série B 2026.</strong> Após a fase de pontos corridos, 1º e 2º sobem diretamente. Os clubes entre 3º e 6º formam os duelos 3º×6º e 4º×5º, em ida e volta; os dois vencedores também sobem. O melhor classificado decide em casa e avança se o agregado terminar empatado. Os quatro eventos da ESPN que ainda aparecem como “TBD” são esses jogos: seus participantes são definidos dentro de cada cenário, portanto entram na simulação mesmo antes da definição real.</p>` : '';
    host.innerHTML = `<p class="simulation-note">Probabilidades estimadas para a ${simulation.competition} ${simulation.season}, com base em <strong>${simulation.scenarios.toLocaleString('pt-BR')}</strong> cenários. A situação inicial tem ${simulation.completed_matches} partidas concluídas e ${simulation.fixtures_remaining} restantes.</p><div class="simulation-grid">${simulationTable(simulation.teams, 'champion_probability', 'Probabilidade de título', 'Chance de terminar em 1º lugar. A apresentação segue a classificação atual por pontos.', true)}${access}${simulationTable(simulation.teams, 'relegation_probability', 'Probabilidade de rebaixamento', `Chance de terminar entre os ${simulation.relegation_slots} últimos.`)}</div><section class="simulation-method"><h2>Como estimamos</h2><p>Em cada cenário, cada fixture restante é sorteado de forma independente a partir do rating Glicko-2 atual e do mando de campo. A probabilidade de empate usa a taxa observada de empates da temporada (${percentage(simulation.observed_draw_rate)}), reduzida quando a diferença de rating entre os clubes cresce e limitada entre ${percentage(simulation.draw_limits[0])} e ${percentage(simulation.draw_limits[1])}.</p>${playoffMethod}<p>Ao final, contamos quantas vezes cada clube foi campeão, terminou nas vagas de acesso quando aplicável, ou caiu. Os desempates seguem pontos, vitórias, saldo de gols, gols pró e nome do clube; para jogos futuros, uma vitória decisiva adiciona uma margem projetada de um gol. É uma projeção baseada nos dados disponíveis, não uma previsão determinística nem recomendação de aposta.</p><p>Partidas ainda sem resultado final confirmado, inclusive as que já começaram, são simuladas como se ainda não tivessem começado. A projeção não considera placar ou tempo de jogo em andamento e só incorpora o resultado após a próxima coleta.</p></section>`;
  };
  el('.simulation-tabs').querySelectorAll('button').forEach(button => button.addEventListener('click', () => { const selected = all.find(simulation => simulation.competition === button.dataset.competition); el('.simulation-tabs').querySelectorAll('button').forEach(item => item.classList.toggle('active', item === button)); render(selected); }));
  render(all[0]);
}

function comparisonExpected(home, away, homeAdvantage = 0) {
  const scale = 173.7178, opponentPhi = Number(away.rd) / scale;
  const g = 1 / Math.sqrt(1 + 3 * opponentPhi * opponentPhi / (Math.PI * Math.PI));
  return 1 / (1 + Math.exp(-g * ((Number(home.rating) + homeAdvantage - Number(away.rating)) / scale)));
}

function headToHead(matches, teamA, teamB) {
  const games = matches.filter(match => (match.home_team === teamA && match.away_team === teamB) || (match.home_team === teamB && match.away_team === teamA));
  const totals = { games: games.length, aWins: 0, draws: 0, bWins: 0 };
  games.forEach(match => {
    const aGoals = match.home_team === teamA ? Number(match.home_goals) : Number(match.away_goals);
    const bGoals = match.home_team === teamB ? Number(match.home_goals) : Number(match.away_goals);
    if (aGoals === bGoals) totals.draws += 1;
    else if (aGoals > bGoals) totals.aWins += 1;
    else totals.bWins += 1;
  });
  return totals;
}

function comparisonChart(historyA, historyB, teamA, teamB) {
  const points = [...historyA, ...historyB];
  if (points.length < 2) return '<p class="empty-list">Não há histórico suficiente no intervalo selecionado.</p>';
  const width = 820, height = 270, padding = { top: 18, right: 22, bottom: 42, left: 48 };
  const dates = points.map(point => new Date(point.at).getTime()), ratings = points.map(point => point.rating);
  const minDate = Math.min(...dates), maxDate = Math.max(...dates), minRating = Math.min(...ratings), maxRating = Math.max(...ratings), pad = Math.max(12, (maxRating - minRating) * .15), low = minRating - pad, high = maxRating + pad;
  const x = value => padding.left + (maxDate === minDate ? (width - padding.left - padding.right) / 2 : (value - minDate) / (maxDate - minDate) * (width - padding.left - padding.right));
  const y = value => padding.top + (high - value) / (high - low) * (height - padding.top - padding.bottom);
  const line = history => history.map(point => `${x(new Date(point.at).getTime()).toFixed(1)},${y(point.rating).toFixed(1)}`).join(' ');
  const grid = [0, .5, 1].map(fraction => { const value = low + (high - low) * fraction, coordinate = y(value); return `<line class="grid" x1="${padding.left}" x2="${width - padding.right}" y1="${coordinate}" y2="${coordinate}"/><text class="axis" x="${padding.left - 7}" y="${coordinate + 4}" text-anchor="end">${Math.round(value)}</text>`; }).join('');
  const labels = [0, .5, 1].map(fraction => { const value = minDate + (maxDate - minDate) * fraction; return `<text class="axis" x="${x(value)}" y="${height - 14}" text-anchor="middle">${new Intl.DateTimeFormat('pt-BR', { month: 'short', year: '2-digit' }).format(new Date(value))}</text>`; }).join('');
  return `<div class="compare-canvas"><svg class="comparison-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Comparação histórica interativa de rating entre ${teamA} e ${teamB}">${grid}<polyline class="line-a" points="${line(historyA)}"/><polyline class="line-b" points="${line(historyB)}"/><line class="compare-crosshair" hidden/><circle class="compare-focus focus-a" r="5.5" hidden/><circle class="compare-focus focus-b" r="5.5" hidden/><rect class="compare-hitbox" x="${padding.left}" y="${padding.top}" width="${width - padding.left - padding.right}" height="${height - padding.top - padding.bottom}"/>${labels}</svg><div class="compare-tooltip" hidden></div></div><div class="compare-legend"><span>${teamA}</span><span>${teamB}</span></div>`;
}

function mountComparisonChart(host, historyA, historyB, teamA, teamB) {
  const points = [...historyA, ...historyB];
  if (!points.length) { host.innerHTML = '<p class="empty-list">Ainda não há histórico para comparar estes clubes.</p>'; return; }
  const toInputDate = value => new Date(value).toISOString().slice(0, 10);
  const first = Math.min(...points.map(point => new Date(point.at).getTime())), last = Math.max(...points.map(point => new Date(point.at).getTime()));
  host.innerHTML = `<div class="chart-controls"><div class="chart-presets" aria-label="Período do histórico"><button type="button" data-months="all" class="active">Tudo</button><button type="button" data-months="24">24 meses</button><button type="button" data-months="12">12 meses</button><button type="button" data-months="6">6 meses</button><button type="button" data-months="3">3 meses</button></div><label class="chart-date">De<input type="date" data-range="start" min="${toInputDate(first)}" max="${toInputDate(last)}" value="${toInputDate(first)}"></label><label class="chart-date">Até<input type="date" data-range="end" min="${toInputDate(first)}" max="${toInputDate(last)}" value="${toInputDate(last)}"></label></div><div class="compare-chart-canvas"></div>`;
  const canvas = host.querySelector('.compare-chart-canvas'), startInput = host.querySelector('[data-range="start"]'), endInput = host.querySelector('[data-range="end"]'), buttons = [...host.querySelectorAll('[data-months]')];
  const nearest = (history, timestamp) => history.reduce((best, point) => !best || Math.abs(new Date(point.at).getTime() - timestamp) < Math.abs(new Date(best.at).getTime() - timestamp) ? point : best, null);
  const bindHover = (visibleA, visibleB) => {
    const svg = canvas.querySelector('.comparison-chart');
    if (!svg) return;
    const width = 820, height = 270, padding = { top: 18, right: 22, bottom: 42, left: 48 }, visible = [...visibleA, ...visibleB], dates = visible.map(point => new Date(point.at).getTime()), ratings = visible.map(point => point.rating);
    const minDate = Math.min(...dates), maxDate = Math.max(...dates), minRating = Math.min(...ratings), maxRating = Math.max(...ratings), pad = Math.max(12, (maxRating - minRating) * .15), low = minRating - pad, high = maxRating + pad;
    const x = value => padding.left + (maxDate === minDate ? (width - padding.left - padding.right) / 2 : (value - minDate) / (maxDate - minDate) * (width - padding.left - padding.right));
    const y = value => padding.top + (high - value) / (high - low) * (height - padding.top - padding.bottom);
    const tooltip = canvas.querySelector('.compare-tooltip'), crosshair = svg.querySelector('.compare-crosshair'), focusA = svg.querySelector('.focus-a'), focusB = svg.querySelector('.focus-b');
    const show = event => { const rect = svg.getBoundingClientRect(), chartX = (event.clientX - rect.left) / rect.width * width, at = minDate + Math.max(0, Math.min(1, (chartX - padding.left) / (width - padding.left - padding.right))) * (maxDate - minDate), a = nearest(visibleA, at), b = nearest(visibleB, at), anchor = nearest(visible, at), anchorX = x(new Date(anchor.at).getTime()); crosshair.setAttribute('x1', anchorX); crosshair.setAttribute('x2', anchorX); crosshair.setAttribute('y1', padding.top); crosshair.setAttribute('y2', height - padding.bottom); crosshair.hidden = false; [[focusA, a], [focusB, b]].forEach(([focus, point]) => { focus.setAttribute('cx', x(new Date(point.at).getTime())); focus.setAttribute('cy', y(point.rating)); focus.hidden = false; }); tooltip.innerHTML = `<span class="chart-tip-date">${time(anchor.at)}</span><strong>${teamA}: ${Math.round(a.rating)} · ${teamB}: ${Math.round(b.rating)}</strong>`; tooltip.style.left = `${anchorX / width * 100}%`; tooltip.style.top = `${Math.min(y(a.rating), y(b.rating)) / height * 100}%`; tooltip.hidden = false; };
    const hide = event => { if (event.pointerType !== 'touch') { tooltip.hidden = true; crosshair.hidden = true; focusA.hidden = true; focusB.hidden = true; } };
    svg.addEventListener('pointermove', show); svg.addEventListener('pointerdown', show); svg.addEventListener('pointerleave', hide);
  };
  const render = () => { const start = new Date(`${startInput.value}T00:00:00-03:00`).getTime(), end = new Date(`${endInput.value}T23:59:59-03:00`).getTime(), within = point => { const at = new Date(point.at).getTime(); return at >= start && at <= end; }, visibleA = historyA.filter(within), visibleB = historyB.filter(within); canvas.innerHTML = start <= end ? comparisonChart(visibleA, visibleB, teamA, teamB) : '<p class="empty-list">A data inicial deve ser anterior à data final.</p>'; if (start <= end && visibleA.length && visibleB.length) bindHover(visibleA, visibleB); };
  const setPeriod = months => { let start = first; if (months !== 'all') { const cutoff = new Date(last); cutoff.setUTCMonth(cutoff.getUTCMonth() - Number(months)); start = Math.max(first, cutoff.getTime()); } startInput.value = toInputDate(start); endInput.value = toInputDate(last); buttons.forEach(button => button.classList.toggle('active', button.dataset.months === String(months))); render(); };
  buttons.forEach(button => button.addEventListener('click', () => setPeriod(button.dataset.months)));
  [startInput, endInput].forEach(input => input.addEventListener('change', () => { buttons.forEach(button => button.classList.remove('active')); render(); }));
  render();
}

function comparisons(data) {
  document.body.innerHTML = shell('Comparar clubes', 'Confrontos');
  const teams = [...data.teams, ...(data.excluded_teams || [])].sort((a, b) => a.name.localeCompare(b.name, 'pt-BR'));
  if (teams.length < 2) { el('#content').innerHTML = '<section class="panel simulation-unavailable"><p>A comparação ficará disponível quando houver ao menos dois clubes no ranking.</p></section>'; return; }
  const rankedTeams = [...data.teams].sort((a, b) => Number(a.position) - Number(b.position));
  const defaultA = rankedTeams[0] || teams[0], defaultB = rankedTeams[1] || teams[1];
  const options = teams.map(team => `<option value="${team.name}"></option>`).join('');
  el('#content').innerHTML = `<p>Compare a força estimada de dois clubes e veja como o mando altera um confronto hipotético. Comece a digitar: a lista se restringe aos nomes mais próximos. O histórico usa o rating registrado após cada partida rastreada.</p><div class="compare-tools"><label>Clube A<input type="search" list="teams-a" data-team="a" value="${defaultA.name}" placeholder="Digite o nome do clube" autocomplete="off"><datalist id="teams-a">${options}</datalist></label><label>Clube B<input type="search" list="teams-b" data-team="b" value="${defaultB.name}" placeholder="Digite o nome do clube" autocomplete="off"><datalist id="teams-b">${options}</datalist></label></div><div class="compare-host"></div>`;
  const selectA = el('[data-team="a"]'), selectB = el('[data-team="b"]'), host = el('.compare-host');
  const render = () => {
    const a = teams.find(team => team.name === selectA.value), b = teams.find(team => team.name === selectB.value);
    if (!a || !b) { host.innerHTML = '<section class="panel simulation-unavailable"><p>Selecione um clube da lista em cada campo para iniciar a comparação.</p></section>'; return; }
    if (a.name === b.name) { host.innerHTML = '<section class="panel simulation-unavailable"><p>Escolha dois clubes diferentes para comparar.</p></section>'; return; }
    const historyA = teamRatingHistory(data.matches, a.name), historyB = teamRatingHistory(data.matches, b.name);
    const h2h = headToHead(data.matches, a.name, b.name);
    host.innerHTML = `<section class="compare-card"><div class="compare-teams"><article class="compare-team">${club(a.name, a.crest, true, true)}<strong>${Math.round(a.rating)}</strong><small>rating · RD ${Number(a.rd).toFixed(1)}</small></article><div class="compare-vs">vs</div><article class="compare-team">${club(b.name, b.crest, true, true)}<strong>${Math.round(b.rating)}</strong><small>rating · RD ${Number(b.rd).toFixed(1)}</small></article></div><div class="matchup"><div><h2>Confronto hipotético</h2><p>Favoritismo Glicko-2, sem odds e sem previsão de placar.</p></div><label class="venue-control">Mando<select data-venue><option value="a">${a.name} mandante</option><option value="neutral">Campo neutro</option><option value="b">${b.name} mandante</option></select></label><strong class="matchup-probability"></strong></div></section><section class="head-to-head"><div><h2>Confrontos diretos</h2><p>${h2h.games ? `${h2h.games} partidas rastreadas entre os dois clubes.` : 'Ainda não há confronto direto rastreado entre os dois clubes.'}</p></div><div class="h2h-stats"><span><strong>${h2h.aWins}</strong>${a.name} venceu</span><span><strong>${h2h.draws}</strong>empates</span><span><strong>${h2h.bWins}</strong>${b.name} venceu</span></div></section><section class="compare-chart"><h2>Histórico de rating</h2><p>As duas trajetórias usam a mesma escala vertical. Passe o cursor ou toque no gráfico para ver os dois valores.</p><div class="compare-history-host"></div></section>`;
    const venue = host.querySelector('[data-venue]'), probability = host.querySelector('.matchup-probability');
    const updateProbability = () => { const chanceA = venue.value === 'a' ? comparisonExpected(a, b, 80) : venue.value === 'b' ? 1 - comparisonExpected(b, a, 80) : comparisonExpected(a, b); probability.textContent = `${a.name} ${Math.round(chanceA * 100)}% · ${b.name} ${Math.round((1 - chanceA) * 100)}%`; };
    venue.addEventListener('change', updateProbability); updateProbability();
    mountComparisonChart(host.querySelector('.compare-history-host'), historyA, historyB, a.name, b.name);
  };
  [selectA, selectB].forEach(input => { input.addEventListener('input', () => { if (teams.some(team => team.name === input.value)) render(); }); input.addEventListener('change', render); }); render();
}

const html = value => String(value ?? '').replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]);
const normalizedTeamName = value => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/\b(?:futebol|clube|club|associacao|esporte|esportes|football|ec|fc|sc|ac|ca|aa|se|sa)\b/g, ' ').replace(/[^a-z0-9]+/g, ' ').trim();
const nameTokens = value => normalizedTeamName(value).split(' ').filter(token => token.length > 2 && !['dos', 'das', 'del'].includes(token));
const namesMatch = (team, outcome) => {
  const left = normalizedTeamName(team), right = normalizedTeamName(outcome);
  if (!left || !right) return false;
  if (left === right || left.includes(right) || right.includes(left)) return true;
  const tokens = nameTokens(left), outcomeTokens = new Set(nameTokens(right));
  return tokens.length > 0 && tokens.every(token => outcomeTokens.has(token));
};
const parsedList = value => {
  if (Array.isArray(value)) return value;
  try { return JSON.parse(value || '[]'); } catch { return []; }
};
const marketStart = market => market.gameStartTime || market.startDate || market.endDate || market.createdAt;
const marketUrl = market => market.eventSlug || market.slug ? `https://polymarket.com/event/${encodeURIComponent(market.eventSlug || market.slug)}` : 'https://polymarket.com';
const responseRows = payload => Array.isArray(payload) ? payload : payload?.data || [];
const marketEventSlug = market => market.eventSlug || market.event_slug || market.event?.slug || market.events?.[0]?.slug;

async function polymarketMarketsForFixtures(fixtures) {
  // Partimos da agenda do FUTRanking — não do catálogo geral do Polymarket.
  // Seis jogos próximos limitam a consulta a, no máximo, doze leituras leves:
  // uma busca pelo mandante e uma leitura do evento para cada confronto.
  const candidates = [...fixtures]
    .filter(fixture => new Date(fixture.scheduled_at).getTime() >= Date.now() - 6 * 60 * 60 * 1000)
    .sort((a, b) => new Date(a.scheduled_at) - new Date(b.scheduled_at))
    .slice(0, 6);
  const discovered = await Promise.allSettled(candidates.map(async fixture => {
    const url = `https://gamma-api.polymarket.com/markets?active=true&closed=false&archived=false&limit=20&q=${encodeURIComponent(fixture.home_team)}`;
    const response = await fetch(url, { headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return { fixture, markets: responseRows(await response.json()) };
  }));
  const events = new Map();
  discovered.forEach(result => {
    if (result.status !== 'fulfilled') return;
    result.value.markets.forEach(market => {
      if (!namesMatch(result.value.fixture.home_team, `${market.question || ''} ${market.title || ''}`)) return;
      const slug = marketEventSlug(market);
      if (slug) events.set(slug, result.value.fixture);
    });
  });
  const loaded = await Promise.allSettled([...events.entries()].slice(0, 6).map(async ([slug, fixture]) => {
    const response = await fetch(`https://gamma-api.polymarket.com/events?slug=${encodeURIComponent(slug)}`, { headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return { fixture, events: responseRows(await response.json()) };
  }));
  return loaded.flatMap(result => result.status === 'fulfilled'
    ? result.value.events.flatMap(event => (event.markets || []).map(market => ({ ...market, eventSlug: event.slug, eventTitle: event.title, gameStartTime: market.gameStartTime || event.startDate || market.startDate })))
    : []);
}

function matchedPolymarketOutcomes(fixtures, markets) {
  const now = Date.now(), seen = new Set(), rows = [];
  const futureFixtures = fixtures.filter(fixture => {
    const scheduled = new Date(fixture.scheduled_at).getTime();
    return Number.isFinite(scheduled) && scheduled >= now - 6 * 60 * 60 * 1000 && scheduled <= now + 21 * 86400000;
  });
  for (const market of markets) {
    const key = market.id || market.conditionId || market.slug;
    if (!key || seen.has(key)) continue;
    seen.add(key);
    const outcomes = parsedList(market.outcomes), prices = parsedList(market.outcomePrices).map(Number);
    if (outcomes.length !== 3 || prices.length !== 3 || prices.some(price => !Number.isFinite(price) || price < 0 || price > 1)) continue;
    const drawIndex = outcomes.findIndex(outcome => /^(draw|tie|empate)$/i.test(String(outcome).trim()));
    if (drawIndex < 0) continue;
    const fixture = futureFixtures.find(candidate => {
      const scheduled = new Date(candidate.scheduled_at).getTime(), started = new Date(marketStart(market)).getTime();
      const dateMatches = !Number.isFinite(started) || Math.abs(started - scheduled) <= 40 * 60 * 60 * 1000;
      const homeIndex = outcomes.findIndex((outcome, index) => index !== drawIndex && namesMatch(candidate.home_team, outcome));
      const awayIndex = outcomes.findIndex((outcome, index) => index !== drawIndex && namesMatch(candidate.away_team, outcome));
      return dateMatches && homeIndex >= 0 && awayIndex >= 0 && homeIndex !== awayIndex;
    });
    if (!fixture) continue;
    const homeIndex = outcomes.findIndex((outcome, index) => index !== drawIndex && namesMatch(fixture.home_team, outcome));
    const awayIndex = outcomes.findIndex((outcome, index) => index !== drawIndex && namesMatch(fixture.away_team, outcome));
    [
      { index: homeIndex, label: fixture.home_team, model: Number(fixture.home_favoritism) / 100 },
      { index: drawIndex, label: 'Empate', model: Number(fixture.draw_probability) / 100 },
      { index: awayIndex, label: fixture.away_team, model: Number(fixture.away_favoritism) / 100 },
    ].forEach(selection => {
      const marketProbability = prices[selection.index];
      if (!Number.isFinite(selection.model) || !Number.isFinite(marketProbability)) return;
      rows.push({ fixture, selection: selection.label, model: selection.model, market: marketProbability, alpha: selection.model - marketProbability, url: marketUrl(market) });
    });
  }
  // O Polymarket também representa uma partida como três mercados binários
  // independentes (mandante vence, empate, visitante vence). Reconstruímos o
  // 1X2 apenas quando os três pertencem ao mesmo evento e o título confirma os
  // dois clubes; isso evita ligar mercados de partidas distintas.
  const eventGroups = new Map();
  markets.forEach(market => {
    const outcomes = parsedList(market.outcomes), prices = parsedList(market.outcomePrices).map(Number);
    const yesIndex = outcomes.findIndex(outcome => /^(yes|sim)$/i.test(String(outcome).trim()));
    const eventKey = market.eventSlug || market.eventId || market.slug;
    if (!eventKey || outcomes.length !== 2 || prices.length !== 2 || yesIndex < 0 || !Number.isFinite(prices[yesIndex])) return;
    if (!eventGroups.has(eventKey)) eventGroups.set(eventKey, []);
    eventGroups.get(eventKey).push({ market, yesPrice: prices[yesIndex] });
  });
  for (const group of eventGroups.values()) {
    const representative = group[0].market;
    const eventText = group.map(({ market }) => `${market.eventTitle || ''} ${market.question || market.title || ''}`).join(' ');
    const fixture = futureFixtures.find(candidate => {
      const scheduled = new Date(candidate.scheduled_at).getTime(), started = new Date(marketStart(representative)).getTime();
      const dateMatches = !Number.isFinite(started) || Math.abs(started - scheduled) <= 40 * 60 * 60 * 1000;
      return dateMatches && namesMatch(candidate.home_team, eventText) && namesMatch(candidate.away_team, eventText);
    });
    if (!fixture) continue;
    const describe = market => `${market.question || ''} ${market.title || ''} ${market.groupItemTitle || ''}`;
    const home = group.find(({ market }) => namesMatch(fixture.home_team, describe(market)));
    const draw = group.find(({ market }) => /\b(draw|tie|empate)\b/i.test(describe(market)));
    const away = group.find(({ market }) => namesMatch(fixture.away_team, describe(market)));
    if (!home || !draw || !away || new Set([home.market.id, draw.market.id, away.market.id]).size !== 3) continue;
    [
      { entry: home, label: fixture.home_team, model: Number(fixture.home_favoritism) / 100 },
      { entry: draw, label: 'Empate', model: Number(fixture.draw_probability) / 100 },
      { entry: away, label: fixture.away_team, model: Number(fixture.away_favoritism) / 100 },
    ].forEach(selection => rows.push({ fixture, selection: selection.label, model: selection.model, market: selection.entry.yesPrice, alpha: selection.model - selection.entry.yesPrice, url: marketUrl(selection.entry.market) }));
  }
  return rows.sort((a, b) => b.alpha - a.alpha || new Date(a.fixture.scheduled_at) - new Date(b.fixture.scheduled_at));
}

function eventTeams(title) {
  const parts = String(title || '').split(/\s+(?:vs\.?|v\.?|x)\s+/i).map(value => value.trim()).filter(Boolean);
  return parts.length === 2 ? parts : [];
}

function marketYesPrice(market) {
  const outcomes = parsedList(market.outcomes);
  const prices = parsedList(market.outcomePrices).map(Number);
  const yes = outcomes.findIndex(outcome => /^(yes|sim)$/i.test(String(outcome).trim()));
  if (yes >= 0 && Number.isFinite(prices[yes])) return prices[yes];
  // Alguns mercados esportivos chegam com o contrato vencedor como primeiro
  // outcome, sem o rótulo literal "Yes".
  return Number.isFinite(prices[0]) ? prices[0] : null;
}

function shortTeamMatch(team, value) {
  if (namesMatch(team, value)) return true;
  const words = normalizedTeamName(team).split(' ').filter(word => word.length >= 3);
  const text = normalizedTeamName(value);
  return words.some(word => new RegExp(`\\b${word.slice(0, 3)}`).test(text));
}

function eventOneXTwo(event) {
  const markets = event.markets || [], teams = eventTeams(event.title);
  for (const market of markets) {
    const outcomes = parsedList(market.outcomes), prices = parsedList(market.outcomePrices).map(Number);
    const drawIndex = outcomes.findIndex(outcome => /^(draw|tie|empate)$/i.test(String(outcome).trim()));
    if (outcomes.length === 3 && drawIndex >= 0 && prices.every(Number.isFinite)) {
      const homeIndex = outcomes.findIndex((outcome, index) => index !== drawIndex && (!teams.length || namesMatch(teams[0], outcome)));
      const awayIndex = outcomes.findIndex((outcome, index) => index !== drawIndex && (!teams.length || namesMatch(teams[1], outcome)));
      if (homeIndex >= 0 && awayIndex >= 0 && homeIndex !== awayIndex) return { home: prices[homeIndex], draw: prices[drawIndex], away: prices[awayIndex] };
    }
  }
  if (teams.length !== 2) return null;
  const contracts = markets.map(market => ({
    market,
    price: marketYesPrice(market),
    text: `${market.question || ''} ${market.title || ''} ${market.groupItemTitle || ''} ${market.slug || ''}`,
  })).filter(item => item.price != null);
  const findYes = (matcher, excluded = new Set()) => {
    const entry = contracts.find(item => !excluded.has(item.market.id) && matcher(item.text));
    return entry || null;
  };
  const drawEntry = findYes(text => /\b(draw|tie|empate)\b/i.test(text));
  const homeEntry = findYes(text => shortTeamMatch(teams[0], text), new Set(drawEntry ? [drawEntry.market.id] : []));
  const awayEntry = findYes(text => shortTeamMatch(teams[1], text), new Set([drawEntry, homeEntry].filter(Boolean).map(entry => entry.market.id)));
  const home = homeEntry?.price, draw = drawEntry?.price, away = awayEntry?.price;
  return home != null && draw != null && away != null ? { home, draw, away } : null;
}

function brazilSerieASeries(sports) {
  const label = item => [item.sport, item.name, item.title, item.label, item.slug, item.series]
    .filter(Boolean).join(' ');
  const isBrazilSerieA = item => {
    const value = normalizedTeamName(label(item));
    return /(brasileirao|brasileiro|brazil|brasil)/.test(value) && /(serie a|seriea|serie-a)/.test(value);
  };
  const sport = sports.find(isBrazilSerieA);
  if (!sport) return null;
  const rawSeries = sport.seriesId ?? sport.series_id ?? sport.series ?? sport.id;
  const ids = Array.isArray(rawSeries) ? rawSeries : String(rawSeries || '').split(',');
  return {
    label: sport.sport || sport.name || sport.title || 'Brasileirão Série A',
    ids: ids.map(value => String(value).trim()).filter(value => /^\d+$/.test(value)),
  };
}

async function polymarketOdds(data) {
  document.body.innerHTML = shell('Odds da Série A', 'Teste de fonte');
  el('#content').innerHTML = `<p class="odds-intro">Odds 1X2 da rodada vigente do Campeonato Brasileiro, publicadas pelo Polymarket. Use a comparação para confrontar cada probabilidade com os fixtures do FUTRanking e ver o alfa em pontos percentuais.</p><div class="odds-toolbar"><span class="odds-status">Carregando a última coleta publicada…</span><button class="odds-mode" type="button" disabled>Comparar com o modelo</button><div class="kelly-control" aria-label="Fração do critério de Kelly"><button type="button" data-kelly="1" class="active">Kelly</button><button type="button" data-kelly="0.5">Kelly/2</button><button type="button" data-kelly="0.25">Kelly/4</button></div></div><section class="panel odds-panel"><div class="row brazil-odds-row table-head"><span>Jogo</span><span>Vitória casa</span><span>Empate</span><span>Vitória visitante</span></div><p class="empty-list">Carregando mercados da Série A…</p></section><aside class="odds-note"><strong>Fonte pública, coleta publicada.</strong> As odds são coletadas pelo workflow na API oficial do Polymarket e servidas pelo próprio FUTRanking. A comparação usa exclusivamente os fixtures já publicados pelo ranking; ela não consulta o Polymarket no navegador.</aside>`;
  const status = el('.odds-status'), panel = el('.odds-panel'), mode = el('.odds-mode'), kellyButtons = [...document.querySelectorAll('[data-kelly]')];
  const teamDisplay = name => {
    const known = (data.teams || []).find(team => namesMatch(team.name, name) || namesMatch(name, team.name));
    return `${known?.crest ? `<img class="crest" src="${html(known.crest)}" alt="" loading="lazy">` : ''}<span>${html(name)}</span>`;
  };
  const splitTeams = game => String(game.title || '').split(/\s+vs\.?\s+/i).map(part => part.trim());
  const displayGame = (home, away) => `<span class="odds-teams">${teamDisplay(home)}<span class="odds-vs">×</span>${teamDisplay(away)}</span>`;
  const fixtureFor = game => {
    const [home, away] = splitTeams(game);
    if (!home || !away) return null;
    return (data.fixtures || []).find(fixture =>
      namesMatch(fixture.home_team, home) && namesMatch(fixture.away_team, away)
    ) || null;
  };
  let games = [], collectedAt = '', sourceError = '', comparing = false, kellyFraction = 1;
  const renderSource = () => {
    status.textContent = `${games.length} jogo${games.length === 1 ? '' : 's'} com mercado 1X2 · coleta de ${collectedAt}`;
    panel.innerHTML = `<div class="row brazil-odds-row table-head"><span>Jogo</span><span>Vitória casa</span><span>Empate</span><span>Vitória visitante</span></div>${games.map(game => { const [home, away] = splitTeams(game); return `<article class="row brazil-odds-row"><span>${displayGame(home || game.title, away || '')}<small>${html(game.codes?.home || 'casa')} · empate · ${html(game.codes?.away || 'visitante')}</small></span><strong>${(Number(game.home) * 100).toFixed(1)}%</strong><strong>${(Number(game.draw) * 100).toFixed(1)}%</strong><strong>${(Number(game.away) * 100).toFixed(1)}%</strong></article>`; }).join('') || `<div class="odds-warning"><p>${html(sourceError || 'A API não retornou jogos 1X2 nesta coleta.')}</p></div>`}`;
  };
  const renderComparison = () => {
    const comparisons = games.flatMap(game => {
      const fixture = fixtureFor(game);
      if (!fixture) return [];
      return [
        { selection: fixture.home_team, model: Number(fixture.home_favoritism) / 100, market: Number(game.home) },
        { selection: 'Empate', model: Number(fixture.draw_probability) / 100, market: Number(game.draw) },
        { selection: fixture.away_team, model: Number(fixture.away_favoritism) / 100, market: Number(game.away) },
      ].filter(row => Number.isFinite(row.model) && Number.isFinite(row.market) && row.market > 0 && row.market < 1).map(row => {
        const alpha = row.model - row.market;
        // Fração de Kelly para um contrato que paga 1 quando o resultado ocorre:
        // f* = (p_modelo - p_mercado) / (1 - p_mercado). Não sugerimos posição negativa.
        const kelly = Math.max(0, Math.min(1, alpha / (1 - row.market)));
        return { ...row, fixture, alpha, kelly };
      });
    }).sort((left, right) => right.alpha - left.alpha || String(left.fixture.home_team).localeCompare(String(right.fixture.home_team), 'pt-BR'));
    const gamesMatched = new Set(comparisons.map(row => `${row.fixture.home_team}|${row.fixture.away_team}`)).size;
    status.textContent = `${gamesMatched} jogo${gamesMatched === 1 ? '' : 's'} conciliado${gamesMatched === 1 ? '' : 's'} · ${comparisons.length} resultado${comparisons.length === 1 ? '' : 's'} 1X2 · alfa = modelo − Polymarket`;
    const kellyLabel = kellyFraction === 1 ? 'Kelly' : kellyFraction === 0.5 ? 'Kelly/2' : 'Kelly/4';
    panel.innerHTML = `<div class="row odds-row kelly-row table-head"><span>Jogo</span><span>Seleção</span><span>Modelo</span><span>Polymarket</span><span>Alfa</span><span>${kellyLabel}</span></div>${comparisons.map(row => `<article class="row odds-row kelly-row"><span class="odds-game">${displayGame(row.fixture.home_team, row.fixture.away_team)}<small>${html(row.fixture.competition || 'Série A')}</small></span><span class="odds-selection">${html(row.selection)}</span><strong class="odds-model">${(row.model * 100).toFixed(1)}%</strong><strong class="odds-market">${(row.market * 100).toFixed(1)}%</strong><strong class="odds-alpha ${row.alpha >= 0 ? 'positive' : 'negative'}">${row.alpha >= 0 ? '+' : ''}${(row.alpha * 100).toFixed(1)} p.p.</strong><strong class="odds-kelly" title="Fração teórica de Kelly, limitada a 0% quando o alfa é negativo">${(row.kelly * kellyFraction * 100).toFixed(1)}%</strong></article>`).join('') || `<div class="odds-warning"><p>Não há fixture publicado que coincida com os ${games.length} jogo${games.length === 1 ? '' : 's'} desta coleta. Quando a agenda correspondente estiver no arquivo do ranking, a comparação aparecerá aqui.</p></div>`}`;
  };
  mode.addEventListener('click', () => {
    comparing = !comparing;
    mode.textContent = comparing ? 'Ver odds da fonte' : 'Comparar com o modelo';
    comparing ? renderComparison() : renderSource();
  });
  kellyButtons.forEach(button => button.addEventListener('click', () => {
    kellyFraction = Number(button.dataset.kelly);
    kellyButtons.forEach(item => item.classList.toggle('active', item === button));
    if (comparing) renderComparison();
  }));
  const load = async () => {
    status.textContent = 'Carregando a última coleta publicada…';
    try {
      const response = await fetch(`./data/polymarket-bra.json?v=${Date.now()}`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      games = Array.isArray(payload.games) ? payload.games : [];
      collectedAt = payload.generated_at ? time(payload.generated_at) : 'horário não informado';
      sourceError = payload.error || '';
      mode.disabled = false;
      renderSource();
    } catch (error) {
      status.textContent = 'Não foi possível carregar a coleta publicada.';
      panel.innerHTML = `<div class="row brazil-odds-row table-head"><span>Jogo</span><span>Vitória casa</span><span>Empate</span><span>Vitória visitante</span></div><div class="odds-warning"><p>Consulta de teste indisponível: ${html(String(error?.message || 'erro de rede'))}.</p></div>`;
    } finally { /* dados são publicados pelo workflow; não há atualização local */ }
  };
  await load();
}

async function legacyPolymarketOdds(data) {
  document.body.innerHTML = shell('Odds do mercado', 'Comparação');
  if (!(data.fixtures || []).length) {
    el('#content').innerHTML = `<p class="odds-intro">A comparação depende dos fixtures futuros publicados pelo FUTRanking.</p><section class="panel simulation-unavailable"><h2>Agenda futura indisponível</h2><p>O arquivo de dados atual não contém fixtures pendentes. Quando a próxima atualização da agenda for publicada, esta página voltará a consultar e conciliar os mercados 1X2 automaticamente.</p></section>`;
    return;
  }
  el('#content').innerHTML = `<p class="odds-intro">Compare o modelo 1X2 do FUTRanking com as probabilidades implícitas nos mercados ativos do Polymarket. Mostramos somente correspondências exatas de clubes e horário, ordenadas pelo maior <strong>alfa</strong>: probabilidade do modelo menos probabilidade do mercado.</p><div class="odds-toolbar"><span class="odds-status">Consultando mercados ativos do Polymarket…</span><button type="button" class="odds-refresh" disabled>Atualizar cotações</button></div><section class="panel odds-panel"><div class="row odds-row table-head"><span>Jogo</span><span>Seleção</span><span>Modelo</span><span>Polymarket</span><span>Alfa</span></div><p class="empty-list">Carregando odds ao vivo…</p></section><aside class="odds-note"><strong>Leitura do alfa.</strong> Um alfa positivo indica que o modelo atribui uma chance maior ao resultado do que o preço observado no mercado. Ele não considera liquidez, spread, taxas, limites, mudanças de escalação nem risco; não é recomendação de aposta.</aside>`;
  const status = el('.odds-status'), button = el('.odds-refresh'), panel = el('.odds-panel');
  const load = async () => {
    button.disabled = true;
    status.textContent = 'Consultando mercados ativos do Polymarket…';
    panel.innerHTML = `<div class="row odds-row table-head"><span>Jogo</span><span>Seleção</span><span>Modelo</span><span>Polymarket</span><span>Alfa</span></div><p class="empty-list">Carregando odds ao vivo…</p>`;
    try {
      const markets = await polymarketMarketsForFixtures(data.fixtures || []);
      const matched = matchedPolymarketOutcomes(data.fixtures || [], markets), rows = matched;
      const matchedGames = new Set(matched.map(row => `${row.fixture.external_id}`)).size;
      status.textContent = `${matchedGames} jogo${matchedGames === 1 ? '' : 's'} conciliado${matchedGames === 1 ? '' : 's'} · ${rows.length} resultado${rows.length === 1 ? '' : 's'} 1X2 exibido${rows.length === 1 ? '' : 's'} · atualizado agora`;
      const emptyMessage = 'Nenhum mercado 1X2 ativo pôde ser conciliado com segurança aos fixtures atuais. Isso pode significar que não há mercado para a agenda disponível ou que o Polymarket ainda não publicou a cotação.';
      panel.innerHTML = `<div class="row odds-row table-head"><span>Jogo</span><span>Seleção</span><span>Modelo</span><span>Polymarket</span><span>Alfa</span></div>${rows.map(row => `<article class="row odds-row"><span class="odds-game"><strong>${html(row.fixture.home_team)} × ${html(row.fixture.away_team)}</strong><small>${html(matchContext(row.fixture))} · ${html(time(row.fixture.scheduled_at))}</small></span><span class="odds-selection">${html(row.selection)}</span><span class="odds-model">${(row.model * 100).toFixed(1)}%</span><span class="odds-market">${(row.market * 100).toFixed(1)}%</span><strong class="odds-alpha ${row.alpha >= 0 ? 'positive' : 'negative'}">${row.alpha >= 0 ? '+' : ''}${(row.alpha * 100).toFixed(1)} p.p.<br><a class="odds-link" href="${html(row.url)}" target="_blank" rel="noopener">ver mercado</a></strong></article>`).join('') || `<p class="empty-list">${emptyMessage}</p>`}`;
    } catch (error) {
      const detail = String(error?.message || 'erro de rede').replace(/[^A-Za-z0-9 .:-]/g, '');
      status.textContent = 'Não foi possível atualizar as odds agora.';
      panel.innerHTML = `<div class="row odds-row table-head"><span>Jogo</span><span>Seleção</span><span>Modelo</span><span>Polymarket</span><span>Alfa</span></div><div class="odds-warning"><p>O Polymarket recusou ou não respondeu à consulta pública neste navegador (${html(detail)}). A página não usa proxy para contornar bloqueios geográficos.</p></div>`;
    } finally { button.disabled = false; }
  };
  button.addEventListener('click', load);
  await load();
}

function dataHealth(data) {
  document.body.innerHTML = shell('Saúde dos dados', 'Transparência');
  const rows = data.data_health || [];
  const coverage = data.coverage || [];
  const countries = [...new Set(coverage.map(row => row.country))].sort((a, b) => a.localeCompare(b, 'pt-BR'));
  const seasons = [...new Set(coverage.map(row => row.season))].sort().reverse();
  el('#content').innerHTML = `<p>Visão do que está efetivamente armazenado e usado pelo ranking. A coleta diária revisa o período recente; a data de sincronização deste painel é ${time(data.generated_at)}.</p><section class="panel health-panel"><div class="row health-row table-head"><span>Competição</span><span>Resultados</span><span>Primeiro jogo</span><span>Último resultado</span><span>Fixtures</span></div>${rows.map(row => `<div class="row health-row"><strong>${row.competition}</strong><span>${row.finished_matches.toLocaleString('pt-BR')}</span><span>${row.first_match_at ? matchTime(row.first_match_at) : '—'}</span><span>${row.last_match_at ? matchTime(row.last_match_at) : '—'}</span><span>${row.pending_fixtures.toLocaleString('pt-BR')}</span></div>`).join('') || '<p class="empty-list">Ainda não há cobertura publicada.</p>'}</section><section class="prose"><h2>Cobertura por país e temporada</h2><p>Use estes filtros para identificar onde a base histórica é mais densa antes de incluir novas competições.</p></section><div class="list-tools"><select class="list-filter coverage-country" aria-label="Filtrar cobertura por país"><option value="">Todos os países</option>${countries.map(country => `<option>${country}</option>`).join('')}</select><select class="list-filter coverage-season" aria-label="Filtrar cobertura por temporada"><option value="">Todas as temporadas</option>${seasons.map(season => `<option>${season}</option>`).join('')}</select></div><section class="panel health-panel coverage-panel"></section><section class="prose"><h2>Como ler</h2><p><strong>Resultados</strong> são jogos finalizados que podem alterar o rating. <strong>Fixtures</strong> são jogos sem placar final; servem para agenda e simulações, mas não atualizam ratings. Uma competição nova passa por carga histórica única antes de entrar na rotina incremental.</p></section>`;
  const countryFilter = el('.coverage-country'), seasonFilter = el('.coverage-season'), panel = el('.coverage-panel');
  const renderCoverage = () => {
    const visible = coverage.filter(row => (!countryFilter.value || row.country === countryFilter.value) && (!seasonFilter.value || row.season === seasonFilter.value));
    panel.innerHTML = `<div class="row health-row table-head"><span>País · temporada</span><span>Competição</span><span>Clubes</span><span>Resultados</span><span></span></div>${visible.map(row => `<div class="row health-row"><strong>${row.country} · ${row.season}</strong><span>${row.competition}</span><span>${row.teams}</span><span>${row.matches.toLocaleString('pt-BR')}</span><span></span></div>`).join('') || '<p class="empty-list">Não há dados neste recorte.</p>'}`;
  };
  countryFilter.addEventListener('change', renderCoverage); seasonFilter.addEventListener('change', renderCoverage); renderCoverage();
}

const percent = value => value == null ? '—' : `${(Number(value) * 100).toFixed(1)}%`;

function backtesting(data) {
  document.body.innerHTML = shell('Validação do modelo', 'Backtesting');
  const backtest = data.backtest;
  if (!backtest?.overall?.matches) {
    el('#content').innerHTML = `<section class="panel empty-list">A validação ficará disponível após o próximo processamento completo dos resultados.</section>`;
    return;
  }
  const choices = [{ competition: '', label: 'Todas as competições', ...backtest.overall }, ...(backtest.competitions || [])];
  el('#content').innerHTML = `<p>Comparamos a expectativa calculada <strong>antes</strong> de cada jogo com o resultado que de fato ocorreu. Se o modelo estiver calibrado, as duas colunas da tabela devem ficar próximas ao longo das faixas.</p><div class="backtest-tools"><label>Competição <select aria-label="Filtrar validação por competição">${choices.map(choice => `<option value="${choice.competition}">${choice.label || choice.competition}</option>`).join('')}</select></label></div><div class="backtest-host"></div>`;
  const host = el('.backtest-host'), select = el('.backtest-tools select');
  const selection = data.model_selection;
  const selectionSection = selection ? `<section class="prose model-selection"><h2>Comparação temporal de variantes</h2><p>O coeficiente de margem foi mantido em <strong>${Number(selection.goal_margin_coefficient).toFixed(2)}</strong>. Cada alternativa de mando é treinada cronologicamente e avaliada em quatro janelas sucessivas a partir de ${matchTime(selection.test_start)}; ao todo, há <strong>${selection.test_matches.toLocaleString('pt-BR')}</strong> jogos fora da amostra. O ranking publicado ainda usa mando +50; o candidato líder não é aplicado automaticamente.</p><section class="panel model-selection-panel"><div class="row model-selection-row table-head"><span>Mando</span><span>EQM</span><span>EAM</span><span>Viés</span></div>${selection.variants.map((variant, index) => `<div class="row model-selection-row ${index === 0 ? 'winner' : ''}"><span>+${variant.home_advantage}</span><span>${variant.brier_score.toFixed(3)}</span><span>${variant.mean_absolute_error.toFixed(3)}</span><strong class="${Math.abs(variant.calibration_bias) <= .03 ? 'positive' : 'negative'}">${variant.calibration_bias >= 0 ? '+' : ''}${(variant.calibration_bias * 100).toFixed(1)} p.p.${index === 0 ? ' · líder' : ''}</strong></div>`).join('')}</section><h3>Estabilidade do líder</h3><section class="panel model-selection-panel"><div class="row model-window-row table-head"><span>Janela</span><span>Início</span><span>Jogos</span><span>EQM</span><span>Viés</span></div>${selection.windows.map((window, index) => { const metrics = selection.winner.windows[index]; return `<div class="row model-window-row"><span>${window.label}</span><span>${matchTime(window.start)}</span><span>${metrics.evaluated_matches.toLocaleString('pt-BR')}</span><span>${metrics.brier_score.toFixed(3)}</span><strong class="${Math.abs(metrics.calibration_bias) <= .03 ? 'positive' : 'negative'}">${metrics.calibration_bias >= 0 ? '+' : ''}${(metrics.calibration_bias * 100).toFixed(1)} p.p.</strong></div>`; }).join('')}</section></section>` : `<section class="prose model-selection"><h2>Comparação temporal de variantes</h2><p>O experimento será exibido após a primeira execução do workflow com a grade de variantes.</p></section>`;
  const render = () => {
    const summary = choices.find(choice => choice.competition === select.value) || backtest.overall;
    host.innerHTML = `<div class="backtest-stats"><div class="backtest-stat"><b>${summary.matches.toLocaleString('pt-BR')}</b><span>jogos avaliados</span></div><div class="backtest-stat"><b>${percent(summary.mean_prediction)}</b><span>expectativa média</span></div><div class="backtest-stat"><b>${percent(summary.mean_observed)}</b><span>resultado médio</span></div><div class="backtest-stat"><b>${summary.brier_score.toFixed(3)}</b><span>erro quadrático médio</span></div></div><section class="panel backtest-panel"><div class="row backtest-row table-head"><span>Faixa prevista</span><span>Jogos</span><span>Previsto</span><span>Observado</span><span>Diferença</span></div>${summary.bins.map(bin => `<div class="row backtest-row"><span>${bin.label}</span><span>${bin.count.toLocaleString('pt-BR')}</span><span>${percent(bin.predicted)}</span><span>${percent(bin.observed)}</span><strong class="${Math.abs(bin.observed - bin.predicted) <= .03 ? 'positive' : 'negative'}">${(bin.observed - bin.predicted >= 0 ? '+' : '') + ((bin.observed - bin.predicted) * 100).toFixed(1)} p.p.</strong></div>`).join('')}</section><section class="prose backtest-note"><h2>Como ler</h2><p>A métrica usa a <strong>pontuação esperada do mandante</strong> no Glicko-2: vitória = 1, empate = 0,5 e derrota = 0. Assim, uma previsão média de 60% em uma faixa é bem calibrada se os mandantes daquela faixa obtiverem aproximadamente 60% de pontuação média. O <strong>erro quadrático médio</strong> e o <strong>erro absoluto médio</strong> (${summary.mean_absolute_error.toFixed(3)}) são melhores quanto menores.</p><p>Não há vazamento de informação: cada expectativa é persistida antes da atualização causada pelo próprio resultado. A análise mede calibração histórica, não retorno financeiro nem recomendação de aposta.</p></section>${selectionSection}`;
  };
  select.addEventListener('change', render);
  render();
}

function method() {
  document.body.innerHTML = shell('Método', 'Como funciona');
  el('#content').innerHTML = `<div class="prose"><p>O FUTRanking usa o <strong>Glicko-2</strong> para estimar força atual dos clubes. Cada resultado é comparado com a expectativa anterior ao jogo, levando em conta a incerteza de ambos.</p><h2>Dados, ordem e frequência</h2><ol><li>A ESPN é a fonte principal. O Global Sports Archive complementa a Série C corrente e a Série D, cujas páginas públicas fornecem jogos, placares e fases. Somente partidas com placar final entram no cálculo.</li><li>A carga histórica começa em 2016. A Série C já preservada da ESPN não é substituída: ao encontrar o mesmo confronto na mesma data, a fonte complementar atualiza o registro existente em vez de criar uma cópia. A Série D recebe a carga histórica do Global Sports Archive.</li><li>Após a carga anual completa, o cron consulta a ESPN a partir do último sucesso, com um dia de segurança. No Global Sports Archive, revisa apenas as duas rodadas mais recentes de cada fase de C e D; uma reconciliação mensal percorre a temporada corrente inteira. Os identificadores <span class="formula">espn:event-id</span> e <span class="formula">gsa:match-id</span>, somados à conciliação por competição, data e clubes, mantêm a importação idempotente.</li><li>Resultados são ordenados pelo campo <strong>played_at</strong> recebido da fonte. Quando uma fonte histórica não informa hora, as partidas daquele dia formam um mesmo grupo, sem ordem artificial entre elas.</li><li>Após cada horário distinto, os ratings são atualizados. Assim, um jogo às 18:00 altera o rating usado por uma partida às 22:00 no mesmo dia.</li><li>Partidas com o <strong>mesmo horário exato</strong> formam um grupo: não há uma ordem temporal verificável entre elas, então usam os mesmos ratings anteriores.</li><li>Um clube novo começa em <strong>r = 1500</strong>, <strong>RD = 350</strong> e volatilidade <strong>σ = 0,06</strong>. Vitória vale <strong>s = 1</strong>, empate <strong>0,5</strong> e derrota <strong>0</strong>.</li></ol><h2>Escala e expectativa</h2><p>O Glicko-2 converte os valores: <span class="formula">μ = (r − 1500) / 173,7178</span> e <span class="formula">φ = RD / 173,7178</span>. A incerteza do adversário é ponderada por <span class="formula">g(φⱼ) = 1 / √(1 + 3φⱼ²/π²)</span>.</p><p class="formula block">Eᵢⱼ = 1 / [1 + exp(−g(φⱼ) · (μᵢ + h/173,7178 − μⱼ))]</p><p><strong>h = +80</strong> para mandante e <strong>−80</strong> para visitante. O favoritismo dos fixtures é essa expectativa em porcentagem: uma medida de força relativa com mando, não odds nem previsão de placar.</p><h2>Margem de gols</h2><p>Vitória, empate e derrota continuam definidos por <span class="formula">s = 1, 0,5, 0</span>; o placar não é convertido em um resultado artificial. Para reconhecer uma vitória larga, a partida recebe um peso de evidência <span class="formula">w = min(1,8; 1 + 0,5·ln(d))</span>, em que <strong>d</strong> é a diferença de gols. Empates e vitórias por um gol usam <strong>w = 1</strong>; dois gols usam 1,35; três, 1,55; e cinco ou mais atingem o teto de 1,80.</p><p>O mesmo peso vale para os dois clubes: uma vitória por margem maior aumenta mais o rating do vencedor e reduz mais o do perdedor. O teto impede que placares incomuns exerçam influência desproporcional.</p><h2>Atualização cronológica</h2><p>Para o grupo de partidas daquele horário, calculamos <span class="formula">v = [Σwg²E(1−E)]⁻¹</span> e <span class="formula">Δ = vΣwg(s−E)</span>. Ganhar acima do esperado aumenta Δ; perder como favorito o reduz.</p><p>A volatilidade σ′ é obtida numericamente, com <strong>τ = 0,5</strong> e <span class="formula">a = ln(σ²)</span>:</p><p class="formula block">f(x) = eˣ(Δ²−φ²−v−eˣ) / [2(φ²+v+eˣ)²] − (x−a)/τ² = 0; &nbsp; σ′ = eˣ⁄²</p><p>Depois: <span class="formula">φ* = √(φ²+σ′²)</span>, <span class="formula">φ′ = [1/φ*² + 1/v]⁻½</span> e <span class="formula">μ′ = μ + φ′²Σwg(s−E)</span>. Por fim, os valores são reconvertidos para rating e RD.</p><h2>Inatividade e impacto</h2><p>Quando um clube fica semanas sem jogar, seu rating não muda, mas seu RD é ampliado antes de sua próxima partida — o modelo passa a ter menos certeza sobre a força anterior. O impacto mostrado em cada jogo é a diferença entre o cálculo do grupo completo e o mesmo cálculo sem aquele jogo; para horários únicos, é o impacto marginal daquela partida.</p><h2>Escalabilidade e correções</h2><p>O banco mantém o estado mais recente de cada clube e marca cada resultado já processado. Assim, o cron normal calcula apenas partidas novas, sem refazer toda a história. Se a fonte corrigir uma partida antiga, se os parâmetros mudarem ou se o catálogo receber uma competição nova, o sistema reconstrói o histórico uma única vez por segurança; esse é um caminho excepcional.</p></div>`;
}

fetch(freshDataUrl).then(r => r.json()).then(data => {
  if (page === 'admin') {
    const ADMIN_USER = 'admin', ADMIN_PASSWORD = 'futranking-local';
    const key = 'futranking-admin-decisions-v1', manualKey = 'futranking-admin-manual-merges-v1';
    const saved = () => JSON.parse(localStorage.getItem(key) || '{}');
    const manualMerges = () => JSON.parse(localStorage.getItem(manualKey) || '[]');
    const renderLogin = () => {
      document.body.innerHTML = `<main class="wrap page"><section class="admin-login"><div class="eyebrow">Área administrativa</div><h1>Revisar identidades</h1><p>Bloqueio local provisório. Não é autenticação de servidor.</p><form><label>Usuário<input name="user" autocomplete="username" required></label><label>Senha<input name="password" type="password" autocomplete="current-password" required></label><p class="login-error" role="alert"></p><button>Entrar</button></form></section></main>`;
      document.querySelector('form').addEventListener('submit', event => { event.preventDefault(); const form = new FormData(event.currentTarget); if (form.get('user') === ADMIN_USER && form.get('password') === ADMIN_PASSWORD) { sessionStorage.setItem('futranking-admin', '1'); renderAdmin(); } else el('.login-error').textContent = 'Usuário ou senha inválidos.'; });
    };
    const renderAdmin = () => {
      const candidates = (data.identity_audit || []).map(candidate => ({ ...candidate, impact: candidate.clubs.reduce((total, team) => total + Number(team.games || 0), 0) })).sort((a, b) => b.impact - a.impact), decisions = saved(), allClubs = data.admin_clubs || [];
      document.body.innerHTML = `<header class="top"><div class="wrap"><a class="brand" href="../index.html"><span class="mark">↗</span>FUTRanking</a><span class="pill">Administração local</span></div></header><main class="wrap page"><div class="eyebrow">Administração</div><h1>Pendências de identidade</h1><p>Revise nomes, estado, escudos e volume de jogos. Os casos com mais partidas aparecem primeiro, para concentrar a revisão onde ela mais afeta o ranking. As decisões são armazenadas somente neste navegador; baixe o arquivo JSON para aplicá-las ao sistema.</p><div class="admin-note">Uma decisão de <strong>unir</strong> não altera o ranking nesta página. Ela cria uma instrução revisável para a próxima atualização do código e do banco.</div><div class="admin-toolbar"><button class="admin-action export">Baixar decisões</button><button class="admin-action secondary clear">Limpar decisões locais</button><span>${candidates.length} pendência${candidates.length === 1 ? '' : 's'} publicada${candidates.length === 1 ? '' : 's'}.</span></div><section class="manual-merge"><h2>Indicar fusão manual</h2><p>Use quando a auditoria não tiver apontado o par. A indicação será validada antes de entrar no banco.</p><form class="manual-merge-form"><input name="first" list="admin-clubs" placeholder="Primeiro clube" required><input name="second" list="admin-clubs" placeholder="Segundo clube" required><button class="admin-action">Adicionar à fila</button><p class="manual-feedback" role="alert"></p></form><datalist id="admin-clubs">${allClubs.map(team => `<option value="${team.name}">${team.country || ''}${team.state ? ` · ${team.state}` : ''}</option>`).join('')}</datalist><ul class="manual-merge-list">${manualMerges().map((pair, index) => `<li>${pair.first} ↔ ${pair.second}<button type="button" data-remove-manual="${index}">Remover</button></li>`).join('') || '<li>Nenhuma fusão manual indicada.</li>'}</ul></section><section class="identity-list">${candidates.map(candidate => { const id = `${candidate.state}:${candidate.key}`; const status = decisions[id] || 'pending'; return `<article class="identity-card" data-id="${id}"><header><div><h2>${candidate.key}</h2><p>${candidate.state === '?' ? 'Estado ainda não identificado' : `Estado: ${candidate.state}`}</p></div><div><span class="identity-impact">${candidate.impact.toLocaleString('pt-BR')} jogos envolvidos</span> <span class="identity-status ${status === 'pending' ? 'pending' : ''}">${status === 'merge' ? 'unir' : status === 'separate' ? 'manter separados' : 'pendente'}</span></div></header><div class="identity-clubs">${candidate.clubs.map(team => `<a class="identity-club club-link" href="../clube.html?time=${encodeURIComponent(team.name)}" target="_blank" rel="noopener" aria-label="Abrir perfil de ${team.name}">${crest(team.crest_url, team.name)}<div><strong>${team.name}</strong><small>${team.country || 'Brasil'}${team.state ? ` · ${team.state}` : ''} · ${Number(team.games || 0).toLocaleString('pt-BR')} jogos</small></div></a>`).join('')}</div><div class="identity-actions"><button class="admin-action" data-decision="merge">Unir</button><button class="admin-action secondary" data-decision="separate">Manter separados</button><button class="admin-action warn" data-decision="pending">Adiar</button></div></article>`; }).join('') || '<p class="empty-list">Não há pendências de identidade no último dado publicado.</p>'}</section></main>`;
      document.querySelectorAll('[data-decision]').forEach(button => button.addEventListener('click', () => { const card = button.closest('[data-id]'), next = saved(); next[card.dataset.id] = button.dataset.decision; localStorage.setItem(key, JSON.stringify(next)); renderAdmin(); }));
      el('.manual-merge-form')?.addEventListener('submit', event => { event.preventDefault(); const form = new FormData(event.currentTarget), first = String(form.get('first') || '').trim(), second = String(form.get('second') || '').trim(), feedback = el('.manual-feedback'); if (!allClubs.some(team => team.name === first) || !allClubs.some(team => team.name === second)) { feedback.textContent = 'Selecione dois clubes existentes na lista.'; return; } if (first === second) { feedback.textContent = 'Escolha dois clubes diferentes.'; return; } const pairs = manualMerges(); if (!pairs.some(pair => new Set([pair.first, pair.second]).size === 2 && new Set([pair.first, pair.second]).has(first) && new Set([pair.first, pair.second]).has(second))) { pairs.push({ first, second }); localStorage.setItem(manualKey, JSON.stringify(pairs)); } renderAdmin(); });
      document.querySelectorAll('[data-remove-manual]').forEach(button => button.addEventListener('click', () => { const pairs = manualMerges(); pairs.splice(Number(button.dataset.removeManual), 1); localStorage.setItem(manualKey, JSON.stringify(pairs)); renderAdmin(); }));
      el('.clear')?.addEventListener('click', () => { localStorage.removeItem(key); localStorage.removeItem(manualKey); renderAdmin(); });
      el('.export')?.addEventListener('click', () => { const blob = new Blob([JSON.stringify({ generated_at: new Date().toISOString(), decisions: saved(), manual_merges: manualMerges() }, null, 2)], { type: 'application/json' }); const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = 'futranking-decisoes-identidade.json'; link.click(); URL.revokeObjectURL(link.href); });
    };
    sessionStorage.getItem('futranking-admin') === '1' ? renderAdmin() : renderLogin();
  }
  if (page === 'ranking') {
    document.body.innerHTML = shell('Ranking');
    const filters = [['general', 'Geral'], ['Série A', 'Série A'], ['Série B', 'Série B'], ['Série C', 'Série C'], ['Série D', 'Série D']];
    const countries = [...new Set([...data.teams, ...(data.excluded_teams || [])].map(team => team.country).filter(country => country && country !== 'País não informado'))].sort((a, b) => a.localeCompare(b, 'pt-BR'));
    el('#content').innerHTML = `<p>Força estimada. Dados sincronizados em ${time(data.generated_at)}. Inclui apenas clubes com jogos rastreados nos últimos ${data.eligibility.max_inactivity_days} dias e RD abaixo de ${data.eligibility.max_rd}. Os filtros por divisão exibem os clubes que disputam aquela Série nesta temporada; o rating continua sendo global. Clique em um clube.</p><div class="ranking-filters" role="group" aria-label="Filtrar ranking">${filters.map(([value, label], index) => `<button type="button" data-division="${value}" class="${index === 0 ? 'active' : ''}">${label}</button>`).join('')}<select class="country-filter" aria-label="Filtrar ranking por país"><option value="">Todos os países</option>${countries.map(country => `<option value="${country}">${country}</option>`).join('')}</select></div><p class="ranking-summary"></p><section class="panel ranking-panel"></section>`;
    const buttons = [...document.querySelectorAll('[data-division]')], countryFilter = el('.country-filter'), summary = el('.ranking-summary'), panel = el('.ranking-panel');
    let selectedDivision = 'general';
    const renderRanking = () => {
      let teams = selectedDivision === 'general' ? data.teams : data.teams.filter(team => (team.divisions || []).includes(selectedDivision));
      if (countryFilter.value) teams = teams.filter(team => team.country === countryFilter.value);
      const scope = [selectedDivision === 'general' ? 'ranking geral' : selectedDivision, countryFilter.value].filter(Boolean).join(' · ');
      summary.textContent = `${teams.length} clubes elegíveis em ${scope}.`;
      panel.innerHTML = `<div class="row rank table-head"><span>Pos.</span><span>Clube</span><span>Rating</span></div>${teams.map((team, index) => `<a class="row rank" href="clube.html?time=${encodeURIComponent(team.name)}"><span>${index + 1}º</span><b>${club(team.name, team.crest)}</b><strong>${Math.round(team.rating)}</strong></a>`).join('') || '<p class="empty-list">Não há clubes elegíveis neste filtro.</p>'}`;
      buttons.forEach(button => button.classList.toggle('active', button.dataset.division === selectedDivision));
    };
    buttons.forEach(button => button.addEventListener('click', () => { selectedDivision = button.dataset.division; renderRanking(); }));
    countryFilter.addEventListener('change', renderRanking);
    renderRanking();
  }
  if (page === 'resultados') {
    document.body.innerHTML = shell('Últimos resultados', 'Transparência');
    el('#content').innerHTML = `<p>Rating após o ciclo e impacto estimado daquele jogo. Horários em Brasília. Pesquise por clube, competição, rodada ou fase.</p><div class="list-host"></div>`;
    mountPagedList(el('.list-host'), data.matches, m => game(m), { search: true, competitionFilter: true, placeholder: 'Buscar clube, competição, rodada ou fase', pageSize: 15, emptyText: 'Nenhum resultado corresponde à busca.' });
  }
  if (page === 'fixtures') {
    document.body.innerHTML = shell('Próximos jogos', 'Agenda');
    el('#content').innerHTML = `<p>Horários em Brasília. Percentuais representam favoritismo Glicko-2 com mando de campo. Consulte toda a agenda disponível e pesquise pelo confronto.</p><div class="list-host"></div>`;
    mountPagedList(el('.list-host'), data.fixtures, m => game(m, true), { search: true, competitionFilter: true, placeholder: 'Buscar clube, competição, rodada ou fase', pageSize: 15, emptyText: 'Nenhum jogo futuro corresponde à busca.' });
  }
  if (page === 'odds') {
    polymarketOdds(data);
  }
  if (page === 'club') {
    const name = q.get('time'), team = [...data.teams, ...(data.excluded_teams || [])].find(t => t.name === name);
    if (!team) { document.body.innerHTML = shell('Clube não encontrado'); return; }
    const matches = data.matches.filter(m => m.home_team === name || m.away_team === name), fixtures = data.fixtures.filter(m => m.home_team === name || m.away_team === name), p = team.performance;
    document.body.innerHTML = shell(club(name, team.crest), 'Perfil do clube');
    const confidence = ratingConfidence(Number(team.rd));
    const country = team.country || 'País não informado';
    const stateTag = countryLabel(country) === 'Brasil' && team.state ? `<span>${team.state}</span>` : '';
    const locationTags = [`<span class="country-tag">${countryFlag(country)}${countryLabel(country)}</span>`, stateTag, ...(team.divisions || []).map(value => `<span>${value}</span>`)].filter(Boolean).join('');
    el('#content').innerHTML = `<a class="back club-return" href="ranking.html">← Voltar ao ranking</a><section class="club-overview"><div class="club-context"><span class="club-context-label">Identidade do clube</span><div class="club-tags">${locationTags}</div></div><div class="club-primary-grid"><article class="club-key-stat"><span>Posição</span><strong>${team.position ? `${team.position}º` : '—'}</strong><small>${team.position ? 'ranking geral atual' : 'fora do ranking atual'}</small></article><article class="club-key-stat rating-key"><span>Rating Glicko-2</span><strong>${Math.round(team.rating)}</strong><small>força estimada</small></article><article class="club-confidence"><div><span>Desvio de rating (RD)</span><strong>${Number(team.rd).toFixed(1)}</strong></div><span class="confidence-badge ${confidence.tone}">${confidence.label}</span><p>${confidence.description} Quanto menor o RD, maior a confiança do modelo.</p></article></div><div class="club-secondary-grid"><article><strong>${p.games}</strong><span>jogos rastreados</span></article><article><strong>${p.wins} · ${p.draws} · ${p.losses}</strong><span>vitórias · empates · derrotas</span></article><article><strong>${p.goals_for}:${p.goals_against}</strong><span>gols pró : contra</span></article></div></section><div class="chart-host"></div><h2>Próximos fixtures</h2><div class="fixtures-host"></div><h2>Últimos resultados</h2><div class="results-host"></div>`;
    mountRatingChart(el('.chart-host'), matches, name);
    mountPagedList(el('.fixtures-host'), fixtures, m => game(m, true), { search: true, competitionFilter: true, placeholder: 'Buscar competição, rodada ou fase', pageSize: 10, emptyText: 'Nenhum fixture futuro disponível.' });
    mountPagedList(el('.results-host'), matches, m => game(m), { search: true, competitionFilter: true, placeholder: 'Buscar competição, rodada ou fase', pageSize: 10, emptyText: 'Nenhum resultado rastreado disponível.' });
  }
  if (page === 'simulation') {
    simulations(data);
  }
  if (page === 'comparison') {
    comparisons(data);
  }
  if (page === 'data-health') {
    dataHealth(data);
  }
  if (page === 'backtest') {
    backtesting(data);
  }
  if (page === 'method') {
    method();
    el('#content').insertAdjacentHTML('beforeend', `<h2>Classificação automática do estádio</h2><p>Para cada evento, o sistema compara o país do estádio informado pela ESPN com os países dos dois clubes. Estádio no país do mandante usa <strong>h = +80</strong>; no país do visitante, <strong>h = −80</strong>; em terceiro país, usa <strong>h = 0</strong> e recebe o rótulo “Campo neutro”. Se o estádio ainda não estiver informado, preservamos o mando padrão; exceções conhecidas, como finais em sede única, permanecem auditáveis por ID de evento.</p>`);
    el('#content').insertAdjacentHTML('beforeend', `<h2>Campo neutro</h2><p>O ajuste de mando é <strong>h = +80</strong> para o mandante e <strong>−80</strong> para o visitante. Em eventos explicitamente marcados como campo neutro, ambos usam <strong>h = 0</strong>. Como a ESPN não fornece essa marcação de modo confiável, as exceções são mantidas em uma lista auditável por ID de evento e recebem o rótulo “Campo neutro” no site.</p><h2>Peso de mata-mata</h2><p>Além do peso pela margem de gols, jogos eliminatórios recebem um multiplicador de evidência: <strong>1,05</strong> na primeira fase, <strong>1,10</strong> na segunda, <strong>1,20</strong> nas oitavas, <strong>1,35</strong> nas quartas, <strong>1,50</strong> nas semifinais e <strong>1,70</strong> na final. Assim, o peso efetivo é <span class="formula">w = w_margem · w_fase</span>. Jogos de liga e fases sem eliminatória usam <strong>w_fase = 1</strong>. Esse peso aumenta a atualização Glicko-2 para os dois clubes, sem mudar o placar, o mando ou a regra de expectativa.</p><h2>Competições e elegibilidade</h2><p>O catálogo atual acompanha ligas nacionais de Argentina, Bolívia, Brasil, Chile, Colômbia, Equador, Paraguai, Peru, Uruguai e Venezuela, além de Copa do Brasil, CONMEBOL Libertadores e CONMEBOL Sul-Americana, desde 2016. Uma nova competição altera a versão do catálogo e provoca uma reconstrução única e cronológica do histórico. O ranking principal só inclui clubes com resultado rastreado nos últimos <strong>90 dias</strong> e <strong>RD abaixo de 120</strong>; clubes fora desses critérios mantêm o histórico, mas não recebem posição até voltarem a ter dados recentes.</p>`);
    el('#content').insertAdjacentHTML('beforeend', `<h2>Formato especial da Série B em 2026</h2><p>A Série B mantém os pontos corridos para o título e para o rebaixamento: o campeão é o 1º colocado após as 38 rodadas, e os quatro últimos caem. O acesso, porém, tem uma regra própria: 1º e 2º sobem direto; 3º×6º e 4º×5º disputam as duas vagas restantes em ida e volta. O clube de melhor campanha decide em casa e avança em caso de empate no placar agregado. Nas simulações, esses quatro participantes são definidos ao final de cada cenário e os dois duelos são sorteados com os ratings e o mando de cada partida. Portanto, os fixtures provisórios “TBD” da ESPN são representados pelo playoff, em vez de serem tratados como clubes fictícios.</p>`);
  }
}).catch(() => { document.body.innerHTML = shell('Dados indisponíveis'); });
