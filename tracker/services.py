from datetime import timedelta, date
from collections import defaultdict
import calendar as cal_module

from django.utils import timezone
from django.db.models import Count, Q
from django.conf import settings as django_settings

from .models import Task, TaskLog

# Curated motivational & habit quotes
QUOTES = [
    {
        "quote": "It's not about motivation, it's about the system.",
        "author": "James Clear"
    },
    {
        "quote": "We are what we repeatedly do. Excellence, then, is not an act, but a habit.",
        "author": "Will Durant"
    },
    {
        "quote": "You do not rise to the level of your goals. You fall to the level of your systems.",
        "author": "James Clear"
    },
    {
        "quote": "Small disciplines repeated with consistency every day lead to great achievements.",
        "author": "John C. Maxwell"
    },
    {
        "quote": "Long-term consistency trumps short-term intensity.",
        "author": "Bruce Lee"
    },
    {
        "quote": "Waste no more time arguing about what a good person should be. Be one.",
        "author": "Marcus Aurelius"
    },
    {
        "quote": "First forget inspiration. Habit is more dependable. Habit will sustain you.",
        "author": "Octavia Butler"
    },
    {
        "quote": "Success is the sum of small efforts, repeated day in and day out.",
        "author": "Robert Collier"
    },
    {
        "quote": "Discipline equals freedom.",
        "author": "Jocko Willink"
    },
    {
        "quote": "Don't count the days, make the days count.",
        "author": "Muhammad Ali"
    },
    {
        "quote": "He who conquers himself is the mightiest warrior.",
        "author": "Confucius"
    },
    {
        "quote": "Action is the foundational key to all success.",
        "author": "Pablo Picasso"
    },
]

MILESTONES = [
    {"days": 3, "title": "Sprout", "icon": "3D", "badge": "3 Days"},
    {"days": 7, "title": "Momentum", "icon": "7D", "badge": "1 Week"},
    {"days": 14, "title": "Habit Former", "icon": "14D", "badge": "2 Weeks"},
    {"days": 30, "title": "Unstoppable", "icon": "30D", "badge": "1 Month"},
    {"days": 60, "title": "Iron Will", "icon": "60D", "badge": "2 Months"},
    {"days": 90, "title": "Mastery", "icon": "90D", "badge": "3 Months"},
    {"days": 180, "title": "Legend", "icon": "180D", "badge": "6 Months"},
    {"days": 365, "title": "Grandmaster", "icon": "365D", "badge": "1 Year"},
]


def get_quote_for_day(today=None, index=None):
    """Returns a deterministic quote for the current day, or a specific index."""
    if not QUOTES:
        return {"quote": "Keep moving forward.", "author": "Anonymous"}
    if index is not None:
        return QUOTES[index % len(QUOTES)]
    today = today or timezone.localdate()
    # Use day of year to deterministically select a quote per day
    day_number = today.toordinal()
    return QUOTES[day_number % len(QUOTES)]


def get_milestone_info(current_streak):
    """Calculates milestone achievement statuses, next target, and progress."""
    result_milestones = []
    current_milestone = None
    next_milestone = None

    for m in MILESTONES:
        reached = current_streak >= m["days"]
        item = {
            "days": m["days"],
            "title": m["title"],
            "icon": m["icon"],
            "badge": m["badge"],
            "reached": reached,
        }
        result_milestones.append(item)
        if reached:
            current_milestone = item
        elif next_milestone is None:
            next_milestone = item

    if next_milestone:
        prev_target = current_milestone["days"] if current_milestone else 0
        span = next_milestone["days"] - prev_target
        current_in_span = max(0, current_streak - prev_target)
        progress_pct = min(100, round((current_in_span / span) * 100)) if span > 0 else 100
        days_remaining = next_milestone["days"] - current_streak
    else:
        progress_pct = 100
        days_remaining = 0

    return {
        "milestones": result_milestones,
        "current_milestone": current_milestone,
        "next_milestone": next_milestone,
        "progress_pct": progress_pct,
        "days_remaining": days_remaining,
    }


def rollover_transient_tasks(today=None):
    """Keçici (is_permanent=False) task-ları gün dəyişəndə aktiv siyahıdan çıxarır.
    TaskLog tarixçəsi silinmir — History/Settings-də qalır."""
    today = today or timezone.localdate()
    transient_tasks = Task.objects.filter(is_active=True, is_permanent=False)
    for task in transient_tasks:
        last_log = task.logs.order_by('-date').first()
        if last_log is not None and last_log.date < today:
            task.is_active = False
            task.save(update_fields=['is_active'])


def get_optimized_task_data(tasks, today=None):
    """Fetches tasks and their corresponding logs in batch to avoid N+1 queries.
    Computes streaks and last 7 days entirely in Python memory."""
    today = today or timezone.localdate()
    task_list = list(tasks)
    if not task_list:
        return []

    task_ids = [t.id for t in task_list]

    # 1. Fetch or create today's logs in batch
    existing_today_logs = {
        log.task_id: log
        for log in TaskLog.objects.filter(task_id__in=task_ids, date=today)
    }

    missing_logs = []
    for task in task_list:
        if task.id not in existing_today_logs:
            missing_logs.append(TaskLog(task=task, date=today, done=False))

    if missing_logs:
        TaskLog.objects.bulk_create(missing_logs, ignore_conflicts=True)
        # Re-fetch any created ones
        for log in TaskLog.objects.filter(task_id__in=task_ids, date=today):
            existing_today_logs[log.task_id] = log

    # 2. Fetch all done OR frozen dates for these tasks in a single query
    done_dates_by_task = defaultdict(set)
    for task_id, d in TaskLog.objects.filter(task_id__in=task_ids).filter(Q(done=True) | Q(is_frozen=True)).values_list('task_id', 'date'):
        done_dates_by_task[task_id].add(d)

    # 3. Compute streaks and last 7 days in memory
    last_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]

    task_data = []
    for task in task_list:
        done_dates = done_dates_by_task[task.id]

        # Streak calculation with grace period
        streak = 0
        day = today
        if day not in done_dates:
            day -= timedelta(days=1)
        while day in done_dates:
            streak += 1
            day -= timedelta(days=1)

        # 7-day mini heatmap
        week = [{'date': d, 'done': d in done_dates} for d in last_7_days]

        task_data.append({
            'task': task,
            'log': existing_today_logs.get(task.id),
            'streak': streak,
            'week': week,
        })

    return task_data


def calculate_best_streak_for_task(task_id):
    """Calculates the all-time maximum consecutive days streak for a task."""
    dates = sorted(TaskLog.objects.filter(task_id=task_id, done=True).values_list('date', flat=True))
    if not dates:
        return 0

    best = 1
    current = 1
    for i in range(1, len(dates)):
        if dates[i] == dates[i - 1] + timedelta(days=1):
            current += 1
            if current > best:
                best = current
        elif dates[i] > dates[i - 1] + timedelta(days=1):
            current = 1
    return best


def get_overall_streak(today=None):
    """Ümumi 'Day Streak': bütün aktiv Permanent task-ların o gün 100% done
    olduğu, bu gündən geriyə ardıcıl gün sayı. Grace period: bu gün hələ
    tam bitirilməyibsə, dünəndən sayır (0'lanmasın). Optimized to 2 SQL queries."""
    today = today or timezone.localdate()
    permanent_tasks = list(Task.objects.filter(is_permanent=True, is_active=True))
    if not permanent_tasks:
        return 0

    perm_ids = [t.id for t in permanent_tasks]
    creation_dates = [t.created_at.date() for t in permanent_tasks]

    # Pre-fetch counts of done OR frozen permanent tasks by date
    done_by_date = dict(
        TaskLog.objects.filter(task_id__in=perm_ids)
        .filter(Q(done=True) | Q(is_frozen=True))
        .values('date')
        .annotate(cnt=Count('id'))
        .values_list('date', 'cnt')
    )

    def tasks_count_on(day):
        return sum(1 for cdate in creation_dates if cdate <= day)

    # Check today
    tasks_today = tasks_count_on(today)
    done_today = done_by_date.get(today, 0)

    day = today
    if tasks_today == 0 or done_today < tasks_today:
        day -= timedelta(days=1)

    streak = 0
    while True:
        needed = tasks_count_on(day)
        if needed == 0:
            break
        actual = done_by_date.get(day, 0)
        if actual < needed:
            break
        streak += 1
        day -= timedelta(days=1)

    return streak


def build_optimized_heatmap(weeks=53, today=None):
    """Builds the 53-week GitHub-style heatmap with 2 queries instead of 370+."""
    today = today or timezone.localdate()
    start = today - timedelta(weeks=weeks - 1)
    start -= timedelta(days=start.weekday())

    # Pre-fetch all task creation dates
    creation_dates = list(Task.objects.values_list('created_at__date', flat=True))
    creation_dates.sort()

    # Pre-fetch done count per date in range
    done_counts = dict(
        TaskLog.objects.filter(date__gte=start, date__lte=today, done=True)
        .values('date')
        .annotate(cnt=Count('id'))
        .values_list('date', 'cnt')
    )

    import bisect

    def count_tasks_created_by(day):
        # bisect_right returns number of items <= day
        return bisect.bisect_right(creation_dates, day)

    week_list = []
    last_month = None
    day = start
    for _ in range(weeks):
        days = []
        for _ in range(7):
            total = count_tasks_created_by(day)
            if total == 0:
                percent = None
                level = 0
            else:
                done = done_counts.get(day, 0)
                percent = round((done / total) * 100)
                if percent <= 0:
                    level = 0
                elif percent <= 25:
                    level = 1
                elif percent <= 50:
                    level = 2
                elif percent <= 75:
                    level = 3
                else:
                    level = 4
            days.append({'date': day, 'percent': percent, 'level': level})
            day += timedelta(days=1)

        month_name = days[0]['date'].strftime('%b').lower()
        label = month_name if month_name != last_month else None
        last_month = month_name
        week_list.append({'days': days, 'label': label})

    return week_list


def current_week_summary(today=None):
    """Cari həftə (Bazar ertəsi - Bazar) xülasəsi."""
    today = today or timezone.localdate()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

    creation_dates = list(Task.objects.values_list('created_at__date', flat=True))
    creation_dates.sort()

    done_counts = dict(
        TaskLog.objects.filter(date__gte=monday, date__lte=sunday, done=True)
        .values('date')
        .annotate(cnt=Count('id'))
        .values_list('date', 'cnt')
    )

    import bisect

    days = []
    for i in range(7):
        day = monday + timedelta(days=i)
        total = bisect.bisect_right(creation_dates, day)
        done = done_counts.get(day, 0)
        days.append({
            'label': labels[i],
            'date': day,
            'done': done,
            'total': total,
            'is_today': day == today,
        })
    return days


def build_optimized_calendar(year, month, today=None):
    """Builds calendar month grid with 2 queries."""
    today = today or timezone.localdate()
    first_day = date(year, month, 1)

    cal_obj = cal_module.Calendar(firstweekday=0)
    month_matrix = cal_obj.monthdatescalendar(year, month)
    start_date = month_matrix[0][0]
    end_date = month_matrix[-1][-1]

    creation_dates = list(Task.objects.values_list('created_at__date', flat=True))
    creation_dates.sort()

    done_counts = dict(
        TaskLog.objects.filter(date__gte=start_date, date__lte=end_date, done=True)
        .values('date')
        .annotate(cnt=Count('id'))
        .values_list('date', 'cnt')
    )

    import bisect

    weeks = []
    for week in month_matrix:
        week_days = []
        for day in week:
            in_month = (day.month == month)
            total = bisect.bisect_right(creation_dates, day)
            if total == 0:
                percent = None
                level = 0
            else:
                done = done_counts.get(day, 0)
                percent = round(done / total * 100)
                if percent <= 0:
                    level = 0
                elif percent <= 25:
                    level = 1
                elif percent <= 50:
                    level = 2
                elif percent <= 75:
                    level = 3
                else:
                    level = 4
            week_days.append({
                'date': day,
                'in_month': in_month,
                'percent': percent,
                'level': level,
                'is_today': day == today,
            })
        weeks.append(week_days)

    return weeks, first_day


def get_productivity_insights(today=None):
    today = today or timezone.localdate()
    # 1. Day of week breakdown across past 90 days
    start_90 = today - timedelta(days=90)
    logs_90 = list(TaskLog.objects.filter(date__gte=start_90, date__lte=today))

    weekday_names = ["Bazar ertəsi", "Çərşənbə axşamı", "Çərşənbə", "Cümə axşamı", "Cümə", "Şənbə", "Bazar"]
    weekday_stats = defaultdict(lambda: {"total": 0, "done": 0})
    for l in logs_90:
        w = l.date.weekday()
        weekday_stats[w]["total"] += 1
        if l.done or l.is_frozen:
            weekday_stats[w]["done"] += 1

    best_day_idx = 0
    best_rate = -1
    for w in range(7):
        st = weekday_stats[w]
        rate = round((st["done"] / st["total"]) * 100) if st["total"] > 0 else 0
        if rate > best_rate and st["total"] > 0:
            best_rate = rate
            best_day_idx = w

    best_day_str = f"{weekday_names[best_day_idx]} ({best_rate}%)" if best_rate >= 0 else "Hələ məlumat kifayət deyil"

    # 2. Week comparison (This week vs Last week)
    monday_this_week = today - timedelta(days=today.weekday())
    monday_last_week = monday_this_week - timedelta(days=7)
    sunday_last_week = monday_this_week - timedelta(days=1)

    done_this_week = TaskLog.objects.filter(date__gte=monday_this_week, date__lte=today, done=True).count()
    done_last_week = TaskLog.objects.filter(date__gte=monday_last_week, date__lte=sunday_last_week, done=True).count()

    if done_last_week > 0:
        diff_pct = round(((done_this_week - done_last_week) / done_last_week) * 100)
    else:
        diff_pct = 100 if done_this_week > 0 else 0

    # 3. Consistency score (0 - 100) over last 30 days
    start_30 = today - timedelta(days=30)
    total_30 = TaskLog.objects.filter(date__gte=start_30, date__lte=today).count()
    done_30 = TaskLog.objects.filter(date__gte=start_30, date__lte=today).filter(Q(done=True) | Q(is_frozen=True)).count()
    consistency_score = round((done_30 / total_30) * 100) if total_30 > 0 else 100

    return {
        "best_day": best_day_str,
        "done_this_week": done_this_week,
        "done_last_week": done_last_week,
        "diff_pct": diff_pct,
        "consistency_score": consistency_score,
    }


def export_all_data_to_dict():
    tasks = Task.objects.prefetch_related('logs').all().order_by('id')
    task_list = []
    for t in tasks:
        task_list.append({
            "title": t.title,
            "note": t.note,
            "deadline": t.deadline.isoformat() if t.deadline else None,
            "is_permanent": t.is_permanent,
            "is_focus": t.is_focus,
            "is_active": t.is_active,
            "created_at": t.created_at.isoformat(),
            "logs": [
                {
                    "date": l.date.isoformat(),
                    "done": l.done,
                    "is_frozen": l.is_frozen,
                }
                for l in t.logs.all().order_by('date')
            ]
        })
    return {
        "app": "Streakly",
        "version": "1.2",
        "exported_at": timezone.now().isoformat(),
        "tasks": task_list,
    }


def import_data_from_dict(data):
    if not isinstance(data, dict) or "tasks" not in data:
        raise ValueError("Yedək faylının formatı düzgün deyil.")

    created_tasks_count = 0
    created_logs_count = 0
    for t_data in data["tasks"]:
        title = t_data.get("title", "").strip()
        if not title:
            continue
        deadline_str = t_data.get("deadline")
        deadline = date.fromisoformat(deadline_str) if deadline_str else None

        task = Task.objects.create(
            title=title,
            note=t_data.get("note", ""),
            deadline=deadline,
            is_permanent=t_data.get("is_permanent", False),
            is_focus=t_data.get("is_focus", False),
            is_active=t_data.get("is_active", True),
        )
        created_tasks_count += 1

        logs_to_create = []
        for l_data in t_data.get("logs", []):
            d_str = l_data.get("date")
            if d_str:
                d = date.fromisoformat(d_str)
                logs_to_create.append(TaskLog(
                    task=task,
                    date=d,
                    done=l_data.get("done", False),
                    is_frozen=l_data.get("is_frozen", False),
                ))
        if logs_to_create:
            TaskLog.objects.bulk_create(logs_to_create, ignore_conflicts=True)
            created_logs_count += len(logs_to_create)

    return created_tasks_count, created_logs_count
