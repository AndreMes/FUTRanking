const q = new URLSearchParams(location.search), page = document.body.dataset.page, el = s => document.querySelector(s);
const date = v => new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium' }).format(new Date(`${v}T12:00:00`));
const time = v => new Intl.DateTimeFormat('pt-BR', { timeZone: 'America/Sao_Paulo', dateStyle: 'short', timeStyle: 'short' }).format(new Date(v));
const matchTime = v => v.includes('T') ? time(v) : date(v);
const crest = (url, name) => url ? `<img class="crest" src="${url}" alt="Brasão do ${name}" loading="lazy">` : '';
const club = (name, url, link = false) => {
  const content = `${crest(url, name)}${name}`;
  return link ? `<a class="club club-link" href="clube.html?time=${encodeURIComponent(name)}">${content}</a>` : `<span class="club">${content}</span>`;
};
const impact = value => `<span class="impact ${value >= 0 ? 'positive' : 'negative'}">${value >= 0 ? '+' : ''}${value?.toFixed(1) ?? '—'}</span>`;
const shell = (title, kicker = 'Brasil · CONMEBOL') => `<header class="top"><div class="wrap"><a class="brand" href="index.html"><span class="mark">↗</span>FUTRanking</a><nav><a href="ranking.html">Ranking</a><a href="resultados.html">Resultados</a><a href="proximos-jogos.html">Próximos jogos</a><a href="simulacoes.html">Simulações</a><a href="metodo.html">Método</a></nav><span class="pill">${kicker}</span></div></header><main class="wrap page"><div class="eyebrow">${kicker}</div><h1>${title}</h1><div id="content"></div></main><footer class="foot"><div class="wrap">FUTRanking · Glicko-2 para o futebol brasileiro</div></footer>`;
const stageName = stage => ({LAST_16: 'Oitavas de final', QUARTER_FINALS: 'Quartas de final', SEMI_FINALS: 'Semifinal', FINAL: 'Final', THIRD_PLACE: 'Disputa do 3º lugar'}[stage] || stage?.replaceAll('_', ' '));
function matchContext(m) { const date = m.played_at || m.scheduled_at; const season = m.season || (m.competition === 'Série A' && date ? String(date).slice(0, 4) : ''); const parts = [[m.competition, season].filter(Boolean).join(' ')]; if (m.stage && m.stage !== 'REGULAR_SEASON') parts.push(stageName(m.stage)); else if (m.matchday) parts.push(`Rodada ${m.matchday}`); if (m.group_name) parts.push(m.group_name); if (m.neutral_site) parts.push('Campo neutro'); return parts.filter(Boolean).join(' · '); }
const contextStyle = document.createElement('style');
contextStyle.textContent = '.competition{display:block;margin-top:4px;color:#006b54;font-size:.68rem;font-weight:800;line-height:1.25}.list-tools{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:24px 0 12px}.list-search,.list-filter{padding:11px 13px;border:1px solid #d8d0c1;border-radius:9px;background:#fffdf8;color:#10231d;font:inherit}.list-search{width:min(100%,420px)}.list-filter{min-width:175px}.pager{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:14px 0 4px;color:#5b6f68;font-size:.88rem}.pager-actions{display:flex;gap:8px}.pager button{border:1px solid #d8d0c1;border-radius:7px;background:#fffdf8;color:#10231d;padding:7px 10px;font:inherit;font-weight:700;cursor:pointer}.pager button:disabled{opacity:.45;cursor:not-allowed}.empty-list{padding:22px;text-align:center;color:#5b6f68}.chart-card{margin:30px 0 34px;padding:24px;border:1px solid #d8d0c1;border-radius:16px;background:#fffdf8}.chart-card h2{margin:0 0 6px}.chart-card p{margin:0 0 16px;color:#5b6f68}.rating-chart{display:block;width:100%;height:auto;overflow:visible}.rating-chart .grid{stroke:#e5ddd0;stroke-width:1}.rating-chart .axis-label{fill:#687a73;font-size:11px}.rating-chart .line{fill:none;stroke:#006b54;stroke-width:3;stroke-linecap:round;stroke-linejoin:round}.rating-chart .point{fill:#f4b942;stroke:#006b54;stroke-width:2}.chart-summary{display:flex;gap:20px;margin-top:12px;color:#5b6f68;font-size:.88rem}.chart-summary strong{color:#10231d}@media(max-width:650px){.list-tools{margin-top:18px}.pager{align-items:flex-start;flex-direction:column}.chart-card{padding:16px}.chart-summary{gap:12px;flex-wrap:wrap}}';
document.head.append(contextStyle);
const chartControlsStyle = document.createElement('style');
chartControlsStyle.textContent = '.chart-controls{display:flex;align-items:end;gap:10px;flex-wrap:wrap;margin:18px 0}.chart-presets{display:flex;gap:6px;flex-wrap:wrap}.chart-presets button{border:1px solid #d8d0c1;border-radius:99px;background:#fffdf8;color:#10231d;padding:7px 10px;font:inherit;font-size:.8rem;font-weight:750;cursor:pointer}.chart-presets button.active{background:#075c42;border-color:#075c42;color:#fff}.chart-date{display:grid;gap:4px;color:#5b6f68;font-size:.72rem;font-weight:750}.chart-date input{border:1px solid #d8d0c1;border-radius:7px;background:#fffdf8;color:#10231d;padding:7px;font:inherit}';
document.head.append(chartControlsStyle);
const simulationStyle = document.createElement('style');
simulationStyle.textContent = '.simulation-note{max-width:760px;margin-bottom:26px}.simulation-grid{display:grid;grid-template-columns:1fr 1fr;gap:22px}.simulation-grid h2{margin-top:0}.simulation-row{grid-template-columns:40px 1fr 66px 82px}.simulation-row strong{text-align:right}.simulation-method{max-width:820px;margin-top:42px;padding:24px;border-left:4px solid #075c42;background:#e9f0e8}.simulation-method h2{margin-top:0}.simulation-method p{color:#34473f}.simulation-unavailable{padding:26px}@media(max-width:780px){.simulation-grid{grid-template-columns:1fr}.simulation-row{grid-template-columns:32px 1fr 54px 72px;font-size:.82rem}.top nav{flex-wrap:wrap;justify-content:center}}';
document.head.append(simulationStyle);
const rankingFilterStyle = document.createElement('style');
rankingFilterStyle.textContent = '.ranking-filters{display:flex;flex-wrap:wrap;gap:8px;margin:22px 0 14px}.ranking-filters button{border:1px solid #d8d0c1;border-radius:999px;background:#fffdf8;color:#10231d;padding:8px 13px;font:inherit;font-size:.85rem;font-weight:800;cursor:pointer}.ranking-filters button.active{background:#075c42;border-color:#075c42;color:#fff}.ranking-summary{margin:0 0 12px;color:#5b6f68;font-size:.9rem}';
document.head.append(rankingFilterStyle);
const clubLinkStyle = document.createElement('style');
clubLinkStyle.textContent = '.club-link{color:inherit;text-decoration:none}.club-link:hover,.club-link:focus-visible{color:#075c42;text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:3px}';
document.head.append(clubLinkStyle);

function game(m, fixture = false) {
  const labels = { IN_PLAY: 'Em andamento', PAUSED: 'Intervalo', POSTPONED: 'Adiado', SUSPENDED: 'Suspenso', CANCELLED: 'Cancelado', FINISHED: 'Aguardando placar' };
  const pending = fixture && (labels[m.status] || (new Date(m.scheduled_at).getTime() <= Date.now() ? 'Aguardando resultado' : null));
  const score = fixture ? (pending ? `<span class="score forecast">${pending}</span>` : `<span class="score forecast">${m.home_favoritism}% · ${m.away_favoritism}%</span>`) : `<span class="score">${m.home_goals}–${m.away_goals}</span>`;
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

function ratingChartSvg(history, team) {
  if (!history.length) return `<p class="empty-list">Não há partidas no intervalo selecionado.</p>`;
  const width = 800, height = 260, padding = { top: 20, right: 24, bottom: 42, left: 52 };
  const dates = history.map(point => new Date(point.at).getTime()), ratings = history.map(point => point.rating);
  const minDate = Math.min(...dates), maxDate = Math.max(...dates), minRating = Math.min(...ratings), maxRating = Math.max(...ratings);
  const ratingPad = Math.max(12, (maxRating - minRating) * 0.15), low = minRating - ratingPad, high = maxRating + ratingPad;
  const x = value => padding.left + (maxDate === minDate ? (width - padding.left - padding.right) / 2 : (value - minDate) / (maxDate - minDate) * (width - padding.left - padding.right));
  const y = value => padding.top + (high - value) / (high - low) * (height - padding.top - padding.bottom);
  const line = history.map(point => `${x(new Date(point.at).getTime()).toFixed(1)},${y(point.rating).toFixed(1)}`).join(' ');
  const tickValues = [0, 0.5, 1].map(fraction => low + (high - low) * fraction);
  const dateLabel = value => new Intl.DateTimeFormat('pt-BR', { timeZone: 'America/Sao_Paulo', month: 'short', year: '2-digit' }).format(new Date(value));
  const dateTicks = [minDate, minDate + (maxDate - minDate) / 2, maxDate];
  const grid = tickValues.map(value => `<line class="grid" x1="${padding.left}" x2="${width - padding.right}" y1="${y(value)}" y2="${y(value)}"/><text class="axis-label" x="${padding.left - 8}" y="${y(value) + 4}" text-anchor="end">${value.toFixed(0)}</text>`).join('');
  const xLabels = dateTicks.map(value => `<text class="axis-label" x="${x(value)}" y="${height - 14}" text-anchor="middle">${dateLabel(value)}</text>`).join('');
  const points = history.map(point => `<circle class="point" cx="${x(new Date(point.at).getTime())}" cy="${y(point.rating)}" r="3.5"><title>${time(point.at)} · rating ${point.rating.toFixed(1)}</title></circle>`).join('');
  const change = history.at(-1).rating - history[0].rating;
  return `<svg class="rating-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Trajetória do rating de ${team}">${grid}<polyline class="line" points="${line}"/>${points}${xLabels}</svg><div class="chart-summary"><span>Primeiro ponto: <strong>${history[0].rating.toFixed(1)}</strong></span><span>Variação: <strong>${change >= 0 ? '+' : ''}${change.toFixed(1)}</strong></span><span>Partidas: <strong>${history.length}</strong></span></div>`;
}

function mountRatingChart(host, matches, team) {
  const history = teamRatingHistory(matches, team);
  if (!history.length) { host.innerHTML = `<section class="chart-card"><h2>Trajetória do rating</h2><p>Ainda não há resultados suficientes para desenhar a trajetória deste clube.</p></section>`; return; }
  const toInputDate = value => new Date(value).toISOString().slice(0, 10);
  const first = new Date(history[0].at).getTime(), last = new Date(history.at(-1).at).getTime();
  host.innerHTML = `<section class="chart-card"><h2>Trajetória do rating</h2><p>Cada ponto representa o rating após uma partida rastreada. Ajuste o período para mudar o eixo X; passe o cursor ou toque em um ponto para ver data, horário e valor.</p><div class="chart-controls"><div class="chart-presets" aria-label="Período do gráfico"><button type="button" data-months="all" class="active">Tudo</button><button type="button" data-months="24">24 meses</button><button type="button" data-months="12">12 meses</button><button type="button" data-months="6">6 meses</button><button type="button" data-months="3">3 meses</button></div><label class="chart-date">De<input type="date" data-range="start" min="${toInputDate(first)}" max="${toInputDate(last)}" value="${toInputDate(first)}"></label><label class="chart-date">Até<input type="date" data-range="end" min="${toInputDate(first)}" max="${toInputDate(last)}" value="${toInputDate(last)}"></label></div><div class="chart-canvas"></div></section>`;
  const canvas = host.querySelector('.chart-canvas'), startInput = host.querySelector('[data-range="start"]'), endInput = host.querySelector('[data-range="end"]'), buttons = [...host.querySelectorAll('[data-months]')];
  const render = () => {
    const start = new Date(`${startInput.value}T00:00:00-03:00`).getTime(), end = new Date(`${endInput.value}T23:59:59-03:00`).getTime();
    canvas.innerHTML = start <= end ? ratingChartSvg(history.filter(point => { const at = new Date(point.at).getTime(); return at >= start && at <= end; }), team) : '<p class="empty-list">A data inicial deve ser anterior à data final.</p>';
  };
  const setPeriod = months => {
    let start = first;
    if (months !== 'all') { const cutoff = new Date(last); cutoff.setUTCMonth(cutoff.getUTCMonth() - Number(months)); start = Math.max(first, cutoff.getTime()); }
    startInput.value = toInputDate(start); endInput.value = toInputDate(last);
    buttons.forEach(button => button.classList.toggle('active', button.dataset.months === String(months)));
    render();
  };
  buttons.forEach(button => button.addEventListener('click', () => setPeriod(button.dataset.months)));
  [startInput, endInput].forEach(input => input.addEventListener('change', () => { buttons.forEach(button => button.classList.remove('active')); render(); }));
  render();
}

const percentage = value => `${(value * 100).toFixed(2)}%`;

function simulationTable(teams, field, title, detail, orderByPoints = false) {
  const rows = teams.filter(team => Number((team[field] * 100).toFixed(2)) > 0).sort((a, b) => orderByPoints ? b.points - a.points || a.position - b.position : b[field] - a[field] || a.position - b.position);
  return `<div><h2>${title}</h2><p>${detail}</p><section class="panel"><div class="row simulation-row table-head"><span>Pos.</span><span>Clube</span><span>Pontos</span><span>Prob.</span></div>${rows.map(team => `<div class="row simulation-row"><span>${team.position}º</span><b>${club(team.name, team.crest, true)}</b><span>${team.points}</span><strong>${percentage(team[field])}</strong></div>`).join('')}</section></div>`;
}

function simulations(data) {
  document.body.innerHTML = shell('Reta final', 'Simulações');
  const simulation = data.simulation;
  if (!simulation?.available) {
    el('#content').innerHTML = `<section class="panel simulation-unavailable"><p>A simulação ficará disponível quando houver resultados e fixtures restantes da Série A na fonte de dados.</p></section>`;
    return;
  }
  el('#content').innerHTML = `<p class="simulation-note">Probabilidades estimadas para a Série A ${simulation.season}, com base em <strong>${simulation.scenarios.toLocaleString('pt-BR')}</strong> cenários simulados. A tabela abaixo parte da situação atual: ${simulation.completed_matches} partidas concluídas e ${simulation.fixtures_remaining} restantes.</p><div class="simulation-grid">${simulationTable(simulation.teams, 'champion_probability', 'Probabilidade de título', 'Chance de terminar em 1º lugar. A apresentação segue a classificação atual por pontos.', true)}${simulationTable(simulation.teams, 'relegation_probability', 'Probabilidade de rebaixamento', 'Chance de terminar entre os quatro últimos.')}</div><section class="simulation-method"><h2>Como estimamos</h2><p>Em cada cenário, cada fixture restante é sorteado de forma independente a partir do rating Glicko-2 atual e do mando de campo. A probabilidade de empate usa a taxa observada de empates da temporada (${percentage(simulation.observed_draw_rate)}), reduzida quando a diferença de rating entre os clubes cresce e limitada entre ${percentage(simulation.draw_limits[0])} e ${percentage(simulation.draw_limits[1])}.</p><p>Ao final, contamos quantas vezes cada clube foi campeão ou terminou no Z-4. Os desempates da simulação seguem pontos, vitórias, saldo de gols, gols pró e nome do clube; para os jogos futuros, uma vitória decisiva adiciona uma margem projetada de um gol. É uma projeção baseada nos dados disponíveis, não uma previsão determinística nem recomendação de aposta.</p></section>`;
  el('.simulation-method').insertAdjacentHTML('beforeend', '<p>Partidas ainda sem resultado final confirmado, inclusive as que já começaram, são simuladas como se ainda não tivessem começado. A projeção não considera o placar ou o tempo de jogo em andamento e só incorpora o resultado após a próxima coleta.</p>');
}

function method() {
  document.body.innerHTML = shell('Método', 'Como funciona');
  el('#content').innerHTML = `<div class="prose"><p>O FUTRanking usa o <strong>Glicko-2</strong> para estimar força atual dos clubes. Cada resultado é comparado com a expectativa anterior ao jogo, levando em conta a incerteza de ambos.</p><h2>Dados, ordem e frequência</h2><ol><li>A coleta ocorre diariamente pela ESPN. O catálogo atual inclui Séries A, B, C e D, Copa do Brasil e CONMEBOL Libertadores; somente partidas com placar final entram no cálculo.</li><li>A carga histórica começa em 2016. Cada competição tem um identificador ESPN e uma entrada em um catálogo central. Ao acrescentar uma competição, a versão desse catálogo muda: o banco troca a carga anterior em uma única transação e recalcula os ratings, sem misturar fontes ou duplicar jogos.</li><li>Depois da carga inicial, o cron revisa apenas os últimos sete dias; no início de cada mês, reconcilia a temporada corrente. O identificador <span class="formula">espn:event-id</span> faz cada importação ser idempotente.</li><li>Resultados são ordenados pelo campo <strong>UTC</strong> <span class="formula">played_at</span>, recebido da fonte. O site converte esse horário para Brasília apenas para exibição.</li><li>Após cada horário distinto, os ratings são atualizados. Assim, um jogo às 18:00 altera o rating usado por uma partida às 22:00 no mesmo dia.</li><li>Partidas com o <strong>mesmo horário exato</strong> formam um grupo: não há uma ordem temporal verificável entre elas, então usam os mesmos ratings anteriores.</li><li>Um clube novo começa em <strong>r = 1500</strong>, <strong>RD = 350</strong> e volatilidade <strong>σ = 0,06</strong>. Vitória vale <strong>s = 1</strong>, empate <strong>0,5</strong> e derrota <strong>0</strong>.</li></ol><h2>Escala e expectativa</h2><p>O Glicko-2 converte os valores: <span class="formula">μ = (r − 1500) / 173,7178</span> e <span class="formula">φ = RD / 173,7178</span>. A incerteza do adversário é ponderada por <span class="formula">g(φⱼ) = 1 / √(1 + 3φⱼ²/π²)</span>.</p><p class="formula block">Eᵢⱼ = 1 / [1 + exp(−g(φⱼ) · (μᵢ + h/173,7178 − μⱼ))]</p><p><strong>h = +50</strong> para mandante e <strong>−50</strong> para visitante. O favoritismo dos fixtures é essa expectativa em porcentagem: uma medida de força relativa com mando, não odds nem previsão de placar.</p><h2>Margem de gols</h2><p>Vitória, empate e derrota continuam definidos por <span class="formula">s = 1, 0,5, 0</span>; o placar não é convertido em um resultado artificial. Para reconhecer uma vitória larga, a partida recebe um peso de evidência <span class="formula">w = min(1,8; 1 + 0,5·ln(d))</span>, em que <strong>d</strong> é a diferença de gols. Empates e vitórias por um gol usam <strong>w = 1</strong>; dois gols usam 1,35; três, 1,55; e cinco ou mais atingem o teto de 1,80.</p><p>O mesmo peso vale para os dois clubes: uma vitória por margem maior aumenta mais o rating do vencedor e reduz mais o do perdedor. O teto impede que placares incomuns exerçam influência desproporcional.</p><h2>Atualização cronológica</h2><p>Para o grupo de partidas daquele horário, calculamos <span class="formula">v = [Σwg²E(1−E)]⁻¹</span> e <span class="formula">Δ = vΣwg(s−E)</span>. Ganhar acima do esperado aumenta Δ; perder como favorito o reduz.</p><p>A volatilidade σ′ é obtida numericamente, com <strong>τ = 0,5</strong> e <span class="formula">a = ln(σ²)</span>:</p><p class="formula block">f(x) = eˣ(Δ²−φ²−v−eˣ) / [2(φ²+v+eˣ)²] − (x−a)/τ² = 0; &nbsp; σ′ = eˣ⁄²</p><p>Depois: <span class="formula">φ* = √(φ²+σ′²)</span>, <span class="formula">φ′ = [1/φ*² + 1/v]⁻½</span> e <span class="formula">μ′ = μ + φ′²Σwg(s−E)</span>. Por fim, os valores são reconvertidos para rating e RD.</p><h2>Inatividade e impacto</h2><p>Quando um clube fica semanas sem jogar, seu rating não muda, mas seu RD é ampliado antes de sua próxima partida — o modelo passa a ter menos certeza sobre a força anterior. O impacto mostrado em cada jogo é a diferença entre o cálculo do grupo completo e o mesmo cálculo sem aquele jogo; para horários únicos, é o impacto marginal daquela partida.</p><h2>Escalabilidade e correções</h2><p>O banco mantém o estado mais recente de cada clube e marca cada resultado já processado. Assim, o cron normal calcula apenas partidas novas, sem refazer toda a história. Se a fonte corrigir uma partida antiga, se os parâmetros mudarem ou se o catálogo receber uma competição nova, o sistema reconstrói o histórico uma única vez por segurança; esse é um caminho excepcional.</p></div>`;
}

fetch('./data/ranking.json').then(r => r.json()).then(data => {
  if (page === 'ranking') {
    document.body.innerHTML = shell('Ranking');
    const filters = [['general', 'Geral'], ['Série A', 'Série A'], ['Série B', 'Série B'], ['Série C', 'Série C']];
    el('#content').innerHTML = `<p>Força estimada. Dados sincronizados em ${time(data.generated_at)}. Inclui apenas clubes com jogos rastreados nos últimos 180 dias e RD abaixo de 120. Os filtros por divisão exibem os clubes que disputam aquela Série nesta temporada; o rating continua sendo global. Clique em um clube.</p><div class="ranking-filters" role="group" aria-label="Filtrar ranking">${filters.map(([value, label], index) => `<button type="button" data-division="${value}" class="${index === 0 ? 'active' : ''}">${label}</button>`).join('')}</div><p class="ranking-summary"></p><section class="panel ranking-panel"></section>`;
    const buttons = [...document.querySelectorAll('[data-division]')], summary = el('.ranking-summary'), panel = el('.ranking-panel');
    const renderRanking = division => {
      const teams = division === 'general' ? data.teams : data.teams.filter(team => (team.divisions || []).includes(division));
      summary.textContent = division === 'general' ? `${teams.length} clubes elegíveis no ranking geral.` : `${teams.length} clubes elegíveis da ${division} nesta temporada.`;
      panel.innerHTML = `<div class="row rank table-head"><span>Pos.</span><span>Clube</span><span>Rating</span></div>${teams.map((team, index) => `<a class="row rank" href="clube.html?time=${encodeURIComponent(team.name)}"><span>${index + 1}º</span><b>${club(team.name, team.crest)}</b><strong>${Math.round(team.rating)}</strong></a>`).join('') || '<p class="empty-list">Não há clubes elegíveis neste filtro.</p>'}`;
      buttons.forEach(button => button.classList.toggle('active', button.dataset.division === division));
    };
    buttons.forEach(button => button.addEventListener('click', () => renderRanking(button.dataset.division)));
    renderRanking('general');
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
  if (page === 'club') {
    const name = q.get('time'), team = [...data.teams, ...(data.excluded_teams || [])].find(t => t.name === name);
    if (!team) { document.body.innerHTML = shell('Clube não encontrado'); return; }
    const matches = data.matches.filter(m => m.home_team === name || m.away_team === name), fixtures = data.fixtures.filter(m => m.home_team === name || m.away_team === name), p = team.performance;
    document.body.innerHTML = shell(club(name, team.crest), 'Perfil do clube');
    el('#content').innerHTML = `<a class="back" href="ranking.html">← Voltar ao ranking</a><div class="stats"><div class="stat"><b>${team.position ? `${team.position}º` : '—'}</b><span>${team.position ? 'posição' : 'fora do ranking'}</span></div><div class="stat"><b>${team.rating.toFixed(1)}</b><span>rating</span></div><div class="stat"><b>${p.games}</b><span>jogos</span></div><div class="stat"><b>${p.wins}-${p.draws}-${p.losses}</b><span>V-E-D</span></div><div class="stat"><b>${p.goals_for}:${p.goals_against}</b><span>gols</span></div><div class="stat"><b>${p.points}</b><span>pontos</span></div></div><div class="chart-host"></div><h2>Próximos fixtures</h2><div class="fixtures-host"></div><h2>Últimos resultados</h2><div class="results-host"></div>`;
    mountRatingChart(el('.chart-host'), matches, name);
    mountPagedList(el('.fixtures-host'), fixtures, m => game(m, true), { pageSize: 10, emptyText: 'Nenhum fixture futuro disponível.' });
    mountPagedList(el('.results-host'), matches, m => game(m), { pageSize: 10, emptyText: 'Nenhum resultado rastreado disponível.' });
  }
  if (page === 'simulation') {
    simulations(data);
  }
  if (page === 'method') {
    method();
    el('#content').insertAdjacentHTML('beforeend', `<h2>Campo neutro</h2><p>O ajuste de mando é <strong>h = +50</strong> para o mandante e <strong>−50</strong> para o visitante. Em eventos explicitamente marcados como campo neutro, ambos usam <strong>h = 0</strong>. Como a ESPN não fornece essa marcação de modo confiável, as exceções são mantidas em uma lista auditável por ID de evento e recebem o rótulo “Campo neutro” no site.</p><h2>Elegibilidade do ranking</h2><p>O ranking principal só inclui clubes com resultado rastreado nos últimos <strong>180 dias</strong> e <strong>RD abaixo de 120</strong>. Esses limites evitam que uma força antiga, sem dados recentes, seja apresentada como força atual. Clubes fora desses critérios mantêm seu histórico, mas não recebem posição até voltarem a ter dados suficientes.</p>`);
  }
}).catch(() => { document.body.innerHTML = shell('Dados indisponíveis'); });
