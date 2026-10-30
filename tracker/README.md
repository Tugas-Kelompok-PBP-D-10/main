# Tracker Module — OlahRasa

## Overview
Tracker merupakan modul pada aplikasi **OlahRasa** yang digunakan untuk memantau aktivitas memasak pengguna, perkembangan nutrisi mingguan, konsistensi memasak, serta pencapaian (*achievements*).
Modul ini terintegrasi dengan Recipe dan Voting/Bookmark agar pengguna dapat melihat progres aktivitas memasak dan resep yang telah disimpan melalui satu dashboard.

Tautan PWS : https://hafiza-nurul-olahrasa.pws.cs.ui.ac.id/

## AI DISCLOSURE 
Dalam proses pengembangan modul Tracker pada proyek OlahRasa, pengembang menggunakan ChatGPT (OpenAI) sebagai alat bantu pembelajaran, diskusi teknis, dan penyelesaian masalah pemrograman.

AI Tools Used
1. ChatGPT (OpenAI): Digunakan untuk memahami konsep Django, mendiskusikan implementasi fitur, menganalisis error, serta membantu penyusunan dokumentasi.
2. Claude : Digunakan untuk merapihkan dan menyesuaikan css.

Prompt Strategy
Strategi penggunaan AI dilakukan secara bertahap dan kontekstual, meliputi:
1. Concept Understanding: Meminta penjelasan konsep Django, seperti models, views, services, migrations, dan hubungan antarmodul.
2. Code Assistance: Memberikan potongan kode yang sedang dikerjakan untuk memperoleh saran implementasi atau perbaikan.
3. Debugging: Menyertakan pesan error dan output terminal agar AI membantu mengidentifikasi kemungkinan penyebab masalah.
4. Integration Guidance: Meminta panduan bertahap dalam mengintegrasikan Tracker dengan modul Recipe dan Voting/Bookmark.
5. Documentation: Menggunakan AI untuk membantu menyusun README agar lebih terstruktur dan mudah dipahami.

Tautan Riwayat Chat AI yang digunakan : 
1. https://chatgpt.com/share/6ae36902-5794-83ec-a505-cf72dbebcd90
2. https://claude.ai/share/18f45afb-de23-4595-af30-aa65d20b1806

Purpose of AI Usage
Penggunaan AI bertujuan untuk:
1. Mendukung proses pembelajaran dan pemahaman teknis.
2. Membantu mengidentifikasi serta menyelesaikan masalah selama pengembangan.
3. Mempermudah proses integrasi antarmodul.
Meningkatkan keterbacaan kode dan dokumentasi


## Main Features
### 1. Cooking History

- Menampilkan riwayat aktivitas memasak pengguna.
- Mencatat nama resep, tanggal memasak, kalori, protein, karbohidrat, dan lemak.
- CookingLog dibuat otomatis ketika pengguna menyelesaikan resep melalui fitur Complete Recipe.
- Pengguna dapat memasak resep yang sama lebih dari sekali.
- Setiap aktivitas memiliki `request_id` unik untuk mencegah pencatatan ganda ketika request yang sama dikirim ulang.

### 2. Cooking Streak

- Menghitung jumlah hari memasak secara berturut-turut.
- Menampilkan *current streak* dan *longest streak*.
- Memasak beberapa kali pada hari yang sama tidak menambah jumlah streak.
- Streak diperbarui ketika aktivitas memasak baru berhasil dicatat.

### 3. Achievement Badges

Sistem achievement memberikan badge berdasarkan jumlah aktivitas memasak atau pencapaian streak.

| Badge | Persyaratan |
|---|---|
| First Cook | Menyelesaikan aktivitas memasak pertama |
| Consistent Chef | Memasak selama 3 hari berturut-turut |
| Master Chef | Menyelesaikan total 10 aktivitas memasak |

Badge yang sudah diperoleh disimpan melalui model `UserBadge`.

Untuk menyiapkan master badge:

```bash
python manage.py seed_badges
```

### 4. Weekly Nutrition Progress

- Menampilkan total protein, karbohidrat, dan lemak dari aktivitas memasak dalam minggu berjalan.
- Menampilkan progress terhadap target nutrisi yang ditetapkan pengguna.
- Menyediakan fitur membuat, melihat, mengubah, dan menghapus Nutrition Target.
- Persentase progress dibatasi maksimal 100% pada tampilan.

### 5. Weekly Cooking Activity

- Menampilkan visualisasi aktivitas memasak selama tujuh hari.
- Membantu pengguna memantau konsistensi memasak dalam minggu berjalan.

### 6. Bookmark Integration

- Menampilkan tiga resep terbaru yang disimpan pengguna.
- Menggunakan data Bookmark dari modul Voting tanpa membuat model Bookmark baru.
- Menyediakan tombol **View All Bookmarks**.
- Kartu Bookmark dapat mengarahkan pengguna ke modal detail resep yang sesuai.
- Setelah menutup modal yang dibuka dari Tracker, pengguna dapat kembali ke dashboard Tracker.

Menyimpan Bookmark tidak otomatis menambah CookingLog. Aktivitas memasak baru dicatat setelah pengguna melakukan konfirmasi Complete Recipe.

### 7. Share Cooking Progress

Pengguna dapat membagikan ringkasan progres memasak melalui fitur berbagi pada dashboard Tracker, termasuk opsi berbagi atau menyimpan gambar progres yang didukung browser.

## Database Models

| Model | Fungsi |
|---|---|
| `CookingLog` | Menyimpan aktivitas memasak dan informasi nutrisinya |
| `CookingStreak` | Menyimpan current streak, longest streak, dan tanggal memasak terakhir |
| `Badge` | Menyimpan master data achievement |
| `UserBadge` | Menyimpan badge yang diperoleh masing-masing pengguna |
| `NutritionTarget` | Menyimpan target protein, karbohidrat, dan lemak pengguna |

## Module Integrations

### Recipe → Tracker

Ketika pengguna melakukan Complete Recipe:

1. Recipe menerima konfirmasi dan `request_id`.
2. Recipe memanggil fungsi integrasi pada `tracker/integrations.py`.
3. Tracker mencatat aktivitas melalui `record_cook()`.
4. CookingStreak diperbarui.
5. Sistem memeriksa apakah pengguna memenuhi syarat badge baru.
6. Aktivitas dapat ditampilkan di dashboard Tracker.

### Voting/Bookmark → Tracker

Tracker mengambil data Bookmark dari modul Voting berdasarkan pengguna yang sedang login.

Data ini hanya digunakan untuk menampilkan resep tersimpan dan memudahkan navigasi ke detail resep.

## Important Files

| File | Fungsi |
|---|---|
| `models.py` | Definisi model database Tracker |
| `views.py` | Dashboard, API data Tracker, Nutrition Target, dan Cooking History |
| `services.py` | Logika pencatatan CookingLog, streak, dan pemberian badge |
| `integrations.py` | Penghubung antara modul Recipe dan Tracker |
| `urls.py` | Routing endpoint Tracker |
| `tests.py` | Pengujian modul Tracker |
| `management/commands/seed_badges.py` | Menyiapkan master achievement |
| `templates/tracker/tracker.html` | Struktur halaman dashboard |
| `static/tracker/` | CSS dan JavaScript antarmuka Tracker |

## Running the Module

Jalankan perintah berikut dari root directory proyek OlahRasa dengan virtual environment aktif.

```bash
python manage.py migrate
python manage.py seed_badges
python manage.py runserver
```

Untuk menjalankan pengujian Tracker:

```bash
python manage.py test tracker
```

## Notes

- Tracker hanya menampilkan data milik pengguna yang sedang login.
- CookingLog dibuat berdasarkan aktivitas memasak yang dikonfirmasi, bukan sekadar membuka atau menyimpan resep.
- CookingStreak dihitung berdasarkan hari, bukan jumlah klik Complete Recipe.
- Master badge perlu tersedia di database agar achievement dapat diberikan.
- Perubahan pada integrasi Recipe dan Bookmark perlu dikoordinasikan dengan pemegang modul terkait.


