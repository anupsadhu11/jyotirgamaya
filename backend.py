import json
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.parse import quote

HOST = os.environ.get('HOST', '127.0.0.1')
PORT = int(os.environ.get('PORT', '8000'))


def get_zodiac(date_string: str) -> str:
    date = datetime.strptime(date_string, '%Y-%m-%d')
    month = date.month
    day = date.day

    if (month == 3 and day >= 21) or (month == 4 and day <= 19):
        return 'Aries'
    if (month == 4 and day >= 20) or (month == 5 and day <= 20):
        return 'Taurus'
    if (month == 5 and day >= 21) or (month == 6 and day <= 20):
        return 'Gemini'
    if (month == 6 and day >= 21) or (month == 7 and day <= 22):
        return 'Cancer'
    if (month == 7 and day >= 23) or (month == 8 and day <= 22):
        return 'Leo'
    if (month == 8 and day >= 23) or (month == 9 and day <= 22):
        return 'Virgo'
    if (month == 9 and day >= 23) or (month == 10 and day <= 22):
        return 'Libra'
    if (month == 10 and day >= 23) or (month == 11 and day <= 21):
        return 'Scorpio'
    if (month == 11 and day >= 22) or (month == 12 and day <= 21):
        return 'Sagittarius'
    if (month == 12 and day >= 22) or (month == 1 and day <= 19):
        return 'Capricorn'
    if (month == 1 and day >= 20) or (month == 2 and day <= 18):
        return 'Aquarius'
    return 'Pisces'


def get_moon_sign(date_string: str) -> str:
    zodiac = get_zodiac(date_string)
    moon_signs = ['Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces', 'Aries', 'Taurus', 'Gemini']
    return moon_signs[(moon_signs.index(zodiac) + 1) % len(moon_signs)]


def get_lagna(time_string: str) -> str:
    hour = int(time_string.split(':')[0])
    lagna_signs = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']
    return lagna_signs[hour % len(lagna_signs)]


def get_nakshatra(date_string: str) -> str:
    day = datetime.strptime(date_string, '%Y-%m-%d').day
    nakshatras = ['Ashwini', 'Bharani', 'Krittika', 'Rohini', 'Mrigashira', 'Ardra', 'Punarvasu', 'Pushya', 'Ashlesha', 'Magha', 'Purva Phalguni', 'Uttara Phalguni']
    return nakshatras[day % len(nakshatras)]


def get_panchang(date_string: str) -> dict:
    day = datetime.strptime(date_string, '%Y-%m-%d').day
    return {
        'tithi': ['Pratipada', 'Dwitiya', 'Tritiya', 'Chaturthi', 'Panchami', 'Shashthi', 'Saptami', 'Ashtami', 'Navami', 'Dashami'][day % 10],
        'nakshatra': ['Rohini', 'Mrigashira', 'Ardra', 'Punarvasu', 'Pushya', 'Ashlesha', 'Magha', 'Purva Phalguni', 'Uttara Phalguni', 'Hasta'][day % 10],
        'yoga': ['Shobhana', 'Sukarma', 'Dhriti', 'Shula', 'Ganda', 'Vriddhi', 'Dhruva', 'Vyaghata', 'Harshana', 'Vajra'][day % 10],
        'karana': ['Bava', 'Balava', 'Kaulava', 'Taitula', 'Garija', 'Vanija', 'Vishti'][day % 7],
        'sunrise': '05:47 AM',
        'sunset': '06:53 PM',
        'rahukalam': '01:30 PM - 03:00 PM',
        'muhurat': '07:30 AM - 09:00 AM'
    }


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


def get_sunrise_sunset(date_string: str, latitude: float, longitude: float):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&daily=sunrise,sunset&timezone=auto&start_date={date_string}&end_date={date_string}"
    try:
        data = fetch_json(url)
    except Exception:
        return {'sunrise': None, 'sunset': None}

    daily = data.get('daily', {})
    sunrise = daily.get('sunrise', [None])[0]
    sunset = daily.get('sunset', [None])[0]
    return {
        'sunrise': sunrise.split('T')[1][:5] if sunrise else None,
        'sunset': sunset.split('T')[1][:5] if sunset else None
    }


def build_reading(payload: dict) -> dict:
    sun_sign = get_zodiac(payload['dob'])
    moon_sign = get_moon_sign(payload['dob'])
    lagna = get_lagna(payload['tob'])
    nakshatra = get_nakshatra(payload['dob'])

    return {
        'name': payload['name'],
        'sunSign': sun_sign,
        'moonSign': moon_sign,
        'lagna': lagna,
        'nakshatra': nakshatra,
        'summary': f"{payload['name']}, your chart suggests a strong blend of {sun_sign} determination and {moon_sign} intuition. The {lagna} lagna points to a life centered on growth, learning, and purposeful action. Your {nakshatra} nakshatra highlights empathy and leadership.",
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
        'location': payload.get('location'),
        'source': 'Open-Meteo geocoding + sunrise/sunset data',
        'panchang': get_panchang(payload['dob'])
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
            daily_data = get_sunrise_sunset(payload['dob'], location['latitude'], location['longitude'])
            reading = build_reading({**payload, 'location': location['name']})
            reading['panchang']['sunrise'] = daily_data.get('sunrise') or reading['panchang']['sunrise']
            reading['panchang']['sunset'] = daily_data.get('sunset') or reading['panchang']['sunset']
            self._send_json(200, reading)
        except Exception as exc:
            self._send_json(500, {'error': str(exc)})


if __name__ == '__main__':
    server = ThreadingHTTPServer((HOST, PORT), AstroHandler)
    print(f'Jyotirgamaya backend running on http://{HOST}:{PORT}')
    server.serve_forever()
