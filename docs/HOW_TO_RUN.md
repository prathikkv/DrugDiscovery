# How to Run & Host BioOrchestrator

## Quick Start — Local

```bash
# 1. Navigate to project
cd /path/to/amgen

# 2. Activate your conda environment
conda activate bioorchestrator   # or whatever you named it

# 3. Copy and fill in your API key
cp .env.example .env
# Edit .env and set: ANTHROPIC_API_KEY=sk-ant-...

# 4. Run the app
streamlit run src/app.py
# Opens at http://localhost:8501
```

**First login:** Go to the Register tab, create a user with role `admin`. Then log in.

---

## One-Click Mac Launcher

Double-click `bioorchestrator_real/BioOrchestrator.command` from Finder.
This auto-activates the conda environment and launches the app in your browser.

If you get a "cannot be opened" warning: right-click → Open → Open anyway.

---

## Generate Showcase Data (One-Time Setup)

Pre-caches results for EGFR, ESR1, PIK3CA, GLP1R, PARP1, CD274 so demos work instantly:

```bash
python scripts/generate_showcase_data.py
```

This takes ~5–10 minutes and makes demos run without live API calls.

---

## Docker Run (Matches Production)

```bash
# Build and start
docker compose up

# Access at http://localhost:8501
# Stop with Ctrl+C, remove containers with:
docker compose down
```

---

## Hosting Options (Free → $25/month)

### Option 1: Streamlit Community Cloud — Free ✅ Recommended

**Best for:** Public demo URL to share with prospects and include in LinkedIn posts.

**Steps:**
1. Push your repo to GitHub (can be public or private)
2. Go to [share.streamlit.io](https://share.streamlit.io) → Sign in with GitHub
3. Click **New app** → Select your repo → Branch: `main`
4. Main file path: `src/app.py`
5. Click **Advanced settings** → **Secrets** → paste:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-your-key-here"
   ```
6. Under **Advanced settings** → set Requirements file: `requirements-cloud.txt`
7. Click **Deploy**

Your URL will be something like `https://bioorchestrator.streamlit.app`

**Notes:**
- `packages.txt` in the repo root is auto-detected for system dependencies
- `requirements-cloud.txt` excludes heavy packages (rpy2, scrublet, gseapy) that fail to compile on Streamlit Cloud
- Free tier: 1 app, sleeps after 7 days of inactivity (wakes on first visit, ~30s)
- Upgrade to $25/month for always-on + custom domain

---

### Option 2: Render — Free / $7/month

**Best for:** Always-on deploy with Docker support.

**Steps:**
1. Push repo to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Build command: `pip install -r requirements-cloud.txt`
5. Start command: `streamlit run src/app.py --server.port $PORT --server.headless true`
6. Add environment variable: `ANTHROPIC_API_KEY` = your key
7. Free tier sleeps after 15 minutes of inactivity. $7/month for always-on.

---

### Option 3: Railway — ~$5/month

**Best for:** Easiest Docker deploy, generous free tier.

**Steps:**
1. Push repo to GitHub (includes `Dockerfile` and `docker-compose.yml`)
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub repo
3. Railway auto-detects the `Dockerfile`
4. Add variable: `ANTHROPIC_API_KEY` = your key
5. Done — Railway auto-assigns a URL

---

### Option 4: Fly.io — Free tier / ~$2/month

```bash
# Install flyctl
brew install flyctl

# Login
fly auth login

# Launch (run from project root)
fly launch --no-deploy

# Set secret
fly secrets set ANTHROPIC_API_KEY=sk-ant-your-key-here

# Deploy
fly deploy
```

Configure `fly.toml` to expose port 8501. Roughly $2–5/month for a shared CPU instance.

---

## Choosing the Right Option

| Goal | Use |
|------|-----|
| Share a demo link TODAY | Streamlit Community Cloud (free) |
| Always-on, looks professional | Render $7/mo or Railway $5/mo |
| Full Docker with your own domain | Fly.io ~$2/mo |
| Enterprise / on-premise demo for a prospect | Docker on their infra or Railway private deploy |

---

## Getting an API Key

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign up → API Keys → Create Key
3. New accounts get $5 free credit — enough for ~50 full target analyses
4. Copy key → paste into `.env` or Streamlit Secrets

---

## Troubleshooting

**App won't start:** Check that `ANTHROPIC_API_KEY` is set. The app can launch without it but AI Insights will fail.

**gseapy install fails:** Run `pip install --prefer-binary gseapy` — this uses pre-built wheels and avoids Rust compilation.

**h5ad files don't load:** `libhdf5-dev` must be installed. On Mac: `brew install hdf5`. On Streamlit Cloud, `packages.txt` handles this automatically.

**Login page not found:** Always run from project root with `streamlit run src/app.py` — do not `cd src` first.
