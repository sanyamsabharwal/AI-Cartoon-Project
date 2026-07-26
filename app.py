import io
import base64
import streamlit as st
import streamlit.components.v1 as components
import os
import time
import requests as http_requests
import json
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image

def render_image_actions(pil_img, label_name, key_prefix):
    """Render Download and Clipboard Copy buttons for an image asset."""
    try:
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        img_bytes = buf.getvalue()
        b64_str = base64.b64encode(img_bytes).decode("utf-8")

        col_dl, col_cp = st.columns([1, 1])
        with col_dl:
            st.download_button(
                label="⬇️ Download Image",
                data=img_bytes,
                file_name=f"{key_prefix}.png",
                mime="image/png",
                key=f"dl_{key_prefix}",
                use_container_width=True
            )
        
        with col_cp:
            components.html(f"""
            <style>
                body {{ margin: 0; padding: 0; background: transparent; overflow: hidden; }}
            </style>
            <button id="cpBtn_{key_prefix}" style="
                display: block;
                width: 100%;
                padding: 9px 8px;
                margin: 0;
                background: linear-gradient(135deg, #10b981, #059669);
                color: #ffffff;
                font-weight: 700;
                font-size: 0.85rem;
                font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
                border: none;
                border-radius: 10px;
                cursor: pointer;
                box-shadow: 0 4px 12px rgba(16, 185, 129, 0.35);
                transition: all 0.2s ease;
                white-space: nowrap;
                text-align: center;
            ">📋 Copy Image to Clipboard</button>
            <script>
            document.getElementById('cpBtn_{key_prefix}').addEventListener('click', async function() {{
                try {{
                    const b64 = '{b64_str}';
                    const binStr = atob(b64);
                    const len = binStr.length;
                    const bytes = new Uint8Array(len);
                    for (let i = 0; i < len; i++) {{
                        bytes[i] = binStr.charCodeAt(i);
                    }}
                    const blob = new Blob([bytes], {{ type: 'image/png' }});
                    await navigator.clipboard.write([
                        new ClipboardItem({{ 'image/png': blob }})
                    ]);
                    var btn = document.getElementById('cpBtn_{key_prefix}');
                    btn.innerText = '✅ Image Copied!';
                    btn.style.background = 'linear-gradient(135deg, #3b82f6, #1d4ed8)';
                    setTimeout(function() {{
                        btn.innerText = '📋 Copy Image to Clipboard';
                        btn.style.background = 'linear-gradient(135deg, #10b981, #059669)';
                    }}, 2200);
                }} catch (err) {{
                    alert('Clipboard access blocked by browser. Please use the Download Image button next to it!');
                }}
            }});
            </script>
            """, height=58)
    except Exception:
        pass

# Page Config
st.set_page_config(
    page_title="AI Character Video Studio | Veo & Gemini",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Load environment variables — supports both local .env and Streamlit Cloud secrets
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY", "")
openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")

# Override with Streamlit Cloud secrets if available (for cloud deployment)
try:
    if not gemini_api_key:
        gemini_api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not openrouter_api_key:
        openrouter_api_key = st.secrets.get("OPENROUTER_API_KEY", "")
except Exception:
    pass  # Running locally without secrets.toml — that's fine

if not gemini_api_key and not openrouter_api_key:
    st.error("⚠️ Please add GEMINI_API_KEY or OPENROUTER_API_KEY to the .env file!")
    st.stop()

# Initialize Gemini Client (for video generation)
@st.cache_resource(show_spinner=False)
def get_gemini_client(key):
    if key:
        return genai.Client(api_key=key)
    return None

gemini_client = get_gemini_client(gemini_api_key)

# OpenRouter Config
OPENROUTER_BASE = "https://openrouter.ai/api/v1"
OPENROUTER_HEADERS = {
    "Authorization": f"Bearer {openrouter_api_key}",
    "Content-Type": "application/json",
    "HTTP-Referer": "http://localhost:8501",
    "X-Title": "AI Character Video Studio",
}

# Ensure output directory exists
OUTPUT_DIR = Path("generated_videos")
OUTPUT_DIR.mkdir(exist_ok=True)

# Custom CSS for Premium Glassmorphism SaaS UI
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    /* Hide Sidebar Completely */
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        display: none !important;
        width: 0 !important;
    }
    
    /* Hide all tooltip icons (?) */
    [data-testid="stTooltipIcon"], button[aria-label*="help"], .stTooltipIcon {
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        height: 0 !important;
    }
    
    .stApp {
        background: radial-gradient(circle at 50% 0%, #1e1b4b 0%, #0f172a 50%, #090d16 100%);
        color: #f8fafc;
    }
    
    .block-container {
        padding-top: 1.8rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }
    
    .hero-container {
        text-align: center;
        padding: 2rem 1.5rem;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 20px;
        backdrop-filter: blur(16px);
        margin-bottom: 1.5rem;
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.35);
    }
    
    .badge-tag {
        display: inline-block;
        padding: 5px 14px;
        background: linear-gradient(90deg, rgba(99, 102, 241, 0.3), rgba(168, 85, 247, 0.3));
        border: 1px solid rgba(168, 85, 247, 0.5);
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 700;
        color: #e9d5ff;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        margin-bottom: 10px;
    }
    
    .hero-title {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #ffffff 0%, #e2e8f0 50%, #a5b4fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.4rem;
        letter-spacing: -0.8px;
    }
    
    .hero-subtitle {
        color: #cbd5e1;
        font-size: 1.05rem;
        max-width: 650px;
        margin: 0 auto;
        font-weight: 400;
        line-height: 1.5;
    }
    
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(15, 23, 42, 0.7) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 18px !important;
        padding: 1.25rem !important;
        backdrop-filter: blur(16px) !important;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.25) !important;
    }
    
    .section-header {
        font-size: 1.15rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 0.8rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    label, p, span {
        color: #f1f5f9;
    }
    
    .stWidgetLabel p {
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        color: #f8fafc !important;
    }
    
    .stTextArea textarea, .stTextInput input, div[data-baseweb="select"] > div {
        background: rgba(30, 41, 59, 0.85) !important;
        border: 1px solid rgba(255, 255, 255, 0.18) !important;
        border-radius: 12px !important;
        color: #ffffff !important;
        font-size: 0.95rem !important;
    }

    div[data-baseweb="select"] span, div[data-baseweb="select"] div {
        color: #ffffff !important;
    }
    
    div[data-baseweb="popover"], 
    div[data-baseweb="menu"], 
    ul[role="listbox"], 
    [data-baseweb="popover"] > div {
        background-color: #1e293b !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 12px !important;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5) !important;
    }

    div[data-baseweb="popover"] li, 
    div[data-baseweb="menu"] li, 
    ul[role="listbox"] li, 
    div[role="option"],
    div[role="option"] * {
        background-color: #1e293b !important;
        color: #f8fafc !important;
        font-size: 0.95rem !important;
        font-weight: 500 !important;
    }

    div[data-baseweb="popover"] li:hover, 
    div[data-baseweb="menu"] li:hover, 
    ul[role="listbox"] li:hover, 
    div[role="option"]:hover,
    div[role="option"]:hover *,
    div[role="option"][aria-selected="true"],
    div[role="option"][aria-selected="true"] * {
        background-color: #334155 !important;
        color: #c084fc !important;
        cursor: pointer !important;
    }
    
    div[role="radiogroup"] {
        background: rgba(30, 41, 59, 0.6);
        padding: 10px 14px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    div[role="radiogroup"] label p {
        color: #e2e8f0 !important;
        font-size: 0.92rem !important;
        font-weight: 500 !important;
    }
    
    [data-testid="stFileUploader"] {
        background: rgba(30, 41, 59, 0.7) !important;
        border: 2px dashed rgba(168, 85, 247, 0.6) !important;
        border-radius: 16px !important;
        padding: 12px !important;
    }

    [data-testid="stFileUploaderDropzone"] {
        background: rgba(15, 23, 42, 0.8) !important;
        border: 1px dashed rgba(168, 85, 247, 0.5) !important;
        border-radius: 12px !important;
    }

    [data-testid="stFileUploader"] section button, 
    [data-testid="stFileUploader"] button, 
    [data-testid="stBaseButton-secondary"] {
        background: linear-gradient(135deg, #a855f7 0%, #6366f1 100%) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.65rem 1.4rem !important;
        box-shadow: 0 4px 15px rgba(168, 85, 247, 0.5) !important;
        font-size: 0.95rem !important;
        transition: all 0.2s ease-in-out !important;
    }
    
    [data-testid="stFileUploader"] section button:hover, 
    [data-testid="stFileUploader"] button:hover {
        transform: scale(1.04) !important;
        box-shadow: 0 6px 22px rgba(168, 85, 247, 0.75) !important;
    }

    [data-testid="stFileUploader"] small, 
    [data-testid="stFileUploader"] p, 
    [data-testid="stFileUploaderDropzoneInstructions"] div, 
    [data-testid="stFileUploaderDropzoneInstructions"] span {
        color: #cbd5e1 !important;
        font-weight: 500 !important;
    }
    
    div.stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #d946ef 100%) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 1.1rem !important;
        padding: 0.85rem 1.5rem !important;
        border-radius: 14px !important;
        border: none !important;
        box-shadow: 0 8px 25px rgba(139, 92, 246, 0.4) !important;
        transition: all 0.3s ease !important;
        cursor: pointer !important;
        letter-spacing: 0.3px;
        margin-top: 0.5rem;
    }
    
    div.stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 12px 35px rgba(139, 92, 246, 0.6) !important;
    }
    
    .result-box {
        background: linear-gradient(180deg, rgba(30, 27, 75, 0.6) 0%, rgba(15, 23, 42, 0.9) 100%);
        border: 1px solid rgba(129, 140, 248, 0.4);
        border-radius: 18px;
        padding: 1.5rem;
        margin-top: 1rem;
        box-shadow: 0 12px 30px rgba(0, 0, 0, 0.4);
    }
    
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 5px 12px;
        background: rgba(16, 185, 129, 0.2);
        border: 1px solid rgba(16, 185, 129, 0.5);
        border-radius: 10px;
        color: #34d399;
        font-weight: 700;
        font-size: 0.85rem;
    }
    
    .quota-warning-box {
        background: rgba(239, 68, 68, 0.12);
        border: 1px solid rgba(239, 68, 68, 0.4);
        border-radius: 14px;
        padding: 1.2rem;
        margin-top: 1rem;
        color: #fca5a5;
    }
    
    .video-result-card {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(59, 130, 246, 0.15));
        border: 1px solid rgba(52, 211, 153, 0.4);
        border-radius: 18px;
        padding: 1.5rem;
        margin-top: 1rem;
        box-shadow: 0 12px 30px rgba(0, 0, 0, 0.35);
    }

    .progress-stage {
        background: rgba(99, 102, 241, 0.12);
        border: 1px solid rgba(99, 102, 241, 0.35);
        border-radius: 14px;
        padding: 1rem 1.25rem;
        margin: 0.5rem 0;
        color: #c7d2fe;
        font-size: 0.95rem;
    }

    .engine-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 8px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }

    .engine-openrouter {
        background: rgba(16, 185, 129, 0.2);
        border: 1px solid rgba(16, 185, 129, 0.5);
        color: #34d399;
    }

    .engine-gemini {
        background: rgba(59, 130, 246, 0.2);
        border: 1px solid rgba(59, 130, 246, 0.5);
        color: #60a5fa;
    }

    video {
        border-radius: 14px !important;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.5) !important;
    }
</style>
""", unsafe_allow_html=True)


# ─── TEXT GENERATION via OpenRouter (FREE) ───
def generate_script_openrouter(character, video_type, custom_description, audio_language):
    """Use OpenRouter free models (no rate limits) for script generation."""
    prompt = f"""You are an elite AI Video Director and Content Creator.
Generate a high-converting 8-second video concept, precise camera prompt, and dialogue script.

### Parameters:
- **Character**: {character}
- **Video Type / Purpose**: {video_type}
- **Audio/Dialogue Language**: {audio_language}
- **Detailed Scene Description & Requirements**: {custom_description if custom_description.strip() else 'Create a fun, high-energy scene featuring the character.'}

### Output Requirements (use the specified language: {audio_language}):
1. **🎬 Visual Scene & Camera Prompt** (Highly detailed for AI Video generator Veo 3.1 - action, camera angles, lighting, background).
2. **🗣️ Script & Dialogue** (Engaging dialogue or narration in {audio_language} with clear emotional cues).
3. **🎵 Audio & SFX Notes** (Background music vibe, sound effects, voice tone. All voiceover in {audio_language}).
"""
    
    # Try multiple free models in order of quality
    free_models = [
        "google/gemma-4-31b-it:free",
        "nvidia/nemotron-3-ultra-550b-a55b:free",
        "nvidia/nemotron-3-super-120b-a12b:free",
        "google/gemma-4-26b-a4b-it:free",
        "openai/gpt-oss-20b:free",
    ]
    
    for model in free_models:
        try:
            resp = http_requests.post(
                f"{OPENROUTER_BASE}/chat/completions",
                headers=OPENROUTER_HEADERS,
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1500,
                    "temperature": 0.8,
                },
                timeout=60
            )
            
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return content, model, False
        except Exception:
            continue
    
    return None, None, True


def generate_fallback_script(character, video_type, custom_description, audio_language):
    """Local fallback if all APIs fail."""
    desc = custom_description.strip() if custom_description.strip() else f"A fun, high-energy scene featuring {character}."
    
    dialogue_map = {
        "Hindi": f'**{character}:** "अरे दोस्तों! तैयार हो जाओ, आज कुछ ज़बरदस्त होने वाला है!"\n**Narration:** "{"इस धमाकेदार ऑफर को अभी आज़माएं!" if "Promotion" in video_type else "देखिए आगे क्या नया कारनामा होता है!"}"',
        "Punjabi": f'**{character}:** "ਯਾਰੋ! ਤਿਆਰ ਹੋ ਜਾਓ, ਅੱਜ ਕੁੱਝ ਧਮਾਕੇਦਾਰ ਹੋਣ ਵਾਲਾ ਏ!"\n**Narration:** "{"ਇਹ ਸ਼ਾਨਦਾਰ ਆਫ਼ਰ ਹੁਣੇ ਅਜ਼ਮਾਓ!" if "Promotion" in video_type else "ਦੇਖੋ ਅੱਗੇ ਕੀ ਨਵਾਂ ਕਾਰਨਾਮਾ ਹੁੰਦਾ ਏ!"}"',
        "English": f'**{character}:** "Hey everyone! Get ready, something amazing is about to happen!"\n**Narration:** "{"Try this incredible offer now!" if "Promotion" in video_type else "Stay tuned to see what happens next!"}"',
    }
    dialogue = dialogue_map.get(audio_language, dialogue_map["Hindi"])
    
    return f"""### 🎬 Visual Scene & Camera Prompt (Creative Studio Engine)
**Scene Setting:** Dynamic medium tracking shot of {character}.
**Visual Details:** {desc}
**Camera & Lighting:** Vibrant 3D animated style, smooth 60fps pan, volumetric lighting, crisp background details.

---

### 🗣️ Script & Dialogue ({audio_language})
{dialogue}

---

### 🎵 Audio & SFX Notes
- **Audio Language:** {audio_language}
- **Background Music:** Energetic cartoon/commercial synth track.
- **Sound Effects:** Whoosh camera transition, cheerful chime effect.
"""


def generate_video_concept(character, video_type, custom_description, pil_images, audio_language):
    """
    Smart script generation:
    1. If images are provided → Use Gemini (multimodal)
    2. Otherwise → Use OpenRouter free models (no rate limits)
    3. Fallback → Local creative engine
    """
    # If images are uploaded, must use Gemini for multimodal
    if pil_images and len(pil_images) > 0 and gemini_client:
        prompt = f"""You are an elite AI Video Director and Content Creator.
Generate a high-converting 8-second video concept, precise camera prompt, and dialogue script.

### Parameters:
- **Character**: {character}
- **Video Type / Purpose**: {video_type}
- **Audio/Dialogue Language**: {audio_language}
- **Detailed Scene Description & Requirements**: {custom_description if custom_description.strip() else 'Create a fun, high-energy scene featuring the character.'}

Note: Reference image assets are provided. Incorporate visual elements from the provided images into the scene design, character details, and visual styling.

### Output Requirements (use the specified language: {audio_language}):
1. **🎬 Visual Scene & Camera Prompt** (Highly detailed for AI Video generator Veo 3.1 - action, camera angles, lighting, background).
2. **🗣️ Script & Dialogue** (Engaging dialogue or narration in {audio_language} with clear emotional cues).
3. **🎵 Audio & SFX Notes** (Background music vibe, sound effects, voice tone. All voiceover in {audio_language}).
"""
        try:
            contents = [prompt] + pil_images
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents
            )
            return response.text, "gemini-2.5-flash", False
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                pass
            else:
                pass
    
    # Use OpenRouter free models (no rate limits!)
    if openrouter_api_key:
        content, model_used, failed = generate_script_openrouter(character, video_type, custom_description, audio_language)
        if not failed and content:
            return content, model_used, False
    
    # Final fallback
    return generate_fallback_script(character, video_type, custom_description, audio_language), "local-fallback", True


# ─── VIDEO GENERATION via Gemini Veo (with automatic polling) ───
def generate_and_poll_video(video_prompt, progress_placeholder):
    """
    Fully automatic video generation:
    1. Submit video generation request to Veo 3.1
    2. Poll the operation until done
    3. Download and save the video locally
    4. Return the local file path for st.video()
    """
    if not gemini_client:
        return {
            "status": "error",
            "message": "Gemini API key not configured. Video generation requires Gemini Veo API."
        }

    MAX_RETRIES = 3
    POLL_INTERVAL = 20  # seconds between polls
    MAX_POLL_TIME = 600  # 10 minute max wait

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            progress_placeholder.markdown(f"""
            <div class="progress-stage">
                🚀 <strong>Step 1/3 — Submitting to Veo 3.1 Fast Generate</strong>
                {"(Retry " + str(attempt) + "/" + str(MAX_RETRIES) + ")" if attempt > 1 else ""}<br>
                <span style="color: #94a3b8; font-size: 0.85rem;">Sending your prompt to Google's video AI engine...</span>
            </div>
            """, unsafe_allow_html=True)

            operation = gemini_client.models.generate_videos(
                model="veo-3.1-fast-generate-preview",
                prompt=video_prompt,
                config=types.GenerateVideosConfig(
                    number_of_videos=1,
                    duration_seconds=8,
                    negative_prompt="blurry, distorted, low quality, artifacts, watermark",
                )
            )

            op_name = operation.name if operation.name else "veo-operation"

            # --- POLLING LOOP ---
            elapsed = 0
            poll_count = 0
            while not operation.done:
                poll_count += 1
                mins = elapsed // 60
                secs = elapsed % 60
                progress_placeholder.markdown(f"""
                <div class="progress-stage">
                    ⏳ <strong>Step 2/3 — Rendering Video</strong> (Poll #{poll_count})<br>
                    <span style="color: #94a3b8; font-size: 0.85rem;">
                        Elapsed: {mins}m {secs}s &nbsp;·&nbsp; Operation: <code>{op_name[:40]}</code><br>
                        Veo is generating frames and compositing your video...
                    </span>
                </div>
                """, unsafe_allow_html=True)

                time.sleep(POLL_INTERVAL)
                elapsed += POLL_INTERVAL

                if elapsed > MAX_POLL_TIME:
                    return {
                        "status": "timeout",
                        "message": f"Video generation timed out after {MAX_POLL_TIME // 60} minutes. Operation: {op_name}"
                    }

                operation = gemini_client.operations.get(operation)

            # --- OPERATION COMPLETE ---
            progress_placeholder.markdown("""
            <div class="progress-stage">
                📥 <strong>Step 3/3 — Downloading Video</strong><br>
                <span style="color: #94a3b8; font-size: 0.85rem;">Operation complete! Saving video to your local drive...</span>
            </div>
            """, unsafe_allow_html=True)

            if operation.error:
                return {
                    "status": "error",
                    "message": f"Veo returned an error: {operation.error}"
                }

            # Extract the generated video
            if operation.response and operation.response.generated_videos:
                generated_video = operation.response.generated_videos[0]
                video_obj = generated_video.video

                timestamp = int(time.time())
                video_filename = OUTPUT_DIR / f"video_{timestamp}.mp4"

                if video_obj.video_bytes:
                    video_filename.write_bytes(video_obj.video_bytes)
                elif video_obj.uri:
                    try:
                        gemini_client.files.download(file=video_obj)
                        if video_obj.video_bytes:
                            video_filename.write_bytes(video_obj.video_bytes)
                        else:
                            return {
                                "status": "error",
                                "message": f"Video generated but bytes unavailable. URI: {video_obj.uri}"
                            }
                    except Exception as dl_err:
                        return {
                            "status": "error",
                            "message": f"Video generated at URI: {video_obj.uri} but download failed: {dl_err}"
                        }
                else:
                    return {
                        "status": "error",
                        "message": "Video operation completed but no video data was returned."
                    }

                progress_placeholder.empty()
                return {
                    "status": "success",
                    "file_path": str(video_filename),
                    "message": f"Video saved to {video_filename}"
                }

            elif hasattr(operation, 'result') and operation.result:
                result = operation.result
                if hasattr(result, 'generated_videos') and result.generated_videos:
                    generated_video = result.generated_videos[0]
                    video_obj = generated_video.video
                    timestamp = int(time.time())
                    video_filename = OUTPUT_DIR / f"video_{timestamp}.mp4"
                    if video_obj.video_bytes:
                        video_filename.write_bytes(video_obj.video_bytes)
                        progress_placeholder.empty()
                        return {
                            "status": "success",
                            "file_path": str(video_filename),
                            "message": f"Video saved to {video_filename}"
                        }

            progress_placeholder.empty()
            return {
                "status": "error",
                "message": "Video generation completed but no video data found in the response."
            }

        except Exception as e:
            err_msg = str(e)
            if ("429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg) and attempt < MAX_RETRIES:
                wait_time = 60 * attempt  # Wait longer: 60s, 120s, 180s
                progress_placeholder.markdown(f"""
                <div class="progress-stage" style="border-color: rgba(251, 191, 36, 0.5); background: rgba(251, 191, 36, 0.08);">
                    ⏸️ <strong>Rate Limited — Auto-Retrying in {wait_time}s</strong> (Attempt {attempt}/{MAX_RETRIES})<br>
                    <span style="color: #fbbf24; font-size: 0.85rem;">
                        API quota hit. Waiting for quota to reset before next attempt...
                    </span>
                </div>
                """, unsafe_allow_html=True)
                time.sleep(wait_time)
                continue
            elif "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                progress_placeholder.empty()
                return {
                    "status": "quota_error",
                    "message": f"Veo API quota exhausted after {MAX_RETRIES} retries. Please wait a few minutes and try again."
                }
            else:
                progress_placeholder.empty()
                return {
                    "status": "error",
                    "message": f"Video generation failed: {err_msg[:300]}"
                }

    progress_placeholder.empty()
    return {"status": "error", "message": "Max retries exceeded."}


# ─── HERO HEADER ───
st.markdown("""
<div class="hero-container">
    <div class="badge-tag">⚡ Fully Automatic AI Video Pipeline</div>
    <div class="hero-title">AI Character Video Studio</div>
    <div class="hero-subtitle">Transform your ideas into character videos — powered by OpenRouter (free text AI) + Google Veo (video generation). Fully automated, zero manual steps.</div>
</div>
""", unsafe_allow_html=True)

# Main Studio Layout
col_left, col_right = st.columns([1.15, 0.85], gap="medium")

with col_left:
    with st.container(border=True):
        st.markdown('<div class="section-header">⚙️ 1. Video Specifications</div>', unsafe_allow_html=True)
        
        video_type = st.radio(
            "Select Video Style / Category:",
            ("Normal Video (Story / Comedy / Entertainment)", "Promotion Video (Ad / Marketing / Product Focus)")
        )
        
        # Main character selection
        character_choice = st.selectbox(
            "Choose Main Character:",
            (
                "Doraemon",
                "Motu Patlu",
                "Chacha Chaudhary",
                "Shaktimaan",
                "Ben 10",
                "Ninja Hattori",
                "Peppa Pig",
                "Pokémon",
                "Beyblade",
                "Chota Bheem",
                "✏️ Add My Own Character",
            )
        )
        
        # Character Asset Mapping
        CHARACTER_ASSETS = {
            "Doraemon": "assets/characters/doraemon.png",
            "Motu Patlu": "assets/characters/motu_patlu.png",
            "Chacha Chaudhary": "assets/characters/chacha_chaudhary.png",
            "Shaktimaan": "assets/characters/shaktimaan.png",
            "Ben 10": "assets/characters/ben_10.png",
            "Ninja Hattori": "assets/characters/ninja_hattori.png",
            "Peppa Pig": "assets/characters/peppa_pig.png",
            "Pokémon": "assets/characters/pokemon.png",
            "Beyblade": "assets/characters/beyblade.png",
            "Chota Bheem": "assets/characters/chota_bheem.png",
        }
        
        char_asset_path = None
        if character_choice == "✏️ Add My Own Character":
            custom_char_name = st.text_input(
                "Enter your animated character name:",
                placeholder="e.g. Tom & Jerry, Shinchan, Dragon Ball Z...",
                key="custom_char_input"
            )
            character = custom_char_name.strip() if custom_char_name.strip() else "Custom Character"
        else:
            character = character_choice
            if character in CHARACTER_ASSETS and os.path.exists(CHARACTER_ASSETS[character]):
                char_asset_path = CHARACTER_ASSETS[character]
        
        # Show Main Character Asset Preview if available
        if char_asset_path:
            st.markdown(f"**⭐ Main Character Reference Asset Loaded (`{character}`):**")
            try:
                char_img = Image.open(char_asset_path)
                st.image(char_img, caption=f"Main Character Asset: {character}", width=180)
                render_image_actions(char_img, character, f"char_{character.replace(' ', '_').lower()}")
            except Exception:
                pass
        
        audio_language = st.selectbox(
            "🔊 Audio / Dialogue Language:",
            ("Hindi", "Punjabi", "English")
        )

    with st.container(border=True):
        st.markdown('<div class="section-header">📝 2. Video Description & Storyline</div>', unsafe_allow_html=True)
        
        custom_description = st.text_area(
            "Describe your video concept in detail:",
            placeholder="e.g. Doraemon opens a futuristic gadget in a vibrant neon street market to help Nobita outsmart a giant robot. Add energetic Hindi comedy dialogue...",
            height=120
        )

    with st.container(border=True):
        st.markdown('<div class="section-header">📦 3. Product / Object to Promote (Optional Upload)</div>', unsafe_allow_html=True)
        
        uploaded_product_files = st.file_uploader(
            "Upload image(s) of the product, item, or object to feature in the video (e.g. shoes, beverage can, gadget, car):",
            type=["png", "jpg", "jpeg", "webp"],
            accept_multiple_files=True
        )
    
    generate_btn = st.button("✨ Generate AI Video Automatically", key="gen_btn")

with col_right:
    with st.container(border=True):
        st.markdown('<div class="section-header">👁️ Studio Live Inspector</div>', unsafe_allow_html=True)
        
        st.markdown(f"""
        - **Target Character**: `{character}` (Asset: `{'Loaded' if char_asset_path else 'None'}`)
        - **Video Category**: `{video_type.split('(')[0].strip()}`
        - **Audio Language**: `{audio_language}`
        - **Custom Prompt**: `{'Provided' if custom_description.strip() else 'Default'}`
        - **Product Uploads**: `{len(uploaded_product_files) if uploaded_product_files else 0} File(s)`
        - **Script Engine**: `{'OpenRouter (Free)' if openrouter_api_key else 'Gemini'}`
        - **Video Engine**: `Gemini Veo 3.1`
        """)
        
        # Combine PIL images for multimodal prompt (Character Asset + Product Uploads)
        pil_images = []
        
        # 1. Main character preset asset
        if char_asset_path:
            try:
                char_img = Image.open(char_asset_path)
                pil_images.append(char_img)
            except Exception:
                pass
        
        # 2. Uploaded product/object files preview
        if uploaded_product_files:
            st.markdown("##### 📦 Uploaded Product / Object Previews:")
            img_cols = st.columns(min(len(uploaded_product_files), 3))
            for idx, file in enumerate(uploaded_product_files):
                try:
                    img = Image.open(file)
                    pil_images.append(img)
                    with img_cols[idx % 3]:
                        st.image(img, caption=f"Product: {file.name[:12]}", width="stretch")
                        render_image_actions(img, file.name, f"prod_{idx}")
                except Exception:
                    st.warning(f"Could not load {file.name}")
        elif char_asset_path:
            st.info("💡 Main character reference image is loaded automatically from `assets/characters`. Upload product images in Section 3 if you are creating a promo/ad!")
        else:
            st.info("💡 Tip: Uploading product reference images helps the AI accurately incorporate your product into the scene!")

# ─── HANDLE VIDEO GENERATION — FULLY AUTOMATIC ───
if generate_btn:
    # ── PHASE 1: Generate Script ──
    with st.spinner("🤖 Generating script via OpenRouter (free, no rate limits)..."):
        script, model_used, is_fallback = generate_video_concept(character, video_type, custom_description, pil_images, audio_language)
    
    engine_label = "OpenRouter Free" if ":free" in (model_used or "") else ("Gemini" if "gemini" in (model_used or "") else "Local Fallback")
    engine_class = "engine-openrouter" if "openrouter" in engine_label.lower() or ":free" in (model_used or "") else "engine-gemini"
    
    if is_fallback:
        st.markdown("""
        <div class="quota-warning-box">
            <strong>⚠️ All AI APIs unavailable:</strong><br>
            Script generated via local Creative Engine fallback. Video generation will still proceed.
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="result-box">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
            <h3 style="margin: 0; color: #f8fafc;">🎬 Generated AI Video Script</h3>
            <span class="engine-badge {engine_class}">{engine_label}</span>
            <span style="color: #64748b; font-size: 0.8rem;">via {model_used or 'unknown'}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(script)

    # ── PHASE 2: Build combined easy-to-copy prompt for Google Flow ──
    desc_text = custom_description.strip() if custom_description.strip() else "high energy fun scene"
    
    combined_flow_prompt = f"""Character: {character}. 3D animated cinematic shot of {character}, {desc_text}. Smooth 60fps motion, vibrant lighting, volumetric atmosphere, detailed character features. Audio language: {audio_language}. Video type: {video_type.split('(')[0].strip()}. Duration: 8 seconds.

{script}""".strip()

    st.markdown("---")
    st.markdown("### 📋 Copy-Ready Prompt for Google Flow")
    st.markdown("Copy the full prompt below and paste it into **Google Flow Studio** to create your video manually:")
    st.code(combined_flow_prompt, language="text")
    
    # Copy button using components.html (st.markdown strips JS events)
    import streamlit.components.v1 as components
    import html as html_module
    
    safe_prompt = html_module.escape(combined_flow_prompt).replace("\n", "\\n").replace("'", "\\'")
    
    components.html(f"""
    <button id="copyBtn" style="
        display: block;
        width: 100%;
        padding: 14px 20px;
        margin: 4px 0 0 0;
        background: linear-gradient(135deg, #6366f1, #8b5cf6, #d946ef);
        color: #ffffff;
        font-weight: 700;
        font-size: 1rem;
        font-family: 'Plus Jakarta Sans', sans-serif;
        border: none;
        border-radius: 12px;
        cursor: pointer;
        box-shadow: 0 6px 20px rgba(139, 92, 246, 0.4);
        transition: all 0.25s ease;
        letter-spacing: 0.3px;
    ">📋 Copy Full Prompt to Clipboard</button>
    <script>
    document.getElementById('copyBtn').addEventListener('click', function() {{
        var text = '{safe_prompt}';
        navigator.clipboard.writeText(text).then(function() {{
            var btn = document.getElementById('copyBtn');
            btn.innerText = '✅ Copied to Clipboard!';
            btn.style.background = 'linear-gradient(135deg, #10b981, #059669)';
            setTimeout(function() {{
                btn.innerText = '📋 Copy Full Prompt to Clipboard';
                btn.style.background = 'linear-gradient(135deg, #6366f1, #8b5cf6, #d946ef)';
            }}, 2500);
        }});
    }});
    document.getElementById('copyBtn').addEventListener('mouseenter', function() {{
        this.style.transform = 'translateY(-2px)';
        this.style.boxShadow = '0 10px 30px rgba(139, 92, 246, 0.6)';
    }});
    document.getElementById('copyBtn').addEventListener('mouseleave', function() {{
        this.style.transform = 'translateY(0)';
        this.style.boxShadow = '0 6px 20px rgba(139, 92, 246, 0.4)';
    }});
    </script>
    """, height=60)

    st.success("✅ Script & Copy-Ready Prompt generated! Click the button above to copy your prompt and paste into Google Flow Studio.")

    # =========================================================================
    # ── PHASE 3: Automatic Video Generation & Veo Polling (COMMENTED FOR FUTURE USE) ──
    # Uncomment the block below to re-enable automatic video generation & polling:
    # =========================================================================
    # st.markdown("---")
    # st.markdown("""
    # <div class="result-box" style="border-color: rgba(52, 211, 153, 0.5); margin-top: 0.8rem;">
    #     <div class="status-pill">🎥 Automatic Video Generation Started</div>
    #     <span class="engine-badge engine-gemini" style="margin-left: 8px;">Gemini Veo 3.1</span>
    #     <p style="color: #cbd5e1; font-size: 0.92rem; margin-top: 8px; margin-bottom: 0;">
    #         Submitting → Polling → Downloading → Playing. <strong>No manual steps required.</strong>
    #     </p>
    # </div>
    # """, unsafe_allow_html=True)
    #
    # progress_area = st.empty()
    # veo_prompt = f"3D animated cinematic shot of {character}, {desc_text}, smooth 60fps motion, vibrant lighting, volumetric atmosphere, detailed character features, 8 seconds."
    # result = generate_and_poll_video(veo_prompt, progress_area)
    #
    # if result["status"] == "success":
    #     video_path = result["file_path"]
    #     st.markdown(f"""
    #     <div class="video-result-card">
    #         <div class="status-pill">✅ Video Generated Successfully!</div>
    #         <p style="color: #d1fae5; font-size: 0.95rem; margin-top: 10px; margin-bottom: 0;">
    #             Your AI video has been rendered and saved automatically.<br>
    #             <code style="color: #6ee7b7;">{video_path}</code>
    #         </p>
    #     </div>
    #     """, unsafe_allow_html=True)
    #     st.video(video_path)
    #     with open(video_path, "rb") as vf:
    #         video_bytes = vf.read()
    #     st.download_button(
    #         label="⬇️ Download Video (MP4)",
    #         data=video_bytes,
    #         file_name=os.path.basename(video_path),
    #         mime="video/mp4"
    #     )
    # elif result["status"] == "quota_error":
    #     st.markdown(f"""
    #     <div class="quota-warning-box">
    #         <div class="status-pill" style="background: rgba(239, 68, 68, 0.2); border-color: rgba(239, 68, 68, 0.5); color: #fca5a5;">
    #             ⚠️ Veo API Quota Exhausted
    #         </div>
    #         <h4 style="margin-top: 10px; color: #fecdd3;">Video API Rate Limit Reached</h4>
    #         <p style="color: #fca5a5; font-size: 0.92rem; margin-bottom: 0;">
    #             {result['message']}<br><br>
    #             <strong>What to do:</strong> Copy the prompt above and paste it into 
    #             <a href="https://labs.google/fx/tools/flow" target="_blank" style="color: #93c5fd;">Google Flow Studio</a>
    #             to generate the video manually with your 50 free daily credits.
    #         </p>
    #     </div>
    #     """, unsafe_allow_html=True)
    # elif result["status"] == "timeout":
    #     st.markdown(f"""
    #     <div class="quota-warning-box" style="border-color: rgba(251, 191, 36, 0.4); background: rgba(251, 191, 36, 0.08);">
    #         <div class="status-pill" style="background: rgba(251, 191, 36, 0.2); border-color: rgba(251, 191, 36, 0.5); color: #fbbf24;">
    #             ⏰ Generation Timed Out
    #         </div>
    #         <p style="color: #fde68a; font-size: 0.92rem; margin-top: 10px; margin-bottom: 0;">
    #             {result['message']}<br>
    #             The video may still be processing. Try again or copy the prompt above into Google Flow.
    #         </p>
    #     </div>
    #     """, unsafe_allow_html=True)
    # else:
    #     st.markdown(f"""
    #     <div class="quota-warning-box">
    #         <div class="status-pill" style="background: rgba(239, 68, 68, 0.2); border-color: rgba(239, 68, 68, 0.5); color: #fca5a5;">
    #             ❌ Generation Error
    #         </div>
    #         <p style="color: #fca5a5; font-size: 0.92rem; margin-top: 10px; margin-bottom: 0;">
    #             {result['message']}<br><br>
    #             You can still copy the prompt above and use <a href="https://labs.google/fx/tools/flow" target="_blank" style="color: #93c5fd;">Google Flow Studio</a> manually.
    #         </p>
    #     </div>
    #     """, unsafe_allow_html=True)
