
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class RegisterForm(UserCreationForm):

    email = forms.EmailField(
        required=True,
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "placeholder": "Masukkan email",
                "autocomplete": "email",
            }
        ),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Berikan styling yang sama kepada semua input.
        for field in self.fields.values():
            field.widget.attrs["class"] = "input-control"

        placeholders = {
            "username": "Masukkan username",
            "password1": "Masukkan password",
            "password2": "Konfirmasi password",
        }

        for field_name, placeholder in placeholders.items():
            self.fields[field_name].widget.attrs["placeholder"] = placeholder

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "Email ini sudah digunakan."
            )

        return email

    def save(self, commit=True):
        user = super().save(commit=False)

        user.email = self.cleaned_data["email"]

        if commit:
            user.save()

        return user
