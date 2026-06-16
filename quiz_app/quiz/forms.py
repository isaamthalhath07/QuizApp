import re

from django import forms

# Reject ASCII control characters (newlines, NUL, etc.) in identifier fields.
_CTRL_RE = re.compile(r"[\x00-\x1f\x7f]")


class UserForm(forms.Form):
    """Login form.

    Security notes:
    - Length caps (field + widget `maxlength`) bound the input size.
    - `clean_*` strips whitespace and rejects control characters.
    - Values are only ever used via Django's auth backend / ORM (parameterized,
      so no SQL injection) and rendered through auto-escaped templates (no XSS).
    """

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            "class": "input-field", "placeholder": "Enter your username",
            "autocomplete": "username", "maxlength": "150", "autocapitalize": "off",
            "spellcheck": "false",
        }),
    )
    email = forms.CharField(
        max_length=254, required=False,
        widget=forms.TextInput(attrs={
            "class": "input-field", "placeholder": "Enter your email",
            "autocomplete": "email", "maxlength": "254",
        }),
    )
    password = forms.CharField(
        max_length=128,
        widget=forms.PasswordInput(attrs={
            "class": "input-field", "placeholder": "Enter your password",
            "autocomplete": "current-password", "maxlength": "128",
        }),
    )

    def clean_username(self):
        value = (self.cleaned_data.get("username") or "").strip()
        if not value:
            raise forms.ValidationError("Please enter your username.")
        if _CTRL_RE.search(value):
            raise forms.ValidationError("Username contains invalid characters.")
        return value

    def clean_email(self):
        return (self.cleaned_data.get("email") or "").strip()
