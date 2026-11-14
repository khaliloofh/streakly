# Streakly

A minimal, dark-themed habit and task tracker built with Django. Create tasks, mark them done, and keep your streaks going — with history, a calendar view, and a clean dark UI.

## Features

- Must do / Better do task categories, with notes and deadlines
- Recurring or one-time tasks — recurring ones reset daily, one-time ones archive once completed
- Daily reset at midnight, in your local timezone
- Full history, nothing gets overwritten
- Per-task streaks, calculated automatically
- Calendar and statistics views
- Dark, distraction-free interface

## Tech

Python, Django 6.1.3, SQLite, vanilla CSS/JS.

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

Then open http://127.0.0.1:8000.

## Structure

```
streakly/
├── streakly_project/   # Django project settings
├── tracker/             # Main app (models, views, templates)
├── static_icons/
├── manage.py
└── start.sh
```

## Roadmap

- [x] Task creation & categories
- [x] Daily reset & history
- [x] Recurring vs. one-time tasks
- [x] Dashboard redesign (sidebar nav, dark UI)
- [ ] Streak milestones
- [ ] Motivational quotes & small animations
- [ ] Background image / custom themes
