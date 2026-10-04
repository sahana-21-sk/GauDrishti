"""GauDrishti dashboard (Person B).



Streamlit product layer only:

\- Reads results.json through app/utils.py

\- Never runs YOLO

\- Provides sidebar navigation for the demo

"""



import sys

from pathlib import Path

import datetime as dt



import pandas as pd

import plotly.express as px

import streamlit as st



sys.path.insert(0, str(Path(__file__).resolve().parent))

import utils as U





# ============================================================

# PAGE CONFIG

# ============================================================



st.set_page_config(

    page_title="GauDrishti",

    page_icon="🐄",

    layout="wide",

)





# ============================================================

# PRODUCT HEADER

# ============================================================



st.markdown(
    """
    <div style="
        padding: 20px;
        border-radius: 15px;
        background: #e8f5e9;
        margin-bottom: 1.2rem;
    ">
        <h1 style="margin:0;">GauDrishti</h1>
        <p style="margin:0.4rem 0 0 0; font-size:1.05rem;">
            AI-Powered Cattle Health Monitoring Ecosystem
        </p>
        <p style="margin:0.2rem 0 0 0; color:#555;">
            From CCTV behaviour analysis to early attention alerts.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.info(

    "GauDrishti is a screening and decision-support tool. "

    "It identifies behavioural deviations for early attention; "

    "a veterinarian makes the final diagnosis."

)





# ============================================================

# SAFE SECTION RUNNER

# ============================================================



def safe(fn, *args):

    try:

        return fn(*args)

    except Exception as e:

        st.error(

            f"Error in {fn.__name__}: "

            f"{type(e).__name__}: {e}"

        )





# ============================================================

# LOAD RESULTS

# ============================================================



# Demo Mode lets the team fall back to data/demo when live

# processing is unavailable.

force_demo = st.sidebar.checkbox(

    "Force Demo Mode",

    value=False,

)



res, folder, mode = U.load_results(force_demo)



if res is None:

    st.error(

        "No results found. Add data/live/results.json "

        "or data/demo/results.json."

    )

    st.stop()



# Data used by all dashboard pages.

cows = {c["id"]: c for c in res.get("cows", [])}

watchlist = res.get("watchlist", [])

alerts_data = res.get("alerts", [])





# ============================================================

# SIDEBAR

# ============================================================



st.sidebar.title("GauDrishti")

st.sidebar.caption("Giving the silent herd a voice.")



st.sidebar.markdown("---")



page = st.sidebar.radio(

    "Navigation",

    [

        "Overview",

        "Alerts",

        "Watchlist",

        "Cow Health",

        "Herd Map",

        "CCTV & Evidence",

        "About",

    ],

)



st.sidebar.markdown("---")



st.sidebar.success(f"Showing: {mode}")



# Alert language

lang_label = st.sidebar.selectbox(

    "Alert language",

    list(U.LANGS),

)

lang = U.LANGS[lang_label]



# Heat/breeding time helper

try:

    h, m = (

        int(x)

        for x in res["meta"]

        .get("video_start_clock", "06:00")

        .split(":")[:2]

    )

except Exception:

    h, m = 6, 0



seen_at = st.sidebar.time_input(

    "Time heat was first seen",

    dt.time(h, m),

)



window = U.breeding_window(seen_at.hour)



st.sidebar.caption(

    "Screening tool, not a diagnosis. A vet confirms."

)





# ============================================================

# OVERVIEW

# ============================================================



def overview():

    st.subheader("Herd Overview")



    c1, c2, c3, c4, c5 = st.columns(5)



    c1.metric(

        "Herd Pulse",

        f"{U.herd_pulse(res)}/100",

    )



    c2.metric(

        "Cows Tracked",

        len(cows),

    )



    c3.metric(

        "Possible Heat",

        sum(x.get("type") == "heat" for x in alerts_data),

    )



    c4.metric(

        "Health Flags",

        sum(x.get("type") == "health" for x in alerts_data),

    )



    c5.metric(

        "Watchlist",

        len(watchlist),

    )



    st.markdown("---")



    # --------------------------------------------------------

    # Processed CCTV

    # --------------------------------------------------------



    st.subheader("Processed CCTV Analysis")



    video = U.media(

        folder,

        res.get("meta", {}).get("processed_video"),

    )



    if video:

        st.video(video)

    else:

        st.info(

            "Processed video not available. "

            "Alerts below still work."

        )



    # --------------------------------------------------------

    # Formal alert summary

    # --------------------------------------------------------



    if alerts_data:

        st.subheader("Active Alerts")



        st.dataframe(

            pd.DataFrame(

                [

                    {

                        "Alert": x.get("id", "-"),

                        "Cow": x.get("cow_id", "-"),

                        "Type": x.get("type", "-"),

                        "Confidence": (

                            f"{int(float(x.get('score', 0)) * 100)}%"

                        ),

                        "Why": "; ".join(x.get("reasons", [])),

                    }

                    for x in alerts_data

                ]

            ),

            hide_index=True,

            width="stretch",

        )

    else:

        st.success("No formal alerts detected.")



    # --------------------------------------------------------

    # Watchlist summary

    # --------------------------------------------------------



    if watchlist:

        st.subheader("Behaviour Watchlist")



        st.dataframe(

            pd.DataFrame(

                [

                    {

                        "Case": x.get("id", "-"),

                        "Cow": x.get("cow_id", "-"),

                        "Score": (

                            f"{int(float(x.get('score', 0)) * 100)}%"

                        ),

                        "Time": f"{x.get('t', '-')}s",

                        "Why": "; ".join(x.get("reasons", [])),

                    }

                    for x in watchlist

                ]

            ),

            hide_index=True,

            width="stretch",

        )





# ============================================================

# ALERTS

# ============================================================



def alerts():

    st.subheader("Alerts")



    if not alerts_data:

        st.success("No alerts detected.")

        return



    for x in alerts_data:

        aid = x.get("id", "alert")

        cow_id = x.get("cow_id", "-")

        score = float(x.get("score", 0))

        alert_type = x.get("type", "health")



        with st.container(border=True):

            st.subheader(

                f"Cow #{cow_id}: possible "

                f"{'heat' if alert_type == 'heat' else 'health issue'} "

                f"({int(score * 100)}%)"

            )



            left, right = st.columns([3, 2])



            with left:

                video = U.media(

                    folder,

                    x.get("clip"),

                )



                if video:

                    st.video(video)

                else:

                    st.caption(

                        "Evidence clip not available."

                    )



            with right:

                st.markdown("**Why this alert was raised:**")



                for reason in x.get("reasons", []):

                    st.write("• " + str(reason))



                if alert_type == "heat":

                    st.info(

                        f"Breeding Time Advisor: best window "

                        f"**{window}**. Call the vet."

                    )



                if st.button(

                    f"Explain in {lang_label.split(' ')[0]}",

                    key=f"ex_{aid}_{lang}",

                ):

                    st.session_state[

                        f"show_{aid}_{lang}"

                    ] = True



                if st.session_state.get(

                    f"show_{aid}_{lang}",

                    False,

                ):

                    text, source = U.explain(

                        x,

                        lang,

                        window,

                    )



                    st.write(text)



                    st.caption(

                        "Written by Gemini"

                        if source == "gemini"

                        else "Template text (Gemini not connected)"

                    )



                    if st.button(

                        "Speak",

                        key=f"sp_{aid}_{lang}",

                    ):

                        audio = U.speak(

                            text,

                            lang,

                            aid,

                            source == "template",

                        )



                        if audio:

                            st.audio(

                                audio,

                                format="audio/mp3",

                            )

                        else:

                            st.info(

                                "Audio unavailable right now. "

                                "The text above has the message."

                            )





# ============================================================

# WATCHLIST

# ============================================================



def watchlist_section():
    st.subheader("Behaviour Watchlist")

    st.caption(
        "These cows show meaningful behavioural deviation "
        "but have not crossed the formal alert threshold."
    )

    if not watchlist:
        st.success("No cows currently require attention.")
        return

    for item in watchlist:
        cow_id = item.get("cow_id", "-")
        watch_id = item.get("id", f"W_{cow_id}")
        score = float(item.get("score", 0))

        # Convert a watchlist case into the same structure
        # expected by U.explain(). This lets Gemini explain
        # Cow #2 even when there are no formal alerts.
        watch_case = {
            "id": watch_id,
            "cow_id": cow_id,
            "type": "health",
            "score": score,
            "reasons": item.get("reasons", []),
        }

        with st.container(border=True):
            st.markdown(
                f"### Cow #{cow_id} — Watch / Attention"
            )

            left, right = st.columns([3, 2])

            with left:
                video = U.media(
                    folder,
                    item.get("clip"),
                )

                if video:
                    st.video(video)
                else:
                    st.info("Evidence clip not available.")

            with right:
                st.metric(
                    "Watch Score",
                    f"{int(score * 100)}%",
                )

                st.write(
                    f"**Detected at:** "
                    f"{item.get('t', '-')} seconds"
                )

                st.write(
                    "**Why this cow is being watched:**"
                )

                for reason in item.get("reasons", []):
                    st.write("• " + str(reason))

                st.warning(
                    "Attention recommended. "
                    "This is a behavioural screening result, "
                    "not a diagnosis."
                )

                st.markdown("---")

                if st.button(
                    f"Explain in {lang_label.split(' ')[0]}",
                    key=f"watch_ex_{watch_id}_{lang}",
                ):
                    st.session_state[
                        f"show_watch_{watch_id}_{lang}"
                    ] = True

                if st.session_state.get(
                    f"show_watch_{watch_id}_{lang}",
                    False,
                ):
                    explanation, source = U.explain(
                        watch_case,
                        lang,
                        window,
                    )

                    st.write(explanation)

                    if source == "gemini":
                        st.caption("Written by Gemini")
                    else:
                        st.caption(
                            "Template text (Gemini not connected)"
                        )

                    if st.button(
                        "Speak",
                        key=f"watch_speak_{watch_id}_{lang}",
                    ):
                        audio = U.speak(
                            explanation,
                            lang,
                            watch_id,
                            source == "template",
                        )

                        if audio:
                            st.audio(
                                audio,
                                format="audio/mp3",
                            )
                        else:
                            st.info(
                                "Audio unavailable right now. "
                                "The text above has the message."
                            )


def health_cards():

    st.subheader("Cow Health Cards")



    if not cows:

        st.info("No cow data available.")

        return



    cid = st.selectbox(

        "Choose a cow",

        list(cows),

        format_func=lambda i: f"Cow #{i}",

    )



    cow = cows[cid]

    stats = cow.get("stats", {})

    baseline = stats.get("baseline", {})

    recent = stats.get("recent", {})



    cow_alerts = [

        x

        for x in alerts_data

        if x.get("cow_id") == cid

    ]



    cow_watchlist = [

        x

        for x in watchlist

        if x.get("cow_id") == cid

    ]



    st.markdown(

        f"### Cow #{cid} Health Card"

    )



    if cow_alerts:

        st.write(

            "Status: "

            + " / ".join(

                f"possible {x.get('type', 'issue')}"

                for x in cow_alerts

            )

        )

    elif cow_watchlist:

        st.write("Status: Watch / Attention")

    else:

        st.write("Status: Normal")



    c1, c2, c3, c4 = st.columns(4)



    speed_recent = float(recent.get("speed", 0))

    speed_baseline = float(baseline.get("speed", 0))



    lying_recent = float(recent.get("lying_pct", 0))

    lying_baseline = float(baseline.get("lying_pct", 0))



    feeding_recent = float(recent.get("feeding_pct", 0))

    feeding_baseline = float(baseline.get("feeding_pct", 0))



    isolation = float(stats.get("isolation_score", 0))



    c1.metric(

        "Movement",

        f"{speed_recent:.3f}",

        f"{speed_recent - speed_baseline:.3f} vs normal",

        delta_color="off",

    )



    c2.metric(

        "Lying",

        f"{int(lying_recent * 100)}%",

        f"{int((lying_recent - lying_baseline) * 100)} pts",

        delta_color="off",

    )



    c3.metric(

        "Feeding",

        f"{int(feeding_recent * 100)}%",

        f"{int((feeding_recent - feeding_baseline) * 100)} pts",

        delta_color="off",

    )



    c4.metric(

        "Isolation",

        f"{int(isolation * 100)}%",

    )



    timeline = cow.get("timeline", [])



    if timeline:

        df = pd.DataFrame(timeline)



        if {"t", "state"}.issubset(df.columns):

            fig = px.scatter(

                df,

                x="t",

                y="state",

                color="state",

                title="Behaviour timeline",

                category_orders={

                    "state": [

                        "lying",

                        "standing",

                        "feeding",

                        "walking",

                    ]

                },

            )



            fig.add_vline(

                x=res.get("meta", {}).get(

                    "baseline_until_s",

                    0,

                ),

                line_dash="dash",

                annotation_text="baseline ends",

            )



            st.plotly_chart(

                fig,

                width="stretch",

            )



    for item in cow_alerts:

        text, _ = U.explain(

            item,

            "en",

            window,

        )



        if "Vet note:" in text:

            text = text.split("Vet note:")[-1].strip()



        st.write(text)



    for item in cow_watchlist:

        st.info(

            "Watchlist: "

            + ", ".join(item.get("reasons", []))

        )





# ============================================================

# HERD MAP

# ============================================================



def herd_map():

    st.subheader("Herd Map")



    duration = max(

        int(res.get("meta", {}).get("duration_s", 1)) - 1,

        1,

    )



    baseline_end = int(

        res.get("meta", {}).get(

            "baseline_until_s",

            0,

        )

    )



    default_time = min(

        duration,

        baseline_end + 1,

    )



    time_value = st.slider(

        "Time (seconds)",

        0,

        duration,

        default_time,

    )



    rows = []



    for cow_id, cow in cows.items():

        position = next(

            (

                point

                for point in cow.get("timeline", [])

                if point.get("t") == time_value

            ),

            None,

        )



        if position:

            rows.append(

                {

                    "cow": f"#{cow_id}",

                    "x": position.get("x", 0),

                    "y": position.get("y", 0),

                    "isolation": cow.get(

                        "stats",

                        {},

                    ).get(

                        "isolation_score",

                        0,

                    ),

                }

            )



    if not rows:

        st.info(

            "No cows visible at this second."

        )

        return



    df = pd.DataFrame(rows)



    fig = px.scatter(

        df,

        x="x",

        y="y",

        text="cow",

        color="isolation",

        range_color=[0, 1],

        color_continuous_scale="RdYlGn_r",

        title="Barn Map — colour = Herd Isolation Score",

    )



    fig.update_traces(

        marker_size=22,

        textposition="top center",

    )



    fig.update_yaxes(

        autorange="reversed",

        range=[0, 1],

    )



    fig.update_xaxes(

        range=[0, 1],

    )



    st.plotly_chart(

        fig,

        width="stretch",

    )





# ============================================================

# CCTV & EVIDENCE

# ============================================================



def cctv_evidence():

    st.subheader("CCTV & Evidence")



    video = U.media(

        folder,

        res.get("meta", {}).get("processed_video"),

    )



    if video:

        st.video(video)

    else:

        st.info(

            "Processed CCTV video is not available right now."

        )



    st.markdown("---")



    st.markdown("### Evidence Clips")



    clips_found = False



    for item in alerts_data + watchlist:

        clip = item.get("clip")



        if not clip:

            continue



        clips_found = True



        cow_id = item.get("cow_id", "-")

        score = int(

            float(item.get("score", 0)) * 100

        )



        st.markdown(

            f"**Cow #{cow_id} — {score}%**"

        )



        clip_video = U.media(

            folder,

            clip,

        )



        if clip_video:

            st.video(clip_video)

        else:

            st.caption(

                f"Evidence clip unavailable: {clip}"

            )



    if not clips_found:

        st.info("No evidence clips are available.")





# ============================================================

# ABOUT

# ============================================================



def about():

    st.subheader("About GauDrishti")



    st.markdown(

        """

        ### GauDrishti



        **AI-Powered Cattle Health Monitoring Ecosystem**



        GauDrishti uses computer vision to monitor cattle

        behaviour and identify animals that may require

        further attention.



        ### What it monitors



        - Cattle movement

        - Feeding behaviour

        - Lying behaviour

        - Isolation

        - Behavioural deviations

        - Possible heat indicators

        - Possible health concerns



        ### How it works



        CCTV footage is processed using AI-based computer

        vision and behavioural analysis. The resulting

        information is presented through this dashboard.



        ### Important



        GauDrishti is a screening and decision-support

        system, not a veterinary diagnosis.



        A qualified veterinarian should make the final

        medical decision.

        """

    )





# ============================================================

# PAGE ROUTING

# ============================================================



if page == "Overview":

    safe(overview)



elif page == "Alerts":

    safe(alerts)



elif page == "Watchlist":

    safe(watchlist_section)



elif page == "Cow Health":

    safe(health_cards)



elif page == "Herd Map":

    safe(herd_map)



elif page == "CCTV & Evidence":

    safe(cctv_evidence)



elif page == "About":

    safe(about)
