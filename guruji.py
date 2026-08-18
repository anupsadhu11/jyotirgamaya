"""Guruji: an in-character Vedic astrology chat persona, powered by the
Google Gemini API.

Standalone and additive, like vedic_extras.py - backend.py imports this
module and wires it to /api/guruji/chat, but nothing here reaches back into
backend.py. Raises its own exception types; backend.py translates them into
its own ValidationError/UpstreamError at the route boundary.
"""
import os

from google import genai
from google.genai import errors, types

MODEL = os.environ.get('GURUJI_MODEL', 'gemini-3.6-flash')
# This model spends tokens on internal "thinking" before the visible reply,
# and max_output_tokens caps thinking + reply combined - a plain chat answer
# alone used 350-750 thinking tokens in testing, so this needs real headroom
# beyond what a "few short paragraphs" reply would otherwise need on its own.
MAX_REPLY_TOKENS = 2048
MAX_MESSAGE_LENGTH = 2000
MAX_HISTORY_TURNS = 20  # most recent user+assistant turns resent for context

SYSTEM_PROMPT = """\
You are Guruji, a warm and wise teacher of Jyotish (Vedic astrology) living inside the \
Jyotirgamaya app. Seekers come to you with questions about their birth chart, planets, \
nakshatras, dashas, and life in general.

VOICE
- Warm, unhurried, and dignified - a patient teacher, not a fortune-telling machine.
- You may address the seeker gently ("dear seeker", "beta" used warmly, never mockingly).
- Ground your teaching in real Jyotish concepts: rashi (signs), graha (planets), nakshatra, \
bhava (houses), dasha periods, karma and dharma - used accurately, not as decoration.
- Keep replies to a few short paragraphs. This is a conversation, not a lecture.

GROUNDING IN THE SEEKER'S OWN CHART
- If the seeker's computed chart is provided below, refer to its actual details naturally \
("Your Moon rests in Sagittarius, which speaks of...") rather than inventing placements.
- If no chart has been generated yet, you may speak in general Jyotish terms and gently \
invite the seeker to generate their reading first for a personal answer.
- Never fabricate specific planetary positions, dates, or dasha periods that were not given \
to you.

PHILOSOPHY AND BOUNDARIES
- Teach the classical view: "the grahas incline, they do not compel." Offer reflection and \
gentle guidance, not fatalistic or absolute predictions (avoid declaring that something \
certainly will or will not happen, especially death, divorce, or financial ruin).
- You are not a doctor, lawyer, or financial adviser. For serious health, legal, or money \
matters, offer the traditional astrological perspective if relevant, then gently encourage \
consulting the appropriate professional - briefly, without moralizing every single reply.
- If asked something with no connection to astrology, life guidance, or the seeker's chart, \
gently and briefly redirect back to what you can help with, in character - do not simply \
refuse or break character.
"""


class GurujiValidationError(Exception):
    """The request itself is invalid (empty message, too long, bad history)."""


class GurujiUnavailableError(Exception):
    """Guruji can't respond right now (not configured, or the API call failed)."""


def _client():
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        raise GurujiUnavailableError(
            'Guruji is not configured yet. Set GEMINI_API_KEY in your .env file to enable this feature.'
        )
    return genai.Client(api_key=api_key)


def _format_reading_context(reading):
    if not reading:
        return None

    lines = [
        f"Name: {reading.get('name', 'the seeker')}",
        f"Sun sign: {reading.get('sunSign')}",
        f"Moon sign: {reading.get('moonSign')}",
        f"Lagna (ascendant): {reading.get('lagna')}",
        f"Nakshatra: {reading.get('nakshatra')} (pada {reading.get('nakshatraPada')})",
    ]

    planets = reading.get('planets') or []
    if planets:
        planet_line = ', '.join(f"{p['name']} in {p['sign']} ({p['degree']:.1f} deg)" for p in planets)
        lines.append(f"Planets: {planet_line}")

    dasha = reading.get('dasha') or {}
    if dasha.get('birthNakshatraLord'):
        lines.append(f"Current dasha lineage starts from: {dasha['birthNakshatraLord']} "
                      f"(balance {dasha.get('balanceAtBirthYears')} years at birth)")

    return '\n'.join(lines)


def _validate(message, history):
    if not message or not message.strip():
        raise GurujiValidationError('Please ask Guruji a question.')
    if len(message) > MAX_MESSAGE_LENGTH:
        raise GurujiValidationError(f'Please keep your question under {MAX_MESSAGE_LENGTH} characters.')
    if history is not None and not isinstance(history, list):
        raise GurujiValidationError('Conversation history is malformed.')


def _to_gemini_contents(message, history):
    """Gemini uses role 'model' where Anthropic/OpenAI-style history uses
    'assistant' - translate at this boundary so the rest of the app (the
    frontend, backend.py's route) can keep using the more common 'assistant'
    naming regardless of which provider is behind ask_guruji()."""
    contents = []
    for turn in (history or [])[-MAX_HISTORY_TURNS:]:
        role = turn.get('role') if isinstance(turn, dict) else None
        content = turn.get('content') if isinstance(turn, dict) else None
        if role in ('user', 'assistant') and content:
            gemini_role = 'model' if role == 'assistant' else 'user'
            contents.append({'role': gemini_role, 'parts': [{'text': str(content)[:MAX_MESSAGE_LENGTH]}]})
    contents.append({'role': 'user', 'parts': [{'text': message.strip()}]})
    return contents


def ask_guruji(message: str, history=None, reading=None) -> str:
    """message: the seeker's new question.
    history: optional list of {"role": "user"|"assistant", "content": str} prior turns.
    reading: optional full reading dict (as returned by /api/astrology/reading), used to
        ground answers in the seeker's own chart.
    Returns Guruji's reply text.
    """
    _validate(message, history)
    client = _client()

    system = SYSTEM_PROMPT
    context = _format_reading_context(reading)
    if context:
        system += f"\n\nTHE SEEKER'S CURRENT CHART (already computed - use it, don't recompute it):\n{context}"

    contents = _to_gemini_contents(message, history)

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=MAX_REPLY_TOKENS,
                # Guruji is a conversational persona, not a reasoning task - a
                # lighter thinking budget roughly halves latency/cost with no
                # noticeable quality loss in testing (thinking_budget=0 is
                # rejected outright by this model, so "low" is the floor).
                thinking_config=types.ThinkingConfig(thinking_level='low'),
            ),
        )
    except errors.APIError as exc:
        raise GurujiUnavailableError('Guruji is unavailable right now. Please try again shortly.') from exc

    reply = (response.text or '').strip()
    if not reply:
        raise GurujiUnavailableError('Guruji had no answer this time. Please try rephrasing your question.')
    return reply
