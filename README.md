# 🧬 NextTwin — Personalized Digital Academic Twin

A full-stack AI-powered platform that creates a **Digital Twin** of a student's academic profile,
predicts performance, simulates career decisions, and uses **Explainable AI** to reason transparently.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.x (stdlib only — `http.server`, `sqlite3`, `hashlib`, `json`) |
| **Database** | SQLite3 (7 normalized tables) |
| **Frontend** | React 18 (CDN) + Recharts |
| **AI Engine** | Pure Python — Linear Regression, Weighted Scoring, Diminishing Returns |
| **XAI** | Factor decomposition with directional reasoning per prediction |

> ✅ **Zero external Python packages** — runs on any system with Python 3.6+

---

## 🚀 LOCAL SETUP (Step by Step)

### Step 1 — Download & Extract
Download the ZIP and extract it. You should see:
```
nexttwin/
├── start.py
├── Procfile
├── backend/
│   ├── server.py
│   ├── db/
│   │   ├── schema.sql
│   │   └── database.py
│   └── services/
│       └── prediction_engine.py
└── frontend/
    └── index.html
```

### Step 2 — Run (no installs needed)
```bash
cd nexttwin
python3 start.py
```

### Step 3 — Open browser
Go to: **http://localhost:3000**

**Demo Login:**
- Email: `demo@nexttwin.ai`
- Password: `demo1234`

---

## ☁️ DEPLOYMENT (Railway + Netlify)

### Backend → Railway.app (Free)

1. Push this folder to a GitHub repo
2. Go to https://railway.app → "New Project" → "Deploy from GitHub"
3. Select your repo
4. Railway auto-detects the `Procfile` and runs `python backend/server.py`
5. Go to your project → Settings → Networking → "Generate Domain"
6. Copy your Railway URL, e.g. `https://nexttwin-production.up.railway.app`

### Frontend → Netlify (Free)

1. Open `frontend/index.html`
2. Find this line near the top of the `<script>` block:
   ```js
   const API = (window.__NEXTTWIN_API__ || ...)
   ```
3. Just above that `<script type="text/babel">` tag, add:
   ```html
   <script>
     window.__NEXTTWIN_API__ = "https://YOUR-RAILWAY-URL.railway.app/api";
   </script>
   ```
   Replace with your actual Railway URL.
4. Go to https://app.netlify.com/drop
5. Drag and drop the `frontend/` folder
6. Done! You get a public URL instantly.

### Test it
- Visit your Netlify URL
- Login with `demo@nexttwin.ai` / `demo1234`
- Dashboard should load with charts and AI predictions

---

## 📁 Project Structure

```
nexttwin/
├── start.py                     # One-command local launcher
├── Procfile                     # For Railway/Render deployment
├── runtime.txt                  # Python version for deployment
│
├── backend/
│   ├── server.py                # Python HTTP API server (REST endpoints)
│   ├── db/
│   │   ├── schema.sql           # SQL schema — 7 normalized tables
│   │   ├── database.py          # SQLite connection manager + seeder
│   │   └── nexttwin.db          # SQLite database (auto-created on first run)
│   └── services/
│       └── prediction_engine.py # AI prediction + simulation engine
│
└── frontend/
    └── index.html               # Single-page React app (self-contained)
```

---

## 🌐 REST API Endpoints

### GET
| Endpoint | Description |
|---|---|
| `/api/health` | Server health check |
| `/api/user/profile` | Student profile |
| `/api/academic/records` | All subject marks |
| `/api/skills` | Skills list |
| `/api/activities` | Activity log |
| `/api/career-goals` | Career goals |
| `/api/predict/cgpa` | CGPA prediction + XAI |
| `/api/predict/placement` | Placement score + XAI |
| `/api/predict/skills` | 3/6/12 month skill forecast |
| `/api/dashboard/summary` | All data for dashboard |

### POST
| Endpoint | Body | Description |
|---|---|---|
| `/api/auth/login` | `{email, password}` | Login |
| `/api/auth/register` | `{name, email, password, branch, semester, cgpa}` | Register |
| `/api/scenario/simulate` | `{scenario_type, params}` | Run What-If simulation |
| `/api/skills/add` | `{skill_name, proficiency, category, hours}` | Add skill |
| `/api/academic/add` | `{subject, marks, semester, exam_type}` | Add record |
| `/api/activities/add` | `{activity_type, description, impact_score, date}` | Log activity |
| `/api/career-goals/add` | `{target_role, target_company, target_salary, target_year}` | Add goal |
