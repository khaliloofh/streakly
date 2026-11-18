from datetime import timedelta, date

from django.test import TestCase, Client
from django.utils import timezone
from django.urls import reverse

from .models import Task, TaskLog
from . import services


class TaskModelTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.task = Task.objects.create(
            title="Read 20 pages",
            note="Focus on non-fiction",
            deadline=self.today + timedelta(days=5),
            is_permanent=True,
            is_focus=False,
        )

    def test_task_creation(self):
        self.assertEqual(str(self.task), "Read 20 pages")
        self.assertTrue(self.task.is_active)
        self.assertTrue(self.task.is_permanent)

    def test_is_overdue(self):
        self.assertFalse(self.task.is_overdue())
        self.task.deadline = self.today - timedelta(days=1)
        self.assertTrue(self.task.is_overdue())
        self.task.deadline = None
        self.assertFalse(self.task.is_overdue())

    def test_current_streak_with_grace_period(self):
        # Done yesterday, not yet done today -> streak should be 1 (grace period)
        yesterday = self.today - timedelta(days=1)
        TaskLog.objects.create(task=self.task, date=yesterday, done=True)
        self.assertEqual(self.task.current_streak(), 1)

        # Done today as well -> streak should be 2
        TaskLog.objects.create(task=self.task, date=self.today, done=True)
        self.assertEqual(self.task.current_streak(), 2)

    def test_best_streak(self):
        # 3 consecutive days in the past
        past_start = self.today - timedelta(days=20)
        for i in range(3):
            TaskLog.objects.create(task=self.task, date=past_start + timedelta(days=i), done=True)

        self.assertEqual(self.task.best_streak(), 3)

        # 4 consecutive days more recently
        recent_start = self.today - timedelta(days=5)
        for i in range(4):
            TaskLog.objects.create(task=self.task, date=recent_start + timedelta(days=i), done=True)

        self.assertEqual(self.task.best_streak(), 4)


class ServicesTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.perm_task = Task.objects.create(
            title="Permanent Workout",
            is_permanent=True,
            is_active=True,
        )
        self.trans_task = Task.objects.create(
            title="Temporary Errand",
            is_permanent=False,
            is_active=True,
        )

    def test_rollover_transient_tasks(self):
        yesterday = self.today - timedelta(days=1)
        TaskLog.objects.create(task=self.trans_task, date=yesterday, done=True)
        TaskLog.objects.create(task=self.perm_task, date=yesterday, done=True)

        services.rollover_transient_tasks(today=self.today)

        self.trans_task.refresh_from_db()
        self.perm_task.refresh_from_db()

        # Transient task should be deactivated
        self.assertFalse(self.trans_task.is_active)
        # Permanent task must remain active
        self.assertTrue(self.perm_task.is_active)

    def test_milestone_info(self):
        info_zero = services.get_milestone_info(0)
        self.assertEqual(info_zero["progress_pct"], 0)
        self.assertEqual(info_zero["days_remaining"], 3)
        self.assertIsNone(info_zero["current_milestone"])
        self.assertEqual(info_zero["next_milestone"]["days"], 3)

        info_five = services.get_milestone_info(5)
        self.assertEqual(info_five["current_milestone"]["days"], 3)
        self.assertEqual(info_five["next_milestone"]["days"], 7)
        self.assertEqual(info_five["days_remaining"], 2)
        self.assertEqual(info_five["progress_pct"], 50)

    def test_overall_streak_calculation(self):
        past_date = timezone.now() - timedelta(days=5)
        Task.objects.filter(id=self.perm_task.id).update(created_at=past_date)

        yesterday = self.today - timedelta(days=1)
        day_before = self.today - timedelta(days=2)

        TaskLog.objects.create(task=self.perm_task, date=day_before, done=True)
        TaskLog.objects.create(task=self.perm_task, date=yesterday, done=True)

        streak = services.get_overall_streak(today=self.today)
        self.assertEqual(streak, 2)

    def test_optimized_heatmap_and_week_summary(self):
        heatmap = services.build_optimized_heatmap(weeks=10, today=self.today)
        self.assertEqual(len(heatmap), 10)
        for week in heatmap:
            self.assertEqual(len(week['days']), 7)

        summary = services.current_week_summary(today=self.today)
        self.assertEqual(len(summary), 7)


class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.today = timezone.localdate()
        self.task = Task.objects.create(
            title="Daily Coding",
            is_permanent=True,
            is_active=True,
        )
        self.log = TaskLog.objects.create(
            task=self.task,
            date=self.today,
            done=False,
        )

    def test_home_view(self):
        res = self.client.get(reverse('home'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Daily Coding")

    def test_create_task_via_post(self):
        res = self.client.post(reverse('home'), {
            'title': 'New Test Task',
            'note': 'Test note',
            'is_permanent': 'on',
        })
        self.assertEqual(res.status_code, 302)
        self.assertTrue(Task.objects.filter(title='New Test Task').exists())

    def test_toggle_done_normal_and_ajax(self):
        # Normal GET redirect
        res = self.client.get(reverse('toggle_done', args=[self.log.id]))
        self.assertEqual(res.status_code, 302)
        self.log.refresh_from_db()
        self.assertTrue(self.log.done)

        # AJAX request returns JSON
        ajax_res = self.client.get(
            reverse('toggle_done', args=[self.log.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(ajax_res.status_code, 200)
        data = ajax_res.json()
        self.assertTrue(data['success'])
        self.assertFalse(data['done'])

    def test_toggle_focus(self):
        self.assertFalse(self.task.is_focus)
        res = self.client.get(reverse('toggle_focus', args=[self.task.id]))
        self.assertEqual(res.status_code, 302)
        self.task.refresh_from_db()
        self.assertTrue(self.task.is_focus)

    def test_toggle_permanent(self):
        self.assertTrue(self.task.is_permanent)
        res = self.client.get(reverse('toggle_permanent', args=[self.task.id]))
        self.assertEqual(res.status_code, 302)
        self.task.refresh_from_db()
        self.assertFalse(self.task.is_permanent)

    def test_update_note(self):
        res = self.client.post(
            reverse('update_note', args=[self.task.id]),
            {'note': 'Updated notes content'},
        )
        self.assertEqual(res.status_code, 302)
        self.task.refresh_from_db()
        self.assertEqual(self.task.note, 'Updated notes content')

    def test_delete_and_restore(self):
        # Delete task
        res = self.client.get(reverse('delete_task', args=[self.task.id]))
        self.assertEqual(res.status_code, 302)
        self.assertFalse(Task.objects.filter(id=self.task.id).exists())

        # Test restore of an inactive task
        inactive_task = Task.objects.create(title="Archived Task", is_active=False)
        restore_res = self.client.get(reverse('restore_task', args=[inactive_task.id]))
        self.assertEqual(restore_res.status_code, 302)
        inactive_task.refresh_from_db()
        self.assertTrue(inactive_task.is_active)

    def test_tasks_view_filtering(self):
        Task.objects.create(title="Transient 1", is_permanent=False, is_active=True)
        res_all = self.client.get(reverse('tasks'))
        self.assertEqual(res_all.status_code, 200)
        self.assertContains(res_all, "Daily Coding")
        self.assertContains(res_all, "Transient 1")

        res_perm = self.client.get(reverse('tasks') + '?filter=permanent')
        self.assertContains(res_perm, "Daily Coding")
        self.assertNotContains(res_perm, "Transient 1")

        res_temp = self.client.get(reverse('tasks') + '?filter=temporary')
        self.assertNotContains(res_temp, "Daily Coding")
        self.assertContains(res_temp, "Transient 1")

    def test_calendar_and_statistics(self):
        cal_res = self.client.get(reverse('calendar'))
        self.assertEqual(cal_res.status_code, 200)

        stat_res = self.client.get(reverse('statistics'))
        self.assertEqual(stat_res.status_code, 200)
        self.assertContains(stat_res, "Daily Coding")

    def test_next_quote(self):
        res = self.client.get(reverse('next_quote'))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn('quote', data)
        self.assertIn('author', data)

    def test_reset_all(self):
        res = self.client.post(reverse('reset_all'))
        self.assertEqual(res.status_code, 302)
        self.assertEqual(Task.objects.count(), 0)
        self.assertEqual(TaskLog.objects.count(), 0)

    def test_toggle_freeze(self):
        self.assertFalse(self.log.is_frozen)
        res = self.client.get(reverse('toggle_freeze', args=[self.log.id]))
        self.assertEqual(res.status_code, 302)
        self.log.refresh_from_db()
        self.assertTrue(self.log.is_frozen)

        # AJAX toggle freeze
        ajax_res = self.client.get(
            reverse('toggle_freeze', args=[self.log.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(ajax_res.status_code, 200)
        data = ajax_res.json()
        self.assertTrue(data['success'])
        self.assertFalse(data['frozen'])

    def test_backup_export_and_import(self):
        import json
        from io import BytesIO
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Export
        export_res = self.client.get(reverse('export_backup'))
        self.assertEqual(export_res.status_code, 200)
        self.assertEqual(export_res['Content-Type'], 'application/json')
        data = json.loads(export_res.content.decode('utf-8'))
        self.assertIn('tasks', data)

        # Import
        backup_content = json.dumps({
            "version": "1.2",
            "tasks": [
                {
                    "title": "Imported Task",
                    "note": "Imported Note",
                    "is_permanent": True,
                    "logs": [{"date": self.today.isoformat(), "done": True, "is_frozen": False}]
                }
            ]
        }).encode('utf-8')
        uploaded = SimpleUploadedFile("backup.json", backup_content, content_type="application/json")
        import_res = self.client.post(reverse('import_backup'), {'backup_file': uploaded})
        self.assertEqual(import_res.status_code, 302)
        self.assertTrue(Task.objects.filter(title="Imported Task").exists())

    def test_productivity_insights_service(self):
        insights = services.get_productivity_insights(today=self.today)
        self.assertIn('best_day', insights)
        self.assertIn('done_this_week', insights)
        self.assertIn('consistency_score', insights)

    def test_wallpaper_upload_and_reset(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        upload_file = SimpleUploadedFile("my_wall.png", fake_png, content_type="image/png")
        res = self.client.post(reverse('upload_wallpaper'), {'wallpaper_file': upload_file})
        self.assertEqual(res.status_code, 302)

        reset_res = self.client.post(reverse('reset_wallpaper'))
        self.assertEqual(reset_res.status_code, 302)
