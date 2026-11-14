from django import forms
from .models import Task


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'category', 'note', 'deadline', 'is_recurring']
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
            'is_recurring': 'Hər gün təkrarlansın',
        }