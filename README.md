# 🔥 FireReach — Autonomous B2B Outreach Engine

FireReach is an AI-powered outreach engine that harvests live buyer-intent signals for a target company, synthesizes them into an account brief, and generates + sends a hyper-personalized outreach email — all in one autonomous pipeline. Built for [Rabbitt AI](https://rabbitt.ai).

> **Zero-template policy:** Every email must reference specific, verified signal data. A confidence gate enforces this at the code level, not just the prompt level.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **LLM** | Groq SDK — `llama-3.3-70b-versatile` |
| **Backend** | FastAPI 0.111.0, Python 3.11, Uvicorn 0.29.0 |
| **Validation** | Pydantic Settings 2.2.1 |
| **HTTP Client** | httpx 0.27.0 (async) |
| **Email** | aiosmtplib 3.0.1 (Gmail SMTP) |
| **Rate Limiting** | slowapi 0.1.9 |
| **Signals** | SerpAPI (free tier — 100 queries/month) |
| **Frontend** | React 18, TailwindCSS, Vite, plain JSX |
| **Deploy** | Render (backend), Vercel (frontend) |

---

## API Keys

### Groq API Key (free)
1. Go to [console.groq.com](https://console.groq.com)
2. Sign up / sign in
3. Navigate to API Keys → Create API Key
4. Copy the key to your `.env` file as `GROQ_API_KEY`

### SerpAPI Key (free — 100 queries/month)
1. Go to [serpapi.com](https://serpapi.com)
2. Sign up for a free account
3. Go to Dashboard → API Key
4. Copy the key to your `.env` file as `SERP_API_KEY`

### Gmail App Password
1. Go to [Google Account → Security](https://myaccount.google.com/security)
2. Enable 2-Factor Authentication (required)
3. Go to **2-Step Verification → App passwords**
4. Generate a new app password (select "Mail" and your device)
5. Copy the 16-character password to your `.env` file as `GMAIL_APP_PASSWORD`
6. Set `GMAIL_USER` to your Gmail address

---

## Local Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- npm or yarn

### 1. Clone and configure

```bash
git clone <your-repo-url>
cd firereach

# Copy environment template
cp .env.example backend/.env
```

Edit `backend/.env` with your API keys (or leave defaults for MOCK_MODE).

### 2. Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173` and proxies API calls to the backend at `http://localhost:8000`.

---

## Running in MOCK_MODE

Set `MOCK_MODE=true` in `backend/.env`. This is **the default** in `.env.example`.

In MOCK_MODE:
- **Zero external API calls** are made (no Groq, SerpAPI, or SMTP)
- All adapters return realistic fixture data
- You don't need valid API keys
- The full pipeline runs end-to-end with mock data

This is ideal for development, testing, and demos.

---

## Deployment

### Backend → Render

1. Create a new **Web Service** on [Render](https://render.com)
2. Connect your GitHub repo
3. Set:
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables: `GROQ_API_KEY`, `SERP_API_KEY`, `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `ALLOWED_ORIGINS` (set to your Vercel URL), `MOCK_MODE=false`

### Frontend → Vercel

1. Create a new project on [Vercel](https://vercel.com)
2. Connect your GitHub repo
3. Set:
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
4. Add environment variable or update `vite.config.js` proxy to point to your Render backend URL

For production, update the API base URL in `App.jsx` or configure Vercel rewrites to proxy `/api` to your Render backend.

---

## Project Structure

```
firereach/
├── backend/
│   ├── main.py                 # FastAPI app, CORS, rate limiter, startup checks
│   ├── config.py               # Pydantic BaseSettings
│   ├── models.py               # All Pydantic request/response models
│   ├── agent/
│   │   ├── orchestrator.py     # Agent loop, tool gating, SSE generator
│   │   └── tools.py            # Groq function-calling tool schemas
│   ├── adapters/
│   │   ├── signal_adapter.py   # SerpAPI integration
│   │   ├── llm_adapter.py      # Groq SDK wrapper
│   │   └── mail_adapter.py     # Gmail SMTP via aiosmtplib
│   ├── routers/
│   │   └── run.py              # All HTTP routes
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   └── components/
│   │       ├── InputForm.jsx
│   │       ├── StatusPanel.jsx
│   │       ├── SignalOutput.jsx
│   │       ├── BriefOutput.jsx
│   │       └── EmailOutput.jsx
│   ├── index.html
│   └── package.json
├── .env.example
├── DOCS.md
└── README.md
```

---

## Submission

Submit your completed project here:
https://docs.google.com/forms/d/e/1FAIpQLSfi7wCK7SO7JAUkUjHIMkpN4dI6YNoqD4XxtMFMmRZ9t_lBpA/viewform

---

## License

Built for the Rabbitt AI challenge.
