# IG Growth Hub - Deployment Guide

## Quick Start for Deployment

### Step 1: Set Up Supabase (Free Database)
1. Go to [supabase.com](https://supabase.com) and create account
2. Create new project (free tier)
3. Go to **Settings → Database** and copy the connection string
4. Save it - you'll need it for Railway

### Step 2: Set Up Razorpay (Payments)
1. Go to [dashboard.razorpay.com](https://dashboard.razorpay.com)
2. Sign up and complete KYC
3. Go to **Settings → API Keys**
4. Generate new keys (use Test mode first!)
5. Save Key ID and Key Secret

### Step 3: Deploy to Railway
1. Push code to GitHub
2. Go to [railway.app](https://railway.app) and sign in with GitHub
3. Click **New Project** → **Deploy from GitHub repo**
4. Select your Instagram automation repo
5. Railway will auto-detect the Dockerfile

### Step 4: Configure Environment Variables
In Railway, add these variables:

```
SECRET_KEY=your-random-32-character-string
DATABASE_URL=postgresql://... (from Supabase)
REDIS_URL=redis://... (optional, use Upstash)
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
GROQ_API_KEY=... (optional)
```

### Step 5: Deploy!
Railway will build and deploy automatically. You'll get a URL like:
`https://your-app.railway.app`

---

## Files Created

| File | Purpose |
|------|---------|
| `Dockerfile` | Container for deploying app |
| `docker-compose.yml` | Local development with DB & Redis |
| `railway.toml` | Railway deployment config |
| `.env.example` | Environment variables template |
| `src/database/models.py` | User, subscription, payment models |
| `src/auth.py` | JWT authentication |
| `src/payments.py` | Razorpay integration |

---

## Local Testing with Docker

```bash
# Build and run everything locally
docker-compose up --build

# Open http://localhost:5000
```

---

## Pricing Summary

| Service | Cost |
|---------|------|
| Railway | Free tier (500 hrs/month) or $5/month |
| Supabase | Free (500MB database) |
| Razorpay | 2% per transaction (no monthly fee) |
| **Your revenue** | ₹300/month per user |
