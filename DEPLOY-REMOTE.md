# 🚀 One-Command Remote Deployment

## Simplest Path: GitHub + Render Auto-Deploy

This is the true zero-effort deployment. Once set up, every git push auto-deploys.

### Step 1: Push to GitHub (Done ✅)

Your repo is now at: https://github.com/CerisonAutomation/free-claude-code

### Step 2: Connect to Render (One-time, 2 minutes)

1. Go to [render.com](https://render.com)
2. Click "New +" → "Web Service"
3. Connect your GitHub account
4. Select `CerisonAutomation/free-claude-code` repo
5. Render will auto-detect `render.yaml`
6. Click "Deploy Web Service"

**That's it!** Render will automatically:
- Build the Docker image
- Deploy Redis and PostgreSQL
- Set environment variables
- Configure health checks
- Enable auto-deploys on git push

### Step 3: Add API Keys (One-time)

In Render dashboard, add these environment variables:
- `NVIDIA_NIM_API_KEY`
- `OPENROUTER_API_KEY`
- `DEEPSEEK_API_KEY`
- `TELEGRAM_BOT_TOKEN` (optional)

### Future Deployments: One Command

```bash
# Make changes
git add .
git commit -m "Update"
git push
```

**Render auto-deploys in ~2 minutes.**

---

## Alternative: Railway (Similar)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize and deploy
railway init
railway up
```

Railway will detect `railway.json` and auto-deploy with Redis/PostgreSQL.

---

## Alternative: Fly.io (CLI-based)

```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Deploy
fly launch
fly deploy
```

Note: Fly.io requires manual Redis/PostgreSQL setup.

---

## Recommended: Render

**Why Render?**
- ✅ True auto-deploy on git push
- ✅ Free Redis and PostgreSQL
- ✅ Auto-detected from `render.yaml`
- ✅ Built-in SSL
- ✅ Zero CLI required after initial GitHub setup
- ✅ Best free tier (90 days free, then $7/mo)

**Total effort:**
- Initial setup: 5 minutes
- Future deployments: 1 command (`git push`)
