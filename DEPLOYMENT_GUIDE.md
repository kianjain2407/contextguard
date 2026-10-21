# ContextGuard: Deployment & Hosting Guide

**How to Deploy ContextGuard for Public & Team Access**  
*Single-container, zero-cost, self-contained deployment options*

---

## 1. Why ContextGuard Is So Easy to Deploy

Because ContextGuard was architected with **DuckDB/SQLite**, **Waitress**, and an embedded **Mock LLM engine**, it has **zero mandatory external cloud dependencies**:
- **No external database server** needed (no PostgreSQL or MongoDB to set up).
- **No Redis / message broker** required.
- **No paid API keys** strictly required (runs out of the box in Mock mode, or with a free Google Gemini / OpenAI key).
- **No Node.js / NPM build step** required (all CSS and JS are natively bundled).

You can deploy it in **less than 5 minutes** using any of the options below.

---

## 2. Option A: Free Cloud Web Hosting (Render / Railway) — *Recommended for Public Sharing*

These platforms give you a free, public `https://contextguard.onrender.com` link that you can share with professors, teammates, or evaluators.

### Deploying to Render.com (100% Free Tier)
1. Push your project to a GitHub repository (e.g. `github.com/your-username/contextguard`).
2. Go to [render.com](https://render.com) and click **"New +" $\to$ "Web Service"**.
3. Select your GitHub repository.
4. Set the following configuration:
   - **Name**: `contextguard`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python wsgi.py`
5. Under **Environment Variables**, add:
   - `PORT` = `5000`
   - `LLM_PROVIDER` = `mock` *(or `gemini` if you add `GEMINI_API_KEY`)*
6. Click **"Deploy Web Service"**.
7. Render will provide a live HTTPS link in 2 minutes.

---

## 3. Option B: Hugging Face Spaces (Free Docker Hosting)

Hugging Face Spaces allows you to run Dockerized applications with persistent public links for free:
1. Go to [huggingface.co/spaces](https://huggingface.co/spaces) and create a new Space.
2. Choose **Docker** as the Space SDK.
3. Push the ContextGuard repository files (including the `Dockerfile` and `requirements.txt`).
4. Hugging Face automatically builds the container and serves it at:
   `https://huggingface.co/spaces/your-username/contextguard`.

---

## 4. Option C: Instant Live Demo via Ngrok / Cloudflare (Zero Deployment, Run from Your Laptop)

If you have ContextGuard running locally and want to show it to someone immediately without setting up cloud servers:

### Using Ngrok:
1. Start ContextGuard on your machine:
   ```bash
   python app.py
   ```
2. In a second terminal window, run:
   ```bash
   ngrok http 5000
   ```
3. Ngrok gives you a temporary public HTTPS link (e.g. `https://a1b2-c3d4.ngrok-free.app`). Send this link to anyone!

### Using Cloudflare Tunnels (No Account Needed):
```bash
npx untun@latest tunnel http://localhost:5000
```
This generates an instant, public Cloudflare HTTPS URL.

---

## 5. Option D: Self-Hosted Docker Container (AWS, DigitalOcean, VPS)

To run ContextGuard in a standard Docker container on any Linux or Windows server:

### 1. Build the Docker Image:
```bash
docker build -t contextguard:latest .
```

### 2. Run the Container:
```bash
docker run -d \
  -p 5000:5000 \
  --name contextguard-app \
  -v $(pwd)/data:/app/data \
  -e LLM_PROVIDER=mock \
  contextguard:latest
```

The app will be accessible at `http://your-server-ip:5000`.

---

## 6. Option E: GitHub Actions CI/CD Integration

ContextGuard can also run automatically as a GitHub Action bot when someone opens a Pull Request on a repository!

Create `.github/workflows/contextguard.yml`:
```yaml
name: ContextGuard Automated Review
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  verify-pr:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install ContextGuard
        run: pip install -r requirements.txt

      - name: Verify PR
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          PR_URL: ${{ github.event.pull_request.html_url }}
        run: |
          python -m contextguard.pipeline --url "$PR_URL"
```

---

## 7. Deployment Health Check

Once deployed, verify that the application is running healthy by querying the `/health` endpoint:

```bash
curl https://your-deployed-domain.com/health
```

Expected response:
```json
{
  "status": "ok",
  "database": "duckdb",
  "llm_provider": "mock",
  "uptime_seconds": 124.5,
  "connected_repositories": 1,
  "active_runs": 0
}
```
