# Migrasi dibuat dengan Django 5.2.17 pada 27 Oktober 2026.

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recipe', '0004_recipe_additional_nutrition_recipe_author_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='recipe',
            name='image',
            field=models.ImageField(blank=True, upload_to='recipes/', verbose_name='Foto resep'),
        ),
        migrations.AddField(
            model_name='recipe',
            name='is_published',
            field=models.BooleanField(default=True, verbose_name='Tampilkan di katalog'),
        ),
        migrations.AddField(
            model_name='recipe',
            name='preparation_time',
            field=models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Waktu persiapan (menit)'),
        ),
        migrations.AddField(
            model_name='recipe',
            name='source_name',
            field=models.CharField(blank=True, max_length=255, verbose_name='Nama sumber resep'),
        ),
        migrations.AddField(
            model_name='recipe',
            name='source_type',
            field=models.CharField(choices=[('auto', 'Pencarian Spoonacular otomatis'), ('local', 'Resep lokal'), ('spoonacular', 'Spoonacular')], default='auto', max_length=16, verbose_name='Jenis sumber data'),
        ),
        migrations.AlterField(
            model_name='recipe',
            name='cooking_time',
            field=models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Waktu memasak (menit)'),
        ),
        migrations.AlterField(
            model_name='recipe',
            name='description',
            field=models.TextField(blank=True, null=True, verbose_name='Deskripsi'),
        ),
        migrations.AlterField(
            model_name='recipe',
            name='ingredients',
            field=models.JSONField(blank=True, default=list, help_text='Gunakan JSON berupa daftar, misalnya [{"name": "kentang", "amount": 300, "unit": "g"}]. Bahan tanpa jumlah numerik boleh disimpan sebagai teks.', verbose_name='Bahan dan takaran'),
        ),
        migrations.AlterField(
            model_name='recipe',
            name='instructions',
            field=models.TextField(blank=True, help_text='Tulis satu langkah per baris. Urutan baris menjadi nomor langkah.', verbose_name='Langkah memasak'),
        ),
        migrations.AlterField(
            model_name='recipe',
            name='nutrition_basis',
            field=models.CharField(choices=[('unknown', 'Belum diketahui'), ('per_serving', 'Per porsi'), ('whole_recipe', 'Total resep'), ('mixed', 'Campuran sumber')], default='unknown', max_length=16),
        ),
        migrations.AlterField(
            model_name='recipe',
            name='servings',
            field=models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1)], verbose_name='Jumlah porsi'),
        ),
        migrations.AlterField(
            model_name='recipe',
            name='title',
            field=models.CharField(max_length=255, verbose_name='Nama resep'),
        ),
    ]
