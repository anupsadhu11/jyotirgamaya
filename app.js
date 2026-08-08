const form = document.getElementById('astrology-form');
const generateBtn = document.getElementById('generate-btn');
const scrollBtn = document.getElementById('scroll-btn');
const tabs = document.querySelectorAll('.tab');
const panels = document.querySelectorAll('.panel');
const planetNodes = document.getElementById('planet-nodes');

function renderChart() {
  const nodes = [
    { label: 'Sun', x: 160, y: 65 },
    { label: 'Moon', x: 240, y: 120 },
    { label: 'Mars', x: 220, y: 220 },
    { label: 'Mercury', x: 120, y: 240 },
    { label: 'Jupiter', x: 70, y: 140 },
    { label: 'Venus', x: 95, y: 85 },
    { label: 'Saturn', x: 250, y: 225 }
  ];

  planetNodes.innerHTML = '';
  nodes.forEach((node, index) => {
    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.setAttribute('cx', node.x);
    circle.setAttribute('cy', node.y);
    circle.setAttribute('r', 10 + index % 2);
    circle.setAttribute('class', 'planet-dot');
    planetNodes.appendChild(circle);

    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    text.setAttribute('x', node.x + 14);
    text.setAttribute('y', node.y - 10);
    text.setAttribute('fill', '#f7c679');
    text.setAttribute('font-size', '11');
    text.textContent = node.label;
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
  renderChart();
}

async function loadReading(data) {
  try {
    const response = await fetch('/api/astrology/reading', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });

    if (!response.ok) {
      throw new Error('Unable to generate a reading right now.');
    }

    const reading = await response.json();
    renderReading(reading);
  } catch (error) {
    document.getElementById('kundali-summary').textContent = error.message;
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
