from django import forms
from .models import Task, WeeklyGoal


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'note', 'deadline', 'is_permanent']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'e.g. Read, Workout, Code...'
            }),
            'note': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': "Additional details, why it's important..."
            }),
            'deadline': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'is_permanent': 'Permanent',
        }


class WeeklyGoalForm(forms.ModelForm):
    class Meta:
        model = WeeklyGoal
        fields = ['title', 'note']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'e.g. Read 1 book, Call family...'
            }),
            'note': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': "Additional details..."
            }),
        }