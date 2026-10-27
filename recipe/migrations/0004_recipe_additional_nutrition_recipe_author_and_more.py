# Migrasi dibuat dengan Django 5.2.17 pada 26 Oktober 2026.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ('recipe', '0003_recipe'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='recipe',
            name='additional_nutrition',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='recipe',
            name='author',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recipes', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='recipe',
            name='calories',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name='recipe',
            name='carbohydrates',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name='recipe',
            name='fat',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name='recipe',
            name='nutrition_basis',
            field=models.CharField(
                choices=[
                    ('unknown', 'Belum diketahui'),
                    ('per_serving', 'Per porsi'),
                    ('whole_recipe', 'Total resep'),
                    ('mixed', 'Campuran sumber'),
                ],
                default='unknown',
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name='recipe',
            name='image_url',
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name='recipe',
            name='servings',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='recipe',
            name='ingredients',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='recipe',
            name='instructions',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='recipe',
            name='protein',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name='recipe',
            name='spoonacular_id',
            field=models.PositiveBigIntegerField(blank=True, null=True, unique=True),
        ),
        migrations.CreateModel(
            name='RecipeInteraction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('viewed_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('recipe', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='interactions', to='recipe.recipe')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recipe_interactions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'constraints': [
                    models.UniqueConstraint(
                        fields=('user', 'recipe'),
                        name='unique_recipe_interaction_user_recipe',
                    ),
                    models.CheckConstraint(
                        condition=Q(('completed_at__isnull', True))
                        | Q(('viewed_at__isnull', False)),
                        name='completed_recipe_was_viewed',
                    ),
                ],
            },
        ),
    ]
