function getVargaKeyFromQuery() {
  const params = new URLSearchParams(window.location.search);
  const key = params.get('varga');
  return CHART_DEFINITIONS.some((def) => def.key === key) ? key : 'D1';
}

function buildDetailRows(reading, key) {
  const ascendantSign = chartAscendant(reading, key);
  const ascendantIndex = ZODIAC_SIGNS.indexOf(ascendantSign);
  const signs = chartPlanetSigns(reading, key);
  const showDegree = key === 'D1';

  const rows = [{
    name: 'Ascendant',
    sign: ascendantSign,
    house: 1,
    degree: null
  }];

  reading.planets.forEach((planet) => {
    const sign = signs[planet.name];
    const signIndex = ZODIAC_SIGNS.indexOf(sign);
    rows.push({
      name: planet.name,
      sign,
      house: houseForSign(signIndex, ascendantIndex),
      degree: showDegree ? planet.degree : null
    });
  });

  return { rows, showDegree };
}

function showEmptyState(message) {
  const emptyState = document.getElementById('detail-empty-state');
  emptyState.querySelector('p').textContent = message;
  emptyState.hidden = false;
  document.getElementById('detail-content').hidden = true;
}

function renderDetail() {
  const raw = sessionStorage.getItem('jyotirgamayaReading');
  if (!raw) {
    showEmptyState('No reading data found for this session. Generate a reading first, then open a chart from the Divisional Charts tab.');
    return;
  }

  let reading;
  try {
    reading = JSON.parse(raw);
  } catch (error) {
    showEmptyState('Saved reading data looks corrupted. Please generate a new reading.');
    return;
  }

  // Anything below this point is defensive: it should always succeed given
  // well-formed reading data, but a rendering bug should show an error
  // message here instead of silently leaving a blank page (see the D1
  // ascendant-degree crash this caught during testing).
  try {
    const key = getVargaKeyFromQuery();
    const definition = CHART_DEFINITIONS.find((def) => def.key === key);
    const ascendantSign = chartAscendant(reading, key);

    document.getElementById('detail-title').textContent = `${definition.label} Chart`;
    document.title = `${definition.label} | Jyotirgamaya`;
    document.getElementById('detail-chart-heading').textContent = `${definition.label} for ${reading.name}`;
    document.getElementById('detail-chart-subheading').textContent = `Ascendant: ${ascendantSign}`;

    const chartContainer = document.getElementById('detail-chart-container');
    chartContainer.innerHTML = '';
    chartContainer.appendChild(buildNorthChartSvg(340, ascendantSign, chartPlanetSigns(reading, key), 14, 11));

    const { rows, showDegree } = buildDetailRows(reading, key);

    const headRow = document.getElementById('detail-table-head');
    headRow.innerHTML = `<th>Body</th><th>Sign</th><th>House</th>${showDegree ? '<th>Degree</th>' : ''}`;

    const tableBody = document.getElementById('detail-table-body');
    tableBody.innerHTML = rows.map((row) => `
      <tr>
        <td>${row.name}</td>
        <td>${row.sign}</td>
        <td>${row.house}</td>
        ${showDegree ? `<td>${row.degree != null ? row.degree.toFixed(2) + '&deg;' : '&mdash;'}</td>` : ''}
      </tr>
    `).join('');

    document.getElementById('detail-empty-state').hidden = true;
    document.getElementById('detail-content').hidden = false;
  } catch (error) {
    console.error('Failed to render chart detail:', error);
    showEmptyState('Something went wrong showing this chart. Please try again from the Divisional Charts tab.');
  }
}

renderDetail();
