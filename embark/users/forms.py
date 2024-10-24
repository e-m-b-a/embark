from django import forms
from django.contrib.auth.forms import UserCreationForm
from users.models import User


class SignupForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')


class ActivationForm(forms.Form):

    token = forms.CharField(max_length=256, min_length=256)
