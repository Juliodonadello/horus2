const scenarioSelect = document.getElementById('scenarioSelect');
const runList = document.getElementById('runList');
const startBtn = document.getElementById('startBtn');

async function loadScenarios() {
  const response = await fetch('/simulation/scenarios');
  const { scenarios } = await response.json();
  scenarioSelect.innerHTML = '';

  Object.entries(scenarios).forEach(([key, values]) => {
    const option = document.createElement('option');
    option.value = key;
    option.textContent = `${key} — ${values.description}`;
    scenarioSelect.appendChild(option);
  });
}

function runCard(run) {
  const card = document.createElement('div');
  card.className = 'run-card';
  card.innerHTML = `
    <div>
      <p><strong>${run.run_id}</strong> · ${run.site_id}</p>
      <p>${run.scenario} | ${run.status} | puntos: ${run.points_written}</p>
    </div>
  `;

  if (run.status === 'running' || run.status === 'stopping') {
    const stopBtn = document.createElement('button');
    stopBtn.textContent = 'Detener';
    stopBtn.onclick = async () => {
      await fetch(`/simulation/stop/${run.run_id}`, { method: 'POST' });
      await refreshRuns();
    };
    card.appendChild(stopBtn);
  }
  return card;
}

async function refreshRuns() {
  const response = await fetch('/simulation/status');
  const { runs } = await response.json();
  runList.innerHTML = '';
  if (!runs.length) {
    runList.textContent = 'Aún no hay simulaciones activas.';
    return;
  }
  runs.slice().reverse().forEach((run) => runList.appendChild(runCard(run)));
}

startBtn.addEventListener('click', async () => {
  const scenario = scenarioSelect.value;
  const siteId = document.getElementById('siteId').value.trim();
  const duration = Number(document.getElementById('duration').value);
  const interval = Number(document.getElementById('interval').value);

  const payload = {
    run_id: `run_${Date.now()}`,
    scenario,
    site_id: siteId,
    duration_seconds: duration,
    interval_seconds: interval,
  };

  await fetch('/simulation/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  await refreshRuns();
});

loadScenarios().then(refreshRuns);
setInterval(refreshRuns, 4000);
