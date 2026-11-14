from datetime import timedelta, date
import calendar as cal_module

from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib import messages
from django.conf import settings as django_settings

from .models import Task, TaskLog
from .forms import TaskForm


def build_heatmap(weeks=53):
    today = timezone.localdate()
    start = today - timedelta(weeks=weeks - 1)
    start -= timedelta(days=start.weekday())

    all_tasks = Task.objects.all()

    week_list = []
    last_month = None
    day = start
    for w in range(weeks):
        days = []
        for d in range(7):
            tasks_that_day = all_tasks.filter(created_at__date__lte=day)
            total = tasks_that_day.count()
            if total == 0:
                percent = None
                level = 0
            else:
                done = TaskLog.objects.filter(task__in=tasks_that_day, date=day, done=True).count()
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
            days.append({'date': day, 'percent': percent, 'level': level})
            day += timedelta(days=1)

        month_name = days[0]['date'].strftime('%b').lower()
        label = month_name if month_name != last_month else None
        last_month = month_name
        week_list.append({'days': days, 'label': label})

    return week_list


def get_task_data(tasks):
    today = timezone.localdate()
    data = []
    for task in tasks:
        if task.is_recurring:
            log, _ = TaskLog.objects.get_or_create(task=task, date=today)
        else:
            log = task.logs.order_by('-date').first()
            if log is None:
                log = TaskLog.objects.create(task=task, date=today, done=False)
        data.append({
            'task': task,
            'log': log,
            'streak': task.current_streak(),
            'week': task.last_n_days(7),
        })
    return data


def home(request):
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Task əlavə olundu!')
            return redirect('home')
    else:
        form = TaskForm()

    today = timezone.localdate()
    tasks = Task.objects.filter(is_active=True)
    task_data = get_task_data(tasks)

    total_tasks = len(task_data)
    done_today = sum(1 for item in task_data if item['log'].done)
    best_streak = max((item['streak'] for item in task_data), default=0)
    heatmap = build_heatmap(weeks=53)

    context = {
        'task_data': task_data,
        'today': today,
        'form': form,
        'total_tasks': total_tasks,
        'done_today': done_today,
        'best_streak': best_streak,
        'heatmap': heatmap,
        'active_page': 'dashboard',
    }
    return render(request, 'tracker/home.html', context)


def toggle_done(request, log_id):
    log = get_object_or_404(TaskLog, id=log_id)
    log.done = not log.done

    if log.done and not log.task.is_recurring:
        log.date = timezone.localdate()
        log.task.is_active = False
        log.task.save()

    log.save()
    return redirect('home')


def delete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    task.delete()
    return redirect('home')


def history(request):
    today = timezone.localdate()
    logs = (
        TaskLog.objects
        .select_related('task')
        .filter(date__lt=today)
        .order_by('-date')
    )

    days = {}
    ordered_dates = []
    for log in logs:
        if log.date not in days:
            days[log.date] = {'date': log.date, 'completed': 0, 'total': 0, 'items': []}
            ordered_dates.append(log.date)
        days[log.date]['total'] += 1
        if log.done:
            days[log.date]['completed'] += 1
        days[log.date]['items'].append(log)

    history_data = [days[d] for d in ordered_dates]

    context = {
        'history_data': history_data,
        'active_page': 'history',
    }
    return render(request, 'tracker/history.html', context)


def tasks_view(request):
    category = request.GET.get('category', 'all')
    tasks = Task.objects.filter(is_active=True)
    if category in ('must', 'better'):
        tasks = tasks.filter(category=category)
    task_data = get_task_data(tasks)

    context = {
        'task_data': task_data,
        'active_category': category,
        'active_page': 'tasks',
    }
    return render(request, 'tracker/tasks.html', context)


def calendar_view(request, year=None, month=None):
    today = timezone.localdate()
    year = year or today.year
    month = month or today.month

    first_day = date(year, month, 1)
    all_tasks = Task.objects.all()

    weeks = []
    cal_obj = cal_module.Calendar(firstweekday=0)
    for week in cal_obj.monthdatescalendar(year, month):
        week_days = []
        for day in week:
            in_month = day.month == month
            tasks_that_day = all_tasks.filter(created_at__date__lte=day)
            total = tasks_that_day.count()
            if total == 0:
                percent = None
                level = 0
            else:
                done = TaskLog.objects.filter(task__in=tasks_that_day, date=day, done=True).count()
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

    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    context = {
        'weeks': weeks,
        'month_name': first_day.strftime('%B %Y'),
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year,
        'next_month': next_month,
        'active_page': 'calendar',
    }
    return render(request, 'tracker/calendar.html', context)


def statistics_view(request):
    active_tasks = Task.objects.filter(is_active=True)

    total_tasks = active_tasks.count()
    total_completed_logs = TaskLog.objects.filter(done=True).count()
    total_logs = TaskLog.objects.count()
    completion_rate = round(total_completed_logs / total_logs * 100) if total_logs else 0

    per_task = []
    for task in active_tasks:
        per_task.append({
            'task': task,
            'streak': task.current_streak(),
            'completions': task.logs.filter(done=True).count(),
        })
    per_task.sort(key=lambda x: x['streak'], reverse=True)

    best_streak = per_task[0]['streak'] if per_task else 0

    context = {
        'total_tasks': total_tasks,
        'total_completed_logs': total_completed_logs,
        'completion_rate': completion_rate,
        'per_task': per_task,
        'best_streak': best_streak,
        'active_page': 'statistics',
    }
    return render(request, 'tracker/statistics.html', context)


def settings_view(request):
    archived_tasks = Task.objects.filter(is_active=False).order_by('-created_at')
    context = {
        'archived_tasks': archived_tasks,
        'time_zone': django_settings.TIME_ZONE,
        'active_page': 'settings',
    }
    return render(request, 'tracker/settings.html', context)


def restore_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    task.is_active = True
    task.save()
    if not task.is_recurring:
        TaskLog.objects.get_or_create(task=task, date=timezone.localdate(), defaults={'done': False})
    messages.success(request, 'Task bərpa olundu!')
    return redirect('settings')


def reset_all(request):
    if request.method == 'POST':
        TaskLog.objects.all().delete()
        Task.objects.all().delete()
        messages.success(request, 'Bütün data silindi.')
    return redirect('settings')