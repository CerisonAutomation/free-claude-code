# 🚀 Free Deployment to Render

**Free tier:** 750 hours/month (24/7), free Redis, free PostgreSQL

## Step 1: Deploy to Render (2 minutes)

1. Go to [render.com](https://render.com)
2. Sign up/login with GitHub
3. Click "New +" → "Web Service"
4. Connect GitHub → Select `CerisonAutomation/free-claude-code`
5. Render auto-detects `render.yaml`
6. Click "Deploy Web Service"

## Step 2: Add API Keys (1 minute)

In Render dashboard → Environment tab, add:
```
NVIDIA_NIM_API_KEY=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
OPENROUTER_API_KEY=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
DEEPSEEK_API_KEY=sk-8cebbda599014950bdbaf5321d4ffded
ANTHROPIC_AUTH_TOKEN=freecc
TELEGRAM_BOT_TOKEN=8346992617:AAG5LVsfFqnJTea2FTSfkeEFgxC08OKurxM
MESSAGING_PLATFORM=telegram
```

## Step 3: Wait for Deploy (2-3 minutes)

Render automatically:
- Builds Docker image
- Deploys Redis
- Deploys PostgreSQL
- Starts the app

**Your app:** `https://free-claude-code.onrender.com`

## Future Updates

```bash
git add .
git commit -m "Update"
git push
```

Auto-deploys in ~2 minutes.
