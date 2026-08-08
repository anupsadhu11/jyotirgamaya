const form = document.getElementById('astrology-form');
const generateBtn = document.getElementById('generate-btn');
const scrollBtn = document.getElementById('scroll-btn');
const saveBtn = document.getElementById('save-btn');
const tabs = document.querySelectorAll('.tab');
const panels = document.querySelectorAll('.panel');
const statusBanner = document.getElementById('status-banner');
const API_BASE = '';

let lastReadingData = null;

function setStatus(message, type = 'info') {
  statusBanner.textContent = message;
  statusBanner.className = `status-banner ${type}`;
}

function renderChart(reading) {
  const container = document.getElementById('kundali-chart-container');
  container.innerHTML = '';
  container.appendChild(buildNorthChartSvg(320, reading.lagna, planetSignMap(reading.planets), 13, 10));
}

function renderVargaCharts(reading) {
  const grid = document.getElementById('varga-charts-grid');
  grid.innerHTML = '';

  CHART_DEFINITIONS.forEach(({ key, label }) => {
    const card = document.createElement('a');
    card.className = 'varga-chart-card';
    card.href = `varga-detail.html?varga=${encodeURIComponent(key)}`;

    const heading = document.createElement('h4');
    heading.textContent = label;
    card.appendChild(heading);

    card.appendChild(buildNorthChartSvg(200, chartAscendant(reading, key), chartPlanetSigns(reading, key), 9, 7));
    grid.appendChild(card);
  });
}

function formatDasaDate(isoString) {
  return new Date(isoString).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

function renderDasha(reading) {
  const { dasha } = reading;
  document.getElementById('dasha-summary').textContent =
    `Birth nakshatra: ${dasha.birthNakshatra} (lord ${dasha.birthNakshatraLord}). ` +
    `Balance of first mahadasha at birth: ${dasha.balanceAtBirthYears} years.`;

  const dashaList = document.getElementById('dasha-list');
  dashaList.innerHTML = dasha.mahadashas.map((md) => `
    <details class="dasha-mahadasha">
      <summary>
        <span class="dasha-lord">${md.lord}</span>
        <span class="dasha-range">${formatDasaDate(md.start)} &ndash; ${formatDasaDate(md.end)}</span>
        <span class="dasha-years">${md.years.toFixed(1)} yrs</span>
      </summary>
      <ul class="dasha-antardasha-list">
        ${md.antardashas.map((ad) => `
          <li>
            <span class="dasha-lord">${ad.lord}</span>
            <span class="dasha-range">${formatDasaDate(ad.start)} &ndash; ${formatDasaDate(ad.end)}</span>
            <span class="dasha-years">${ad.years.toFixed(2)} yrs</span>
          </li>
        `).join('')}
      </ul>
    </details>
  `).join('');
}

function renderReading(reading) {
  document.getElementById('sun-sign').textContent = reading.sunSign;
  document.getElementById('moon-sign').textContent = reading.moonSign;
  document.getElementById('lagna').textContent = reading.lagna;
  document.getElementById('nakshatra').textContent = reading.nakshatra;
  document.getElementById('kundali-summary').textContent = reading.summary;

  const planetList = document.getElementById('planet-list');
  planetList.innerHTML = reading.insights.map((item) => `
    <div class="insight-item">
      <strong>${item.title}</strong>
      <span>${item.text}</span>
    </div>
  `).join('');

  document.getElementById('tithi').textContent = reading.panchang.tithi;
  document.getElementById('panchang-nakshatra').textContent = reading.panchang.nakshatra;
  document.getElementById('yoga').textContent = reading.panchang.yoga;
  document.getElementById('karana').textContent = reading.panchang.karana;
  document.getElementById('sunrise').textContent = reading.panchang.sunrise;
  document.getElementById('sunset').textContent = reading.panchang.sunset;
  document.getElementById('rahukalam').textContent = reading.panchang.rahukalam;
  document.getElementById('muhurat').textContent = reading.panchang.muhurat;

  document.getElementById('guidance-list').innerHTML = reading.guidance.map((item) => `<li>${item}</li>`).join('');
  renderChart(reading);
  renderVargaCharts(reading);
  renderDasha(reading);
}

async function loadReading(data) {
  generateBtn.disabled = true;
  form.querySelector('button[type="submit"]').disabled = true;
  setStatus('Generating your reading...', 'loading');

  try {
    const response = await fetch(`${API_BASE}/api/astrology/reading`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });

    if (!response.ok) {
      throw new Error('Unable to generate a reading right now.');
    }

    const reading = await response.json();
    renderReading(reading);
    lastReadingData = data;
    // Detail chart pages (varga-detail.html) read this to avoid a second
    // API round trip; sessionStorage keeps it scoped to this tab/session.
    sessionStorage.setItem('jyotirgamayaReading', JSON.stringify(reading));
    setStatus(`Reading ready for ${reading.name || 'you'}.`, 'success');
  } catch (error) {
    document.getElementById('kundali-summary').textContent = error.message;
    setStatus(error.message, 'error');
  } finally {
    generateBtn.disabled = false;
    form.querySelector('button[type="submit"]').disabled = false;
  }
}

async function saveReading() {
  if (!lastReadingData) {
    setStatus('Generate a reading before saving it.', 'error');
    return;
  }

  saveBtn.disabled = true;
  setStatus('Saving your reading...', 'loading');

  try {
    const response = await fetch(`${API_BASE}/api/readings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(lastReadingData)
    });

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.error || 'Unable to save this reading right now.');
    }

    setStatus('Reading saved. View it on the Dashboard.', 'success');
  } catch (error) {
    setStatus(error.message, 'error');
  } finally {
    saveBtn.disabled = false;
  }
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  const data = {
    name: document.getElementById('name').value || 'Guest',
    dob: document.getElementById('dob').value,
    tob: document.getElementById('tob').value,
    place: document.getElementById('place').value
  };
  loadReading(data);
});

generateBtn.addEventListener('click', () => form.requestSubmit());
scrollBtn.addEventListener('click', () => {
  document.getElementById('panchang-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
});
saveBtn.addEventListener('click', saveReading);

tabs.forEach((tab) => {
  tab.addEventListener('click', () => {
    tabs.forEach((button) => button.classList.remove('active'));
    tab.classList.add('active');

    const target = tab.dataset.target;
    panels.forEach((panel) => panel.classList.toggle('active', panel.id === `${target}-panel`));
  });
});

loadReading({ name: 'Aarav', dob: '1995-07-12', tob: '06:30', place: 'Varanasi, India' });
