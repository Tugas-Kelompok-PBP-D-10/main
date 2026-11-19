
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_protect

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount

from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .forms import RegisterForm


# Mengambil CSRF token untuk autentikasi berbasis session
@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([AllowAny])
def csrf_api(request):
    return Response({
        "csrf_token": get_token(request._request)
    })


# API Register
@api_view(["POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([AllowAny])
@csrf_protect
def register_api(request):
    form = RegisterForm(request.data)

    if form.is_valid():
        user = form.save()

        return Response({
            "success": True,
            "message": "Registrasi berhasil.",
            "username": user.username,
        }, status=status.HTTP_201_CREATED)

    return Response({
        "success": False,
        "errors": dict(form.errors),
    }, status=status.HTTP_400_BAD_REQUEST)


# API Login
@api_view(["POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([AllowAny])
@csrf_protect
def login_api(request):
    form = AuthenticationForm(
        request._request,
        data=request.data
    )

    if form.is_valid():
        user = form.get_user()
        auth_login(request._request, user)

        return Response({
            "success": True,
            "message": "Login berhasil.",
            "username": user.username,
        })

    return Response({
        "success": False,
        "errors": dict(form.errors),
    }, status=status.HTTP_400_BAD_REQUEST)


# API Logout
@api_view(["POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def logout_api(request):
    auth_logout(request._request)

    return Response({
        "success": True,
        "message": "Logout berhasil.",
    })


# API Profile
@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def profile_api(request):
    user = request.user

    email_verified = EmailAddress.objects.filter(
        user=user,
        primary=True,
        verified=True,
    ).exists()

    google_connected = SocialAccount.objects.filter(
        user=user,
        provider="google",
    ).exists()

    return Response({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "email_verified": email_verified,
        "google_connected": google_connected,
    })
