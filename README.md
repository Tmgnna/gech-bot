# 🚗 Car Equb Bot + Admin Panel

Telegram bot for selling car equb (ዕጣ) tickets with a built-in web admin panel.

## Features
- 🌍 Bilingual (አማርኛ / Afaan Oromoo)
- 🚗 Multiple cars managed from web admin
- 🎟️ Ticket ranges up to 4000+ per car
- 💳 Bank payment info displayed to users
- 📸 Payment screenshot + TX ref verification
- ✅ Approve / Reject from Telegram **and** web
- 🌐 Web admin panel with login
- 🔔 Notifications to user & admin group
- 🚀 Ready for Render (webhook)

## Quick Deploy to Render

### 1. Fork / clone this repo

### 2. Create a Render Web Service
- **Environment:** Python 3
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `python app.py`

### 3. Set Environment Variables
Copy `.env.example` and fill in all values in the Render dashboard.

### 4. Health Check Path
`/health`

### 5. Admin Panel
After deploy, visit:
