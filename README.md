# Gaudrishti: Giving the silent herd a voice
Non-invasive cattle health monitoring from ordinary CCTV video. Screening tool, not a diagnosis: a vet confirms.

## Architecture (process first, show later)
`Video -> YOLO -> tracking -> behaviours -> baseline -> alerts -> results.json + processed_video.mp4 + clips/` (runs once on Colab)
then `Streamlit app` only READS those files. The app never runs YOLO, so it cannot crash on stage.

## Run the app
```
pip install -r requirements.txt
streamlit run app/app.py
```
It opens in **Demo Mode** (synthetic data in data/demo). Put real output in `data/live/` and it switches automatically.

## Run the CV pipeline (Colab)
Open `colab/gaudrishti_colab.ipynb` in Google Colab (GPU), edit the git URL, run the cells. Then unzip `output.zip` into `data/live/` so you get `data/live/results.json`.

## Gemini (optional, falls back to template text)
Copy `.env.example` to `.env` and add your key. On Streamlit Cloud: App settings > Secrets > `GEMINI_API_KEY = "..."`. Never commit the key.

## Deploy
Push to GitHub > share.streamlit.io > New app > main file `app/app.py`. Keep demo files small (under ~25 MB).

## Features
Breeding Time Advisor (AM-PM rule), local-language voice alerts (gTTS), Herd Isolation Score, Cow Health Card, Daily Herd Pulse, evidence clip for every alert.

## Honest notes
Behaviours are rule-based from box geometry, so alerts say "possible". Thresholds in `colab/analysis.py` (CFG) need tuning on your own video. Tracker ID switches in crowded scenes can split one cow into two IDs: pick a clear clip. Check the Hindi/Telugu text with a native speaker.
