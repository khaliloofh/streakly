#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate

if ! curl -s http://127.0.0.1:2200 > /dev/null; then
    nohup python manage.py runserver > /tmp/streakly.log 2>&1 &
    sleep 1.5
fi

google-chrome-stable --app=http://127.0.0.1:2200