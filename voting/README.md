# Voting & Bookmark Module — OlahRasa

## Overview
Voting & Bookmark merupakan modul pada aplikasi **OlahRasa** yang digunakan untuk mengelola interaksi pengguna terhadap resep, yaitu memberikan *upvote/downvote* dan menyimpan resep favorit melalui fitur **Bookmark**.
Modul ini terintegrasi dengan Recipe dan Tracker agar pengguna dapat menyimpan resep, melihat kembali resep yang tersimpan pada halaman Bookmark, serta melihat ringkasannya pada dashboard Tracker.

Dokumentasi ini mencakup fitur **Voting**, **Bookmark**, dan **Bookmark Page**.

Tautan PWS : https://hafiza-nurul-olahrasa.pws.cs.ui.ac.id/

## Main Features
### 1. Voting (Upvote & Downvote)

- Pengguna yang sudah login dapat memberikan **upvote** (+1) atau **downvote** (-1) pada setiap resep melalui tombol panah pada kartu resep atau modal detail resep.
- Satu pengguna hanya dapat memiliki satu vote pada satu resep. Hal ini dijaga oleh `UniqueConstraint` pada model `Vote`.
- Nilai vote hanya boleh `1` atau `-1`. Hal ini dijaga oleh `CheckConstraint` pada database dan validasi pada `cast_vote()`.
- Menekan tombol vote yang sama sekali lagi akan membatalkan vote (*toggle*).
- Menekan tombol vote yang berlawanan akan mengganti vote sebelumnya, misalnya dari upvote menjadi downvote.
- Request dikirim menggunakan AJAX sehingga skor dan warna tombol langsung berubah tanpa reload halaman.
- Tombol vote dinonaktifkan sementara request berjalan agar pengguna tidak mengirim vote berulang kali.
- Tombol yang sedang aktif ditandai dengan `aria-pressed`, dan kursor yang diarahkan ke skor menampilkan jumlah upvote dan downvote.
- Pengguna yang belum login hanya dapat melihat skor resep dan diarahkan ke halaman login ketika ingin memberikan vote.
- Proses vote dijalankan di dalam `transaction.atomic()` dan mengunci data resep dengan `select_for_update()` agar skor tetap konsisten ketika beberapa pengguna memberikan vote bersamaan.

### 2. Skor Popularitas

- Skor resep dihitung dari total nilai seluruh vote (jumlah upvote dikurangi jumlah downvote).
- Skor ditampilkan di antara tombol upvote dan downvote pada setiap resep.
- Fungsi `with_popularity()` pada `services.py` menambahkan nilai `popularity` pada queryset resep sehingga resep dapat diurutkan berdasarkan skor tertinggi.
- Resep yang belum memiliki vote memiliki skor 0.
- Skor yang sama digunakan oleh filter **Skor minimal** pada Bookmark Page.

### 3. Auto-Delete Moderation

- Resep akan dihapus secara permanen apabila mencapai **100 downvote**.
- Pengecekan dilakukan otomatis setiap kali pengguna memberikan vote melalui `check_auto_delete()`.
- Aturan ini hanya berlaku untuk resep komunitas (resep yang memiliki author). Resep dari API tidak akan pernah dihapus otomatis.
- Resep dengan 99 downvote masih dipertahankan.
- Ketika resep terhapus, server mengembalikan `deleted: true`, lalu antarmuka menampilkan notifikasi **Resep dihapus** dan mengarahkan pengguna kembali ke daftar resep.
- Seluruh vote dan bookmark yang terkait dengan resep tersebut ikut terhapus.

### 4. Bookmark Recipe

- Pengguna yang sudah login dapat menyimpan resep melalui ikon bookmark pada kartu resep atau modal detail resep.
- Menekan ikon bookmark yang sama sekali lagi akan melepas resep dari daftar bookmark (*toggle*).
- Request dikirim menggunakan AJAX sehingga ikon langsung berubah tanpa reload halaman.
- Jumlah bookmark pada judul halaman Bookmark ikut diperbarui setiap kali bookmark ditambahkan atau dilepas.
- Satu pengguna hanya dapat membookmark satu resep satu kali. Hal ini dijaga oleh `UniqueConstraint` pada model `Bookmark`.
- Pengguna yang belum login hanya dapat melihat skor resep dan diarahkan ke halaman login ketika ingin menyimpan resep.
- Jika resep dihapus, misalnya karena mencapai batas 100 downvote pada Auto-Delete Moderation, bookmark yang terkait ikut terhapus.

### 5. Bookmark Page

Halaman **Bookmark Saya** dapat diakses melalui menu navbar pada `/voting/bookmarks/`. Halaman ini menampilkan seluruh resep yang disimpan pengguna dalam bentuk grid kartu.

- Halaman hanya dapat diakses oleh pengguna yang sudah login.
- Data bookmark diambil secara asinkron dari endpoint `bookmark_list_api`, sehingga pencarian, filter, dan pagination berjalan tanpa reload halaman.
- Menampilkan state *loading*, *error*, dan *empty* dengan pesan yang berbeda untuk kondisi belum ada bookmark dan kondisi tidak ada hasil yang cocok.
- Setiap kartu menampilkan foto, judul, sumber resep, waktu persiapan, waktu memasak, porsi, dan skor vote.
- Kartu menampilkan penanda **Sudah dimasak** berdasarkan data `RecipeInteraction` dari modul Recipe.
- Resep yang sudah tidak dipublikasikan tetap tampil dengan label **Tidak tersedia**.
- Pengguna dapat melakukan vote dan melepas bookmark langsung dari kartu.
- Klik pada kartu membuka modal detail resep.

### 6. Search, Sort, dan Filter

- Pencarian berdasarkan judul resep dengan *debounce* 300 ms agar request tidak dikirim pada setiap ketukan.
- Pengurutan berdasarkan **Terbaru**, **Terlama**, atau **Judul A-Z**.
- Filter **Sumber**: resep komunitas atau resep dari API.
- Filter **Vote saya**: resep yang saya upvote, saya downvote, atau belum saya vote.
- Filter **Skor minimal**: hanya menampilkan resep dengan total skor sama dengan atau di atas nilai yang diisi.
- Filter **Kategori** akan muncul otomatis apabila `CATEGORY_FIELD` pada `services.py` diaktifkan. Saat ini filter ini disembunyikan karena model Recipe belum memiliki field kategori.
- Semua filter dapat dikombinasikan dan dikembalikan ke kondisi awal melalui tombol **Reset**.
- Filter dan nomor halaman disimpan pada query string URL, sehingga halaman tetap sama ketika di-refresh.

### 7. Pagination

- Menampilkan 12 bookmark pada setiap halaman.
- Request lama dibatalkan menggunakan `AbortController` ketika pengguna mengubah filter, agar hasil request sebelumnya tidak menimpa hasil terbaru.

### 8. Hapus Semua Bookmark

- Tombol **Hapus semua** menampilkan konfirmasi sebelum bookmark dihapus.
- Fitur ini hanya menghapus bookmark milik pengguna yang sedang login.
- Tombol disembunyikan apabila pengguna belum memiliki bookmark.

## Database Models

| Model | Fungsi |
|---|---|
| `Bookmark` | Menyimpan resep yang disimpan pengguna beserta waktu penyimpanannya |
| `Vote` | Menyimpan upvote (+1) atau downvote (-1) pengguna pada sebuah resep |

Field pada model `Vote`:

| Field | Fungsi |
|---|---|
| `user` | Pengguna yang memberikan vote |
| `recipe` | Resep yang diberi vote |
| `value` | Nilai vote, yaitu `1` (upvote) atau `-1` (downvote) |
| `created_at` | Waktu vote diberikan |

Field pada model `Bookmark`:

| Field | Fungsi |
|---|---|
| `user` | Pemilik bookmark |
| `recipe` | Resep yang disimpan |
| `created_at` | Waktu resep disimpan, digunakan untuk pengurutan Terbaru dan Terlama |

## Endpoints

| Method | URL | Fungsi |
|---|---|---|
| `POST` | `/voting/<recipe_id>/vote/` | Memberikan, mengganti, atau membatalkan vote. Menerima parameter `value` (`1` atau `-1`) |
| `POST` | `/voting/<recipe_id>/vote/remove/` | Menghapus vote milik pengguna pada resep tersebut |
| `GET` | `/voting/<recipe_id>/summary/` | Mengambil ringkasan vote resep dalam format JSON |
| `POST` | `/voting/<recipe_id>/bookmark/` | Menyimpan atau melepas bookmark dan mengembalikan jumlah bookmark terbaru |
| `POST` | `/voting/bookmarks/clear/` | Menghapus seluruh bookmark milik pengguna |
| `GET` | `/voting/api/bookmarks/` | Mengambil data bookmark dalam format JSON untuk Bookmark Page |
| `GET` | `/voting/bookmarks/` | Menampilkan halaman Bookmark |

Respons endpoint vote berisi `upvotes`, `downvotes`, `score`, `user_vote` (`1`, `-1`, atau `null`), dan `deleted` (bernilai `true` apabila resep terhapus oleh Auto-Delete Moderation). Nilai vote selain `1` dan `-1` ditolak dengan status `400`, dan resep yang tidak ditemukan mengembalikan status `404`.

Endpoint `summary` dapat diakses tanpa login. Pengguna yang belum login hanya menerima `score`, sedangkan pengguna yang sudah login menerima rincian lengkap beserta vote miliknya.

Endpoint JSON menggunakan decorator `ajax_login_required`. Apabila pengguna belum login, server mengembalikan status `401` beserta `login_url` agar JavaScript dapat mengarahkan pengguna ke halaman login. Endpoint `POST` juga dilindungi oleh CSRF token.

Parameter yang didukung oleh `/voting/api/bookmarks/`: `q`, `sort`, `source`, `vote`, `min_score`, `category`, dan `page`.

Respons API berisi `results`, `pagination`, `total` (seluruh bookmark pengguna), `filtered_count` (jumlah setelah filter), dan `categories`.

## Module Integrations

### Voting/Bookmark → Recipe

- Bookmark mengacu pada model `Recipe`.
- Status **Sudah dimasak** pada Bookmark Page dibaca dari `RecipeInteraction` milik modul Recipe.
- Modal detail resep pada Bookmark Page menggunakan `recipe.js` dan endpoint API modul Recipe.
- Tombol vote dan bookmark dapat dipasang pada kartu resep dengan template tag `{% recipe_actions recipe %}`.
- Auto-Delete Moderation menghapus data `Recipe` milik modul Recipe apabila resep komunitas mencapai 100 downvote.
- Halaman Recipe dan Inventori memeriksa ketersediaan route voting melalui `_voting_routes_available()` sebelum menampilkan tombol vote dan bookmark.

### Voting/Bookmark → Tracker

Tracker mengambil data Bookmark berdasarkan pengguna yang sedang login untuk menampilkan resep tersimpan terbaru dan tombol **View All Bookmarks** yang mengarah ke Bookmark Page.

### Voting/Bookmark → Authentication

Seluruh aksi Vote dan Bookmark membutuhkan pengguna yang sudah login melalui `settings.LOGIN_URL`. Pengguna yang belum login diarahkan ke halaman login dan dikembalikan ke halaman sebelumnya setelah berhasil masuk.

## Important Files

| File | Fungsi |
|---|---|
| `models.py` | Definisi model `Vote` dan `Bookmark` |
| `views.py` | Endpoint vote, ringkasan vote, toggle bookmark, hapus semua bookmark, halaman Bookmark, dan API Bookmark |
| `services.py` | Logika vote, skor popularitas, Auto-Delete Moderation, toggle bookmark, dan filter Bookmark Page |
| `decorators.py` | `ajax_login_required` untuk endpoint JSON |
| `urls.py` | Routing endpoint Voting dan Bookmark |
| `templatetags/voting_tags.py` | Template tag `recipe_actions` untuk tombol vote dan bookmark |
| `templates/voting/bookmark_list.html` | Struktur dan script halaman Bookmark |
| `templates/voting/_recipe_actions.html` | Komponen tombol vote dan bookmark |
| `templates/voting/_recipe_modal.html` | Modal detail resep |
| `static/voting/voting.js` | Logika klik vote dan bookmark di sisi klien |
| `static/voting/bookmark-list.css` | Tampilan halaman Bookmark |
| `static/voting/recipe-card-modal.css` | Tampilan kartu resep dan modal |
| `test_endpoints.py`, `test_bookmark_endpoints.py`, `test_bookmark_page.py`, `test_services.py`, `test_tag.py` | Pengujian modul |

## Running the Module

Jalankan perintah berikut dari root directory proyek OlahRasa dengan virtual environment aktif.

```bash
python manage.py migrate
python manage.py runserver
```

Untuk menjalankan pengujian Voting & Bookmark:

```bash
python manage.py test voting
```

## Notes

- Setiap pengguna hanya dapat memiliki satu vote pada satu resep, dan vote dapat diubah atau dibatalkan kapan saja.
- Auto-Delete Moderation bersifat permanen dan hanya berlaku untuk resep komunitas, bukan resep dari API.
- Bookmark Page hanya menampilkan data milik pengguna yang sedang login.
- Menyimpan bookmark tidak otomatis menambah CookingLog pada Tracker. Aktivitas memasak baru dicatat setelah pengguna melakukan konfirmasi Complete Recipe.
- Filter kategori tidak muncul selama `CATEGORY_FIELD` bernilai `None`.
- Bootstrap hanya dimuat pada halaman Bookmark dan tidak dimuat pada `base.html`.
- Perubahan pada integrasi Recipe dan Tracker perlu dikoordinasikan dengan pemegang modul terkait.

## AI DISCLOSURE
Dalam pembuatan modul voting & bookmark, Generative AI Claude digunakan untuk membantu memberikan panduan dalam pengerjaan, alat bantu pembelajaran, serta diskusi teknis.


Prompt Strategy:
1. Concept Understanding: Meminta penjelasan konsep Django, seperti models, views, services, constraint database, AJAX, dan penggunaan template tag.
2. Code Assistance: Memberikan potongan kode yang sedang dikerjakan untuk memperoleh saran implementasi atau perbaikan pada fitur bookmark dan Bookmark Page.
3. Debugging: Menyertakan pesan error dan output terminal agar AI membantu mengidentifikasi kemungkinan penyebab masalah.
4. Integration Guidance: Meminta panduan dalam mengintegrasikan Voting & Bookmark dengan modul Recipe dan Tracker.
5. Documentation: Menggunakan AI untuk membantu menyusun README agar lebih terstruktur dan mudah dipahami.


Tautan riwayat chat AI yang digunakan:
1. https://claude.ai/share/ea49ac92-1b77-4a45-857c-cb72f80ff9e3
2. https://claude.ai/share/612a4fa9-d3ab-4f4d-8938-b56bf9c65d98


Purpose of AI Usage: 
1. Mendukung proses pembelajaran dan pemahaman teknis.
2. Membantu mengidentifikasi serta menyelesaikan masalah selama pengembangan.
3. Mempermudah proses integrasi antarmodul.
4. Meningkatkan keterbacaan kode dan dokumentasi.