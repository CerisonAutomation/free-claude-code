# 🆓 FREE Cloud Hosting Options

## Top Free Platforms (Ranked by Value)

| Platform | Free Tier | Limitations | Best For |
|----------|-----------|-------------|----------|
| **Render** | 750h/month | Sleeps after 15min inactivity | Simple, reliable |
| **Railway** | $5 credit/month | Requires credit card | Easy setup |
| **Fly.io** | Free VMs | Limited to 3 regions | Global deployment |
| **Koyeb** | 512MB RAM, 1 vCPU | Global edge | Serverless |
| **Zeabur** | 2 vCPU, 2GB RAM | Limited regions | Developer-friendly |

---

## 🚀 Option 1: Render (Easiest - RECOMMENDED)

**Free Tier:** 750 hours/month (~1 month continuous)

**Pros:**
- ✅ No credit card required
- ✅ Auto-SSL included
- ✅ PostgreSQL free tier available
- ✅ Simple git-based deployment

**Cons:**
- ⚠️ Spins down after 15min inactivity
- ⚠️ Cold start ~30s

### Deploy to Render

```bash
# 1. Push to GitHub
git add .
git commit -m "Add cloud deployment configs"
git push

# 2. Go to render.com
# 3. Click "New +" → "Web Service"
# 4. Connect your GitHub repo
# 5. Use these settings:
#    - Build Command: (empty - uses Dockerfile)
#    - Start Command: uvicorn server:app --host 0.0.0.0 --port 8082
#    - Runtime: Docker
# 6. Add environment variables from .env
# 7. Deploy!
```

**Keep it alive (no sleep):** Use [UptimeRobot](https://uptimerobot.com) to ping `/health` every 5 minutes.

---

## 🚀 Option 2: Railway (Developer Experience)

**Free Tier:** $5 credit/month (enough for small deployment)

**Pros:**
- ✅ Excellent UI
- ✅ Built-in database
- ✅ Preview deployments
- ✅ Auto-scaling

**Cons:**
- ⚠️ Requires credit card
- ⚠️ Credit runs out eventually

### Deploy to Railway

```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login
railway login

# 3. Initialize
railway init

# 4. Deploy
railway up

# 5. Add environment variables in Railway dashboard
```

---

## 🚀 Option 3: Fly.io (Global Edge)

**Free Tier:** 3 free VMs (1GB RAM each)

**Pros:**
- ✅ Global deployment (multiple regions)
- ✅ No sleep - always running
- ✅ Built-in CDN
- ✅ WireGuard VPN

**Cons:**
- ⚠️ Requires credit card
- ⚠️ More complex setup

### Deploy to Fly.io

```bash
# 1. Install Fly CLI
curl -L https://fly.io/install.sh | sh

# 2. Login
fly auth login

# 3. Launch
fly launch

# 4. Scale to multiple regions (optional)
fly scale count 3 --region iad
fly scale count 1 --region lhr
fly scale count 1 --region sin

# 5. Deploy
fly deploy
```

---

## 🚀 Option 4: Koyeb (Serverless)

**Free Tier:** 512MB RAM, 1 vCPU, unlimited hours

**Pros:**
- ✅ True serverless (pay-per-use)
- ✅ Global edge network
- ✅ No sleep
- ✅ Built-in metrics

**Cons:**
- ⚠️ Smaller resources
- ⚠️ Requires Docker

### Deploy to Koyeb

```bash
# 1. Install Koyeb CLI
curl -sSL https://cli.koyeb.com/install.sh | sh

# 2. Login
koyeb login

# 3. Deploy from Docker
koyeb app init free-claude-code
koyeb service create free-claude-code \
  --dockerfile Dockerfile \
  --ports 8082:8082 \
  --env NVIDIA_NIM_API_KEY=$NVIDIA_NIM_API_KEY \
  --env OPENROUTER_API_KEY=$OPENROUTER_API_KEY \
  --env DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY \
  --env REDIS_URL=$REDIS_URL \
  --env DATABASE_URL=$DATABASE_URL
```

---

## 🚀 Option 5: Zeabur (Fastest Setup)

**Free Tier:** 2 vCPU, 2GB RAM

**Pros:**
- ✅ Fastest deployment
- ✅ Built-in database
- ✅ Real-time logs
- ✅ Auto-SSL

**Cons:**
- ⚠️ Newer platform
- ⚠️ Limited regions

### Deploy to Zeabur

```bash
# 1. Go to zeabur.com
# 2. Connect GitHub
# 3. Create new project
# 4. Import repo
# 5. Select Dockerfile
# 6. Add environment variables
# 7. Deploy!
```

---

## 🏆 RECOMMENDATION: Render

**Why Render for FREE hosting:**
1. **No credit card** required
2. **750 hours/month** = continuous deployment
3. **Simplest setup** - just connect GitHub
4. **Auto-SSL** included
5. **Built-in database** (PostgreSQL free tier)

**To keep it awake:**
- Use [UptimeRobot](https://uptimerobot.com) (free)
- Ping `https://your-app.onrender.com/health` every 5 minutes
- This prevents the 15min sleep

---

## 🔧 Keep Your App Awake (Render)

```bash
# Create a cron job on any free service (GitHub Actions, etc.)
# Or use UptimeRobot (easiest - web UI)

# UptimeRobot setup:
# 1. Go to uptimerobot.com
# 2. Create new monitor
# 3. Type: HTTPS
# 4. URL: https://your-app.onrender.com/health
# 5. Interval: 5 minutes
# 6. Save
```

---

## 📊 Comparison Summary

| Platform | Setup Time | Always On | SSL | Database | Credit Card |
|----------|------------|-----------|-----|----------|-------------|
| Render | 5 min | ❌ (fixable) | ✅ | ✅ | ❌ |
| Railway | 3 min | ✅ | ✅ | ✅ | ✅ |
| Fly.io | 10 min | ✅ | ✅ | ❌ | ✅ |
| Koyeb | 8 min | ✅ | ✅ | ❌ | ✅ |
| Zeabur | 2 min | ✅ | ✅ | ✅ | ❌ |

---

## 🎯 Quick Start (Render - Recommended)

```bash
# 1. Commit and push
git add .
git commit -m "Ready for cloud deployment"
git push

# 2. Go to render.com → New Web Service
# 3. Connect repo
# 4. Settings:
#    - Runtime: Docker
#    - Build: Dockerfile
#    - Start: uvicorn server:app --host 0.0.0.0 --port 8082
# 5. Add env vars from .env
# 6. Deploy!

# 7. Add to UptimeRobot to keep awake
```

**That's it - your proxy is now hosted for FREE!**
