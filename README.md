# Baba Quran (بابا قرآن)

An automated, local, and stateful WhatsApp bot that schedules daily Quran readings (images + metadata), tracks member emoji reactions in real-time, and sends gentle private reminder DMs to members who haven't read their daily pages within 12 hours.

---

## 📋 Preparation Checklist (Before Starting)

To get everything ready, follow these simple steps on your dedicated WhatsApp phone:

### 1. On Your Dedicated Phone
1. **Create the Group**:
   - Open WhatsApp on the dedicated phone.
   - Create a new WhatsApp group (e.g. named `ختمة القرآن الكريم` or any name you like).
   - Add all members (family/friends) who will participate in the daily reading.
2. **(Recommended) Make the Bot Admin**:
   - Ensure the dedicated WhatsApp phone number is an Admin in the group so it can view all participants and message smoothly.

---

## 🚀 Step-by-Step Setup Guide

### Step 1: Run the Interactive Setup Wizard
Run the setup script which will guide you through connecting your account:
```bash
python3 scripts/setup_whatsapp.py
```
1. **Link WhatsApp**:
   - On your phone: Open WhatsApp ➔ **Settings** (or 3 dots) ➔ **Linked Devices** (الأجهزة المرتبطة) ➔ **Link a Device** (ربط جهاز).
   - Scan the QR code displayed in the terminal.
   - *Note*: You only need to scan this once; the session is securely saved locally in `data/session/`.
2. **Select / Confirm Group**:
   - Enter your group JID or group name when prompted.
   - The wizard automatically saves it to `.env` and syncs the member roster to the local database.

---

## 🌐 Web Admin Dashboard Management

You can start, stop, and manage the background Web Admin server using the convenient `./manage.sh` script:

```bash
# Start the web server in the background
./manage.sh start

# Check web server running status & PID
./manage.sh status

# Stop the web server
./manage.sh stop

# Restart the web server
./manage.sh restart

# View live server logs
./manage.sh logs
```

Once started, open your browser at:
👉 **[http://localhost:8080](http://localhost:8080)**

---

## 🏃 Running the Application

### 1. Start the Daily Automation
```bash
python3 src/main.py
```
- The bot will stay active in the background.
- It will automatically post **2 pages at 07:00 AM** every morning (Asia/Riyadh time).
- It tracks reactions in real-time.
- At **07:00 PM** (12 hours later), it checks who hasn't reacted and sends them a polite private DM reminder.

### 2. Trigger Today's Post Immediately (Optional Test)
To post today's pages immediately without waiting for 07:00 AM:
```bash
python3 src/main.py --run-now
```

---

## 🛠️ Handy Management Commands

| Action | Command |
| :--- | :--- |
| **Check Database & Khatmah Progress** | `python3 scripts/init_db.py --status` |
| **Change Next Start Page (e.g. Page 1)** | `python3 scripts/init_db.py --set-page 1` |
| **Change Daily Pages Count (e.g. 4 pages)** | `python3 scripts/init_db.py --set-pages-per-day 4` |
| **Post an Off-The-Plan Surah Immediately** | `python3 scripts/post_surah.py "Mulk"` or `python3 scripts/post_surah.py "Yasin"` |
| **List Group Members & Toggle Exemptions** | `python3 scripts/sync_members.py --list`<br>`python3 scripts/sync_members.py --exempt "PHONE_OR_JID"` |
| **Run Unit Tests** | `python3 -m unittest discover -s tests -v` |
