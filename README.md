# Geo Motion

Independent geography-documentary pipeline, separate from `YT_channel`.

## First prototype: The Suez Canal
A 36-second 1280×720 map-motion explainer with Natural Earth land geometry, an animated Europe-to-Asia shipping route, camera framing changes, location labels, chapter lower-thirds, eSpeak NG narration, H.264/AAC MP4 and ffprobe validation.

## Run locally
Requires Python 3.11+, FFmpeg and eSpeak NG.
```bash
pip install -r requirements.txt
python render_geo_doc.py --output output/suez-canal-documentary.mp4 --seconds 36
```

Push to `main` or manually run **Geo Motion — documentary prototype**. The MP4 is uploaded as a workflow artifact.

Map geometry: Natural Earth Vector, public-domain dataset. Route and narration are illustrative; verify factual claims and source statistics before publication.

Current limitations: simplified equirectangular projection, one illustrative route, synthetic narration and basic map styling. This is a technical prototype, not yet a finished documentary studio.
