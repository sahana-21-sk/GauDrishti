"""Gaudrishti dashboard (Person B). Reads results.json only. Never runs YOLO. Never crashes: see safe()."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import datetime as dt
import pandas as pd
import plotly.express as px
import streamlit as st
import utils as U

st.set_page_config(page_title="Gaudrishti", page_icon="🐄", layout="wide")


def safe(fn, *a):
    try:
        return fn(*a)
    except Exception as e:
        st.warning(f"This section could not load ({type(e).__name__}). The rest of the app still works.")


# ---------- sidebar ----------
st.sidebar.title("🐄 Gaudrishti")
st.sidebar.caption("Giving the silent herd a voice.")
force_demo = st.sidebar.checkbox("Force Demo Mode", value=False)
res, folder, mode = U.load_results(force_demo)
if res is None:
    st.error("No results found. Add data/live/results.json or data/demo/results.json.")
    st.stop()
st.sidebar.success(f"Showing: {mode}")
lang_label = st.sidebar.selectbox("Alert language", list(U.LANGS))
lang = U.LANGS[lang_label]
h, m = (int(x) for x in res["meta"].get("video_start_clock", "06:00").split(":")[:2])
seen_at = st.sidebar.time_input("Time heat was first seen", dt.time(h, m))
window = U.breeding_window(seen_at.hour)
st.sidebar.caption("Screening tool, not a diagnosis. A vet confirms.")
cows = {c["id"]: c for c in res["cows"]}


# ---------- sections ----------
def overview():
    a = res["alerts"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Herd Pulse", f"{U.herd_pulse(res)}/100")
    c2.metric("Cows tracked", len(cows))
    c3.metric("Possible heat", sum(x["type"] == "heat" for x in a))
    c4.metric("Health flags", sum(x["type"] == "health" for x in a))
    v = U.media(folder, res["meta"].get("processed_video"))
    st.video(v) if v else st.info("Processed video not available. Alerts below still work.")
    if a:
        st.dataframe(pd.DataFrame([dict(Alert=x["id"], Cow=x["cow_id"], Type=x["type"],
                                        Confidence=f"{int(x['score'] * 100)}%", Why="; ".join(x["reasons"]))
                                   for x in a]), hide_index=True, width="stretch")
    else:
        st.success("No alerts. The herd looks normal.")


def alerts():
    if not res["alerts"]:
        st.success("No alerts.")
    for x in res["alerts"]:
        aid = x["id"]
        with st.container(border=True):
            st.subheader(f"Cow #{x['cow_id']}: possible {'heat' if x['type'] == 'heat' else 'health issue'} "
                         f"({int(x['score'] * 100)}%)")
            l, r = st.columns([3, 2])
            with l:
                v = U.media(folder, x.get("clip"))
                st.video(v) if v else st.caption("Evidence clip not available.")
            with r:
                for why in x["reasons"]:
                    st.write("• " + why)
                if x["type"] == "heat":
                    st.info(f"Breeding Time Advisor: best window **{window}**. Call the vet.")
                if st.button(f"Explain in {lang_label.split(' ')[0]}", key=f"ex_{aid}_{lang}"):
                    st.session_state[f"show_{aid}_{lang}"] = True
                if st.session_state.get(f"show_{aid}_{lang}"):
                    text, src = U.explain(x, lang, window)
                    st.write(text)
                    st.caption("Written by Gemini" if src == "gemini" else "Template text (Gemini not connected)")
                    if st.button("🔊 Speak", key=f"sp_{aid}_{lang}"):
                        audio = U.speak(text, lang, aid, src == "template")
                        st.audio(audio, format="audio/mp3") if audio else st.info("Audio unavailable right now. The text above has the message.")


def health_cards():
    cid = st.selectbox("Choose a cow", list(cows), format_func=lambda i: f"Cow #{i}")
    c = cows[cid]
    s = c["stats"]
    mine = [x for x in res["alerts"] if x["cow_id"] == cid]
    st.markdown(f"### Cow #{cid} Health Card")
    st.write("Status: " + (" / ".join(f"possible {x['type']}" for x in mine) if mine else "normal"))
    b, r = s["baseline"], s["recent"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Movement", f"{r['speed']}", f"{round(r['speed'] - b['speed'], 3)} vs normal", delta_color="off")
    c2.metric("Lying", f"{int(r['lying_pct'] * 100)}%", f"{int((r['lying_pct'] - b['lying_pct']) * 100)} pts", delta_color="off")
    c3.metric("Feeding", f"{int(r['feeding_pct'] * 100)}%", f"{int((r['feeding_pct'] - b['feeding_pct']) * 100)} pts", delta_color="off")
    c4.metric("Isolation", f"{int(s['isolation_score'] * 100)}%")
    df = pd.DataFrame(c["timeline"])
    fig = px.scatter(df, x="t", y="state", color="state", title="Behaviour timeline (seconds)",
                     category_orders={"state": ["lying", "standing", "feeding", "walking"]})
    fig.add_vline(x=res["meta"].get("baseline_until_s", 0), line_dash="dash", annotation_text="baseline ends")
    st.plotly_chart(fig, width="stretch")
    for x in mine:
        text, _ = U.explain(x, "en", window)
        st.write(text.split("Vet note:")[-1].strip() if "Vet note:" in text else text)


def herd_map():
    dur = max(int(res["meta"].get("duration_s", 1)) - 1, 1)
    t = st.slider("Time (seconds)", 0, dur, min(dur, int(res["meta"].get("baseline_until_s", 0)) + 1))
    rows = []
    for i, c in cows.items():
        p = next((q for q in c["timeline"] if q["t"] == t), None)
        if p:
            rows.append(dict(cow=f"#{i}", x=p["x"], y=p["y"], isolation=c["stats"]["isolation_score"]))
    if not rows:
        st.info("No cows visible at this second.")
        return
    df = pd.DataFrame(rows)
    fig = px.scatter(df, x="x", y="y", text="cow", color="isolation", range_color=[0, 1],
                     color_continuous_scale="RdYlGn_r", title="Barn map (colour = Herd Isolation Score)")
    fig.update_traces(marker_size=22, textposition="top center")
    fig.update_yaxes(autorange="reversed", range=[0, 1])
    fig.update_xaxes(range=[0, 1])
    st.plotly_chart(fig, width="stretch")


t1, t2, t3, t4 = st.tabs(["Overview", "Alerts", "Cow Health Cards", "Herd Map"])
with t1: safe(overview)
with t2: safe(alerts)
with t3: safe(health_cards)
with t4: safe(herd_map)
