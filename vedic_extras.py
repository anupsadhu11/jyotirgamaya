"""Divisional charts (varga) and Vimshottari dasha.

Deliberately standalone: does not import from backend.py (backend.py imports
this module, and importing back would create a circular import), so the
zodiac/nakshatra tables are duplicated here rather than shared. Keep them in
sync with backend.py's ZODIAC_SIGNS/NAKSHATRAS if either ever changes.

These are traditional Parashari calculation rules (Brihat Parashara Hora
Shastra), not derived from physics the way the ephemeris/ascendant code is -
so unlike that code they can't be checked against an independent numeric
oracle. They're implemented from standard, widely-published reference rules,
and were reviewed and confirmed against a trusted reference chart before
being wired into the API.
"""
from datetime import datetime, timedelta

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

DAYS_PER_YEAR = 365.25  # Vimshottari "year" approximation used here; some
                        # traditions use the precise 365.2563-day sidereal year.

# Order is fixed and cyclical; nakshatra lord = DASHA_LORDS[nakshatra_index % 9].
DASHA_LORDS = ['Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu', 'Jupiter', 'Saturn', 'Mercury']
DASHA_YEARS = {
    'Ketu': 7, 'Venus': 20, 'Sun': 6, 'Moon': 10, 'Mars': 7,
    'Rahu': 18, 'Jupiter': 16, 'Saturn': 19, 'Mercury': 17
}  # sums to 120


def _sign_index(sidereal_longitude: float) -> int:
    return int(sidereal_longitude // 30) % 12


def _degree_in_sign(sidereal_longitude: float) -> float:
    return sidereal_longitude % 30


def varga_d2_hora(sidereal_longitude: float) -> str:
    """Hora (D2): wealth. Parashari rule - odd signs give Sun's Hora (Leo)
    in the first half / Moon's Hora (Cancer) in the second half; even signs
    the reverse. Result is always Cancer or Leo."""
    s = _sign_index(sidereal_longitude)
    d = _degree_in_sign(sidereal_longitude)
    first_half = d < 15
    is_odd_sign = (s % 2 == 0)  # Aries=0 is the 1st (odd) sign
    if is_odd_sign:
        return 'Leo' if first_half else 'Cancer'
    return 'Cancer' if first_half else 'Leo'


def varga_d3_drekkana(sidereal_longitude: float) -> str:
    """Drekkana (D3): siblings. Each 10 deg third of a sign maps to the
    same / 5th / 9th sign from it (a trinal, fire-triangle pattern)."""
    s = _sign_index(sidereal_longitude)
    d = _degree_in_sign(sidereal_longitude)
    k = int(d // 10)  # 0, 1, 2
    offset = (0, 4, 8)[k]
    return ZODIAC_SIGNS[(s + offset) % 12]


def varga_d7_saptamsa(sidereal_longitude: float) -> str:
    """Saptamsa (D7): children. Odd signs count the 7 divisions starting
    from themselves; even signs start from the 7th sign from them."""
    s = _sign_index(sidereal_longitude)
    d = _degree_in_sign(sidereal_longitude)
    k = int(d // (30 / 7))  # 0..6
    is_odd_sign = (s % 2 == 0)
    start = s if is_odd_sign else (s + 6) % 12
    return ZODIAC_SIGNS[(start + k) % 12]


def varga_d9_navamsa(sidereal_longitude: float) -> str:
    """Navamsa (D9): spouse/dharma, the most commonly used divisional
    chart. Starting sign depends on the birth sign's modality (cardinal
    starts from itself, fixed starts 9th from itself, mutable 5th)."""
    s = _sign_index(sidereal_longitude)
    d = _degree_in_sign(sidereal_longitude)
    k = int(d // (30 / 9))  # 0..8
    modality = s % 3  # 0=movable/cardinal, 1=fixed, 2=dual/mutable
    start_offset = {0: 0, 1: 8, 2: 4}[modality]
    start = (s + start_offset) % 12
    return ZODIAC_SIGNS[(start + k) % 12]


def varga_d10_dasamsa(sidereal_longitude: float) -> str:
    """Dasamsa (D10): career. Odd signs count from themselves; even signs
    from the 9th sign from them."""
    s = _sign_index(sidereal_longitude)
    d = _degree_in_sign(sidereal_longitude)
    k = int(d // 3)  # 0..9
    is_odd_sign = (s % 2 == 0)
    start = s if is_odd_sign else (s + 8) % 12
    return ZODIAC_SIGNS[(start + k) % 12]


def varga_d12_dwadasamsa(sidereal_longitude: float) -> str:
    """Dwadasamsa (D12): parents. Always counts from the birth sign itself."""
    s = _sign_index(sidereal_longitude)
    d = _degree_in_sign(sidereal_longitude)
    k = int(d // 2.5)  # 0..11
    return ZODIAC_SIGNS[(s + k) % 12]


VARGA_FUNCTIONS = {
    'D2_Hora': varga_d2_hora,
    'D3_Drekkana': varga_d3_drekkana,
    'D7_Saptamsa': varga_d7_saptamsa,
    'D9_Navamsa': varga_d9_navamsa,
    'D10_Dasamsa': varga_d10_dasamsa,
    'D12_Dwadasamsa': varga_d12_dwadasamsa,
}


def compute_vargas(sidereal_longitude: float) -> dict:
    """All implemented divisional charts for a single planet's sidereal longitude."""
    return {name: fn(sidereal_longitude) for name, fn in VARGA_FUNCTIONS.items()}


def vimshottari_dasha(moon_sidereal_longitude: float, birth_datetime_utc: datetime,
                       antardasha: bool = True, cycles: int = 1):
    """Vimshottari mahadasha sequence (one full 120-year cycle by default),
    each with its antardasha (sub-period) breakdown.

    birth_datetime_utc: the birth moment in UTC (not local time).
    """
    span = 360.0 / 27.0
    nakshatra_index = int(moon_sidereal_longitude // span) % 27
    position_in_nakshatra = moon_sidereal_longitude % span
    fraction_elapsed = position_in_nakshatra / span

    starting_lord_index = nakshatra_index % 9
    lord_order = DASHA_LORDS[starting_lord_index:] + DASHA_LORDS[:starting_lord_index]

    mahadashas = []
    cursor = birth_datetime_utc
    for cycle in range(cycles):
        for i, lord in enumerate(lord_order):
            full_years = DASHA_YEARS[lord]
            if cycle == 0 and i == 0:
                # First dasha at birth is partial: only the balance remaining.
                years = full_years * (1 - fraction_elapsed)
            else:
                years = full_years
            days = years * DAYS_PER_YEAR
            start = cursor
            end = cursor + timedelta(days=days)

            entry = {
                'lord': lord,
                'start': start.isoformat(timespec='seconds') + 'Z',
                'end': end.isoformat(timespec='seconds') + 'Z',
                'years': round(years, 3)
            }
            if antardasha:
                entry['antardashas'] = _antardashas(lord, start, years)
            mahadashas.append(entry)
            cursor = end

    return {
        'birthNakshatra': NAKSHATRAS[nakshatra_index],
        'birthNakshatraLord': DASHA_LORDS[starting_lord_index],
        'balanceAtBirthYears': round(DASHA_YEARS[DASHA_LORDS[starting_lord_index]] * (1 - fraction_elapsed), 3),
        'mahadashas': mahadashas
    }


def _antardashas(mahadasha_lord: str, mahadasha_start: datetime, mahadasha_years: float):
    """Sub-periods within one mahadasha: same 9-lord cycle, starting from the
    mahadasha's own lord, each sized proportionally to that sub-lord's share
    of the full 120-year cycle."""
    start_index = DASHA_LORDS.index(mahadasha_lord)
    order = DASHA_LORDS[start_index:] + DASHA_LORDS[:start_index]

    antardashas = []
    cursor = mahadasha_start
    for sub_lord in order:
        sub_years = mahadasha_years * (DASHA_YEARS[sub_lord] / 120.0)
        sub_days = sub_years * DAYS_PER_YEAR
        start = cursor
        end = cursor + timedelta(days=sub_days)
        antardashas.append({
            'lord': sub_lord,
            'start': start.isoformat(timespec='seconds') + 'Z',
            'end': end.isoformat(timespec='seconds') + 'Z',
            'years': round(sub_years, 3)
        })
        cursor = end
    return antardashas
