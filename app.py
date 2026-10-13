
import os
import base64
import mimetypes
import tempfile

import gradio as gr
from dotenv import load_dotenv
from google import genai
from gtts import gTTS

# --------------------------------------------------
# 1. SETTINGS
# --------------------------------------------------

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError(
        "GEMINI_API_KEY পাওয়া যায়নি। "
        "app.py-এর পাশে .env ফাইলে API key দাও।"
    )

client = genai.Client(api_key=API_KEY)
MODEL_NAME = "gemini-3.8-flash"


# --------------------------------------------------
# 2. IMAGE HELPER
# --------------------------------------------------

def get_base64_image(image_path):
    if not os.path.exists(image_path):
        return ""

    try:
        mime_type = mimetypes.guess_type(image_path)[0]
        if not mime_type or not mime_type.startswith("image/"):
            return ""

        with open(image_path, "rb") as image_file:
            encoded = base64.b64encode(
                image_file.read()
            ).decode("utf-8")

        return f"data:{mime_type};base64,{encoded}"

    except Exception:
        return ""


avatar_base64 = get_base64_image("avatar.png")
ninja_bg_base64 = get_base64_image("Rninja.png")


# --------------------------------------------------
# 3. FILE PATH HELPER
# --------------------------------------------------

def get_file_path(file_item):
    """Gradio-এর বিভিন্ন file format থেকে path বের করে।"""

    if isinstance(file_item, str):
        return file_item

    if isinstance(file_item, dict):
        return (
            file_item.get("path")
            or file_item.get("name")
            or file_item.get("orig_name")
        )

    return getattr(file_item, "path", None)


# --------------------------------------------------
# 4. CHAT + GEMINI + BENGALI VOICE
# --------------------------------------------------

def chat_and_speak(message, history):
    history = list(history or [])

    if not message:
        return history, None

    # Gradio MultimodalTextbox data
    if isinstance(message, dict):
        user_text = (message.get("text") or "").strip()
        files = message.get("files") or []
    else:
        user_text = str(message).strip()
        files = []

    if not user_text and not files:
        return history, None

    display_msg = user_text or "ফাইল বিশ্লেষণ করতে বলেছি।"

    if files:
        display_msg += f"\n\n📎 সংযুক্ত ফাইল: {len(files)}টি"

    try:
        contents = []

        # Upload images and documents to Gemini
        for file_item in files:
            file_path = get_file_path(file_item)

            if not file_path or not os.path.isfile(file_path):
                raise ValueError(
                    "একটি আপলোড করা ফাইলের path পাওয়া যায়নি।"
                )

            uploaded_file = client.files.upload(
                file=file_path
            )
            contents.append(uploaded_file)

        # Add user prompt
        if user_text:
            contents.append(user_text)
        elif files:
            contents.append(
                "সংযুক্ত ফাইলটি বিশ্লেষণ করো। "
                "প্রয়োজনে বাংলায় বিস্তারিত ব্যাখ্যা দাও।"
            )

        # Current Gemini model
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
        )

        bot_reply = (
            getattr(response, "text", None)
            or "দুঃখিত, AI থেকে কোনো টেক্সট উত্তর পাওয়া যায়নি।"
        )

        # Add conversation messages
        history.append({
            "role": "user",
            "content": display_msg,
        })
        history.append({
            "role": "assistant",
            "content": bot_reply,
        })

        # Generate Bengali voice (optional)
        audio_path = None

        try:
            with tempfile.NamedTemporaryFile(
                suffix=".mp3",
                delete=False,
            ) as audio_file:
                audio_path = audio_file.name

            tts = gTTS(
                text=bot_reply,
                lang="bn",
                slow=False,
            )
            tts.save(audio_path)

        except Exception as voice_error:
            print("Voice generation failed:", voice_error)
            audio_path = None

        return history, audio_path

    except Exception as error:
        error_msg = f"ত্রুটি ঘটেছে: {error}"

        history.append({
            "role": "user",
            "content": display_msg,
        })
        history.append({
            "role": "assistant",
            "content": error_msg,
        })

        return history, None


# --------------------------------------------------
# 5. PREMIUM NINJA DESIGN
# --------------------------------------------------

custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');

body, .gradio-container {
    font-family: 'Poppins', sans-serif !important;
    color: #f3f4f6 !important;
    background-color: #05070a !important;
}

.premium-card {
    border: 2px solid rgba(0,191,255,0.5);
    padding: 25px;
    border-radius: 22px;
    max-width: 650px;
    margin: 15px auto 25px;
    text-align: center;
    background: rgba(10,17,26,0.92);
    box-shadow: 0 0 25px rgba(0,191,255,0.2);
}

.agent-avatar {
    width: 125px;
    height: 125px;
    border-radius: 50%;
    border: 4px solid #00bff5;
    object-fit: cover;
    box-shadow: 0 0 22px rgba(0,191,255,0.45);
}

.agent-title {
    font-size: 30px;
    font-weight: 700;
    color: #d4af37;
    margin: 12px 0 5px;
}

.agent-subtitle {
    color: #00bff5;
    font-size: 12px;
    letter-spacing: 2px;
    text-transform: uppercase;
}

.gr-chatbot, [data-testid="chatbot"] {
    border: 1px solid rgba(0,191,255,0.5) !important;
    border-radius: 15px !important;
}

button.primary {
    background: linear-gradient(135deg,#00bff5,#0077b6) !important;
    color: #05070a !important;
    font-weight: 600 !important;
}
"""


# --------------------------------------------------
# 6. BUILD THE APP
# --------------------------------------------------

avatar_html = (
    f'<img src="{avatar_base64}" class="agent-avatar" '
    'alt="HB AI Avatar">'
    if avatar_base64
    else '<div style="font-size:75px">🤖</div>'
)

background_style = (
    f"background-image: linear-gradient("
    f"rgba(5,7,10,0.84), rgba(5,7,10,0.94)), "
    f"url('{ninja_bg_base64}');"
    if ninja_bg_base64
    else "background-color:#05070a;"
)

with gr.Blocks(title="HB Official AI") as demo:

    gr.HTML(
        f"""
        <div style="{background_style}
                    background-size:cover;
                    background-position:center;
                    background-attachment:fixed;
                    padding:20px 10px;
                    border-radius:18px;">

            <div class="premium-card">
                {avatar_html}
                <h1 class="agent-title">HB Official AI</h1>
                <p class="agent-subtitle">
                    Premium Multimodal Assistant
                </p>
                <p>
                    🤖 AI Chat · 🖼️ Image & PDF · 🔊 বাংলা Voice
                </p>
            </div>
        </div>
        """
    )

    chatbot = gr.Chatbot(
    label="HB AI Conversation",
    height=430,
)

    msg = gr.MultimodalTextbox(
        label="তোমার মেসেজ",
        placeholder="এখানে প্রশ্ন লেখো অথবা ছবি/PDF আপলোড করো...",
        file_count="multiple",
        file_types=["image", ".pdf", ".txt"],
        sources=["upload"],
        show_label=True,
    )

    audio_output = gr.Audio(
        label="🔊 AI Voice Response",
        autoplay=True,
        type="filepath",
    )

    gr.Markdown(
        "ছবি বা PDF বিশ্লেষণের জন্য ফাইল আপলোড করে "
        "মেসেজ পাঠাও। বাংলা voice পেতে ইন্টারনেট সংযোগ প্রয়োজন।"
    )

    msg.submit(
        fn=chat_and_speak,
        inputs=[msg, chatbot],
        outputs=[chatbot, audio_output],
    )


# --------------------------------------------------
# 7. START SERVER
# --------------------------------------------------

if __name__ == "__main__":
    demo.queue().launch(
        theme=gr.themes.Soft(
            primary_hue="cyan",
            neutral_hue="slate",
        ),
        css=custom_css,
    )