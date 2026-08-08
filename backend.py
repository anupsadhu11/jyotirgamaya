import json
import math
import os
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.parse import quote

import astronomy as astro

HOST = os.environ.get('HOST', '127.0.0.1')
PORT = int(os.environ.get('PORT', '8000'))

ZODIAC_SIGNS = [
    'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
    'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
]

NAKSHATRAS = [
    'Ashwini', 'Bharani', 'Krittika', 'Rohini', 'Mrigashira', 'Ardra', 'Punarvasu',
    'Pushya', 'Ashlesha', 'Magha', 'Purva Phalguni', 'Uttara Phalguni', 'Hasta',
    'Chitra', 'Swati', 'Vishakha', 'Anuradha', 'Jyeshtha', 'Mula', 'Purva Ashadha',
    'Uttara Ashadha', 'Shravana', 'Dhanishta', 'Shatabhisha', 'Purva Bhadrapada',
    'Uttara Bhadrapada', 'Revati'
]

TITHI_NAMES = [
    'Pratipada', 'Dwitiya', 'Tritiya', 'Chaturthi', 'Panchami', 'Shashthi', 'Saptami',
    'Ashtami', 'Navami', 'Dashami', 'Ekadashi', 'Dwadashi', 'Trayodashi', 'Chaturdashi'
]

YOGA_NAMES = [
    'Vishkambha', 'Priti', 'Ayushman', 'Saubhagya', 'Shobhana', 'Atiganda', 'Sukarma',
    'Dhriti', 'Shula', 'Ganda', 'Vriddhi', 'Dhruva', 'Vyaghata', 'Harshana', 'Vajra',
    'Siddhi', 'Vyatipata', 'Variyana', 'Parigha', 'Shiva', 'Siddha', 'Sadhya', 'Shubha',
    'Shukla', 'Brahma', 'Indra', 'Vaidhriti'
]

MOVABLE_KARANAS = ['Bava', 'Balava', 'Kaulava', 'Taitila', 'Garaja', 'Vanija', 'Vishti']
FIXED_KARANAS_END = ['Shakuni', 'Chatushpada', 'Naga']

GRAHA_BODIES = {
    'Sun': astro.Body.Sun,
    'Moon': astro.Body.Moon,
    'Mars': astro.Body.Mars,
    'Mercury': astro.Body.Mercury,
    'Jupiter': astro.Body.Jupiter,
    'Venus': astro.Body.Venus,
    'Saturn': astro.Body.Saturn,
}

J2000_JD = 2451545.0


def julian_day(time: astro.Time) -> float:
    return time.ut + J2000_JD


def lahiri_ayanamsa(jd_ut: float) -> float:
    """Approximate Lahiri (Chitrapaksha) ayanamsa: ~23.85333 deg at J2000.0,
    precessing at the general precession rate (~50.2388475 arcsec/year).
    Matches published Lahiri tables to within a few arcminutes, which is
    sufficient for sign/nakshatra placement (it is not swisseph's exact
    polynomial, which includes small periodic terms)."""
    years_since_j2000 = (jd_ut - J2000_JD) / 365.25
    return 23.85333 + (50.2388475 / 3600.0) * years_since_j2000


def obliquity_of_ecliptic(jd_ut: float) -> float:
    t = (jd_ut - J2000_JD) / 36525.0
    return 23.439291111 - 0.0130042 * t - 1.64e-7 * t ** 2 + 5.04e-7 * t ** 3


def tropical_longitude(body, time: astro.Time) -> float:
    if body == astro.Body.Sun:
        return astro.SunPosition(time).elon
    if body == astro.Body.Moon:
        return astro.EclipticGeoMoon(time).lon
    return astro.Ecliptic(astro.GeoVector(body, time, True)).elon


def mean_lunar_node_longitude(jd_ut: float) -> float:
    """Mean ascending lunar node (Rahu), the convention most Vedic software
    uses by default. Ketu is exactly opposite (+180 deg)."""
    t = (jd_ut - J2000_JD) / 36525.0
    node = (125.0445479 - 1934.1362891 * t + 0.0020754 * t ** 2
            + t ** 3 / 467441.0 - t ** 4 / 60616000.0)
    return node % 360


def ascendant_tropical(time: astro.Time, jd_ut: float, latitude: float, longitude: float) -> float:
    gast_hours = astro.SiderealTime(time)
    gst_deg = gast_hours * 15.0
    ramc = math.radians((gst_deg + longitude) % 360)
    eps = math.radians(obliquity_of_ecliptic(jd_ut))
    phi = math.radians(latitude)

    y = -math.cos(ramc)
    x = math.sin(ramc) * math.cos(eps) + math.tan(phi) * math.sin(eps)
    return math.degrees(math.atan2(y, x)) % 360


def sign_from_longitude(sidereal_longitude: float) -> str:
    return ZODIAC_SIGNS[int(sidereal_longitude // 30) % 12]


def degree_in_sign(sidereal_longitude: float) -> float:
    return round(sidereal_longitude % 30, 2)


def nakshatra_from_longitude(moon_sidereal_longitude: float):
    span = 360.0 / 27.0
    index = int(moon_sidereal_longitude // span) % 27
    pada = int((moon_sidereal_longitude % span) // (span / 4)) + 1
    return NAKSHATRAS[index], pada


def get_tithi(sun_sidereal: float, moon_sidereal: float):
    diff = (moon_sidereal - sun_sidereal) % 360
    tithi_index = int(diff // 12)
    paksha = 'Shukla' if tithi_index < 15 else 'Krishna'
    day_in_paksha = tithi_index % 15
    if day_in_paksha == 14:
        name = 'Purnima' if paksha == 'Shukla' else 'Amavasya'
    else:
        name = TITHI_NAMES[day_in_paksha]
    return name, paksha


def get_yoga(sun_sidereal: float, moon_sidereal: float) -> str:
    total = (sun_sidereal + moon_sidereal) % 360
    index = int(total // (360.0 / 27.0)) % 27
    return YOGA_NAMES[index]


def get_karana(sun_sidereal: float, moon_sidereal: float) -> str:
    diff = (moon_sidereal - sun_sidereal) % 360
    karana_index = int(diff // 6)
    if karana_index == 0:
        return 'Kimstughna'
    if karana_index >= 57:
        return FIXED_KARANAS_END[karana_index - 57]
    return MOVABLE_KARANAS[(karana_index - 1) % 7]


def to_readable_time(time_24h: str):
    if not time_24h:
        return None
    hour, minute = (int(part) for part in time_24h.split(':')[:2])
    suffix = 'PM' if hour >= 12 else 'AM'
    normalized_hour = ((hour + 11) % 12) + 1
    return f'{normalized_hour}:{minute:02d} {suffix}'


def compute_rahukalam(sunrise_24h: str, sunset_24h: str, weekday_index: int) -> str:
    # weekday_index: Monday=0 ... Sunday=6 (datetime.weekday())
    segment_order = {0: 2, 1: 7, 2: 5, 3: 6, 4: 4, 5: 3, 6: 8}
    sunrise_dt = datetime.strptime(sunrise_24h, '%H:%M')
    sunset_dt = datetime.strptime(sunset_24h, '%H:%M')
    segment_length = (sunset_dt - sunrise_dt) / 8
    segment = segment_order[weekday_index]
    start = sunrise_dt + segment_length * (segment - 1)
    end = start + segment_length
    return f"{start.strftime('%I:%M %p').lstrip('0')} - {end.strftime('%I:%M %p').lstrip('0')}"


def compute_abhijit_muhurat(sunrise_24h: str, sunset_24h: str) -> str:
    sunrise_dt = datetime.strptime(sunrise_24h, '%H:%M')
    sunset_dt = datetime.strptime(sunset_24h, '%H:%M')
    day_length = sunset_dt - sunrise_dt
    midday = sunrise_dt + day_length / 2
    half_span = day_length / 30  # Abhijit spans 1/15th of daylight, centered on solar noon
    start = midday - half_span
    end = midday + half_span
    return f"{start.strftime('%I:%M %p').lstrip('0')} - {end.strftime('%I:%M %p').lstrip('0')}"


def fetch_json(url: str):
    req = Request(url, headers={'User-Agent': 'Jyotirgamaya/1.0'})
    with urlopen(req, timeout=10) as response:
        return json.load(response)


def geocode_place(place: str):
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={quote(place)}&count=1&format=json"
    data = fetch_json(url)
    result = data.get('results', [{}])[0]
    if not result:
        raise RuntimeError('No location match found')
    return {
        'name': f"{result.get('name')}, {result.get('country')}",
        'latitude': result.get('latitude'),
        'longitude': result.get('longitude')
    }


def fetch_daily_astro_data(date_string: str, latitude: float, longitude: float):
    """Sunrise/sunset and UTC offset for the birth date. Tries the historical
    archive first (birth dates are almost always in the past); falls back to
    the forecast endpoint, which only covers roughly the last 3 months to the
    next 2 weeks."""
    params = (f"latitude={latitude}&longitude={longitude}&daily=sunrise,sunset"
              f"&timezone=auto&start_date={date_string}&end_date={date_string}")
    urls = [
        f"https://archive-api.open-meteo.com/v1/archive?{params}",
        f"https://api.open-meteo.com/v1/forecast?{params}",
    ]

    for url in urls:
        try:
            data = fetch_json(url)
        except Exception:
            continue

        daily = data.get('daily', {})
        sunrise = daily.get('sunrise', [None])[0]
        sunset = daily.get('sunset', [None])[0]
        if sunrise and sunset:
            return {
                'sunrise': sunrise.split('T')[1][:5],
                'sunset': sunset.split('T')[1][:5],
                'utcOffsetSeconds': data.get('utc_offset_seconds', 0)
            }

    return {'sunrise': None, 'sunset': None, 'utcOffsetSeconds': 0}


def build_reading(payload: dict) -> dict:
    name = payload['name']
    dob = payload['dob']
    tob = payload['tob']
    latitude = payload['latitude']
    longitude = payload['longitude']
    utc_offset_seconds = payload['utcOffsetSeconds']
    sunrise_24h = payload['sunrise']
    sunset_24h = payload['sunset']

    local_dt = datetime.strptime(f'{dob} {tob}', '%Y-%m-%d %H:%M')
    utc_dt = local_dt - timedelta(seconds=utc_offset_seconds)
    time = astro.Time.Make(utc_dt.year, utc_dt.month, utc_dt.day,
                            utc_dt.hour, utc_dt.minute, utc_dt.second)
    jd_ut = julian_day(time)
    ayanamsa = lahiri_ayanamsa(jd_ut)

    planets = []
    sidereal_longitudes = {}
    for graha_name, body in GRAHA_BODIES.items():
        sidereal = (tropical_longitude(body, time) - ayanamsa) % 360
        sidereal_longitudes[graha_name] = sidereal
        planets.append({
            'name': graha_name,
            'longitude': round(sidereal, 2),
            'sign': sign_from_longitude(sidereal),
            'degree': degree_in_sign(sidereal)
        })

    rahu_sidereal = (mean_lunar_node_longitude(jd_ut) - ayanamsa) % 360
    ketu_sidereal = (rahu_sidereal + 180) % 360
    for graha_name, sidereal in (('Rahu', rahu_sidereal), ('Ketu', ketu_sidereal)):
        planets.append({
            'name': graha_name,
            'longitude': round(sidereal, 2),
            'sign': sign_from_longitude(sidereal),
            'degree': degree_in_sign(sidereal)
        })

    sun_sidereal = sidereal_longitudes['Sun']
    moon_sidereal = sidereal_longitudes['Moon']

    ascendant_sidereal = (ascendant_tropical(time, jd_ut, latitude, longitude) - ayanamsa) % 360
    sun_sign = sign_from_longitude(sun_sidereal)
    moon_sign = sign_from_longitude(moon_sidereal)
    lagna = sign_from_longitude(ascendant_sidereal)
    nakshatra, pada = nakshatra_from_longitude(moon_sidereal)

    tithi, paksha = get_tithi(sun_sidereal, moon_sidereal)
    yoga = get_yoga(sun_sidereal, moon_sidereal)
    karana = get_karana(sun_sidereal, moon_sidereal)
    weekday_index = datetime.strptime(dob, '%Y-%m-%d').weekday()

    if sunrise_24h and sunset_24h:
        rahukalam = compute_rahukalam(sunrise_24h, sunset_24h, weekday_index)
        muhurat = compute_abhijit_muhurat(sunrise_24h, sunset_24h)
    else:
        rahukalam = '—'
        muhurat = '—'

    return {
        'name': name,
        'sunSign': sun_sign,
        'moonSign': moon_sign,
        'lagna': lagna,
        'nakshatra': nakshatra,
        'nakshatraPada': pada,
        'summary': (
            f"{name}, your chart suggests a strong blend of {sun_sign} determination and "
            f"{moon_sign} intuition. The {lagna} lagna points to a life centered on growth, "
            f"learning, and purposeful action. Your {nakshatra} nakshatra (pada {pada}) "
            f"highlights empathy and leadership."
        ),
        'insights': [
            {'title': 'Career Path', 'text': 'Your chart favors strategic thinking, communication, and service-led leadership.'},
            {'title': 'Relationships', 'text': 'You are happiest when you nurture calm, honest, and spiritually grounded bonds.'},
            {'title': 'Wellbeing', 'text': 'A morning routine, breathwork, and mindful eating will deepen your balance.'}
        ],
        'guidance': [
            'Begin your day with a brief meditation and gratitude practice.',
            'Use the morning muhurat for planning, study, and important decisions.',
            'Avoid impulsive spending or heated conversations around midday.'
        ],
        'location': payload.get('locationName'),
        'source': 'Astronomy Engine ephemeris (Lahiri ayanamsa) + Open-Meteo geocoding/sunrise data',
        'planets': planets,
        'panchang': {
            'tithi': tithi,
            'paksha': paksha,
            'nakshatra': nakshatra,
            'yoga': yoga,
            'karana': karana,
            'sunrise': to_readable_time(sunrise_24h) or '—',
            'sunset': to_readable_time(sunset_24h) or '—',
            'rahukalam': rahukalam,
            'muhurat': muhurat
        }
    }


class AstroHandler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/health':
            self._send_json(200, {'status': 'ok', 'message': 'Jyotirgamaya backend is running.'})
            return
        self._send_json(404, {'error': 'Not found'})

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != '/api/astrology/reading':
            self._send_json(404, {'error': 'Not found'})
            return

        length = int(self.headers.get('Content-Length', '0'))
        body = self.rfile.read(length).decode('utf-8')
        payload = json.loads(body) if body else {}

        try:
            if not payload.get('name') or not payload.get('dob') or not payload.get('tob') or not payload.get('place'):
                self._send_json(400, {'error': 'Please provide name, date of birth, time of birth, and place.'})
                return

            location = geocode_place(payload['place'])
            daily_data = fetch_daily_astro_data(payload['dob'], location['latitude'], location['longitude'])
            reading = build_reading({
                **payload,
                'latitude': location['latitude'],
                'longitude': location['longitude'],
                'locationName': location['name'],
                **daily_data
            })
            self._send_json(200, reading)
        except Exception as exc:
            self._send_json(500, {'error': str(exc)})


if __name__ == '__main__':
    server = ThreadingHTTPServer((HOST, PORT), AstroHandler)
    print(f'Jyotirgamaya backend running on http://{HOST}:{PORT}')
    server.serve_forever()
