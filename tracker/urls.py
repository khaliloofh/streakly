from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('toggle/<int:log_id>/', views.toggle_done, name='toggle_done'),
    path('freeze/<int:log_id>/', views.toggle_freeze, name='toggle_freeze'),
    path('focus/<int:task_id>/', views.toggle_focus, name='toggle_focus'),
    path('permanent/<int:task_id>/', views.toggle_permanent, name='toggle_permanent'),
    path('note/<int:task_id>/', views.update_note, name='update_note'),
    path('delete/<int:task_id>/', views.delete_task, name='delete_task'),
    path('history/', views.history, name='history'),
    path('tasks/', views.tasks_view, name='tasks'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('calendar/<int:year>/<int:month>/', views.calendar_view, name='calendar_month'),
    path('statistics/', views.statistics_view, name='statistics'),
    path('settings/', views.settings_view, name='settings'),
    path('restore/<int:task_id>/', views.restore_task, name='restore_task'),
    path('reset-all/', views.reset_all, name='reset_all'),
    path('quote/next/', views.next_quote, name='next_quote'),
    path('backup/export/', views.export_backup, name='export_backup'),
    path('backup/import/', views.import_backup, name='import_backup'),
    path('wallpaper/upload/', views.upload_wallpaper, name='upload_wallpaper'),
    path('wallpaper/reset/', views.reset_wallpaper, name='reset_wallpaper'),
    path('weekly-goal/add/', views.add_weekly_goal, name='add_weekly_goal'),
    path('weekly-goal/toggle/<int:log_id>/', views.toggle_weekly_goal, name='toggle_weekly_goal'),
    path('weekly-goal/delete/<int:goal_id>/', views.delete_weekly_goal, name='delete_weekly_goal'),
    path('weekly-goal/edit/<int:goal_id>/', views.edit_weekly_goal, name='edit_weekly_goal'),
]