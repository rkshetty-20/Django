from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Course, Preference, Student


class StudentLoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Username / USN',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your username or USN',
            'id': 'id_username',
        })
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password',
            'id': 'id_password',
        })
    )


class PreferenceForm(forms.Form):
    choice1 = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        label='1st Choice (Highest Priority)',
        widget=forms.Select(attrs={'class': 'form-select pref-select', 'id': 'choice1'}),
        empty_label='— Select your 1st preference —',
    )
    choice2 = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        label='2nd Choice',
        widget=forms.Select(attrs={'class': 'form-select pref-select', 'id': 'choice2'}),
        empty_label='— Select your 2nd preference —',
    )
    choice3 = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        label='3rd Choice (Fallback)',
        widget=forms.Select(attrs={'class': 'form-select pref-select', 'id': 'choice3'}),
        empty_label='— Select your 3rd preference —',
    )

    def clean(self):
        cleaned = super().clean()
        c1 = cleaned.get('choice1')
        c2 = cleaned.get('choice2')
        c3 = cleaned.get('choice3')
        choices = [c for c in [c1, c2, c3] if c]
        if len(choices) != len(set(c.id for c in choices)):
            raise forms.ValidationError('You cannot select the same course more than once.')
        return cleaned