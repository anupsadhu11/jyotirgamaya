// Shared North Indian chart renderer, used by both index.html (app.js) and
// varga-detail.html (varga-detail.js). Loaded as a plain script before
// either of those, so everything here is a global.

const ZODIAC_SIGNS = [
  'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
  'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
];

const PLANET_ABBR = {
  Sun: 'Su', Moon: 'Mo', Mars: 'Ma', Mercury: 'Me', Jupiter: 'Ju',
  Venus: 'Ve', Saturn: 'Sa', Rahu: 'Ra', Ketu: 'Ke'
};

function houseForSign(signIndex, ascendantIndex) {
  return ((signIndex - ascendantIndex + 12) % 12) + 1;
}

function planetSignMap(planets, signKey) {
  const map = {};
  planets.forEach((planet) => {
    map[planet.name] = signKey ? planet.vargas[signKey] : planet.sign;
  });
  return map;
}

// D1 (Rasi) isn't a "varga" in the API response (it's just each planet's
// base sign/reading.lagna, with no vargas key) - these two helpers paper
// over that so callers can treat all seven charts uniformly.
const CHART_DEFINITIONS = [
  { key: 'D1', label: 'D1 – Rasi' },
  { key: 'D2_Hora', label: 'D2 – Hora' },
  { key: 'D3_Drekkana', label: 'D3 – Drekkana' },
  { key: 'D7_Saptamsa', label: 'D7 – Saptamsa' },
  { key: 'D9_Navamsa', label: 'D9 – Navamsa' },
  { key: 'D10_Dasamsa', label: 'D10 – Dasamsa' },
  { key: 'D12_Dwadasamsa', label: 'D12 – Dwadasamsa' }
];

function chartAscendant(reading, key) {
  return key === 'D1' ? reading.lagna : reading.ascendantVargas[key];
}

function chartPlanetSigns(reading, key) {
  return planetSignMap(reading.planets, key === 'D1' ? null : key);
}

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
