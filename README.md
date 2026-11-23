# Streakly

A minimal, aesthetic habit and personal task tracker built with Django. Create permanent habits or daily transient tasks, mark them done with instant snappy animations, track your streaks with a GitHub-style heatmap, and celebrate milestones — all in a customizable dark interface.

## Features

- **Permanent vs. Transient Tasks**: Permanent tasks (habits) persist daily with continuous streak tracking; transient tasks rollover and archive automatically at the end of the day.
- **Grace Period Streaks**: If today's habits aren't checked off yet, your streak safely counts from yesterday without dropping to zero mid-day.
- **Streak Freeze (İstirahət / Dondurma ❄️)**: Xəstələndikdə və ya istirahət günlərində taskı donduraraq zəhmətlə qazanılmış streak-i qorumaq imkanı.
- **Streak Milestones & Badges**: Unlock milestones (3d Sprout 🌱, 7d Momentum ⚡, 14d Habit Former 🚀, 30d Unstoppable 🔥, 60d Iron Will 🛡️, 90d Mastery 👑, 180d Legend 🌟, 365d Grandmaster 🏆) with celebratory particle confetti.
- **Dynamic Motivational Quotes**: Curated stoic and habit wisdom from James Clear, Marcus Aurelius, Bruce Lee, etc., rotating daily or shuffle-able on click.
- **Themes & Themed Wallpapers**: 5 distinct dark themes with matching high-resolution artistic vector wallpapers:
  - 🔥 **Ember** (Default warm charcoal & terracotta with ambient stone art)
  - ⚡ **Cyber** (Deep dark & neon cyan with tech grid & glowing telemetry)
  - 🌲 **Emerald** (Pine obsidian & mint green with organic topographic contours)
  - 🔮 **Amethyst** (Royal violet & bright lavender with crystal constellation geometry)
  - ⚪ **Mono** (Pure minimal graphite & titanium with isometric clean angles)
- **Power-User Keyboard Shortcuts**:
  - `n` — Focus on new task input
  - `1` .. `9` — Instantly toggle task #1 through #9
  - `t` — Cycle through all 5 themes with dynamic wallpaper transitions
  - `?` — Open shortcuts cheat-sheet modal
  - `Esc` — Close modals / blur input
- **Tactile Web Audio Feedback**: Pleasant synthesized audio chime when completing a habit (synthesized via browser Web Audio API, zero external MP3s required; can be toggled in Settings).
- **Ağıllı İnsight-lar & Analitika**: Həftəlik dinamika müqayisəsi, ən məhsuldar gün analizi və 30 günlük intizam/davamlılıq balı.
- **Tam JSON Backup (Export & Import)**: Tək kliklə bütün taskları və tarixçəni JSON faylı kimi yükləmək və ya bərpa etmək.
- **GitHub-Style Heatmap & Calendar**: 53-week visual activity heatmap and monthly calendar views.
- **Snappy Micro-interactions**: AJAX checkmark toggling with zero full-page jump, bounce pop animations, and celebration confetti.
- **High Performance**: 97% reduction in SQL queries (~11 queries per page load down from 420+).
- **Comprehensive Test Suite**: Full unit tests for models, rollover services, streaks, milestones, freeze, backup, and views.

## Tech

Python, Django 6.1.3, SQLite, Vanilla CSS/JS.

## Setup

```bash
git clone https://github.com/khaliloofh/streakly.git
cd streakly
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Then open http://127.0.0.1:2200.

Run unit tests:
```bash
python manage.py test tracker
```

## Structure

```
streakly/
├── streakly_project/   # Django project settings & URLs
├── tracker/            # Main app
│   ├── models.py       # Task & TaskLog models (with streak freeze support)
│   ├── services.py     # High-performance aggregation, heatmap, milestones, insights & backup
│   ├── views.py        # Clean controller views with AJAX, referer & backup support
│   ├── urls.py         # App routing
│   ├── forms.py        # TaskForm
│   ├── tests.py        # Comprehensive 22 unit tests
│   ├── templates/      # Django HTML templates
│   └── static/         # Static assets & wallpapers (Ember, Cyber, Emerald, Amethyst, Mono)
├── static_icons/
├── manage.py
└── start.sh            # Desktop Chrome app launcher
```

## Roadmap

- [x] Task creation & categories
- [x] Daily reset & history
- [x] Recurring (Permanent) vs. one-time (Transient) tasks
- [x] Dashboard redesign (sidebar nav, dark UI)
- [x] Streak milestones & celebratory badges
- [x] Motivational quotes & small animations
- [x] Background image / custom themes & themed vector wallpapers
- [x] Power-user keyboard shortcuts (`n`, `1-9`, `t`, `?`, `Esc`)
- [x] Tactile audio feedback (Web Audio chime)
- [x] Streak freeze & rest day mechanics (❄️)
- [x] JSON Backup (Export / Import)
- [x] Productivity insights & consistency score
