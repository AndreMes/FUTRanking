const q = new URLSearchParams(location.search), page = document.body.dataset.page, el = s => document.querySelector(s);
const date = v => new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium' }).format(new Date(`${v}T12:00:00`));
const time = v => new Intl.DateTimeFormat('pt-BR', { timeZone: 'America/Sao_Paulo', dateStyle: 'short', timeStyle: 'short' }).format(new Date(v));
const matchTime = v => v.includes('T') ? time(v) : date(v);
const crest = (url, name) => url ? `<img class="crest" src="${url}" alt="Brasão do ${name}" loading="lazy">` : '';
const club = (name, url) => `<span class="club">${crest(url, name)}${name}</span>`;
const impact = value => `<span class="impact ${value >= 0 ? 'positive' : 'negative'}">${value >= 0 ? '+' : ''}${value?.toFixed(1) ?? '—'}</span>`;
const shell = (title, kicker = 'Série A · Brasil') => `<header class="top"><div class="wrap"><a class="brand" href="index.html"><span class="mark">↗</span>FUTRanking</a><nav><a href="ranking.html">Ranking</a><a href="resultados.html">Resultados</a><a href="proximos-jogos.html">Próximos jogos</a><a href="metodo.html">Método</a></nav><span class="pill">${kicker}</span></div></header><main class="wrap page"><div class="eyebrow">${kicker}</div><h1>${title}</h1><div id="content"></div></main><footer class="foot"><div class="wrap">FUTRanking · Glicko-2 para o futebol brasileiro</div></footer>`;

function game(m, fixture = false) {
  const score = fixture ? `<span class="score forecast">${m.home_favoritism}% · ${m.away_favoritism}%</span>` : `<span class="score">${m.home_goals}–${m.away_goals}</span>`;
  const homeMeta = fixture ? `Rating ${m.home_rating.toFixed(1)}` : `Rating ${m.home_rating_after?.toFixed(1) ?? '—'} · impacto ${impact(m.home_rating_effect)}`;
  const awayMeta = fixture ? `Rating ${m.away_rating.toFixed(1)}` : `Rating ${m.away_rating_after?.toFixed(1) ?? '—'} · impacto ${impact(m.away_rating_effect)}`;
  return `<article class="row"><span class="date">${fixture ? time(m.scheduled_at) : matchTime(m.played_at)}</span><span class="home">${club(m.home_team, m.home_crest)}<small class="rating">${homeMeta}</small></span>${score}<span class="away">${club(m.away_team, m.away_crest)}<small class="rating">${awayMeta}</small></span></article>`;
}

function method() {
  document.body.innerHTML = shell('Método', 'Como funciona');
  el('#content').innerHTML = `<div class="prose"><p>O FUTRanking usa o <strong>Glicko-2</strong> para estimar a força atual dos clubes. Ele compara o resultado observado com o esperado e considera a incerteza de ambos.</p><h2>Hipóteses do modelo</h2><ol><li>Clube novo: <strong>r = 1500</strong>, <strong>RD = 350</strong> e volatilidade <strong>σ = 0,06</strong>.</li><li>O período é uma <strong>semana</strong>: todos os jogos usam o rating do início dela e são calculados juntos.</li><li>O resultado é <strong>s = 1</strong> (vitória), <strong>0,5</strong> (empate) ou <strong>0</strong> (derrota).</li><li>O mandante recebe <strong>55 pontos</strong> apenas na expectativa pré-jogo; o bônus não aparece no rating do clube.</li><li>Sem jogo, o rating permanece, mas o RD cresce: há menos certeza após inatividade.</li></ol><h2>Escala e expectativa</h2><p>O modelo converte os valores: <span class="formula">μ = (r − 1500) / 173,7178</span> e <span class="formula">φ = RD / 173,7178</span>. A incerteza do adversário pesa por <span class="formula">g(φⱼ) = 1 / √(1 + 3φⱼ²/π²)</span>.</p><p class="formula block">Eᵢⱼ = 1 / [1 + exp(−g(φⱼ) · (μᵢ + h/173,7178 − μⱼ))]</p><p><strong>h = +55</strong> para o mandante e <strong>−55</strong> para o visitante. O favoritismo dos fixtures é essa expectativa em porcentagem; não é odds nem previsão de placar.</p><h2>Atualização semanal</h2><p>Para a semana, calculamos <span class="formula">v = [Σg²E(1−E)]⁻¹</span> e <span class="formula">Δ = vΣg(s−E)</span>. Ganhar acima do esperado aumenta Δ; perder como favorito o reduz.</p><p>A volatilidade σ′ é a raiz numérica, com <strong>τ = 0,5</strong> e <span class="formula">a = ln(σ²)</span>, de:</p><p class="formula block">f(x) = eˣ(Δ²−φ²−v−eˣ) / [2(φ²+v+eˣ)²] − (x−a)/τ² = 0; &nbsp; σ′ = eˣ⁄²</p><p>Em seguida: <span class="formula">φ* = √(φ²+σ′²)</span>, <span class="formula">φ′ = [1/φ*² + 1/v]⁻½</span> e <span class="formula">μ′ = μ + φ′²Σg(s−E)</span>. Por fim, reconvertemos para rating e RD.</p><h2>Impacto por jogo</h2><p>O impacto exibido é <span class="formula">rating da semana completa − rating da mesma semana sem aquela partida</span>. É a contribuição marginal do jogo e não depende de uma ordem artificial entre jogos da mesma semana.</p><h2>Dados e limites</h2><p>Resultados, agenda e brasões vêm do football-data.org. Apenas partidas finalizadas alteram o ranking; fixtures são projeções.</p></div>`;
}

fetch('./data/ranking.json').then(r => r.json()).then(data => {
  if (page === 'ranking') {
    document.body.innerHTML = shell('Ranking');
    el('#content').innerHTML = `<p>Força estimada. Dados sincronizados em ${time(data.generated_at)}. Clique em um clube.</p><section class="panel"><div class="row rank table-head"><span>Pos.</span><span>Clube</span><span>Rating</span></div>${data.teams.map(t => `<a class="row rank" href="clube.html?time=${encodeURIComponent(t.name)}"><span>${t.position}º</span><b>${club(t.name, t.crest)}</b><strong>${t.rating.toFixed(1)}</strong></a>`).join('')}</section>`;
  }
  if (page === 'resultados') {
    document.body.innerHTML = shell('Últimos resultados', 'Transparência');
    el('#content').innerHTML = `<p>Rating após o ciclo e impacto estimado daquele jogo. Horários em Brasília.</p><section class="panel">${data.matches.slice(0, 30).map(m => game(m)).join('')}</section>`;
  }
  if (page === 'fixtures') {
    document.body.innerHTML = shell('Próximos jogos', 'Agenda');
    el('#content').innerHTML = `<p>Horários em Brasília. Percentuais representam favoritismo Glicko-2 com mando de campo.</p><section class="panel">${data.fixtures.map(m => game(m, true)).join('') || '<p style="padding:20px">Nenhum jogo futuro disponível.</p>'}</section>`;
  }
  if (page === 'club') {
    const name = q.get('time'), team = data.teams.find(t => t.name === name);
    if (!team) { document.body.innerHTML = shell('Clube não encontrado'); return; }
    const matches = data.matches.filter(m => m.home_team === name || m.away_team === name).slice(0, 12), fixtures = data.fixtures.filter(m => m.home_team === name || m.away_team === name), p = team.performance;
    document.body.innerHTML = shell(club(name, team.crest), 'Perfil do clube');
    el('#content').innerHTML = `<a class="back" href="ranking.html">← Voltar ao ranking</a><div class="stats"><div class="stat"><b>${team.position}º</b><span>posição</span></div><div class="stat"><b>${team.rating.toFixed(1)}</b><span>rating</span></div><div class="stat"><b>${p.games}</b><span>jogos</span></div><div class="stat"><b>${p.wins}-${p.draws}-${p.losses}</b><span>V-E-D</span></div><div class="stat"><b>${p.goals_for}:${p.goals_against}</b><span>gols</span></div><div class="stat"><b>${p.points}</b><span>pontos</span></div></div><h2>Próximos fixtures</h2><section class="panel">${fixtures.map(m => game(m, true)).join('') || '<p style="padding:20px">Nenhum fixture futuro disponível.</p>'}</section><h2>Últimos resultados</h2><section class="panel">${matches.map(m => game(m)).join('')}</section>`;
  }
  if (page === 'method') method();
}).catch(() => { document.body.innerHTML = shell('Dados indisponíveis'); });

