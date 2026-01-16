# 🔥 IG Growth Hub

A modern, safe Instagram + Threads growth platform with profile SEO analysis and smart automation.

![IG Growth Hub](https://via.placeholder.com/800x400/0a0a0f/E1306C?text=IG+Growth+Hub)

## ✨ Features

- **🎨 Premium Dashboard** - Beautiful dark theme with glassmorphism design
- **📊 Profile Score** - 0-100 scoring based on SEO best practices
- **💡 Smart Suggestions** - Actionable tips for bio, captions, hashtags
- **🚀 Growth Booster** - Human-like engagement automation
- **🧵 Threads Support** - Cross-platform growth strategy
- **🔒 100% Local** - Your data never leaves your machine

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# Install packages
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 2. Configure Environment

```bash
# Copy example env file
copy .env.example .env

# Edit .env with your credentials (optional for demo)
```

### 3. Run the App

```bash
# Start the server
python backend/app.py
```

### 4. Open in Browser

Navigate to **http://localhost:5000**

## 📁 Project Structure

```
social-growth-bot/
├── frontend/           # Web UI
│   ├── index.html      # Login page
│   ├── dashboard.html  # Main dashboard
│   ├── css/style.css   # Premium styling
│   └── js/             # Frontend logic
├── backend/
│   └── app.py          # Flask API server
├── src/
│   ├── browser.py      # Playwright automation
│   ├── human_behavior.py  # Anti-detection
│   ├── rate_limiter.py # Action limits
│   ├── config.py       # Configuration
│   └── seo/
│       └── analyzer.py # Profile scoring
└── data/
    └── sessions/       # Browser sessions
```

## 📊 Profile Scoring

Your profile is scored across 6 categories:

| Category | Max | What We Check |
|----------|-----|---------------|
| Bio Optimization | 25 | Keywords, email, CTA, location |
| Name Field SEO | 15 | Niche keywords, format |
| Content Consistency | 20 | Posting frequency, niche focus |
| Hashtag Strategy | 15 | 3-2-1 formula, variety |
| Engagement Rate | 15 | Follower ratio, visibility |
| Profile Completeness | 10 | Picture, highlights, link |

## 🔒 Rate Limits

Safe defaults to protect your account:

| Action | Per Hour | Per Day |
|--------|----------|---------|
| Likes | 30 | 300 |
| Follows | 20 | 150 |
| Comments | 10 | 80 |

## ⚠️ Disclaimer

This tool is for educational purposes. Use responsibly and at your own risk. Automated actions may violate platform terms of service.

## 📄 License

MIT License - Use freely, modify as needed.
