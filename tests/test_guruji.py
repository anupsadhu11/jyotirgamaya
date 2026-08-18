import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from google.genai import errors

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import guruji


def make_text_response(text):
    response = MagicMock()
    response.text = text
    return response


SAMPLE_READING = {
    'name': 'Aarav',
    'sunSign': 'Gemini',
    'moonSign': 'Sagittarius',
    'lagna': 'Cancer',
    'nakshatra': 'Purva Ashadha',
    'nakshatraPada': 2,
    'planets': [
        {'name': 'Sun', 'sign': 'Gemini', 'degree': 25.46},
        {'name': 'Moon', 'sign': 'Sagittarius', 'degree': 19.65},
    ],
    'dasha': {'birthNakshatraLord': 'Venus', 'balanceAtBirthYears': 10.52},
}


class TestValidation(unittest.TestCase):
    def test_empty_message_rejected(self):
        with self.assertRaises(guruji.GurujiValidationError):
            guruji._validate('   ', None)

    def test_none_message_rejected(self):
        with self.assertRaises(guruji.GurujiValidationError):
            guruji._validate(None, None)

    def test_too_long_message_rejected(self):
        with self.assertRaises(guruji.GurujiValidationError):
            guruji._validate('x' * (guruji.MAX_MESSAGE_LENGTH + 1), None)

    def test_malformed_history_rejected(self):
        with self.assertRaises(guruji.GurujiValidationError):
            guruji._validate('What does my chart say?', 'not-a-list')

    def test_valid_message_passes(self):
        guruji._validate('What does my chart say?', [{'role': 'user', 'content': 'hi'}])


class TestReadingContext(unittest.TestCase):
    def test_none_reading_gives_none_context(self):
        self.assertIsNone(guruji._format_reading_context(None))
        self.assertIsNone(guruji._format_reading_context({}))

    def test_reading_context_includes_key_facts(self):
        context = guruji._format_reading_context(SAMPLE_READING)
        self.assertIn('Gemini', context)
        self.assertIn('Sagittarius', context)
        self.assertIn('Cancer', context)
        self.assertIn('Purva Ashadha', context)
        self.assertIn('Venus', context)

    def test_reading_context_survives_missing_dasha(self):
        reading = {k: v for k, v in SAMPLE_READING.items() if k != 'dasha'}
        context = guruji._format_reading_context(reading)
        self.assertIsNotNone(context)


class TestAskGuruji(unittest.TestCase):
    def setUp(self):
        self.env_patch = patch.dict(os.environ, {'GEMINI_API_KEY': 'test-key'})
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()

    def test_missing_api_key_raises_unavailable(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(guruji.GurujiUnavailableError):
                guruji.ask_guruji('What does my chart say?')

    def test_successful_reply(self):
        with patch.object(guruji.genai, 'Client') as MockClient:
            client = MockClient.return_value
            client.models.generate_content.return_value = make_text_response('Dear seeker, the stars incline...')

            reply = guruji.ask_guruji('What does my chart say?', reading=SAMPLE_READING)

            self.assertEqual(reply, 'Dear seeker, the stars incline...')
            call_kwargs = client.models.generate_content.call_args.kwargs
            self.assertEqual(call_kwargs['model'], guruji.MODEL)
            self.assertIn('Gemini', call_kwargs['config'].system_instruction)
            self.assertEqual(call_kwargs['contents'][-1],
                              {'role': 'user', 'parts': [{'text': 'What does my chart say?'}]})

    def test_history_is_included_and_capped(self):
        with patch.object(guruji.genai, 'Client') as MockClient:
            client = MockClient.return_value
            client.models.generate_content.return_value = make_text_response('reply')

            long_history = [{'role': 'user', 'content': f'q{i}'} for i in range(50)]
            guruji.ask_guruji('latest question', history=long_history)

            sent_contents = client.models.generate_content.call_args.kwargs['contents']
            # capped history + the new message
            self.assertEqual(len(sent_contents), guruji.MAX_HISTORY_TURNS + 1)
            self.assertEqual(sent_contents[-1]['parts'][0]['text'], 'latest question')

    def test_assistant_role_translated_to_model(self):
        with patch.object(guruji.genai, 'Client') as MockClient:
            client = MockClient.return_value
            client.models.generate_content.return_value = make_text_response('reply')

            history = [{'role': 'user', 'content': 'hi'}, {'role': 'assistant', 'content': 'namaste'}]
            guruji.ask_guruji('next question', history=history)

            sent_contents = client.models.generate_content.call_args.kwargs['contents']
            self.assertEqual([c['role'] for c in sent_contents], ['user', 'model', 'user'])

    def test_history_ignores_malformed_entries(self):
        with patch.object(guruji.genai, 'Client') as MockClient:
            client = MockClient.return_value
            client.models.generate_content.return_value = make_text_response('reply')

            history = [{'role': 'system', 'content': 'ignored'}, {'role': 'user'}, {'content': 'no role'}]
            guruji.ask_guruji('question', history=history)

            sent_contents = client.models.generate_content.call_args.kwargs['contents']
            self.assertEqual(sent_contents, [{'role': 'user', 'parts': [{'text': 'question'}]}])

    def test_api_error_raises_unavailable(self):
        with patch.object(guruji.genai, 'Client') as MockClient:
            client = MockClient.return_value
            client.models.generate_content.side_effect = errors.ClientError(
                code=429, response_json={'error': {'message': 'rate limited'}}
            )

            with self.assertRaises(guruji.GurujiUnavailableError):
                guruji.ask_guruji('What does my chart say?')

    def test_empty_reply_raises_unavailable(self):
        with patch.object(guruji.genai, 'Client') as MockClient:
            client = MockClient.return_value
            client.models.generate_content.return_value = make_text_response('   ')

            with self.assertRaises(guruji.GurujiUnavailableError):
                guruji.ask_guruji('What does my chart say?')

    def test_blocked_response_with_no_text_raises_unavailable(self):
        with patch.object(guruji.genai, 'Client') as MockClient:
            client = MockClient.return_value
            client.models.generate_content.return_value = make_text_response(None)

            with self.assertRaises(guruji.GurujiUnavailableError):
                guruji.ask_guruji('What does my chart say?')

    def test_no_reading_omits_context_from_system_prompt(self):
        with patch.object(guruji.genai, 'Client') as MockClient:
            client = MockClient.return_value
            client.models.generate_content.return_value = make_text_response('reply')

            guruji.ask_guruji('What is a nakshatra?')

            call_kwargs = client.models.generate_content.call_args.kwargs
            self.assertNotIn("SEEKER'S CURRENT CHART", call_kwargs['config'].system_instruction)


if __name__ == '__main__':
    unittest.main()
