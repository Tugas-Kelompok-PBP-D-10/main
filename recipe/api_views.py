from rest_framework import generics
from .models import Recipe
from .serializers import RecipeSerializer


class RecipeListAPIView(generics.ListAPIView):
    serializer_class = RecipeSerializer

    def get_queryset(self):
        return Recipe.objects.filter(is_published=True).order_by("-created_at")


class RecipeDetailAPIView(generics.RetrieveAPIView):
    queryset = Recipe.objects.filter(is_published=True)
    serializer_class = RecipeSerializer