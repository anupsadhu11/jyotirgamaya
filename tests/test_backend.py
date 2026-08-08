import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import backend


class TestZodiacHelpers(unittest.TestCase):
    def test_sign_from_longitude_boundaries(self):
        self.assertEqual(backend.sign_from_longitude(0), 'Aries')
        self.assertEqual(backend.sign_from_longitude(29.99), 'Aries')
        self.assertEqual(backend.sign_from_longitude(30), 'Taurus')
        self.assertEqual(backend.sign_from_longitude(85.46), 'Gemini')
        self.assertEqual(backend.sign_from_longitude(330), 'Pisces')
        self.assertEqual(backend.sign_from_longitude(360), 'Aries')  # wraps

    def test_degree_in_sign(self):
        self.assertAlmostEqual(backend.degree_in_sign(85.46), 25.46, places=2)
        self.assertAlmostEqual(backend.degree_in_sign(30), 0.0, places=2)

    def test_nakshatra_from_longitude(self):
        name, pada = backend.nakshatra_from_longitude(0)
        self.assertEqual(name, 'Ashwini')
        self.assertEqual(pada, 1)

        # Each nakshatra spans 13d20m (360/27); each pada spans a quarter of that.
        name, pada = backend.nakshatra_from_longitude(15.0)
        self.assertEqual(name, 'Bharani')
        self.assertEqual(pada, 1)

        # Known value from the Aarav/Varanasi regression case.
        name, pada = backend.nakshatra_from_longitude(259.65)
        self.assertEqual(name, 'Purva Ashadha')
        self.assertEqual(pada, 2)


class TestPanchangCalculations(unittest.TestCase):
    def test_get_tithi_shukla_and_krishna(self):
        name, paksha = backend.get_tithi(sun_sidereal=0, moon_sidereal=5)
        self.assertEqual((name, paksha), ('Pratipada', 'Shukla'))

        name, paksha = backend.get_tithi(sun_sidereal=0, moon_sidereal=175)
        self.assertEqual((name, paksha), ('Purnima', 'Shukla'))

        name, paksha = backend.get_tithi(sun_sidereal=0, moon_sidereal=185)
        self.assertEqual((name, paksha), ('Pratipada', 'Krishna'))

        name, paksha = backend.get_tithi(sun_sidereal=0, moon_sidereal=355)
        self.assertEqual((name, paksha), ('Amavasya', 'Krishna'))

    def test_get_yoga(self):
        self.assertEqual(backend.get_yoga(0, 0), 'Vishkambha')

    def test_get_karana_fixed_and_movable(self):
        # First half of Shukla Pratipada is always the fixed Kimstughna karana.
        self.assertEqual(backend.get_karana(sun_sidereal=0, moon_sidereal=3), 'Kimstughna')
        # Verified by hand against the Aarav/Varanasi case (Purnima, near end).
        self.assertEqual(backend.get_karana(sun_sidereal=85.46, moon_sidereal=259.65), 'Bava')
        # Last three half-tithis of the month (karana index 57/58/59, each a
        # 6-degree span of the Sun-Moon angular difference) are the fixed end karanas.
        self.assertEqual(backend.get_karana(sun_sidereal=0, moon_sidereal=345), 'Shakuni')
        self.assertEqual(backend.get_karana(sun_sidereal=0, moon_sidereal=351), 'Chatushpada')
        self.assertEqual(backend.get_karana(sun_sidereal=0, moon_sidereal=357), 'Naga')

    def test_to_readable_time(self):
        self.assertEqual(backend.to_readable_time('05:15'), '5:15 AM')
        self.assertEqual(backend.to_readable_time('18:51'), '6:51 PM')
        self.assertEqual(backend.to_readable_time('00:00'), '12:00 AM')
        self.assertEqual(backend.to_readable_time('12:00'), '12:00 PM')
        self.assertIsNone(backend.to_readable_time(None))

    def test_compute_rahukalam_matches_hand_verified_example(self):
        # Wednesday (weekday index 2), Varanasi 1995-07-12 sunrise/sunset.
        result = backend.compute_rahukalam('05:15', '18:51', weekday_index=2)
        self.assertEqual(result, '12:03 PM - 1:45 PM')

    def test_compute_abhijit_muhurat_matches_hand_verified_example(self):
        result = backend.compute_abhijit_muhurat('05:15', '18:51')
        self.assertEqual(result, '11:35 AM - 12:30 PM')


class TestAstronomicalHelpers(unittest.TestCase):
    def test_lahiri_ayanamsa_near_j2000(self):
        self.assertAlmostEqual(backend.lahiri_ayanamsa(backend.J2000_JD), 23.85333, places=3)

    def test_lahiri_ayanamsa_increases_over_time(self):
        earlier = backend.lahiri_ayanamsa(backend.J2000_JD - 365.25 * 10)
        later = backend.lahiri_ayanamsa(backend.J2000_JD + 365.25 * 10)
        self.assertLess(earlier, later)

    def test_obliquity_near_j2000(self):
        self.assertAlmostEqual(backend.obliquity_of_ecliptic(backend.J2000_JD), 23.439291, places=3)

    def test_mean_lunar_node_in_range(self):
        node = backend.mean_lunar_node_longitude(backend.J2000_JD)
        self.assertGreaterEqual(node, 0)
        self.assertLess(node, 360)

    def test_rahu_ketu_are_opposite(self):
        rahu = backend.mean_lunar_node_longitude(backend.J2000_JD) % 360
        ketu = (rahu + 180) % 360
        self.assertAlmostEqual((ketu - rahu) % 360, 180, places=6)

    def test_ascendant_tropical_in_range(self):
        time = backend.astro.Time.Make(1995, 7, 12, 1, 0, 0)
        jd_ut = backend.julian_day(time)
        asc = backend.ascendant_tropical(time, jd_ut, latitude=25.32, longitude=83.01)
        self.assertGreaterEqual(asc, 0)
        self.assertLess(asc, 360)


class TestValidation(unittest.TestCase):
    def test_missing_fields_rejected(self):
        with self.assertRaises(backend.ValidationError):
            backend.validate_payload({'name': 'Aarav'})

    def test_bad_dob_format_rejected(self):
        payload = {'name': 'Aarav', 'dob': '12-07-1995', 'tob': '06:30', 'place': 'Varanasi'}
        with self.assertRaises(backend.ValidationError):
            backend.validate_payload(payload)

    def test_bad_tob_format_rejected(self):
        payload = {'name': 'Aarav', 'dob': '1995-07-12', 'tob': '6:30am', 'place': 'Varanasi'}
        with self.assertRaises(backend.ValidationError):
            backend.validate_payload(payload)

    def test_valid_payload_passes(self):
        payload = {'name': 'Aarav', 'dob': '1995-07-12', 'tob': '06:30', 'place': 'Varanasi'}
        backend.validate_payload(payload)  # should not raise


VARANASI_GEOCODE_RESPONSE = {
    'results': [{'name': 'Varanasi', 'country': 'India', 'latitude': 25.3176, 'longitude': 82.9739}]
}
VARANASI_DAILY_RESPONSE = {
    'utc_offset_seconds': 19800,
    'daily': {'sunrise': ['1995-07-12T05:15'], 'sunset': ['1995-07-12T18:51']}
}


class TestUpstreamLookupsMocked(unittest.TestCase):
    def setUp(self):
        backend._geocode_cache.clear()
        backend._daily_astro_cache.clear()

    def test_geocode_place_success_and_cache(self):
        with patch.object(backend, 'fetch_json', return_value=VARANASI_GEOCODE_RESPONSE) as mock_fetch:
            first = backend.geocode_place('Varanasi, India')
            second = backend.geocode_place('Varanasi, India')

        self.assertEqual(first['latitude'], 25.3176)
        self.assertEqual(first, second)
        mock_fetch.assert_called_once()  # second call was a cache hit

    def test_geocode_place_not_found(self):
        with patch.object(backend, 'fetch_json', return_value={'results': []}):
            with self.assertRaises(backend.ValidationError):
                backend.geocode_place('Nowhereville Zzz')

    def test_geocode_place_network_failure(self):
        with patch.object(backend, 'fetch_json', side_effect=backend.URLError('boom')):
            with self.assertRaises(backend.UpstreamError):
                backend.geocode_place('Varanasi, India')

    def test_fetch_daily_astro_data_success(self):
        with patch.object(backend, 'fetch_json', return_value=VARANASI_DAILY_RESPONSE):
            result = backend.fetch_daily_astro_data('1995-07-12', 25.3176, 82.9739)

        self.assertEqual(result['sunrise'], '05:15')
        self.assertEqual(result['sunset'], '18:51')
        self.assertEqual(result['utcOffsetSeconds'], 19800)

    def test_fetch_daily_astro_data_all_sources_fail(self):
        with patch.object(backend, 'fetch_json', side_effect=Exception('unreachable')):
            result = backend.fetch_daily_astro_data('1995-07-12', 25.3176, 82.9739)

        self.assertIsNone(result['sunrise'])
        self.assertIsNone(result['sunset'])


class TestGenerateReadingRegression(unittest.TestCase):
    """Locks in the Aarav/Varanasi values verified by hand during development,
    so a future change to the ephemeris/ayanamsa/panchang logic that shifts
    these results has to be a deliberate, visible decision."""

    def setUp(self):
        backend._geocode_cache.clear()
        backend._daily_astro_cache.clear()

    def test_known_chart(self):
        payload = {'name': 'Aarav', 'dob': '1995-07-12', 'tob': '06:30', 'place': 'Varanasi, India'}
        with patch.object(backend, 'fetch_json') as mock_fetch:
            mock_fetch.side_effect = [VARANASI_GEOCODE_RESPONSE, VARANASI_DAILY_RESPONSE]
            reading = backend.generate_reading(payload)

        self.assertEqual(reading['sunSign'], 'Gemini')
        self.assertEqual(reading['moonSign'], 'Sagittarius')
        self.assertEqual(reading['lagna'], 'Capricorn')
        self.assertEqual(reading['nakshatra'], 'Purva Ashadha')
        self.assertEqual(reading['nakshatraPada'], 2)
        self.assertEqual(reading['panchang']['tithi'], 'Purnima')
        self.assertEqual(reading['panchang']['paksha'], 'Shukla')
        self.assertEqual(reading['panchang']['yoga'], 'Indra')
        self.assertEqual(reading['panchang']['karana'], 'Bava')
        self.assertEqual(reading['panchang']['sunrise'], '5:15 AM')
        self.assertEqual(reading['panchang']['sunset'], '6:51 PM')
        self.assertEqual(reading['panchang']['rahukalam'], '12:03 PM - 1:45 PM')
        self.assertEqual(reading['panchang']['muhurat'], '11:35 AM - 12:30 PM')

        rahu = next(p for p in reading['planets'] if p['name'] == 'Rahu')
        ketu = next(p for p in reading['planets'] if p['name'] == 'Ketu')
        self.assertAlmostEqual((ketu['longitude'] - rahu['longitude']) % 360, 180, places=1)


class TestPersistence(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        self.db_patch = patch.object(backend, 'DB_PATH', self.db_path)
        self.db_patch.start()
        backend.init_db()

    def tearDown(self):
        self.db_patch.stop()
        os.remove(self.db_path)

    def _sample_reading(self):
        return {
            'sunSign': 'Gemini', 'moonSign': 'Sagittarius', 'lagna': 'Capricorn',
            'nakshatra': 'Purva Ashadha', 'nakshatraPada': 2, 'planets': [], 'insights': [],
            'guidance': [], 'panchang': {}, 'summary': 'test', 'location': 'Varanasi, India',
            'source': 'test', 'name': 'Aarav'
        }

    def test_save_list_get_delete_roundtrip(self):
        payload = {'name': 'Aarav', 'dob': '1995-07-12', 'tob': '06:30', 'place': 'Varanasi, India'}
        saved = backend.save_reading_record(payload, self._sample_reading())
        self.assertIn('id', saved)
        self.assertIn('createdAt', saved)

        listed = backend.list_reading_records()
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]['id'], saved['id'])
        self.assertEqual(listed[0]['sunSign'], 'Gemini')

        fetched = backend.get_reading_record(saved['id'])
        self.assertEqual(fetched['name'], 'Aarav')
        self.assertEqual(fetched['nakshatraPada'], 2)

        backend.delete_reading_record(saved['id'])
        self.assertEqual(backend.list_reading_records(), [])

    def test_get_missing_reading_raises_not_found(self):
        with self.assertRaises(backend.NotFoundError):
            backend.get_reading_record(999)

    def test_delete_missing_reading_raises_not_found(self):
        with self.assertRaises(backend.NotFoundError):
            backend.delete_reading_record(999)


if __name__ == '__main__':
    unittest.main()
