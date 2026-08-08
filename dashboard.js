const API_BASE = '';
const listEl = document.getElementById('recent-readings-list');
const insightsEl = document.getElementById('saved-insights');

async function deleteReading(id) {
  try {
    const response = await fetch(`${API_BASE}/api/readings/${id}`, { method: 'DELETE' });
    if (!response.ok) throw new Error('Unable to delete this reading.');
    loadReadings();
  } catch (error) {
    listEl.innerHTML = `<li>${error.message}</li>`;
  }
}

function renderReadings(readings) {
  if (!readings.length) {
    listEl.innerHTML = '<li>No saved readings yet. Generate one on the home page and click "Save This Reading".</li>';
    insightsEl.textContent = 'Save a reading to see your latest chart highlights here.';
    return;
  }

  listEl.innerHTML = readings.map((reading) => `
    <li class="reading-row">
      <span class="reading-info">
        <strong>${reading.name}</strong>
        <span class="reading-meta">${reading.dob} &middot; ${reading.sunSign} Sun / ${reading.moonSign} Moon / ${reading.lagna} Lagna</span>
      </span>
      <button class="link-btn" data-id="${reading.id}" aria-label="Delete reading for ${reading.name}">Delete</button>
    </li>
  `).join('');

  listEl.querySelectorAll('.link-btn').forEach((button) => {
    button.addEventListener('click', () => deleteReading(button.dataset.id));
  });

  const [latest] = readings;
  insightsEl.textContent = `${latest.name}'s latest chart: ${latest.sunSign} Sun, ${latest.moonSign} Moon, ${latest.lagna} Lagna.`;
}

async function loadReadings() {
  try {
    const response = await fetch(`${API_BASE}/api/readings`);
    if (!response.ok) throw new Error('Unable to load saved readings.');
    const { readings } = await response.json();
    renderReadings(readings);
  } catch (error) {
    listEl.innerHTML = `<li>${error.message}</li>`;
  }
}

loadReadings();
