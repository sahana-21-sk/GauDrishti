"""Helpers for the Streamlit app (Person B). Every function fails safe: nothing here may crash the UI."""
import io, json, os
from pathlib import Path
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
LIVE, DEMO, AUDIO = ROOT / "data" / "live", ROOT / "data" / "demo", ROOT / "data" / "audio"
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except Exception:
    pass

LANGS = {"English": "en", "हिन्दी (Hindi)": "hi", "తెలుగు (Telugu)": "te"}
LANG_NAME = {"en": "English", "hi": "Hindi", "te": "Telugu"}


def load_results(force_demo=False):
    """Live results first, then Demo Mode. Returns (results, folder, mode)."""
    order = [("Demo mode", DEMO)] if force_demo else [("Live results", LIVE), ("Demo mode", DEMO)]
    for mode, folder in order:
        p = folder / "results.json"
        try:
            if p.exists():
                res = json.loads(p.read_text(encoding="utf-8"))
                if all(k in res for k in ("meta", "cows", "alerts")) and res["cows"]:
                    return res, folder, mode
        except Exception:
            pass
    return None, DEMO, "No data"


def media(folder, rel):
    try:
        if rel and (Path(folder) / rel).exists():
            return str(Path(folder) / rel)
    except Exception:
        pass
    return None


def breeding_window(hour):
    """AM-PM rule: heat seen in the morning -> breed this evening; seen in the afternoon/evening -> next morning."""
    return "today 4 PM to 8 PM" if hour < 12 else "tomorrow 6 AM to 10 AM"


def herd_pulse(res):
    """0-100. Each cow starts at 100 and loses up to 60 points based on her strongest alert."""
    worst = {}
    for a in res.get("alerts", []):
        worst[a["cow_id"]] = max(worst.get(a["cow_id"], 0), a["score"])
    cows = [c["id"] for c in res["cows"]]
    return round(sum(100 - 60 * worst.get(i, 0) for i in cows) / max(len(cows), 1))


def _fallback(alert, lang, window):
    i, heat = alert["cow_id"], alert["type"] == "heat"
    why = "; ".join(alert.get("reasons", []))
    if lang == "hi":
        return (f"गाय #{i} में गर्मी (heat) के संकेत मिले हैं। प्रजनन के लिए सबसे अच्छा समय: {window}। कृपया पशु चिकित्सक से संपर्क करें।"
                if heat else f"गाय #{i} में बीमारी के शुरुआती संकेत दिखे हैं। कृपया पशु चिकित्सक से जाँच कराएँ।")
    if lang == "te":
        return (f"ఆవు #{i} లో వేడి (heat) లక్షణాలు కనిపించాయి. ఉత్తమ గర్భధారణ సమయం: {window}. దయచేసి పశువైద్యుడిని సంప్రదించండి."
                if heat else f"ఆవు #{i} లో అనారోగ్య ప్రారంభ లక్షణాలు కనిపించాయి. దయచేసి పశువైద్యుడిని సంప్రదించండి.")
    if heat:
        return (f"Cow #{i} may be in heat. Why: {why}. Best breeding window: {window}. Please call your vet.\n"
                f"Vet note: possible estrus, confidence {int(alert['score'] * 100)}%.")
    return (f"Cow #{i} shows possible early signs of illness. Why: {why}. Please get her checked by a vet.\n"
            f"Vet note: behaviour change vs own baseline, score {int(alert['score'] * 100)}%.")


def _secret(name):
    v = os.getenv(name)
    if v:
        return v
    try:
        return st.secrets.get(name)
    except Exception:
        return None


def _gemini(prompt):
    key = _secret("GEMINI_API_KEY")
    if not key:
        return None
    try:
        from google import genai
        r = genai.Client(api_key=key).models.generate_content(
            model=_secret("GEMINI_MODEL") or "gemini-2.5-flash", contents=prompt)
        return (r.text or "").strip() or None
    except Exception:
        return None


def explain(alert, lang, window):
    """Returns (text, source). source = 'gemini' or 'template'. Cached per alert+language."""
    cache = st.session_state.setdefault("expl", {})
    k = (alert["id"], lang, window)
    if k not in cache:
        prompt = (
            "You help small dairy farmers in India. A camera system flagged a cow using these signals "
            f"(a screening, not a diagnosis):\nType: {alert['type']}\nCow: #{alert['cow_id']}\n"
            f"Confidence: {int(alert['score'] * 100)}%\nReasons: {'; '.join(alert.get('reasons', []))}\n"
            f"Best breeding window (heat only): {window}\n\n"
            f"Write in {LANG_NAME[lang]}: (1) two short, simple sentences for the farmer saying what was "
            "seen and what to do (use the word 'possible', never claim a diagnosis); then (2) one line "
            "starting with 'Vet note:' (in English) for the vet. Plain text, no markdown.")
        t = _gemini(prompt)
        cache[k] = (t, "gemini") if t else (_fallback(alert, lang, window), "template")
    return cache[k]


def speak(text, lang, alert_id, allow_pregen):
    """MP3 bytes or None. Uses pre-generated audio first (only for template text), then gTTS live."""
    try:
        f = AUDIO / f"{alert_id}_{lang}.mp3"
        if allow_pregen and f.exists():
            return f.read_bytes()
    except Exception:
        pass
    try:
        from gtts import gTTS
        buf = io.BytesIO()
        gTTS(text=text.split("\nVet note:")[0], lang=lang).write_to_fp(buf)
        return buf.getvalue()
    except Exception:
        return None
