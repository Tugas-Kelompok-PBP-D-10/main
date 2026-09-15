CP 1

OlahRasa (Olah Bahan Sisa, Jadi Suatu Rasa)
Deskripsi Produk :
OlahRasa dirancang untuk mengatasi masalah pemborosan makanan (*food waste*) sekaligus menjadi asisten dapur andalan. Sehingga kamu tidak perlu lagi belanja bahan baru untuk mengikuti resep, sistem kami yang akan mencarikan resep sesuai dengan bahan makanan yang kamu miliki saat ini.

## ✨ Fitur Utama
- 🔍 **Smart Filter :** Masukkan bahan makanan yang tersisa di dapur (misal: telur, nasi). Sistem hanya akan menampilkan resep yang cocok.
- 🏆 **Algoritma :** Resep akan diurutkan secara otomatis berdasarkan kecocokan bahan & waktu, tingginya kandungan nutrisi (terutama protein), dan seberapa populer resep tersebut di komunitas.
- 👨‍🍳 **User-Generated Content:** Pengguna bisa berkreasi dan mengunggah resep andalan mereka sendiri langsung ke dalam *database*.
- ⚖️ **Sistem Reputasi & Auto-Moderasi:** Kami menggunakan sistem *upvote* dan *downvote*. Jika ada resep fiktif atau *troll* yang mendapat hingga 100 *downvote*, sistem akan menghapusnya secara permanen!

Rencana Modul :
Untuk pengembangan tahap awal, sistem ini difokuskan pada lima modul utama. yaitu:

1. Modul Autentikasi Pengguna & Admin
Deskripsi: Modul ini bertindak sebagai pintu utama untuk login pada website.
Beberapa Fitur Utama : 
- Atutentikasi Google OAuth: Akses masuk one-click yang aman menggunakan akun Google tanpa perlu mengelola kata sandi internal.
- Manajemen Profil: Pengaturan informasi dasar pengguna, seperti foto profil, nama tampilan, dan bio.
- Pengaturan Preferensi: Menyimpan preferensi gizi dan target personal (seperti target protein atau tujuan diet) untuk merekomendasikan resep yang relevan di dashboard.

2. Modul Inventaris & Stok Bahan Pengguna
Deskripsi: Modul ini berfungsi sebagai tempat penyimpanan dan pengelolaan stok bahan makanan sisa yang dimiliki pengguna secara real-time.
Beberapa Fitur Utama :
- Kelola Stok Bahan: Menambah, memperbarui, atau menghapus daftar bahan makanan sisa yang ada di dapur (misal: telur, nasi, kentang).
- Fitur Smart Filter: Memadukan ketersediaan stok bahan milik pengguna dengan mesin pencari untuk menyaring resep yang bisa langsung dimasak.
- Pemantauan Ketersediaan: Mencatat estimasi jumlah dan porsi bahan sisa secara real-time.

3. Modul Katalog Resep & Nutrisi
Deskripsi: Modul ini menjadi pusat referensi resep yang menggabungkan data resep bawaan dengan kontribusi resep mandiri dari pengguna (User-Generated Content).
Beberapa Fitur Utama :
- Integrasi API: Menampilkan ribuan resep bawaan yang terstruktur lengkap dengan takaran dan informasi nutrisi presisi.
- Unggah Resep: Memfasilitasi pengguna untuk membagikan resep kreasi mandiri ke dalam database aplikasi.
- Validasi & Kalkulasi Nutrisi Otomatis: Menghubungkan bahan dari resep buatan pengguna ke Spoonacular API untuk mengalkulasi total kandungan gizi (terutama protein) secara otomatis.

4. Modul Like and Dislike Recipe 
Deskripsi: Modul ini mengelola sistem kurasi berbasis forum komunitas untuk menjaga kualitas konten resep serta mengukur tingkat popularitasnya.
Beberapa Fitur Utama :
- Sistem Voting (Upvote & Downvote): Fitur apresiasi dan kurasi interaktif (+1 atau -1) bagi pengguna terautentikasi untuk setiap resep komunitas.
- Skor Popularitas: Kalkulasi skor reputasi otomatis untuk menaikkan resep-resep terbaik ke posisi teratas halaman rekomendasi.
- Auto-Delete Moderation: Mekanisme pembersihan otomatis yang menghapus resep fiktif atau troll secara permanen jika terakumulasi mencapai 100 downvote.

5. Modul Pelacak Aktivitas (Tracker & Achievement)
Deskripsi: Modul ini berfungsi untuk merekam riwayat memasak pengguna, mengukur dampak pengurangan pemborosan makanan (food waste reduction), serta meningkatkan motivasi pengguna melalui fitur achievement.
Beberapa Fitur Utama :
- Pencatatan Riwayat Masak: Merekam setiap aktivitas memasak yang dilakukan pengguna di dalam aplikasi.
- Pengurangan Stok Otomatis (Auto-Deduct): Otomatis memotong jumlah bahan terkait di Modul Inventaris setelah pengguna mengonfirmasi selesai memasak.
- Cooking Streak & Badges: Menghitung konsistensi hari memasak secara berturut-turut serta menampilkan akumulasi nutrisi yang didapat (protein, kalori, karbohidrat) beserta lencana pencapaian.


Public API yang di gunakan :
Modul pertama adalah sistem Login yang diintegrasikan menggunakan layanan Google OAuth. Pendekatan ini memungkinkan pengguna untuk langsung masuk dan mengakses aplikasi secara aman menggunakan akun Google mereka masing-masing, sehingga proses autentikasi menjadi lebih cepat tanpa perlu repot membuat kata sandi baru.

Modul kedua adalah Data Makanan yang mengandalkan integrasi penuh dengan API publik dari Spoonacular. Melalui API ini, aplikasi secara otomatis memiliki ribuan referensi resep bawaan yang sudah lengkap dengan presisi takaran dan hitungan nutrisi, terutama total protein. Menariknya, saat pengguna memasukkan resep buatan mereka sendiri, sistem akan langsung menghubungkan data bahan tersebut ke Spoonacular untuk mengkalkulasi dan memvalidasi kandungan gizinya secara otomatis. Hal ini memastikan seluruh resep di dalam sistem memiliki standar informasi nutrisi yang konsisten.

Modul ketiga adalah Tracker yang difungsikan untuk merekam riwayat memasak dan pemakaian bahan makanan sisa oleh pengguna. Berbeda dengan modul makanan yang menarik data dari luar, sistem pelacakan ini dibangun dan berjalan secara mandiri menggunakan basis data internal pada sisi peladen (backend). Dengan begitu, seluruh riwayat aktivitas dikelola sepenuhnya oleh sistem internal untuk memastikan kelancaran alur data pelacakan.

Peran Pengguna : 
Dalam platform ini, pengguna tidak hanya bertindak sebagai konsumen, tetapi juga memiliki peran aktif sebagai kontributor dan kurator komunitas. Secara mendasar, pengguna yang sudah masuk melalui akun Google dapat memanfaatkan sistem untuk mencari inspirasi memasak hanya dengan memasukkan bahan sisa. Selain itu, aktivitas dan riwayat memasak mereka akan tercatat secara personal melalui sistem tracker yang terintegrasi di dalam aplikasi.

Lebih dari sekadar mencari resep, pengguna juga berperan langsung dalam membangun dan menjaga kualitas isi database. Sebagai kontributor, pengguna dapat mengunggah resep buatan sendiri yang kandungan nutrisinya akan langsung divalidasi otomatis oleh sistem Spoonacular. Sementara itu, sebagai kurator, pengguna memegang kendali atas moderasi konten melalui fitur upvote dan downvote.

Penilaian kolektif dari pengguna inilah yang pada akhirnya menggerakkan algoritma utama aplikasi. Pilihan mereka menentukan apakah sebuah resep layak diprioritaskan di posisi teratas, atau justru dieliminasi secara permanen oleh sistem moderasi otomatis karena telah menyentuh batas 100 downvote.

Pembagian Tugas Modul per masing - masing anggota : 
1. Modul Autentikasi Pengguna & Admin (NAUFAL KHAIRIY ZULKARNAIN SORMIN)
2. Modul Inventaris & Stok Bahan Pengguna (VELICIA WILLY)
3. Modul Katalog Resep & Nutrisi (MOHAMMAD ZAKY PRASTIO)
4. Modul Like and Dislike Recipe (NARENDRA RAMA PRAWIRA)
5. Modul Pelacak Aktivitas (Tracker & Achievement) (HAFIZA NURUL HIDAYAH)

Pembagian Peran Utama Masing - Masing Anggota :
 1. MOHAMMAD ZAKY PRASTIO : Backend & API
 2. HAFIZA NURUL HIDAYAH : Frontend & UIUX
 3. NAUFAL KHAIRIY ZULKARNAIN SORMIN : Frontend & UIUX
 4. VELICIA WILLY : Backend & API
 5. NARENDRA RAMA PRAWIRA : Backend & API