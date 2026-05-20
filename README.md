# 🧠 Malik — Multimodal AI Assistant
### Voice + Vision + Context Intelligence

A production-grade multimodal AI assistant with real-time voice, image understanding, intelligent long-term memory, and offline-capable local operation.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🎙️ **Talk with Voice** | Real-time speech recognition and natural TTS for hands-free interaction |
| 🖼️ **Understand Images & Screens** | Upload or capture images for AI analysis and screen understanding |
| 🖥️ **Analyze & Control the PC** | Support for intelligent desktop assistance and task execution |
| 💻 **Help with Coding** | Assist with code authoring, debugging, and development workflows |
| 🧠 **Solve Problems Intelligently** | Reason across tasks and provide thoughtful solutions |
| 🤖 **Execute Tasks Autonomously** | Plan and act on user instructions with autonomous task execution |
| 🧬 **Maintain Long-term Memory** | Persistent session history and context across interactions |
| 🧑‍🤝‍🧑 **Use Multiple AI Agents** | Coordinate with specialized agents for richer multimodal workflows |
| 🌐 **Work Locally & Offline** | Designed to run locally and minimize cloud dependency whenever possible |
| 🧑‍💼 **Professional Operating Assistant** | Behave like a professional assistant that manages tasks, context, and workflow |
| 🔊 **Voice Output** | Natural TTS via gTTS or ElevenLabs |
| 🌐 **Multilingual** | English + Urdu support |
| ⚡ **Fast & Async** | Async FastAPI backend with minimal latency |
| 🎨 **Premium UI** | Futuristic dark glassmorphism design |

---

## 🚀 Quick Start

### Step 1 — Clone & Install

```bash
git clone <your-repo>
cd ai_malik

# Install Python dependencies
pip install -r requirements.txt
```

### Step 2 — Configure API Keys

```bash
cp .env.example .env
```

Open `.env` and fill in your keys:
```env
# Minimum required — get free at console.groq.com
GROQ_API_KEY=gsk_your_key_here

# Optional — for GPT-4o Vision (better image analysis)
OPENAI_API_KEY=sk-your_key_here

# Optional — for premium natural TTS voice
ELEVENLABS_API_KEY=your_key_here
```

> **All configuration lives in `.env` — there is no settings UI in the app.**

### Step 3 — Start Backend

```bash
cd backend
python main.py
```

Backend runs at: `http://localhost:8000`

### Step 4 — Open Frontend

Option A — Direct file open:
```
Open frontend/index.html in your browser
```

Option B — Via backend (recommended):
```
Navigate to http://localhost:8000
```

---

## 🔑 Getting API Keys

### Groq (Free — Recommended)
1. Visit [console.groq.com](https://console.groq.com)
2. Sign up for free
3. Create API key
4. Enables: LLaMA 3.3 70B chat + Whisper STT + Vision

### OpenAI (Optional)
1. Visit [platform.openai.com](https://platform.openai.com)
2. Create API key
3. Enables: GPT-4o Vision (superior image analysis)

### ElevenLabs (Optional — Premium TTS)
1. Visit [elevenlabs.io](https://elevenlabs.io)
2. Create API key
3. Enables: Ultra-realistic voice synthesis

---

## 🏗️ Architecture

```
User Input (Voice/Text/Image)
        ↓
   Input Layer
   ├── Web Speech API (STT)
   ├── Text normalization
   └── Image base64 encoding
        ↓
   FastAPI Backend
   ├── /api/chat/message    ← Main multimodal endpoint
   ├── /api/voice/synthesize
   ├── /api/vision/analyze
   └── /api/memory/
        ↓
   Multimodal Fusion Engine
   ├── Build context object
   ├── Merge: text + speech + image + history
   └── Detect intent
        ↓
   LLM Service (Groq/OpenAI)
   └── Generate intelligent response
        ↓
   Response Layer
   ├── Text display (typed animation)
   ├── TTS synthesis (gTTS/ElevenLabs)
   └── Memory persistence
```

---

## 📁 Project Structure

```
ai_malik/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings from .env
│   ├── routes/
│   │   ├── chat.py          # Main chat + multimodal fusion
│   │   ├── voice.py         # TTS endpoints
│   │   ├── vision.py        # Image analysis endpoints
│   │   └── memory.py        # Conversation memory endpoints
│   ├── services/
│   │   ├── llm_service.py   # Groq/OpenAI LLM integration
│   │   ├── vision_service.py # Image understanding
│   │   ├── tts_service.py   # Text-to-speech
│   │   ├── speech_service.py # Speech-to-text (Whisper)
│   │   └── memory_service.py # Conversation history
│   └── models/
│       └── schemas.py       # Pydantic data models
├── frontend/
│   └── index.html           # Complete frontend (single file)
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🧠 Multimodal Context Object

Every AI request is structured as:

```json
{
  "user_input": "What's in this image?",
  "speech_text": "What's in this image?",
  "image_analysis": "A sunset over mountains with...",
  "conversation_history": [...],
  "intent": "image_query",
  "timestamp": "2024-01-15T10:30:00Z",
  "session_id": "malik_abc123",
  "language": "en"
}
```

---

## 🎨 Frontend Features

- **Dark mode** with animated particle background
- **Glassmorphism** panels with blur effects
- **Voice waveform** animation during speech
- **Real-time mic** with pulse animation
- **Image drag & drop** or camera capture
- **Chat bubbles** with multimodal tags
- **Typing indicator** while AI processes
- **Status indicator**: Idle / Listening / Thinking / Speaking
- **Language switcher**: English / Urdu

---

## ⚙️ Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | — | Groq API key (recommended) |
| `LLM_MODEL` | `llama-3.3-70b-versatile` | LLM model to use |
| `TTS_PROVIDER` | `gtts` | `gtts` or `elevenlabs` |
| `MEMORY_TYPE` | `file` | `file` (persistent) or `memory` |
| `MEMORY_MAX_HISTORY` | `50` | Max messages to keep |

---

## 🛠️ Troubleshooting

**Backend not connecting?**
- Make sure you're running `python main.py` from inside the `backend/` directory
- Check port 8000 is not already in use
- Verify your `.env` file exists and has a valid `GROQ_API_KEY`

**Voice not working?**
- Chrome/Edge recommended for Web Speech API
- Allow microphone permissions when prompted

**Image analysis not working?**
- Set `GROQ_API_KEY` or `OPENAI_API_KEY` in your `.env` file
- Groq supports: `llama-3.2-11b-vision-preview` (set `VISION_PROVIDER=groq`)
- OpenAI supports: `gpt-4o-mini` (set `VISION_PROVIDER=openai`)

---

## 📝 License

MIT — Build something great!
