(() => {
  const $ = (id) => document.getElementById(id);
  const money = new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'USD' });

  // ---------- Token (solo en esta pestaña) ----------
  $('token').value = sessionStorage.getItem('gb_token') || '';
  $('token').addEventListener('input', () => sessionStorage.setItem('gb_token', $('token').value));

  // ---------- Gráficas ----------
  const grid = 'rgba(128,128,128,.25)';
  const opts = (legend = true) => ({
    animation: false, responsive: true, maintainAspectRatio: false,
    scales: { y: { beginAtZero: true, grid: { color: grid } }, x: { grid: { color: grid } } },
    plugins: { legend: { display: legend, labels: { boxWidth: 12 } } },
  });
  const line = (label, color, fill) => ({
    label, data: [], borderColor: color, backgroundColor: color + '26',
    fill, tension: 0.25, pointRadius: 0,
  });
  const chartRps = new Chart($('chart-rps'), {
    type: 'line',
    data: { labels: [], datasets: [line('Peticiones/s', '#2563eb', true), line('Errores/s', '#dc2626', false)] },
    options: opts(),
  });
  const chartLat = new Chart($('chart-lat'), {
    type: 'line',
    data: { labels: [], datasets: [line('Latencia p95 (ms)', '#d97706', true)] },
    options: opts(),
  });
  const bars = (label, color) => ({
    type: 'bar',
    data: { labels: [], datasets: [{ label, data: [], backgroundColor: color }] },
    options: opts(true),
  });
  const chartPods = new Chart($('chart-pods'), bars('Respuestas por pod (generador)', '#16a34a'));
  const chartBurst = new Chart($('chart-burst'), bars('Respuestas por pod (ráfaga)', '#7c3aed'));

  const short = (name) => (name.length > 18 ? '…' + name.slice(-14) : name);

  function setBars(chart, counts) {
    const entries = Object.entries(counts).sort((a, b) => a[0].localeCompare(b[0]));
    chart.data.labels = entries.map(([k]) => short(k));
    chart.data.datasets[0].data = entries.map(([, v]) => v);
    chart.update();
  }

  // ---------- Panel 1: ráfaga desde el navegador ----------
  $('btn-burst').addEventListener('click', async () => {
    const n = Math.min(500, Math.max(10, Number($('burst-n').value) || 100));
    const counts = {};
    const nodes = {};
    let errors = 0, next = 0;
    $('btn-burst').disabled = true;
    $('burst-caption').textContent = 'Enviando…';
    const worker = async () => {
      while (next < n) {
        next++;
        try {
          const r = await fetch('/api/whoami', { cache: 'no-store' });
          const d = await r.json();
          counts[d.pod] = (counts[d.pod] || 0) + 1;
          nodes[d.node] = (nodes[d.node] || 0) + 1;
        } catch { errors++; }
      }
    };
    await Promise.all(Array.from({ length: 10 }, worker));
    setBars(chartBurst, counts);
    const nNodes = Object.keys(nodes).length;
    $('burst-caption').textContent =
      `${n - errors} respuestas de ${Object.keys(counts).length} pod(s) en ${nNodes} nodo(s)` +
      (errors ? ` · ${errors} errores` : '');
    $('btn-burst').disabled = false;
  });

  // ---------- Panel 2: generador de tráfico ----------
  const syncControls = () => {
    $('rps-val').textContent = $('rps').value;
    $('ms-wrap').style.display = $('mode').value === 'work' ? '' : 'none';
  };
  $('rps').addEventListener('input', syncControls);
  $('mode').addEventListener('change', syncControls);
  syncControls();

  $('btn-start').addEventListener('click', async () => {
    const body = {
      mode: $('mode').value, rps: Number($('rps').value),
      duration: Number($('duration').value), ms: Number($('ms').value),
    };
    try {
      const r = await fetch('/loadgen/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Token': $('token').value },
        body: JSON.stringify(body),
      });
      const d = await r.json().catch(() => ({}));
      $('msg').textContent = r.ok ? 'Prueba iniciada' : (d.error || `Error ${r.status}`);
    } catch { $('msg').textContent = 'No se pudo contactar con el generador'; }
    poll();
  });

  $('btn-stop').addEventListener('click', async () => {
    try {
      const r = await fetch('/loadgen/stop', { method: 'POST', headers: { 'X-Token': $('token').value } });
      $('msg').textContent = r.ok ? 'Prueba detenida' : `Error ${r.status}`;
    } catch { $('msg').textContent = 'No se pudo contactar con el generador'; }
    poll();
  });

  const ms = (v) => (v == null ? '—' : `${v} ms`);

  function render(s) {
    $('rps').max = s.limits.max_rps;
    $('duration').max = s.limits.max_duration;
    const st = s.stats;
    // Mientras corre, el último segundo está incompleto: no se dibuja
    const tl = (s.running ? st.timeline.slice(0, -1) : st.timeline).slice(-60);
    chartRps.data.labels = tl.map((p) => `${p.t}s`);
    chartRps.data.datasets[0].data = tl.map((p) => p.rps);
    chartRps.data.datasets[1].data = tl.map((p) => p.errors);
    chartRps.update();
    chartLat.data.labels = tl.map((p) => `${p.t}s`);
    chartLat.data.datasets[0].data = tl.map((p) => p.p95_ms);
    chartLat.update();
    setBars(chartPods, st.pods);

    $('k-state').textContent = s.running ? `Corriendo (${s.elapsed}s)` : 'Detenido';
    $('k-total').textContent = st.total;
    $('k-errors').textContent = st.errors;
    $('k-dropped').textContent = st.dropped;
    $('k-p50').textContent = ms(st.p50_ms);
    $('k-p95').textContent = ms(st.p95_ms);
    $('btn-start').disabled = s.running;
    $('btn-stop').disabled = !s.running;
  }

  async function poll() {
    try {
      const r = await fetch('/loadgen/status', { cache: 'no-store' });
      if (!r.ok) throw new Error(r.status);
      render(await r.json());
      $('lg-offline').hidden = true;
    } catch { $('lg-offline').hidden = false; }
  }
  setInterval(poll, 1000);
  poll();

  // ---------- Panel 3: la aplicación bancaria ----------
  async function loadAccount() {
    try {
      const r = await fetch('/api/cuenta', { cache: 'no-store' });
      const d = await r.json();
      $('saldo').textContent = money.format(d.saldo);
      $('motor').textContent = d.motor_db;
      $('pod-resp').textContent = d.pod;
      $('ver').textContent = d.version;
      const ul = $('movs');
      ul.replaceChildren();
      for (const m of d.movimientos) {
        const li = document.createElement('li');
        const left = document.createElement('span');
        left.textContent = `${m.tipo} → ${m.destino}`;   // textContent: evita inyección HTML
        const right = document.createElement('span');
        right.textContent = `${money.format(m.monto)} · ${m.fecha}`;
        li.append(left, right);
        ul.append(li);
      }
    } catch { $('saldo').textContent = 'Sin conexión'; }
  }

  $('transfer-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const r = await fetch('/api/transfer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ destino: $('destino').value, monto: Number($('monto').value) }),
      });
      const d = await r.json();
      $('transfer-msg').textContent = r.ok ? `${d.mensaje} (pod ${d.pod})` : d.error;
    } catch { $('transfer-msg').textContent = 'Error de conexión'; }
    loadAccount();
  });
  loadAccount();
})();
