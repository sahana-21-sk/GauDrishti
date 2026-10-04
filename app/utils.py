"""Helpers for the Streamlit app (Person B).

All functions fail safely so a missing API key, broken audio,
or missing data should not crash the Streamlit dashboard.
"""

import io
import json
import os
from pathlib import Path

import streamlit as st


# ============================================================
# PROJECT PATHS
# ============================================================

ROOT = Path(__file__).resolve().parent.parent

LIVE = ROOT / "data" / "live"
DEMO = ROOT / "data" / "demo"
AUDIO = ROOT / "data" / "audio"


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

try:
    from dotenv import load_dotenv

    # Load .env from the project root
    load_dotenv(ROOT / ".env")

except Exception:
    pass


# ============================================================
# LANGUAGES
# ============================================================

LANGS = {
    "English": "en",
    "हिन्दी (Hindi)": "hi",
    "తెలుగు (Telugu)": "te",
}

LANG_NAME = {
    "en": "English",
    "hi": "Hindi",
    "te": "Telugu",
}


# ============================================================
# LOAD RESULTS
# ============================================================

def load_results(force_demo=False):
    """Load live results first, then fall back to demo results."""

    if force_demo:
        order = [
            ("Demo mode", DEMO)
        ]
    else:
        order = [
            ("Live results", LIVE),
            ("Demo mode", DEMO),
        ]

    for mode, folder in order:

        results_file = folder / "results.json"

        try:

            if not results_file.exists():
                continue

            res = json.loads(
                results_file.read_text(encoding="utf-8")
            )

            # Basic validation
            required = ("meta", "cows", "alerts")

            if all(key in res for key in required) and res["cows"]:

                return res, folder, mode

        except Exception:
            continue

    return None, DEMO, "No data"


# ============================================================
# MEDIA FILES
# ============================================================

def media(folder, rel):
    """Return a media file path if it exists."""

    try:

        if not rel:
            return None

        path = Path(folder) / rel

        if path.exists():
            return str(path)

    except Exception:
        pass

    return None


# ============================================================
# BREEDING WINDOW
# ============================================================

def breeding_window(hour):
    """Return a simple breeding-window suggestion."""

    if hour < 12:
        return "today 4 PM to 8 PM"

    return "tomorrow 6 AM to 10 AM"


# ============================================================
# HERD PULSE
# ============================================================

def herd_pulse(res):
    """Calculate a simple 0-100 herd health pulse."""

    try:

        worst = {}

        for alert in res.get("alerts", []):

            cow_id = alert.get("cow_id")

            score = float(alert.get("score", 0))

            worst[cow_id] = max(
                worst.get(cow_id, 0),
                score
            )

        cows = [
            cow.get("id")
            for cow in res.get("cows", [])
        ]

        if not cows:
            return 100

        values = []

        for cow_id in cows:

            alert_score = worst.get(cow_id, 0)

            value = 100 - (60 * alert_score)

            values.append(value)

        return round(
            sum(values) / len(values)
        )

    except Exception:
        return 100


# ============================================================
# FALLBACK EXPLANATION
# ============================================================

def _fallback(alert, lang, window):

    try:

        cow_id = alert.get("cow_id", "?")

        alert_type = alert.get("type", "")

        heat = alert_type == "heat"

        reasons = alert.get("reasons", [])

        why = "; ".join(reasons)

        score = int(
            float(alert.get("score", 0)) * 100
        )

        # -------------------------
        # HINDI
        # -------------------------

        if lang == "hi":

            if heat:

                return (
                    f"गाय #{cow_id} में गर्मी (heat) के संभावित संकेत "
                    f"मिले हैं। प्रजनन के लिए सबसे अच्छा समय: "
                    f"{window}। कृपया पशु चिकित्सक से संपर्क करें।\n"
                    f"Vet note: Possible estrus, confidence {score}%."
                )

            return (
                f"गाय #{cow_id} में बीमारी के शुरुआती संभावित संकेत "
                f"दिखे हैं। कृपया पशु चिकित्सक से जाँच कराएँ।\n"
                f"Vet note: Possible health concern, confidence {score}%."
            )

        # -------------------------
        # TELUGU
        # -------------------------

        if lang == "te":

            if heat:

                return (
                    f"ఆవు #{cow_id} లో వేడి (heat) లక్షణాలు కనిపించాయి. "
                    f"ఉత్తమ గర్భధారణ సమయం: {window}. "
                    f"దయచేసి పశువైద్యుడిని సంప్రదించండి.\n"
                    f"Vet note: Possible estrus, confidence {score}%."
                )

            return (
                f"ఆవు #{cow_id} లో అనారోగ్యానికి సంబంధించిన "
                f"ప్రారంభ లక్షణాలు కనిపించాయి. "
                f"దయచేసి పశువైద్యుడిని సంప్రదించండి.\n"
                f"Vet note: Possible health concern, confidence {score}%."
            )

        # -------------------------
        # ENGLISH
        # -------------------------

        if heat:

            return (
                f"Cow #{cow_id} may be in heat. "
                f"Why: {why}. "
                f"Best breeding window: {window}. "
                f"Please contact your vet.\n"
                f"Vet note: Possible estrus, confidence {score}%."
            )

        return (
            f"Cow #{cow_id} shows possible early signs of illness. "
            f"Why: {why}. "
            f"Please get her checked by a vet.\n"
            f"Vet note: Possible health concern, confidence {score}%."
        )

    except Exception:

        return (
            "The system detected a possible behavioural concern. "
            "Please consult a veterinarian."
        )


# ============================================================
# SECRET / API KEY
# ============================================================

def _secret(name):
    """Read a secret from .env first, then Streamlit Secrets."""

    # 1. Try environment variable / .env
    try:

        value = os.getenv(name)

        if value:
            return value.strip()

    except Exception:
        pass

    # 2. Try Streamlit Secrets
    try:

        value = st.secrets.get(name)

        if value:
            return str(value).strip()

    except Exception:
        pass

    return None


# ============================================================
# GEMINI CONNECTION
# ============================================================

def _gemini(prompt):
    """Send a prompt to Gemini.

    Returns:
        Generated text if successful.
        None if Gemini is unavailable.

    Errors are shown in Streamlit so debugging is easier.
    """

    # --------------------------------------------------------
    # Get API key
    # --------------------------------------------------------

    key = _secret("GEMINI_API_KEY")

    if not key:

        st.warning(
            "Gemini API key not found. "
            "Using the built-in fallback explanation."
        )

        return None

    # --------------------------------------------------------
    # Import Gemini SDK
    # --------------------------------------------------------

    try:

        from google import genai

    except Exception as e:

        st.error(
            "Gemini package is not installed. "
            "Run: pip install google-genai"
        )

        return None

    # --------------------------------------------------------
    # Get model
    # --------------------------------------------------------

    model=_secret("GEMINI_MODEL") or "gemini-3.8-flash"

    # --------------------------------------------------------
    # Call Gemini
    # --------------------------------------------------------

    try:

        client = genai.Client(
            api_key=key
        )

        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )

        text = getattr(response, "text", None)

        if text:

            text = text.strip()

            if text:
                return text

        st.warning(
            "Gemini responded but returned no text. "
            "Using the fallback explanation."
        )

        return None

    except Exception as e:

        # IMPORTANT:
        # We show the actual error while debugging.
        st.error(
            f"Gemini connection failed: {type(e).__name__}: {e}"
        )

        return None


# ============================================================
# EXPLANATION
# ============================================================

def explain(alert, lang, window):
    """Generate an explanation using Gemini.

    Returns:
        (text, source)

    source:
        'gemini'
        or
        'template'
    """

    # Session-state cache
    cache = st.session_state.setdefault(
        "expl",
        {}
    )

    alert_id = alert.get(
        "id",
        f"{alert.get('cow_id', 'unknown')}_{alert.get('type', 'unknown')}"
    )

    cache_key = (
        alert_id,
        lang,
        window
    )

    # Return cached response
    if cache_key in cache:

        return cache[cache_key]

    # --------------------------------------------------------
    # Build Gemini prompt
    # --------------------------------------------------------

    alert_type = alert.get(
        "type",
        "unknown"
    )

    cow_id = alert.get(
        "cow_id",
        "unknown"
    )

    score = int(
        float(alert.get("score", 0)) * 100
    )

    reasons = "; ".join(
        alert.get("reasons", [])
    )

    language_name = LANG_NAME.get(
        lang,
        "English"
    )

    prompt = f"""
You are an assistant helping small dairy farmers in India.

A computer-vision system has flagged a cow.

IMPORTANT:
This is an early-warning screening system, NOT a medical diagnosis.

Cow ID: #{cow_id}

Alert type:
{alert_type}

Confidence:
{score}%

Observed reasons:
{reasons}

Suggested breeding window:
{window}

Write the response in {language_name}.

Follow this exact structure:

1. Give two short, simple sentences for the farmer.
2. Explain what the system observed.
3. Give a sensible next action.
4. Never claim that the cow definitely has a disease or is definitely in heat.
5. Use words such as "possible", "may", or "appears".
6. Then provide one final line beginning with:

Vet note:

Keep the response short and easy to understand.

Do not use markdown.
"""

    # --------------------------------------------------------
    # Try Gemini
    # --------------------------------------------------------

    generated = _gemini(prompt)

    if generated:

        result = (
            generated,
            "gemini"
        )

    else:

        result = (
            _fallback(
                alert,
                lang,
                window
            ),
            "template"
        )

    # Save to session cache
    cache[cache_key] = result

    return result


# ============================================================
# VOICE / gTTS
# ============================================================

def speak(
    text,
    lang,
    alert_id,
    allow_pregen
):
    """Generate MP3 audio.

    Priority:
    1. Pre-generated audio
    2. gTTS
    3. None
    """

    # --------------------------------------------------------
    # Pre-generated audio
    # --------------------------------------------------------

    try:

        audio_file = (
            AUDIO /
            f"{alert_id}_{lang}.mp3"
        )

        if (
            allow_pregen
            and audio_file.exists()
        ):

            return audio_file.read_bytes()

    except Exception:
        pass

    # --------------------------------------------------------
    # gTTS
    # --------------------------------------------------------

    try:

        from gtts import gTTS

        # Don't read the English vet note aloud
        speech_text = text

        if "\nVet note:" in speech_text:

            speech_text = (
                speech_text
                .split("\nVet note:", 1)[0]
            )

        buffer = io.BytesIO()

        tts = gTTS(
            text=speech_text,
            lang=lang
        )

        tts.write_to_fp(buffer)

        return buffer.getvalue()

    except Exception as e:

        st.warning(
            f"Voice generation unavailable: {e}"
        )

        return None