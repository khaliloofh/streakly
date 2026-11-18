from datetime import timedelta, date

from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib import messages
from django.conf import settings as django_settings
from django.http import JsonResponse
from django.db.models import Count

from .models import Task, TaskLog
from .forms import TaskForm
from . import services


def _safe_redirect(request, fallback='home'):
    referer = request.META.get('HTTP_REFERER')
    if referer and referer.startswith(('http://', 'https://', '/')):
        return redirect(referer)
    return redirect(fallback)


def home(request):
    services.rollover_transient_tasks()

    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Task əlavə olundu!')
            return redirect('home')
    else:
        form = TaskForm()

    today = timezone.localdate()
    tasks = Task.objects.filter(is_active=True).order_by('-is_focus', '-created_at')
    task_data = services.get_optimized_task_data(tasks, today=today)

    total_tasks = len(task_data)
    done_today = sum(1 for item in task_data if item['log'] and item['log'].done)
    best_streak = max((item['streak'] for item in task_data), default=0)
    current_streak = services.get_overall_streak(today=today)

    milestone_info = services.get_milestone_info(current_streak)
    heatmap = services.build_optimized_heatmap(weeks=53, today=today)
    week_summary = services.current_week_summary(today=today)
    week_done_sum = sum(d['done'] for d in week_summary)
    week_total_sum = sum(d['total'] for d in week_summary)

    focus_data = [item for item in task_data if item['task'].is_focus]
    quote_data = services.get_quote_for_day(today=today)
    insights = services.get_productivity_insights(today=today)

    context = {
        'task_data': task_data,
        'today': today,
        'form': form,
        'total_tasks': total_tasks,
        'done_today': done_today,
        'best_streak': best_streak,
        'current_streak': current_streak,
        'milestones': milestone_info['milestones'],
        'current_milestone': milestone_info['current_milestone'],
        'next_milestone': milestone_info['next_milestone'],
        'progress_pct': milestone_info['progress_pct'],
        'days_remaining': milestone_info['days_remaining'],
        'week_summary': week_summary,
        'week_done_sum': week_done_sum,
        'week_total_sum': week_total_sum,
        'focus_data': focus_data,
        'heatmap': heatmap,
        'quote': quote_data,
        'insights': insights,
        'active_page': 'dashboard',
    }
    return render(request, 'tracker/home.html', context)


def toggle_done(request, log_id):
    log = get_object_or_404(TaskLog, id=log_id)
    log.done = not log.done
    if log.done:
        log.is_frozen = False
    log.save(update_fields=['done', 'is_frozen'])

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
        streak = log.task.current_streak()
        overall = services.get_overall_streak()
        return JsonResponse({
            'success': True,
            'done': log.done,
            'frozen': log.is_frozen,
            'task_id': log.task.id,
            'streak': streak,
            'overall_streak': overall,
        })

    return _safe_redirect(request, 'home')


def toggle_freeze(request, log_id):
    log = get_object_or_404(TaskLog, id=log_id)
    log.is_frozen = not log.is_frozen
    if log.is_frozen:
        log.done = False
    log.save(update_fields=['is_frozen', 'done'])

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
        return JsonResponse({
            'success': True,
            'frozen': log.is_frozen,
            'done': log.done,
            'task_id': log.task.id,
            'streak': log.task.current_streak(),
        })

    messages.success(request, f'"{log.task.title}" donduruldu.' if log.is_frozen else 'Dondurma ləğv edildi.')
    return _safe_redirect(request, 'home')


def toggle_focus(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    task.is_focus = not task.is_focus
    task.save(update_fields=['is_focus'])
    return _safe_redirect(request, 'home')


def toggle_permanent(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    task.is_permanent = not task.is_permanent
    task.save(update_fields=['is_permanent'])
    return _safe_redirect(request, 'home')


def update_note(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if request.method == 'POST':
        task.note = request.POST.get('note', '').strip()
        task.save(update_fields=['note'])
        messages.success(request, 'Qeyd yeniləndi!')
    return _safe_redirect(request, 'home')


def delete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    task.delete()
    messages.success(request, 'Task silindi.')
    return _safe_redirect(request, 'home')


def history(request):
    today = timezone.localdate()
    logs = (
        TaskLog.objects
        .select_related('task')
        .filter(date__lt=today)
        .order_by('-date', 'task__title')
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
    services.rollover_transient_tasks()

    filter_type = request.GET.get('filter', 'all')
    tasks = Task.objects.filter(is_active=True).order_by('-created_at')
    if filter_type == 'permanent':
        tasks = tasks.filter(is_permanent=True)
    elif filter_type == 'temporary':
        tasks = tasks.filter(is_permanent=False)

    task_data = services.get_optimized_task_data(tasks)

    context = {
        'task_data': task_data,
        'active_filter': filter_type,
        'active_page': 'tasks',
    }
    return render(request, 'tracker/tasks.html', context)


def calendar_view(request, year=None, month=None):
    today = timezone.localdate()
    year = year or today.year
    month = month or today.month

    weeks, first_day = services.build_optimized_calendar(year, month, today=today)

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
    active_tasks = list(Task.objects.filter(is_active=True))

    total_tasks = len(active_tasks)
    total_completed_logs = TaskLog.objects.filter(done=True).count()
    total_logs = TaskLog.objects.count()
    completion_rate = round(total_completed_logs / total_logs * 100) if total_logs else 0

    per_task = []
    task_ids = [t.id for t in active_tasks]
    done_counts_by_task = dict(
        TaskLog.objects.filter(task_id__in=task_ids, done=True)
        .values('task_id')
        .annotate(cnt=Count('id'))
        .values_list('task_id', 'cnt')
    )

    optimized_data = services.get_optimized_task_data(active_tasks)
    for item in optimized_data:
        t = item['task']
        per_task.append({
            'task': t,
            'streak': item['streak'],
            'best_streak': t.best_streak(),
            'completions': done_counts_by_task.get(t.id, 0),
        })
    per_task.sort(key=lambda x: (x['streak'], x['best_streak']), reverse=True)

    best_streak = max((row['streak'] for row in per_task), default=0)
    insights = services.get_productivity_insights(today=timezone.localdate())

    context = {
        'total_tasks': total_tasks,
        'total_completed_logs': total_completed_logs,
        'completion_rate': completion_rate,
        'per_task': per_task,
        'best_streak': best_streak,
        'insights': insights,
        'active_page': 'statistics',
    }
    return render(request, 'tracker/statistics.html', context)


def settings_view(request):
    archived_tasks = Task.objects.filter(is_active=False).order_by('-created_at')
    custom_wall_path = django_settings.BASE_DIR / 'tracker' / 'static' / 'tracker' / 'img' / 'custom-user-wallpaper.png'
    has_custom_wallpaper = custom_wall_path.exists()
    context = {
        'archived_tasks': archived_tasks,
        'time_zone': django_settings.TIME_ZONE,
        'has_custom_wallpaper': has_custom_wallpaper,
        'active_page': 'settings',
    }
    return render(request, 'tracker/settings.html', context)


def upload_wallpaper(request):
    if request.method == 'POST' and request.FILES.get('wallpaper_file'):
        img = request.FILES['wallpaper_file']
        dest = django_settings.BASE_DIR / 'tracker' / 'static' / 'tracker' / 'img' / 'custom-user-wallpaper.png'
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, 'wb+') as f:
            for chunk in img.chunks():
                f.write(chunk)
        messages.success(request, 'Xüsusi arxa plan şəkli yadda saxlanıldı.')
    return redirect('settings')


def reset_wallpaper(request):
    if request.method == 'POST':
        dest = django_settings.BASE_DIR / 'tracker' / 'static' / 'tracker' / 'img' / 'custom-user-wallpaper.png'
        if dest.exists():
            dest.unlink()
        messages.success(request, 'Arxa plan şəkli defolta qaytarıldı.')
    return redirect('settings')


def restore_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    task.is_active = True
    task.save(update_fields=['is_active'])
    TaskLog.objects.get_or_create(task=task, date=timezone.localdate(), defaults={'done': False})
    messages.success(request, 'Task bərpa olundu!')
    return _safe_redirect(request, 'settings')


def reset_all(request):
    if request.method == 'POST':
        TaskLog.objects.all().delete()
        Task.objects.all().delete()
        messages.success(request, 'Bütün data silindi.')
    return redirect('settings')


def export_backup(request):
    import json
    from django.http import HttpResponse
    data = services.export_all_data_to_dict()
    filename = f"streakly_backup_{timezone.localdate().isoformat()}.json"
    response = HttpResponse(
        json.dumps(data, indent=2, ensure_ascii=False),
        content_type='application/json'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def import_backup(request):
    import json
    if request.method == 'POST' and request.FILES.get('backup_file'):
        try:
            content = request.FILES['backup_file'].read().decode('utf-8')
            data = json.loads(content)
            t_cnt, l_cnt = services.import_data_from_dict(data)
            messages.success(request, f"Uğurla {t_cnt} task və {l_cnt} log bərpa edildi!")
        except Exception as e:
            messages.error(request, f"Bərpa zamanı xəta: {str(e)}")
    else:
        messages.error(request, "Zəhmət olmasa düzgün JSON backup faylı seçin.")
    return redirect('settings')


def next_quote(request):
    """Returns a random quote for interactive shuffling."""
    import random
    idx = random.randint(0, len(services.QUOTES) - 1)
    q = services.QUOTES[idx]
    return JsonResponse(q)
