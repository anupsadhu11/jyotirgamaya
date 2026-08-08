import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import vedic_extras as ve


class TestVargas(unittest.TestCase):
    def test_d2_hora_only_ever_cancer_or_leo(self):
        for lon in range(0, 360, 7):
            sign = ve.varga_d2_hora(lon)
            self.assertIn(sign, ('Cancer', 'Leo'))

    def test_d3_drekkana_thirds(self):
        # Aries (sign index 0): 0-10 -> Aries, 10-20 -> Leo (+4), 20-30 -> Sagittarius (+8)
        self.assertEqual(ve.varga_d3_drekkana(5), 'Aries')
        self.assertEqual(ve.varga_d3_drekkana(15), 'Leo')
        self.assertEqual(ve.varga_d3_drekkana(25), 'Sagittarius')

    def test_d12_dwadasamsa_always_starts_from_birth_sign(self):
        # First 2.5 deg of any sign maps to that sign itself.
        self.assertEqual(ve.varga_d12_dwadasamsa(1), 'Aries')
        self.assertEqual(ve.varga_d12_dwadasamsa(31), 'Taurus')

    def test_d9_navamsa_known_value(self):
        # Sun at 85.46 deg (25.46 deg into Gemini, a dual/mutable sign) ->
        # verified by hand and matches the reviewed Aarav/Varanasi sample.
        self.assertEqual(ve.varga_d9_navamsa(85.46), 'Taurus')

    def test_compute_vargas_returns_all_six(self):
        result = ve.compute_vargas(100.0)
        self.assertEqual(set(result.keys()), set(ve.VARGA_FUNCTIONS.keys()))
        for sign in result.values():
            self.assertIn(sign, ve.ZODIAC_SIGNS)


class TestVimshottariDasha(unittest.TestCase):
    def test_nakshatra_lord_table_matches_standard_assignment(self):
        # Spot-check against the well-known Vimshottari nakshatra-lord table.
        cases = {
            'Ashwini': 'Ketu', 'Bharani': 'Venus', 'Krittika': 'Sun',
            'Purva Ashadha': 'Venus', 'Revati': 'Mercury',
        }
        span = 360 / 27
        for name, expected_lord in cases.items():
            index = ve.NAKSHATRAS.index(name)
            lon = index * span + 1  # 1 deg into the nakshatra
            result = ve.vimshottari_dasha(lon, datetime(2000, 1, 1), antardasha=False, cycles=1)
            self.assertEqual(result['birthNakshatraLord'], expected_lord)

    def test_balance_is_full_dasha_at_exact_nakshatra_start(self):
        span = 360 / 27
        ashwini_start = 0.0
        result = ve.vimshottari_dasha(ashwini_start, datetime(2000, 1, 1), antardasha=False, cycles=1)
        self.assertAlmostEqual(result['balanceAtBirthYears'], ve.DASHA_YEARS['Ketu'], places=3)

    def test_balance_approaches_zero_at_nakshatra_end(self):
        span = 360 / 27
        almost_next = span - 0.001
        result = ve.vimshottari_dasha(almost_next, datetime(2000, 1, 1), antardasha=False, cycles=1)
        self.assertLess(result['balanceAtBirthYears'], 0.01)

    def test_mahadasha_sequence_follows_fixed_cyclical_order(self):
        result = ve.vimshottari_dasha(50.0, datetime(2000, 1, 1), antardasha=False, cycles=1)
        lords = [md['lord'] for md in result['mahadashas']]
        start = ve.DASHA_LORDS.index(result['birthNakshatraLord'])
        expected = ve.DASHA_LORDS[start:] + ve.DASHA_LORDS[:start]
        self.assertEqual(lords, expected)

    def test_mahadasha_total_matches_120_year_cycle_minus_elapsed(self):
        for lon in (0.0, 33.3, 111.1, 250.0, 359.0):
            with self.subTest(lon=lon):
                result = ve.vimshottari_dasha(lon, datetime(2000, 1, 1), antardasha=False, cycles=1)
                total = sum(md['years'] for md in result['mahadashas'])
                first_lord = result['mahadashas'][0]['lord']
                elapsed = ve.DASHA_YEARS[first_lord] - result['balanceAtBirthYears']
                self.assertAlmostEqual(total, 120 - elapsed, places=2)

    def test_antardashas_sum_to_their_mahadasha(self):
        result = ve.vimshottari_dasha(200.0, datetime(2000, 1, 1), antardasha=True, cycles=1)
        for md in result['mahadashas']:
            ad_total = sum(ad['years'] for ad in md['antardashas'])
            self.assertAlmostEqual(ad_total, md['years'], places=2)

    def test_antardasha_order_starts_from_mahadasha_lord(self):
        result = ve.vimshottari_dasha(200.0, datetime(2000, 1, 1), antardasha=True, cycles=1)
        first_md = result['mahadashas'][0]
        self.assertEqual(first_md['antardashas'][0]['lord'], first_md['lord'])

    def test_dates_are_contiguous(self):
        result = ve.vimshottari_dasha(80.0, datetime(1995, 7, 12, 1, 0, 0), antardasha=False, cycles=1)
        mahadashas = result['mahadashas']
        for prev, nxt in zip(mahadashas, mahadashas[1:]):
            self.assertEqual(prev['end'], nxt['start'])


if __name__ == '__main__':
    unittest.main()
