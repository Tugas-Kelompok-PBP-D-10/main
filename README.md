CP 1
Deskripsi Produk : 
Platform ini dirancang untuk mengatasi masalah pemborosan makanan (*food waste*) sekaligus menjadi asisten dapur andalan. Kamu tidak perlu lagi belanja bahan baru untuk mengikuti resep, sistem kami yang akan mencarikan resep sesuai dengan bahan makanan yang kamu miliki saat ini.

## ✨ Fitur Utama
- 🔍 **Smart Filter :** Masukkan bahan makanan yang tersisa di dapur (misal: telur, nasi). Sistem hanya akan menampilkan resep yang cocok.
- 🏆 **Algoritma :** Resep akan diurutkan secara otomatis berdasarkan kecocokan bahan & waktu, tingginya kandungan nutrisi (terutama protein), dan seberapa populer resep tersebut di komunitas.
- 👨‍🍳 **User-Generated Content:** Pengguna bisa berkreasi dan mengunggah resep andalan mereka sendiri langsung ke dalam *database*.
- ⚖️ **Sistem Reputasi & Auto-Moderasi:** Kami menggunakan sistem *upvote* dan *downvote*. Jika ada resep fiktif atau *troll* yang mendapat hingga 100 *downvote*, sistem akan menghapusnya secara permanen!

Rencana Modul :
Untuk pengembangan tahap awal, sistem ini difokuskan pada tiga modul utama. Modul pertama adalah Login yang berfungsi untuk mengatur akses dan autentikasi pengguna. Modul kedua adalah Tracker, yang nantinya difungsikan untuk melacak aktivitas masakan atau riwayat penggunaan bahan oleh pengguna di dalam aplikasi.

Modul ketiga sekaligus yang paling inti adalah Data Makanan. Modul ini membagi sumber datanya menjadi dua kategori. Kategori pertama berisi data makanan bawaan yang sudah tersedia secara default di dalam database sistem. Kategori kedua berisi data makanan hasil input manual dari pengguna. Penggabungan dua sumber data ini dibuat agar referensi bahan dan resep di dalam aplikasi bisa terus bertambah dari kontribusi komunitas.

Public API yang di gunakan :
Untuk pengembangan tahap awal, sistem ini difokuskan pada tiga modul utama. Modul pertama adalah sistem Login yang diintegrasikan menggunakan layanan Google OAuth. Pendekatan ini memungkinkan pengguna untuk langsung masuk dan mengakses aplikasi secara aman menggunakan akun Google mereka masing-masing, sehingga proses autentikasi menjadi lebih cepat tanpa perlu repot membuat kata sandi baru.

Modul kedua adalah Data Makanan yang mengandalkan integrasi penuh dengan API publik dari Spoonacular. Melalui API ini, aplikasi secara otomatis memiliki ribuan referensi resep bawaan yang sudah lengkap dengan presisi takaran dan hitungan nutrisi, terutama total protein. Menariknya, saat pengguna memasukkan resep buatan mereka sendiri, sistem akan langsung menghubungkan data bahan tersebut ke Spoonacular untuk mengkalkulasi dan memvalidasi kandungan gizinya secara otomatis. Hal ini memastikan seluruh resep di dalam sistem memiliki standar informasi nutrisi yang konsisten.

Modul ketiga adalah Tracker yang difungsikan untuk merekam riwayat memasak dan pemakaian bahan makanan sisa oleh pengguna. Berbeda dengan modul makanan yang menarik data dari luar, sistem pelacakan ini dibangun dan berjalan secara mandiri menggunakan basis data internal pada sisi peladen (backend). Dengan begitu, seluruh riwayat aktivitas dikelola sepenuhnya oleh sistem internal untuk memastikan kelancaran alur data pelacakan.

peran Pengguna : 
Dalam platform ini, pengguna tidak hanya bertindak sebagai konsumen, tetapi juga memiliki peran aktif sebagai kontributor dan kurator komunitas. Secara mendasar, pengguna yang sudah masuk melalui akun Google dapat memanfaatkan sistem untuk mencari inspirasi memasak hanya dengan memasukkan bahan sisa. Selain itu, aktivitas dan riwayat memasak mereka akan tercatat secara personal melalui sistem tracker yang terintegrasi di dalam aplikasi.

Lebih dari sekadar mencari resep, pengguna juga berperan langsung dalam membangun dan menjaga kualitas isi database. Sebagai kontributor, pengguna dapat mengunggah resep buatan sendiri yang kandungan nutrisinya akan langsung divalidasi otomatis oleh sistem Spoonacular. Sementara itu, sebagai kurator, pengguna memegang kendali atas moderasi konten melalui fitur upvote dan downvote.

Penilaian kolektif dari pengguna inilah yang pada akhirnya menggerakkan algoritma utama aplikasi. Pilihan mereka menentukan apakah sebuah resep layak diprioritaskan di posisi teratas, atau justru dieliminasi secara permanen oleh sistem moderasi otomatis karena telah menyentuh batas 100 downvote.
