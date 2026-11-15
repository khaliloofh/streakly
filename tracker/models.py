from django.db import models
from django.utils import timezone


class Task(models.Model):
    MUST = 'must'
    BETTER = 'better'
    CATEGORY_CHOICES = [
        (MUST, 'Must do'),
        (BETTER, 'Better do'),
    ]

    title = models.CharField(max_length=200)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default=MUST)
    note = models.TextField(blank=True)
    deadline = models.DateField(null=True, blank=True)
    is_recurring = models.BooleanField(default=True, verbose_name='Hər gün təkrarlansın')
    is_focus = models.BooleanField(default=False, verbose_name="Today's Focus")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title

    def current_streak(self):
        from datetime import timedelta
        streak = 0
        day = timezone.localdate()
        while True:
            log = self.logs.filter(date=day, done=True).first()
            if log:
                streak += 1
                day -= timedelta(days=1)
            else:
                break
        return streak

    def last_n_days(self, n=7):
        from datetime import timedelta
        today = timezone.localdate()
        days = []
        for i in range(n - 1, -1, -1):
            day = today - timedelta(days=i)
            log = self.logs.filter(date=day, done=True).first()
            days.append({'date': day, 'done': bool(log)})
        return days

    def is_overdue(self):
        if self.deadline is None:
            return False
        return self.deadline < timezone.localdate()


class TaskLog(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='logs')
    date = models.DateField()
    done = models.BooleanField(default=False)

    class Meta:
        unique_together = ('task', 'date')

    def __str__(self):
        return f"{self.task.title} - {self.date} - {'done' if self.done else 'not done'}"