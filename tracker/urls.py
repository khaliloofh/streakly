from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('toggle/<int:log_id>/', views.toggle_done, name='toggle_done'),
    path('delete/<int:task_id>/', views.delete_task, name='delete_task'),
    path('history/', views.history, name='history'),
    path('tasks/', views.tasks_view, name='tasks'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('calendar/<int:year>/<int:month>/', views.calendar_view, name='calendar_month'),
    path('statistics/', views.statistics_view, name='statistics'),
    path('settings/', views.settings_view, name='settings'),
    path('restore/<int:task_id>/', views.restore_task, name='restore_task'),
    path('reset-all/', views.reset_all, name='reset_all'),
]