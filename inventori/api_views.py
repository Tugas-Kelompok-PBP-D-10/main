from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view, authentication_classes, permission_classes,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Inventori, Bahan
from .serializers import BahanSerializer

@api_view(["GET", "HEAD", "POST"])
@authentication_classes([SessionAuthentication])
def bahan_list(request):
    if request.method in ("GET", "HEAD"):
        bahans = Bahan.objects.filter(inventory__user=request.user)
        serializer = BahanSerializer(bahans, many=True, context={"request": request})
        return Response(serializer.data)

    serializer = BahanSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    serializer.save(inventory=request.user.inventori)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(["GET", "HEAD", "PUT", "PATCH", "DELETE"])
@authentication_classes([SessionAuthentication])
def bahan_detail(request, bahan_id):
    bahan = get_object_or_404(
        Bahan.objects.filter(inventory__user=request.user), pk=bahan_id,
    )
    if request.method in ("GET", "HEAD"):
        serializer = BahanSerializer(bahan, context={"request": request})
        return Response(serializer.data)

    if request.method == "DELETE":
        bahan.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = BahanSerializer(
        bahan, data=request.data, partial=request.method == "PATCH",
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)