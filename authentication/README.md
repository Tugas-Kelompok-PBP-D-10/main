# Authentication Module — OlahRasa

## Overview

Modul Authentication merupakan modul yang bertanggung jawab atas proses autentikasi dan pengelolaan akun pengguna pada aplikasi **OlahRasa**.

Modul ini menyediakan registrasi akun, login dan logout manual, integrasi login Google melalui Django Allauth, halaman profil, serta akses ke pengaturan akun. Setelah pengguna berhasil login, sistem mengarahkan pengguna ke halaman Recipe sebagai halaman utama aplikasi.

**Penanggung jawab modul:** Naufal Khairiy Zulkarnain Sormin

**Link PWS:** https://hafiza-nurul-olahrasa.pws.cs.ui.ac.id/

## AI Disclosure

Dalam pengembangan modul Authentication, saya menggunakan **ChatGPT (OpenAI)** sebagai alat bantu untuk memahami konsep Django, mendiskusikan implementasi fitur, memperbaiki masalah pada kode, menyesuaikan antarmuka, serta membantu proses integrasi dengan modul lain.

AI digunakan sebagai pendukung proses pengembangan, bukan sebagai pengganti pemahaman dan tanggung jawab pengembang. Saran AI perlu disesuaikan dengan struktur proyek, diperiksa kembali, dan diuji sebelum digunakan.

### AI Tools Used

**ChatGPT (OpenAI)** digunakan untuk:

1. **Concept Understanding:** Memahami alur autentikasi Django, penggunaan `UserCreationForm`, `AuthenticationForm`, decorator `login_required`, session, CSRF, dan template Django.
2. **Code Assistance:** Mendiskusikan implementasi register, login, logout, profil pengguna, pengaturan akun, dan konfigurasi Google OAuth.
3. **UI Styling:** Membantu memahami dan menyesuaikan HTML, Bootstrap, CSS, responsivitas, palet warna Figma, serta pemuatan font Austen.
4. **Debugging:** Menganalisis error terkait CSRF, autentikasi, konfigurasi Django, dan integrasi antarmodul.
5. **Integration Guidance:** Membantu menyesuaikan redirect pengguna setelah login agar menuju modul Recipe, sekaligus menyelaraskan routing dengan branch integrasi kelompok.
6. **Documentation:** Membantu menyusun dokumentasi teknis dan AI disclosure modul Authentication.

### Prompt Strategy

Strategi penggunaan AI dilakukan secara bertahap. Saya biasanya menjelaskan fitur yang ingin dibuat atau masalah yang dihadapi, memberikan konteks kode atau output terminal yang relevan, kemudian meminta penjelasan, alternatif implementasi, atau langkah perbaikan.

Contoh topik permintaan yang dibahas bersama ChatGPT:

| Topik | Bentuk bantuan AI | Implementasi pada proyek |
|---|---|---|
| Login dan registrasi | Penjelasan form bawaan Django serta alur autentikasi | `forms.py` dan `views.py` |
| Google OAuth | Diskusi konfigurasi Django Allauth dan callback login | Konfigurasi Allauth, URL, dan template login |
| Profile dan Account Settings | Diskusi status verifikasi email dan akun Google yang terhubung | `profile_page`, `profile.html`, dan halaman Allauth |
| Bootstrap dan CSS | Penjelasan struktur template, kelas Bootstrap, serta penyesuaian desain Figma | `auth_base.html`, `login.html`, `register.html`, `login.css`, dan `profile.css` |
| Integrasi dengan Recipe | Penyesuaian tujuan redirect dari Tracker ke Recipe | `authentication/views.py`, `olahrasa/urls.py`, dan `olahrasa/settings.py` |
| Debugging Git | Analisis konflik saat menggabungkan branch Authentication dan branch integrasi | Penyelesaian konflik konfigurasi dan routing |

Tabel tersebut merangkum penggunaan AI selama proses pengembangan, bukan menyatakan bahwa semua kode dihasilkan secara otomatis oleh AI.

### Verification and Responsibility

Saran dan potongan kode dari AI diperiksa kembali berdasarkan struktur aplikasi OlahRasa, terutama penggunaan nama URL, template, form, dan konfigurasi yang sudah tersedia.

Perubahan diintegrasikan secara manual ke proyek dan ditinjau melalui Git diff serta proses pengujian lokal sesuai kebutuhan. Permasalahan yang muncul, seperti konflik Git dan error konfigurasi, ditelusuri kembali menggunakan output terminal.

Modul Authentication saat ini belum memiliki rangkaian automated unit test khusus yang lengkap. Oleh karena itu, penggunaan AI tidak dijadikan dasar untuk mengklaim bahwa seluruh skenario telah lolos pengujian otomatis.

### Tautan Riwayat Chat AI

**ChatGPT (OpenAI):**

https://chatgpt.com/s/t_6ae4778544b48191b33c1eeeb76dadab

## Main Features

### 1. User Registration

- Pengguna dapat membuat akun menggunakan username, email, dan password.
- Menggunakan `RegisterForm` yang mewarisi `UserCreationForm` bawaan Django.
- Memvalidasi format email, keunikan email, dan aturan password.
- Setelah registrasi berhasil, pengguna diarahkan ke halaman login.

### 2. Manual Login

- Pengguna dapat login menggunakan username dan password.
- Menggunakan `AuthenticationForm` serta fungsi autentikasi Django.
- Menampilkan pesan kesalahan apabila autentikasi gagal.
- Pengguna yang berhasil login diarahkan ke halaman Recipe.

### 3. Google OAuth Login

- Integrasi login melalui akun Google menggunakan `django-allauth`.
- Tombol Google tersedia pada halaman login.
- Autentikasi menggunakan layanan Google OAuth dan konfigurasi kredensial aplikasi.
- Pengguna dapat memanfaatkan akun Google sebagai metode autentikasi alternatif.

### 4. User Profile

- Menampilkan username dan email pengguna.
- Menampilkan status verifikasi email melalui data Django Allauth.
- Menampilkan status keterhubungan akun Google.
- Akses halaman profil dibatasi untuk pengguna yang telah login.

### 5. Account Settings

Halaman Profile menyediakan navigasi menuju fitur manajemen akun Django Allauth, meliputi:

- Pengelolaan alamat email.
- Perubahan atau pengaturan password.
- Pengelolaan akun sosial yang terhubung.

### 6. Logout and Access Protection

- Logout menggunakan request `POST`.
- Form dilindungi menggunakan CSRF token.
- Setelah logout, pengguna diarahkan ke halaman login.
- Halaman yang membutuhkan autentikasi menggunakan decorator `login_required`.

### 7. UI and Responsive Design

- Halaman login dan register menggunakan Bootstrap 5.3.
- Styling tambahan menggunakan CSS khusus Authentication.
- Antarmuka disesuaikan dengan palet warna Figma OlahRasa.
- Menggunakan font Austen untuk tipografi halaman Authentication.
- Layout disesuaikan agar dapat digunakan pada ukuran layar desktop dan mobile.

## Module Integration

### Authentication → Recipe

Ketika pengguna berhasil login secara manual, sistem mengarahkan pengguna ke URL bernama `recipe:home`.

Pengaturan `LOGIN_REDIRECT_URL` digunakan untuk mendukung alur redirect autentikasi Django dan Django Allauth.

Saat pengguna mengakses halaman utama website, sistem memeriksa status login. Pengguna yang telah login diarahkan menuju Recipe, sedangkan pengguna yang belum login diarahkan menuju halaman Login.

### Authentication → Django Allauth

Django Allauth digunakan untuk mendukung Google OAuth, status email, pengelolaan password, dan akun sosial yang terhubung.

Data pengguna utama tetap menggunakan model `User` bawaan Django.

## Important Files

| File | Fungsi |
|---|---|
| `authentication/forms.py` | Form registrasi dan validasi email |
| `authentication/views.py` | Logika register, login, logout, dan profile |
| `authentication/urls.py` | Routing halaman Authentication |
| `authentication/templates/login.html` | Template login |
| `authentication/templates/register.html` | Template registrasi |
| `authentication/templates/auth_base.html` | Layout bersama halaman login dan register |
| `authentication/templates/profile.html` | Halaman informasi profil dan pengaturan akun |
| `authentication/static/css/login.css` | Styling login dan register |
| `authentication/static/css/profile.css` | Styling Profile dan Account Settings |
| `olahrasa/templates/allauth/layouts/base.html` | Layout halaman manajemen akun Allauth |
| `olahrasa/settings.py` | Konfigurasi autentikasi, OAuth, email, dan redirect |
| `olahrasa/urls.py` | Integrasi routing Authentication dengan modul kelompok |

## Running the Module

Jalankan dari direktori utama proyek dengan virtual environment Python yang sudah aktif.

1. Instal dependensi menggunakan `python -m pip install -r requirements.txt`.
2. Siapkan konfigurasi environment yang diperlukan, terutama kredensial Google OAuth jika ingin menguji login Google.
3. Jalankan migrasi menggunakan `python manage.py migrate`.
4. Periksa konfigurasi Django menggunakan `python manage.py check`.
5. Jalankan aplikasi menggunakan `python manage.py runserver`.

Halaman yang dapat diakses:

| URL | Fungsi |
|---|---|
| `/login/` | Login manual atau Google |
| `/register/` | Registrasi pengguna |
| `/profile/` | Profil dan pengaturan akun |
| `/recipe/` | Halaman utama setelah login |

## Notes

- Modul Authentication menggunakan model `User` bawaan Django, bukan model pengguna kustom.
- Halaman Profile menampilkan informasi akun dan menyediakan akses ke fitur Allauth; modul ini belum mengimplementasikan penyuntingan foto profil, bio, atau preferensi gizi secara mandiri.
- Fitur email dan Google OAuth membutuhkan konfigurasi environment yang sesuai.
- Keamanan dan konfigurasi deployment produksi tetap perlu diverifikasi secara terpisah.
- Automated unit test khusus Authentication belum dikembangkan secara lengkap pada `authentication/tests.py`.