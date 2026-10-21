import streamlit as st
import asyncio
import edge_tts
import subprocess
import os
import requests

st.set_page_config(page_title="Movie Recap Studio", layout="wide")
st.title("🎬 Movie Recap Auto-Generator (Myanmar)")

# --- 1. Sidebar: API Keys & Voice Settings ---
with st.sidebar:
    st.header("🔑 API & အသံ ရွေးချယ်မှု")
    tts_engine = st.selectbox("အသံစနစ် ရွေးပါ", ["Free Myanmar TTS (Edge)", "ElevenLabs API (Premium)"])
    
    api_key = ""
    if tts_engine == "ElevenLabs API (Premium)":
        api_key = st.text_input("ElevenLabs API Key ထည့်ပါ", type="password")
        voice_id = st.text_input("Voice ID ထည့်ပါ", value="21m00Tcm4TlvDq8ikWAM")
    else:
        voice_choice = st.selectbox("မြန်မာအသံ ရွေးပါ", [
            "ယောက်ျားလေးအသံ (Nyi Nyi)", 
            "မိန်းကလေးအသံ (Thiha)"
        ])
        voice_id = "my-MM-NyiNyiNeural" if "Nyi Nyi" in voice_choice else "my-MM-ThihaNeural"

    st.divider()
    st.header("🎨 စာတန်းထိုး ဖောင့်နှင့် ဒီဇိုင်း")
    font_choice = st.selectbox("ဖောင့် (Font) ရွေးပါ", ["Pyidaungsu", "Myanmar Square", "Gantgaw", "Masterpiece"])
    font_size = st.slider("စာလုံး အရွယ်အစား", 14, 40, 22)
    font_color = st.color_picker("စာလုံး အရောင်", "#FFFF00") # အဝါရောင် Default

# --- 2. Main Area: Video, Script & Blocker Settings ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("၁။ ဗီဒီယိုနှင့် ဇာတ်လမ်းထည့်ရန်")
    video_file = st.file_uploader("မူရင်း ဗီဒီယိုဖိုင် တင်ပါ (MP4)", type=["mp4", "mkv", "mov"])
    mute_original = st.checkbox("မူရင်းဗီဒီယို အသံဖျောက်မည် (Mute Original Audio)", value=True)
    script_text = st.text_area("မြန်မာ ဇာတ်လမ်းအကျဉ်း (Script) ထည့်ပါ...", height=200, placeholder="ဒီနေရာမှာ ဇာတ်လမ်းအကျဉ်း ရေးပါ...")

with col2:
    st.subheader("၂။ မူရင်းစာတန်းထိုးနှင့် Logo ဖုံးရန်")
    
    # Subtitle Blocker
    cover_old_sub = st.checkbox("မူရင်း စာတန်းထိုးကို ဘားတန်းဖြင့် ဖုံးမည်", value=True)
    if cover_old_sub:
        box_y = st.slider("ဖုံးမည့် ဘားတန်း အပေါ်/အောက် နေရာ (Y Position %)", 50, 95, 82)
        box_h = st.slider("ဖုံးမည့် ဘားတန်း အထူ (Height px)", 30, 150, 65)
        box_opacity = st.slider("ဘားတန်း အမည်းရောင် အပြင်း/အပျော့", 0.3, 1.0, 0.8)

    st.divider()
    
    # Logo Blocker
    cover_logo = st.selectbox("မူရင်း Logo ဖုံးမည့်ပုံစံ", ["မဖုံးပါ", "ကိုယ်ပိုင် Logo ဖြင့် အုပ်မည်", "အမည်းရောင်ကွက်ဖြင့် ဖုံးမည်"])
    logo_file = None
    if cover_logo != "မဖုံးပါ":
        logo_pos = st.selectbox("ဖုံးမည့် ထောင့်နေရာ", ["ညာဘက် အပေါ်ထောင့် (Top-Right)", "ဘယ်ဘက် အပေါ်ထောင့် (Top-Left)", "ညာဘက် အောက်ထောင့် (Bottom-Right)"])
        if cover_logo == "ကိုယ်ပိုင် Logo ဖြင့် အုပ်မည်":
            logo_file = st.file_uploader("ကိုယ်ပိုင် Logo ပုံတင်ပါ (PNG/JPG)", type=["png", "jpg"])

# --- 3. Helper Function: Generate Audio & Subtitle ---
async def generate_edge_tts(text, voice, audio_out, sub_out):
    communicate = edge_tts.Communicate(text, voice)
    submaker = edge_tts.SubMaker()
    with open(audio_out, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.create_sub((chunk["offset"], chunk["duration"]), chunk["text"])
    with open(sub_out, "w", encoding="utf-8") as sf:
        sf.write(submaker.generate_subs())

def hex_to_ass_color(hex_color):
    # Convert #RRGGBB to ASS format &H00BBGGRR
    h = hex_color.lstrip('#')
    return f"&H00{h[4:6]}{h[2:4]}{h[0:2]}"

# --- 4. Process Video Button ---
if st.button("🚀 Recap Video စတင်ထုတ်လုပ်မည်", use_container_width=True):
    if not video_file or not script_text:
        st.error("ကျေးဇူးပြု၍ ဗီဒီယိုဖိုင်နှင့် ဇာတ်လမ်းစာသား ပြည့်စုံစွာ ထည့်သွင်းပါ။")
    else:
        with st.spinner("အသံနှင့် စာတန်းထိုးများ ဖန်တီးနေပါသည်..."):
            # Save uploaded video
            with open("input.mp4", "wb") as f:
                f.write(video_file.read())

            # 1. Generate Voice & SRT
            if tts_engine == "Free Myanmar TTS (Edge)":
                asyncio.run(generate_edge_tts(script_text, voice_id, "voice.mp3", "sub.vtt"))
            else:
                # ElevenLabs API Call
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
                headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
                data = {"text": script_text, "model_id": "eleven_multilingual_v2"}
                response = requests.post(url, json=data, headers=headers)
                with open("voice.mp3", "wb") as f:
                    f.write(response.content)
                # Fallback simple subtitle if using ElevenLabs
                with open("sub.vtt", "w", encoding="utf-8") as sf:
                    sf.write("WEBVTT\n\n00:00:00.000 --> 00:05:00.000\n" + script_text)

        with st.spinner("ဗီဒီယို တည်းဖြတ်နေပါသည် (FFmpeg)..."):
            # Build FFmpeg Filter Complex
            vf_filters = []
            
            # Cover old subtitle with box
            if cover_old_sub:
                vf_filters.append(f"drawbox=x=0:y=ih*({box_y}/100):w=iw:h={box_h}:color=black@{box_opacity}:t=fill")
            
            # Cover Logo with black box if selected
            if cover_logo == "အမည်းရောင်ကွက်ဖြင့် ဖုံးမည်":
                if "Top-Right" in logo_pos:
                    vf_filters.append("drawbox=x=iw-160:y=20:w=140:h=60:color=black@0.9:t=fill")
                elif "Top-Left" in logo_pos:
                    vf_filters.append("drawbox=x=20:y=20:w=140:h=60:color=black@0.9:t=fill")
                else:
                    vf_filters.append("drawbox=x=iw-160:y=ih-80:w=140:h=60:color=black@0.9:t=fill")

            # Burn new Myanmar Subtitles
            ass_color = hex_to_ass_color(font_color)
            sub_style = f"FontName={font_choice},FontSize={font_size},PrimaryColour={ass_color},OutlineColour=&H00000000,BorderStyle=1,Outline=2,Alignment=2,MarginV=35"
            vf_filters.append(f"subtitles=sub.vtt:force_style='{sub_style}'")

            vf_string = ",".join(vf_filters)

            # Build FFmpeg Command
            cmd = ["ffmpeg", "-y", "-i", "input.mp4", "-i", "voice.mp3"]
            
            # Handle custom logo image overlay
            if cover_logo == "ကိုယ်ပိုင် Logo ဖြင့် အုပ်မည်" and logo_file:
                with open("logo.png", "wb") as lf:
                    lf.write(logo_file.read())
                cmd.extend(["-i", "logo.png"])
                pos_xy = "W-w-20:20" if "Top-Right" in logo_pos else ("20:20" if "Top-Left" in logo_pos else "W-w-20:H-h-20")
                filter_complex = f"[0:v]{vf_string}[bg];[2:v]scale=120:-1[lg];[bg][lg]overlay={pos_xy}[outv]"
                cmd.extend(["-filter_complex", filter_complex, "-map", "[outv]"])
            else:
                cmd.extend(["-vf", vf_string, "-map", "0:v:0"])

            # Audio Mapping (Mute original or Mix)
            if mute_original:
                cmd.extend(["-map", "1:a:0"])
            else:
                cmd.extend(["-filter_complex", "[0:a]volume=0.1[a0];[1:a]volume=1.0[a1];[a0][a1]amix=inputs=2:duration=first[outa]", "-map", "[outa]"])

            cmd.extend(["-c:v", "libx264", "-preset", "fast", "-c:a", "aac", "-shortest", "output.mp4"])
            
            subprocess.run(cmd)

        st.success("✅ Movie Recap ဗီဒီယို ထုတ်လုပ်ပြီးပါပြီ!")
        st.video("output.mp4")
        with open("output.mp4", "rb") as file:
            st.download_button("📥 ဗီဒီယို ဒေါင်းလုဒ်ဆွဲရန်", data=file, file_name="myanmar_recap.mp4", mime="video/mp4")
          
