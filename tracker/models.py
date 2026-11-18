from django.db import models
from django.utils import timezone


class Task(models.Model):
    title = models.CharField(max_length=200)
    note = models.TextField(blank=True)
    deadline = models.DateField(null=True, blank=True)
    is_permanent = models.BooleanField(default=False, verbose_name='Permanent')
    is_focus = models.BooleanField(default=False, verbose_name="Today's Focus")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title

    def current_streak(self):
        from datetime import timedelta
        streak = 0
        day = timezone.localdate()
        # grace period: bugün hələ done və ya frozen deyilsə, dünəndən say (streak 0-a düşməsin)
        if not self.logs.filter(date=day).filter(models.Q(done=True) | models.Q(is_frozen=True)).exists():
            day -= timedelta(days=1)
        while True:
            log = self.logs.filter(date=day).filter(models.Q(done=True) | models.Q(is_frozen=True)).first()
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

    def best_streak(self):
        dates = sorted(self.logs.filter(done=True).values_list('date', flat=True))
        if not dates:
            return 0
        from datetime import timedelta
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


class TaskLog(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='logs')
    date = models.DateField()
    done = models.BooleanField(default=False)
    is_frozen = models.BooleanField(default=False, verbose_name="Dondurulub")

    class Meta:
        unique_together = ('task', 'date')

    def __str__(self):
        return f"{self.task.title} - {self.date} - {'done' if self.done else 'not done'}"