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

const ZODIAC_SIGNS = [
  'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
  'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
];

const PLANET_ABBR = {
  Sun: 'Su', Moon: 'Mo', Mars: 'Ma', Mercury: 'Me', Jupiter: 'Ju',
  Venus: 'Ve', Saturn: 'Sa', Rahu: 'Ra', Ketu: 'Ke'
};

// North Indian chart layout: a fixed 12-house grid (4 "kite" houses at the
// cardinal midpoints, 8 triangular houses at the corners) built from 10 line
// segments - the outer square, both diagonals, and the diamond connecting
// the edge midpoints. House 1 is always the top kite; houses run clockwise
// from there. Which zodiac sign occupies which house depends on the
// ascendant, but the house *shapes and positions* never move.
function northChartGeometry(size) {
  const m = size * 0.06;
  const TL = { x: m, y: m };
  const TR = { x: size - m, y: m };
  const BR = { x: size - m, y: size - m };
  const BL = { x: m, y: size - m };
  const TM = { x: (TL.x + TR.x) / 2, y: TL.y };
  const RM = { x: TR.x, y: (TR.y + BR.y) / 2 };
  const BM = { x: (BL.x + BR.x) / 2, y: BL.y };
  const LM = { x: TL.x, y: (TL.y + BL.y) / 2 };
  const mid = (a, b) => ({ x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 });
  const M1 = mid(TM, RM);
  const M2 = mid(RM, BM);
  const M3 = mid(BM, LM);
  const M4 = mid(LM, TM);
  const centroid = (pts) => ({
    x: pts.reduce((sum, p) => sum + p.x, 0) / pts.length,
    y: pts.reduce((sum, p) => sum + p.y, 0) / pts.length
  });
  // Kite houses (1/4/7/10) span from their tip out to the center point, so a
  // plain 4-point average gets dragged toward the center and ends up looking
  // lower/less prominent than the small corner triangles beside it. Weight
  // toward the tip instead (and drop the center point) so the top/right/
  // bottom/left houses read as a clean row alongside their corner neighbors.
  const kiteLabelPoint = (tip, side1, side2) => ({
    x: tip.x * 0.5 + side1.x * 0.25 + side2.x * 0.25,
    y: tip.y * 0.5 + side1.y * 0.25 + side2.y * 0.25
  });

  return {
    gridLines: [
      [TL, TR], [TR, BR], [BR, BL], [BL, TL],
      [TL, BR], [TR, BL],
      [TM, RM], [RM, BM], [BM, LM], [LM, TM]
    ],
    houseLabelPoints: [
      kiteLabelPoint(TM, M1, M4), centroid([TM, TR, M1]), centroid([TR, RM, M1]),
      kiteLabelPoint(RM, M2, M1), centroid([RM, BR, M2]), centroid([BR, BM, M2]),
      kiteLabelPoint(BM, M3, M2), centroid([BM, BL, M3]), centroid([BL, LM, M3]),
      kiteLabelPoint(LM, M4, M3), centroid([LM, TL, M4]), centroid([TL, TM, M4])
    ]
  };
}

function buildNorthChartSvg(size, ascendantSign, planetSignsByName, fontSize, signFontSize) {
  const ns = 'http://www.w3.org/2000/svg';
  const geo = northChartGeometry(size);
  const ascendantIndex = ZODIAC_SIGNS.indexOf(ascendantSign);

  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('viewBox', `0 0 ${size} ${size}`);
  svg.setAttribute('class', 'north-chart');
  svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', `North Indian chart, ascendant ${ascendantSign}`);

  geo.gridLines.forEach(([p1, p2]) => {
    const line = document.createElementNS(ns, 'line');
    line.setAttribute('x1', p1.x);
    line.setAttribute('y1', p1.y);
    line.setAttribute('x2', p2.x);
    line.setAttribute('y2', p2.y);
    line.setAttribute('class', 'north-chart-grid');
    svg.appendChild(line);
  });

  for (let house = 1; house <= 12; house++) {
    const signIndex = (ascendantIndex + house - 1) % 12;
    const planetsHere = Object.entries(planetSignsByName)
      .filter(([, sign]) => ZODIAC_SIGNS.indexOf(sign) === signIndex)
      .map(([name]) => PLANET_ABBR[name] || name);
    if (house === 1) planetsHere.unshift('Asc');

    const point = geo.houseLabelPoints[house - 1];

    const signText = document.createElementNS(ns, 'text');
    signText.setAttribute('x', point.x);
    signText.setAttribute('y', point.y - signFontSize * 0.4);
    signText.setAttribute('text-anchor', 'middle');
    signText.setAttribute('class', 'north-chart-sign-number');
    signText.setAttribute('font-size', signFontSize);
    signText.textContent = signIndex + 1;
    svg.appendChild(signText);

    const planetsText = document.createElementNS(ns, 'text');
    planetsText.setAttribute('x', point.x);
    planetsText.setAttribute('y', point.y + fontSize * 0.9);
    planetsText.setAttribute('text-anchor', 'middle');
    planetsText.setAttribute('class', 'north-chart-planets');
    planetsText.setAttribute('font-size', fontSize);
    planetsText.textContent = planetsHere.join(' ');
    svg.appendChild(planetsText);
  }

  return svg;
}

function planetSignMap(planets, signKey) {
  const map = {};
  planets.forEach((planet) => {
    map[planet.name] = signKey ? planet.vargas[signKey] : planet.sign;
  });
  return map;
}

function renderChart(reading) {
  const container = document.getElementById('kundali-chart-container');
  container.innerHTML = '';
  container.appendChild(buildNorthChartSvg(320, reading.lagna, planetSignMap(reading.planets), 13, 10));
}

const VARGA_LABELS = {
  D2_Hora: 'D2 – Hora',
  D3_Drekkana: 'D3 – Drekkana',
  D7_Saptamsa: 'D7 – Saptamsa',
  D9_Navamsa: 'D9 – Navamsa',
  D10_Dasamsa: 'D10 – Dasamsa',
  D12_Dwadasamsa: 'D12 – Dwadasamsa'
};

function renderVargaCharts(reading) {
  const grid = document.getElementById('varga-charts-grid');
  grid.innerHTML = '';

  Object.entries(VARGA_LABELS).forEach(([key, label]) => {
    const wrapper = document.createElement('div');
    wrapper.className = 'varga-chart-card';

    const heading = document.createElement('h4');
    heading.textContent = label;
    wrapper.appendChild(heading);

    wrapper.appendChild(buildNorthChartSvg(200, reading.ascendantVargas[key], planetSignMap(reading.planets, key), 9, 7));
    grid.appendChild(wrapper);
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
