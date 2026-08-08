const form = document.getElementById('astrology-form');
const generateBtn = document.getElementById('generate-btn');
const scrollBtn = document.getElementById('scroll-btn');
const tabs = document.querySelectorAll('.tab');
const panels = document.querySelectorAll('.panel');
const planetNodes = document.getElementById('planet-nodes');
const statusBanner = document.getElementById('status-banner');
const API_BASE = '';

function setStatus(message, type = 'info') {
  statusBanner.textContent = message;
  statusBanner.className = `status-banner ${type}`;
}

function renderChart(planets = []) {
  const cx = 160;
  const cy = 160;
  const radius = 103;

  planetNodes.innerHTML = '';
  planets.forEach((planet) => {
    // 0 deg (sidereal Aries) at the top, increasing clockwise with longitude.
    const angle = ((planet.longitude - 90) * Math.PI) / 180;
    const x = cx + radius * Math.cos(angle);
    const y = cy + radius * Math.sin(angle);

    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.setAttribute('cx', x);
    circle.setAttribute('cy', y);
    circle.setAttribute('r', 8);
    circle.setAttribute('class', 'planet-dot');
    planetNodes.appendChild(circle);

    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    const labelOffset = Math.cos(angle) >= 0 ? 12 : -12;
    text.setAttribute('x', x + labelOffset);
    text.setAttribute('y', y);
    text.setAttribute('text-anchor', labelOffset > 0 ? 'start' : 'end');
    text.setAttribute('fill', '#f7c679');
    text.setAttribute('font-size', '11');
    text.textContent = planet.name;
    planetNodes.appendChild(text);
  });
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
  renderChart(reading.planets);
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
    setStatus(`Reading ready for ${reading.name || 'you'}.`, 'success');
  } catch (error) {
    document.getElementById('kundali-summary').textContent = error.message;
    setStatus(error.message, 'error');
  } finally {
    generateBtn.disabled = false;
    form.querySelector('button[type="submit"]').disabled = false;
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

tabs.forEach((tab) => {
  tab.addEventListener('click', () => {
    tabs.forEach((button) => button.classList.remove('active'));
    tab.classList.add('active');

    const target = tab.dataset.target;
    panels.forEach((panel) => panel.classList.toggle('active', panel.id === `${target}-panel`));
  });
});

loadReading({ name: 'Aarav', dob: '1995-07-12', tob: '06:30', place: 'Varanasi, India' });
