import streamlit as st
import subprocess
import os
import json
import tempfile
import re
import time
from pathlib import Path
from anthropic import Anthropic

# Google Drive setup
CREDENTIALS_FILE = Path(__file__).parent / "credentials.json"
TOKEN_FILE = Path(__file__).parent / "token.json"
GDRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]

def get_drive_service():
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), GDRIVE_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), GDRIVE_SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    return build("drive", "v3", credentials=creds)


def upload_to_drive(file_path: str) -> str:
    from googleapiclient.http import MediaFileUpload
    service = get_drive_service()
    file_name = Path(file_path).name
    file_metadata = {"name": file_name}
    media = MediaFileUpload(file_path, mimetype="video/mp4", resumable=True)
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, webViewLink"
    ).execute()
    # Make it accessible to anyone with the link
    service.permissions().create(
        fileId=file["id"],
        body={"type": "anyone", "role": "reader"}
    ).execute()
    return file.get("webViewLink", "")

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ClipForge – Viral Clip Maker",
    page_icon="🎬",
    layout="centered",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0a0a0a;
    color: #f0ece4;
}

h1, h2, h3 {
    font-family: 'Syne', sans-serif;
}

.main-title {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 3rem;
    background: linear-gradient(135deg, #ff6b35, #f7c59f, #ff6b35);
    background-size: 200%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: shimmer 3s infinite;
    line-height: 1.1;
}

@keyframes shimmer {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

.subtitle {
    color: #8a8278;
    font-size: 1rem;
    font-weight: 300;
    letter-spacing: 0.05em;
    margin-top: -0.5rem;
    margin-bottom: 2rem;
}

.stTextInput > div > div > input {
    background: #1a1a1a !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 12px !important;
    color: #f0ece4 !important;
    font-family: 'DM Sans', sans-serif !important;
    padding: 0.75rem 1rem !important;
}

.stTextInput > div > div > input:focus {
    border-color: #ff6b35 !important;
    box-shadow: 0 0 0 2px rgba(255, 107, 53, 0.2) !important;
}

.stButton > button {
    background: linear-gradient(135deg, #ff6b35, #e84d1c) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    padding: 0.75rem 2rem !important;
    width: 100% !important;
    transition: all 0.2s ease !important;
    letter-spacing: 0.03em !important;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(255, 107, 53, 0.35) !important;
}

.clip-card {
    background: #141414;
    border: 1px solid #222;
    border-radius: 16px;
    padding: 1.5rem;
    margin: 1rem 0;
    position: relative;
    overflow: hidden;
}

.clip-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #ff6b35, transparent);
}

.clip-number {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 2rem;
    color: #ff6b35;
    opacity: 0.4;
    position: absolute;
    top: 1rem;
    right: 1.5rem;
}

.clip-title {
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 1.1rem;
    color: #f0ece4;
    margin-bottom: 0.4rem;
}

.clip-meta {
    font-size: 0.8rem;
    color: #8a8278;
    margin-bottom: 0.75rem;
    font-weight: 500;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

.clip-hook {
    font-size: 0.95rem;
    color: #c8c0b4;
    line-height: 1.6;
    border-left: 2px solid #ff6b35;
    padding-left: 0.75rem;
    margin: 0.5rem 0;
}

.viral-score {
    display: inline-block;
    background: rgba(255,107,53,0.15);
    color: #ff6b35;
    border-radius: 6px;
    padding: 0.2rem 0.6rem;
    font-size: 0.8rem;
    font-weight: 700;
    font-family: 'Syne', sans-serif;
    margin-top: 0.5rem;
}

.feature-toggle {
    background: #141414;
    border: 1px solid #222;
    border-radius: 12px;
    padding: 1rem 1.25rem;
    margin: 0.4rem 0;
}

.stSelectbox > div > div {
    background: #1a1a1a !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 12px !important;
    color: #f0ece4 !important;
}

div[data-testid="stExpander"] {
    background: #141414;
    border: 1px solid #222 !important;
    border-radius: 12px !important;
}

.stSlider > div > div > div {
    background: #ff6b35 !important;
}
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">ClipForge</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">PASTE A YOUTUBE LINK → GET A VIRAL CLIP</div>', unsafe_allow_html=True)

# ── API Key ────────────────────────────────────────────────────────────────────
with st.expander("⚙️  Settings", expanded=not bool(os.environ.get("ANTHROPIC_API_KEY"))):
    api_key_input = st.text_input(
        "Anthropic API Key",
        type="password",
        value=os.environ.get("ANTHROPIC_API_KEY", ""),
        placeholder="sk-ant-...",
        help="Get yours at console.anthropic.com"
    )
    if api_key_input:
        os.environ["ANTHROPIC_API_KEY"] = api_key_input

# ── Main form ──────────────────────────────────────────────────────────────────
st.markdown("#### Drop your YouTube link")
youtube_url = st.text_input("", placeholder="https://www.youtube.com/watch?v=...", label_visibility="collapsed")

col1, col2 = st.columns(2)
with col1:
    num_clips = st.selectbox("How many clips?", [1, 2, 3], index=1)
with col2:
    clip_length = st.selectbox("Max clip length", ["30 sec", "45 sec", "60 sec"], index=1)

vibe = st.selectbox("Clip vibe", ["🔥 Most viral moment", "😂 Funniest moment", "💡 Most insightful", "😱 Most shocking", "🎯 Best hook/intro"])

# ── Feature Toggles ────────────────────────────────────────────────────────────
st.markdown("#### ✨ Enhancement Features")

col_a, col_b, col_c = st.columns(3)
with col_a:
    enable_voiceover = st.checkbox("🎙️ AI Voiceover", value=False, help="Claude writes a voiceover script and mixes it on top of the original audio")
with col_b:
    enable_subtitles = st.checkbox("💬 Subtitles", value=False, help="Burn auto-generated subtitles into the video")
with col_c:
    enable_crop = st.checkbox("📱 9:16 Crop", value=False, help="Crop and scale clip to 1080x1920 vertical (TikTok/Reels/Shorts)")

if enable_voiceover:
    voiceover_style = st.selectbox(
        "Voiceover style",
        ["🎯 Hype/Energetic", "😌 Calm/Educational", "😂 Comedic", "📰 News Anchor"],
        help="Tone for the AI-generated voiceover script"
    )
else:
    voiceover_style = None

run_btn = st.button("⚡ FORGE MY CLIPS")

# ── Helpers ────────────────────────────────────────────────────────────────────

def check_deps(need_voiceover=False):
    issues = []
    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        issues.append("`yt-dlp` not found — run: `pip install yt-dlp`")
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        issues.append("`ffmpeg` not found — install from https://ffmpeg.org/download.html")
    try:
        import whisper  # noqa
    except ImportError:
        issues.append("`openai-whisper` not found — run: `pip install openai-whisper`")
    if need_voiceover:
        try:
            import edge_tts  # noqa
        except ImportError:
            issues.append("`edge-tts` not found — run: `pip install edge-tts`")
    return issues


def download_video(url: str, out_dir: str) -> str:
    out_template = os.path.join(out_dir, "source.%(ext)s")
    subprocess.run(
        ["yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
         "--merge-output-format", "mp4", "-o", out_template, url],
        check=True, capture_output=True, text=True
    )
    for f in Path(out_dir).iterdir():
        if f.stem == "source" and f.suffix in (".mp4", ".mkv", ".webm"):
            return str(f)
    raise FileNotFoundError("Downloaded file not found.")


def transcribe(video_path: str):
    import whisper
    model = whisper.load_model("base")
    result = model.transcribe(video_path, word_timestamps=False)
    return result


def pick_clips_with_claude(transcript_segments, num_clips: int, max_seconds: int, vibe: str) -> list:
    client = Anthropic()
    segments_text = "\n".join(
        f"[{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text'].strip()}"
        for seg in transcript_segments
        if seg.get("text", "").strip()
    )

    vibe_map = {
        "🔥 Most viral moment": "highest viral potential, broad appeal",
        "😂 Funniest moment": "funniest, most entertaining",
        "💡 Most insightful": "most insightful or educational",
        "😱 Most shocking": "most surprising or controversial",
        "🎯 Best hook/intro": "best opening hook or strong introduction",
    }
    vibe_desc = vibe_map.get(vibe, "highest viral potential")

    prompt = f"""You are a viral content strategist. Analyze this transcript and identify the {num_clips} best clip(s) for TikTok/Reels.

Each clip must:
- Be {max_seconds} seconds or shorter
- Start with a strong hook (no slow build-ups)
- Have high retention (people won't scroll away)
- Focus on: {vibe_desc}

TRANSCRIPT:
{segments_text}

Respond ONLY with valid JSON. No markdown, no explanation, just the JSON array.

Format:
[
  {{
    "clip_number": 1,
    "title": "Short punchy title",
    "start_time": 12.5,
    "end_time": 41.0,
    "viral_score": 92,
    "hook": "Why this clip is viral — what makes the first 2 seconds irresistible",
    "caption": "Suggested TikTok caption with hashtags",
    "clip_transcript": "The exact words spoken in this clip segment"
  }}
]"""

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.content[0].text.strip()
    raw = re.sub(r"^```json|^```|```$", "", raw, flags=re.MULTILINE).strip()
    return json.loads(raw)


def generate_voiceover_script(clip: dict, style: str) -> str:
    """Use Claude to write a voiceover script for the clip."""
    client = Anthropic()

    style_map = {
        "🎯 Hype/Energetic": "high energy, hype, exciting — like a sports commentator or hype man",
        "😌 Calm/Educational": "calm, clear, informative — like a documentary narrator",
        "😂 Comedic": "funny, witty, comedic timing — like a stand-up comedian doing commentary",
        "📰 News Anchor": "professional, authoritative, news anchor style",
    }
    style_desc = style_map.get(style, "high energy and engaging")

    prompt = f"""Write a short voiceover script for this viral clip.

Clip title: {clip['title']}
Clip transcript: {clip.get('clip_transcript', clip['hook'])}
Duration: {clip['end_time'] - clip['start_time']:.0f} seconds
Style: {style_desc}

Rules:
- The voiceover should be SHORT — it will play on top of the original audio, so keep it punchy
- Max 2-3 sentences
- Match the energy of the clip
- Do NOT repeat what's being said word for word — add commentary/context
- Respond with ONLY the voiceover text, nothing else"""

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()


def synthesize_voiceover(script: str, out_path: str):
    """Use edge-tts to synthesize the voiceover script to an audio file."""
    import asyncio
    import edge_tts

    async def _synthesize():
        communicate = edge_tts.Communicate(script, voice="en-US-GuyNeural")
        await communicate.save(out_path)

    asyncio.run(_synthesize())


def mix_voiceover(video_path: str, voiceover_audio: str, out_path: str):
    """Mix voiceover on top of original audio (voiceover slightly quieter)."""
    subprocess.run([
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", voiceover_audio,
        "-filter_complex",
        "[0:a]volume=0.6[orig];[1:a]volume=1.0[vo];[orig][vo]amix=inputs=2:duration=first[aout]",
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac",
        out_path
    ], check=True, capture_output=True)


def burn_subtitles(video_path: str, segments: list, clip_start: float, clip_end: float, out_path: str, tmp_dir: str):
    """Generate an SRT file for the clip and burn subtitles into the video."""
    # Filter segments that fall within clip range
    clip_segments = [
        s for s in segments
        if s["end"] > clip_start and s["start"] < clip_end
    ]

    # Write SRT file
    srt_path = os.path.join(tmp_dir, "subtitles.srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        for idx, seg in enumerate(clip_segments, 1):
            # Offset timestamps relative to clip start
            start = max(0, seg["start"] - clip_start)
            end = min(clip_end - clip_start, seg["end"] - clip_start)
            text = seg["text"].strip()

            def fmt_time(t):
                h = int(t // 3600)
                m = int((t % 3600) // 60)
                s = int(t % 60)
                ms = int((t % 1) * 1000)
                return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

            f.write(f"{idx}\n{fmt_time(start)} --> {fmt_time(end)}\n{text}\n\n")

    # Burn subtitles with ffmpeg
    # Use a clean white font with dark outline for readability
    subtitle_filter = (
        f"subtitles='{srt_path}':force_style='"
        "FontName=Arial,FontSize=18,PrimaryColour=&Hffffff,OutlineColour=&H000000,"
        "BorderStyle=1,Outline=2,Shadow=0,Alignment=2'"
    )

    subprocess.run([
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", subtitle_filter,
        "-c:a", "copy",
        out_path
    ], check=True, capture_output=True)


def crop_9_16(video_path: str, out_path: str):
    """Crop and scale video to 1080x1920 (9:16) for TikTok/Reels/Shorts."""
    # Crop to 9:16 ratio from center, then scale to 1080x1920
    subprocess.run([
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", "crop='min(iw,ih*9/16)':'min(ih,iw*16/9)',scale=1080:1920",
        "-c:a", "copy",
        "-c:v", "libx264",
        "-preset", "fast",
        out_path
    ], check=True, capture_output=True)


def suggest_trending_audio(clip: dict) -> str:
    """Use Claude to suggest trending TikTok audio for the clip."""
    client = Anthropic()
    prompt = f"""You are a TikTok growth expert. Based on this clip, suggest 5 trending TikTok sounds/audio that would boost its reach.

Clip title: {clip['title']}
Clip vibe/hook: {clip['hook']}
Viral score: {clip['viral_score']}/100

For each suggestion provide:
- The audio/song name and artist (or sound name if it's a TikTok original sound)
- Why it fits this clip
- How to find it (search term to use in TikTok's sound library)

Also include 2-3 general tips for using audio to boost this specific clip's performance.

Be specific and practical. Focus on sounds that are actually trending right now on TikTok."""

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()



    duration = end - start
    subprocess.run(
        ["ffmpeg", "-y", "-ss", str(start), "-i", source,
         "-t", str(duration), "-c:v", "libx264", "-c:a", "aac",
         "-preset", "fast", out_path],
        check=True, capture_output=True
    )


# ── Main logic ─────────────────────────────────────────────────────────────────
if run_btn:
    if not youtube_url:
        st.error("Please paste a YouTube URL first.")
        st.stop()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.error("Add your Anthropic API key in Settings above.")
        st.stop()

    issues = check_deps(need_voiceover=enable_voiceover)
    if issues:
        st.error("Missing dependencies:")
        for i in issues:
            st.markdown(f"- {i}")
        st.stop()

    max_sec = int(clip_length.split()[0])
    output_dir = Path("clipforge_output")
    output_dir.mkdir(exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:

        # Step 1 – Download
        with st.status("📥  Downloading video...", expanded=True) as status:
            st.write("Fetching from YouTube...")
            try:
                video_path = download_video(youtube_url, tmpdir)
                st.write(f"✅ Got it: `{Path(video_path).name}`")
            except Exception as e:
                status.update(label="Download failed", state="error")
                st.error(f"Could not download video: {e}")
                st.stop()
            status.update(label="✅ Video downloaded", state="complete")

        # Step 2 – Transcribe
        with st.status("🎙️  Transcribing audio...", expanded=True) as status:
            st.write("Running Whisper (this takes ~1 min for a 10-min video)...")
            try:
                result = transcribe(video_path)
                segments = result.get("segments", [])
                st.write(f"✅ Transcribed {len(segments)} segments")
            except Exception as e:
                status.update(label="Transcription failed", state="error")
                st.error(f"Transcription error: {e}")
                st.stop()
            status.update(label="✅ Transcription complete", state="complete")

        # Step 3 – AI analysis
        with st.status("🧠  Claude is finding viral moments...", expanded=True) as status:
            st.write("Analyzing for maximum virality...")
            try:
                clips = pick_clips_with_claude(segments, num_clips, max_sec, vibe)
                st.write(f"✅ Found {len(clips)} clip(s)")
            except Exception as e:
                status.update(label="AI analysis failed", state="error")
                st.error(f"Claude error: {e}")
                st.stop()
            status.update(label="✅ Viral moments identified", state="complete")

        # Step 4 – Cut + enhance clips
        with st.status("✂️  Cutting and enhancing your clips...", expanded=True) as status:
            cut_paths = []
            for clip in clips:
                n = clip['clip_number']
                base_name = f"clip_{n}_{int(time.time())}"
                current_path = os.path.join(tmpdir, f"{base_name}_raw.mp4")

                st.write(f"✂️ Cutting clip {n}: {clip['start_time']}s → {clip['end_time']}s")
                try:
                    cut_clip(video_path, clip["start_time"], clip["end_time"], current_path)
                    st.write(f"✅ Clip {n} cut")
                except Exception as e:
                    st.warning(f"Could not cut clip {n}: {e}")
                    continue

                # 16:9 Crop
                if enable_crop:
                    st.write(f"📐 Cropping clip {n} to 16:9...")
                    cropped_path = os.path.join(tmpdir, f"{base_name}_cropped.mp4")
                    try:
                        crop_9_16(current_path, cropped_path)
                        current_path = cropped_path
                        st.write(f"✅ Clip {n} cropped to 9:16")
                    except Exception as e:
                        st.warning(f"Could not crop clip {n}: {e}")

                # Subtitles
                if enable_subtitles:
                    st.write(f"💬 Burning subtitles into clip {n}...")
                    subbed_path = os.path.join(tmpdir, f"{base_name}_subbed.mp4")
                    try:
                        burn_subtitles(current_path, segments, clip["start_time"], clip["end_time"], subbed_path, tmpdir)
                        current_path = subbed_path
                        st.write(f"✅ Subtitles burned into clip {n}")
                    except Exception as e:
                        st.warning(f"Could not burn subtitles for clip {n}: {e}")

                # AI Voiceover
                if enable_voiceover:
                    st.write(f"🎙️ Generating AI voiceover for clip {n}...")
                    try:
                        script = generate_voiceover_script(clip, voiceover_style)
                        st.write(f"📝 Voiceover: *\"{script}\"*")
                        vo_audio = os.path.join(tmpdir, f"{base_name}_vo.mp3")
                        synthesize_voiceover(script, vo_audio)
                        voiced_path = os.path.join(tmpdir, f"{base_name}_voiced.mp4")
                        mix_voiceover(current_path, vo_audio, voiced_path)
                        current_path = voiced_path
                        st.write(f"✅ Voiceover mixed into clip {n}")
                    except Exception as e:
                        st.warning(f"Could not add voiceover to clip {n}: {e}")

                # Copy final clip to output folder
                final_name = f"viral_clip_{n}_{int(time.time())}.mp4"
                final_path = str(output_dir / final_name)
                import shutil
                shutil.copy2(current_path, final_path)
                cut_paths.append(final_path)
                st.write(f"✅ Clip {n} ready")

            status.update(label="✅ All clips ready!", state="complete")

    # ── Results ────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔥 Your Clips Are Ready")

    for i, clip in enumerate(clips):
        st.markdown(f"""
        <div class="clip-card">
            <div class="clip-number">0{clip['clip_number']}</div>
            <div class="clip-title">{clip['title']}</div>
            <div class="clip-meta">⏱ {clip['start_time']:.0f}s – {clip['end_time']:.0f}s &nbsp;|&nbsp; {clip['end_time']-clip['start_time']:.0f}s long</div>
            <div class="clip-hook">{clip['hook']}</div>
            <div class="viral-score">🔥 Viral Score: {clip['viral_score']}/100</div>
        </div>
        """, unsafe_allow_html=True)

        if i < len(cut_paths):
            path = cut_paths[i]
            if os.path.exists(path):
                st.video(path)
                with open(path, "rb") as f:
                    st.download_button(
                        f"⬇️  Download Clip {clip['clip_number']}",
                        f,
                        file_name=f"viral_clip_{clip['clip_number']}.mp4",
                        mime="video/mp4",
                        key=f"dl_{i}"
                    )

        with st.expander("📋 Suggested Caption"):
            st.code(clip.get("caption", ""), language=None)

        with st.expander("🎵 Trending Audio Suggestions"):
            if st.button(f"Get Audio Ideas for Clip {clip['clip_number']}", key=f"audio_{i}"):
                with st.spinner("Claude is finding the best sounds for your clip..."):
                    try:
                        suggestions = suggest_trending_audio(clip)
                        st.markdown(suggestions)
                    except Exception as e:
                        st.error(f"Could not get audio suggestions: {e}")

        # Google Drive upload
        if i < len(cut_paths) and CREDENTIALS_FILE.exists():
            if st.button(f"☁️ Upload Clip {clip['clip_number']} to Google Drive", key=f"gdrive_{i}"):
                with st.spinner("Uploading to Google Drive..."):
                    try:
                        link = upload_to_drive(cut_paths[i])
                        st.success(f"✅ Uploaded! [Open in Google Drive]({link})")
                        st.info("💡 Open Google Drive on your phone to find and post the clip to TikTok!")
                    except Exception as e:
                        st.error(f"Upload failed: {e}")

    st.success(f"✅ Done! Clips saved to `clipforge_output/` folder.")
