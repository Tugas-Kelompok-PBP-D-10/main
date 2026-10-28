from django.shortcuts import render,redirect
from django.contrib import messages

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount

from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout

from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required

from django.views.decorators.http import require_POST

from .forms import RegisterForm

# Create your views here.

def welcome(request):

    if request.user.is_authenticated:
        return redirect("tracker:tracker")

    return render(request, 'welcome.html')

def register_page(request):

    if request.user.is_authenticated:
        return redirect("tracker:tracker")

    if request.method == "POST":

        form = RegisterForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Registrasi berhasil! Silahkan login.")
            return redirect("authentication:login")

    else:
        form = RegisterForm()

    return render(request, "register.html", {
        "form":form,
    })

def login_page(request):

    if request.user.is_authenticated:
        return redirect("tracker:tracker")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)

        if form.is_valid():
            user = form.get_user()
            auth_login(request,user)
            return redirect("tracker:tracker")

    else:
        form = AuthenticationForm(request)

    form.fields["username"].widget.attrs.update({
        "class": "form-control auth-input",
        "placeholder": "Masukkan username",
        "autocomplete": "username",
    })

    form.fields["password"].widget.attrs.update({
        "class" : "form-control auth-input",
        "placeholder":"Masukkan password",
        "autocomplete": "current-password",
    })

    return render(request, 'login.html',{
        "form":form,
    })

@login_required(login_url="authentication:login")
def dashboard(request):
    return render(request, "dashboard.html")

@require_POST
def logout_page(request):
    auth_logout(request)
    return redirect("authentication:login")

@login_required(login_url="authentication:login")
def profile_page(request):
    user = request.user

    primary_email = EmailAddress.objects.filter(
        user=user,
        primary=True,
    ).first()

    email_verified = bool(
        primary_email and primary_email.verified
    )

    google_connected = SocialAccount.objects.filter(
        user=user,
        provider="google",
    ).exists()

    return render(request, "profile.html", {
        "email_verified": email_verified,
        "google_connected": google_connected,
    })