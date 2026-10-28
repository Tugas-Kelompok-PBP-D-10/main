# Migrasi dibuat dengan Django 5.2.17 pada 28 Oktober 2026.

import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


def salin_penyelesaian_lama(apps, schema_editor):
    RecipeInteraction = apps.get_model("recipe", "RecipeInteraction")
    RecipeCookingEvent = apps.get_model("recipe", "RecipeCookingEvent")
    database = schema_editor.connection.alias

    interactions = RecipeInteraction.objects.using(database).filter(
        completed_at__isnull=False
    )
    for interaction in interactions.iterator():
        RecipeCookingEvent.objects.using(database).create(
            user_id=interaction.user_id,
            recipe_id=interaction.recipe_id,
            completed_at=interaction.completed_at,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('recipe', '0006_recipe_image_recipe_is_published_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='recipe',
            name='submission_key',
            field=models.UUIDField(blank=True, editable=False, null=True, unique=True),
        ),
        migrations.CreateModel(
            name='RecipeCookingEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('completed_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('recipe', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cooking_events', to='recipe.recipe')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recipe_cooking_events', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-completed_at', '-pk'),
            },
        ),
        migrations.RunPython(
            salin_penyelesaian_lama,
            migrations.RunPython.noop,
        ),
    ]
