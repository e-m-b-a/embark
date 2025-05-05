# pylint: disable=R0901
__copyright__ = "Copyright 2024-2025 Siemens Energy AG"
__author__ = "Benedikt Kuehne"
__license__ = "MIT"

from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.contrib.auth.forms import (
    UserCreationForm,
    AuthenticationForm,
    PasswordResetForm,
)

from users.models import User


username_validator = UnicodeUsernameValidator()


class SignUpForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=12,
        min_length=4,
        required=False,
        help_text="Optional: First Name",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "First Name"}
        ),
    )

    last_name = forms.CharField(
        max_length=12,
        min_length=4,
        required=False,
        help_text="Optional: Last Name",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    email = forms.EmailField(
        max_length=50,
        help_text="Required. Inform a valid email address.",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        help_text=password_validation.password_validators_help_text_html(),
    )

    password2 = forms.CharField(
        label="Password Confirmation",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        help_text="Just Enter the same password, for confirmation",
    )

    username = forms.CharField(
        label="Username",
        max_length=150,
        help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.",
        validators=[username_validator],
        error_messages={"unique": "A user with that username already exists."},
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    usable_password = None

    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
        )


class LoginForm(AuthenticationForm):
    error_messages = {
        "invalid_login": "Please enter a correct %(username)s and password. Note that both fields may be case-sensitive.",
        "inactive": "This account is not yet activated",
        "deactivated": "Account was deactivated",
    }


class ResetForm(PasswordResetForm):
    pass
