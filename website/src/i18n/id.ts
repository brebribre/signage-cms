/** Every word the site says, in Indonesian. Same shape as en.ts, which the type enforces. */
import type { Messages } from './en'

const id: Messages = {
  meta: {
    title: 'Paskall. Digital signage yang berjalan sendiri',
    description: 'Paskall menayangkan gambar, video, dan situs web langsung di setiap layar Anda: digital signage, smart TV, dan Android box.',
  },
  lang: { label: 'Bahasa', en: 'English', id: 'Bahasa Indonesia' },
  nav: {
    label: 'Situs',
    menu: 'Menu',
    links: { screens: 'Layar', content: 'Konten', publish: 'Publikasi', platforms: 'Platform', faq: 'FAQ', home: 'Beranda', demo: 'Demo' },
    signIn: 'Masuk',
    requestAccess: 'Request Akses',
  },
  hero: {
    title: 'Cara cerdas mengelola layar Anda.',
    subtitle: 'Gambar, video, dan situs web, di layar apa pun.',
    cta: 'Request Akses',
    demo: 'Lihat demo',
    screens: [
      { name: 'TV Lobi', kind: 'Android box' },
      { name: 'Totem pintu masuk', kind: 'Smart TV' },
      { name: 'Resepsionis', kind: 'Android box' },
      { name: 'Layar kafe', kind: 'Browser' },
    ],
    campaign: 'Kampanye toko',
    hint: 'Pilih playlist. Semua layar ikut berubah.',
    picker: 'Yang ditayangkan layar',
    press: { value: '1 klik', label: 'Untuk memperbarui semua layar' },
    any: { value: 'Layar apa pun', label: 'Android, smart TV, dan browser' },
    pair: 'Hubungkan layar dengan kode enam huruf',
  },
  slides: [
    { name: 'Jam buka', title: 'Buka sampai 21.00', sub: 'Dapur tutup pukul 20.30' },
    { name: 'Menu makan siang', title: 'Menu spesial hari ini', sub: 'Tanyakan di kasir' },
    { name: 'Lowongan kerja', title: 'Kami sedang merekrut', sub: 'Pindai di resepsionis' },
    { name: 'Selamat datang', title: 'Selamat datang', sub: 'Wifi: tamu' },
  ],
  online: 'Daring',
  venues: {
    label: 'Tempat Paskall digunakan',
    items: ['Kafe', 'LOBI', 'klinik', 'Ritel', 'KAMPUS', 'Restoran', 'Hotel', 'SHOWROOM'],
  },
  features: {
    lead: 'Paskall adalah CMS untuk Digital Signage.',
    rest: 'Hubungkan layar, rancang tayangannya, dan publikasikan ke semua layar sekaligus.',
  },
  connect: {
    title: 'Hubungkan layar Anda',
    body: 'Ketik kode enam huruf dari pemutar, dan layar langsung bergabung.',
    statUnder: 'Kurang dari',
    statValue: '1 menit',
    statCaption: 'Untuk menghubungkan layar baru',
    live: 'Aktif',
    photoAlt: 'Layar kafe yang dijalankan Paskall',
    screens: [
      { name: 'TV Lobi', kind: 'Android box' },
      { name: 'Totem pintu masuk', kind: 'Smart TV' },
      { name: 'Layar kafe', kind: 'Browser' },
    ],
  },
  design: {
    tablist: 'Editor',
    inPaskall: 'di Paskall',
    tabs: [
      { label: 'Desain', title: 'Desain konten Anda.', text: 'Foto, video, situs web, dan teks, sesuai bentuk asli layar.' },
      { label: 'Playlist', title: 'Putar secara berurutan.', text: 'Atur urutan dan lama tayang masing-masing.' },
      { label: 'Jadwal', title: 'Tentukan di mana dan kapan.', text: 'Pilih layar dan jamnya, menurut jam dan hari.' },
    ],
  },
  publish: {
    title: 'Publikasikan dengan mudah',
    body: 'Perubahan terpublikasi dalam hitungan detik.',
    ready: 'Siap dipublikasikan',
    sending: 'Mengirim ke layar',
    live: 'Tayang di semua layar',
    button: 'Publikasikan',
    publishing: 'Mengirim',
    published: 'Terpublikasi',
    screens: [
      { name: 'TV Lobi', kind: 'Android box' },
      { name: 'Pintu masuk', kind: 'Smart TV' },
      { name: 'Kafe', kind: 'Browser' },
    ],
  },
  platforms: {
    lead: 'Dirancang untuk fleksibilitas.',
    rest: 'Satu pemutar, di layar apa pun yang sudah Anda miliki.',
    items: [
      { name: 'Android', text: 'Pasang .apk kami di Android TV box dan perangkat Android lainnya.' },
      { name: 'Browser Smart TV', text: 'Memanfaatkan browser bawaan smart TV, tanpa perlu instalasi.' },
      { name: 'Browser', text: 'Perangkat apa pun yang bisa menjalankan browser.' },
    ],
  },
  responsive: {
    lead: 'Pantau dari mana saja.',
    rest: 'Paskall CMS bisa dipakai di ponsel, tablet, dan monitor.',
    monitorAlt: 'Dasbor Paskall di monitor',
  },
  demo: {
    metaTitle: 'Paskall. Demo',
    title: 'Menghubungkan Layar hingga Menayangkan Konten',
    videoLabel: 'Demo: Paskall CMS di laptop di samping TV yang berubah di setiap langkah',
    left: 'Paskall CMS',
    right: 'Layar sungguhan',
  },
  faq: {
    title: 'Pertanyaan yang Sering Diajukan',
    more: 'Ada pertanyaan lain?',
    write: 'Tulis ke kami',
    items: [
      { q: 'Perangkat apa yang saya butuhkan?', a: 'Android TV box atau tablet apa pun, atau smart TV dengan browser. Kendali jarak jauh penuh memerlukan pemutar Android yang diatur sebagai Device Owner, dan kami bisa membantu mengaturnya.' },
      { q: 'Apa yang terjadi jika internet terputus?', a: 'Tidak ada yang terlihat. File tersimpan di layar, jadi tayangan terus berputar dan menyusul begitu jaringan kembali.' },
      { q: 'Apakah staf bisa mengubah konten dengan aman?', a: 'Bisa. Mereka hanya mendapat layar yang Anda izinkan, dan setiap perubahan pada layar menunggu persetujuan Anda.' },
      { q: 'Seberapa besar video yang bisa diunggah?', a: 'Unggah file aslinya. Paskall membuat salinan yang bisa diputar di setiap layar: 4K untuk Android box dan 1080p untuk browser TV.' },
    ],
  },
  footer: {
    title: 'Pasang layar pertama Anda di Paskall',
    body: 'Tinggalkan kontak Anda, dan kami akan menghubungi Anda untuk menyiapkan akun.',
    cta: 'Request Akses',
    signIn: 'Masuk',
    form: {
      name: 'Nama',
      company: 'Perusahaan',
      optional: '(opsional)',
      email: 'Email',
      phone: 'Nomor telepon',
      eitherHint: 'Email atau nomor telepon, mana saja yang Anda suka. Minimal salah satu.',
      sending: 'Mengirim…',
      sentTitle: 'Terima kasih!',
      sentBody: 'Permintaan Anda sudah kami terima, dan kami akan segera menghubungi Anda.',
      errors: {
        name: 'Mohon isi nama Anda.',
        contact: 'Mohon isi email atau nomor telepon agar kami bisa menghubungi Anda.',
        email: 'Sepertinya email itu kurang tepat.',
        phone: 'Sepertinya nomor telepon itu kurang tepat.',
        send: 'Gagal terkirim. Periksa koneksi Anda lalu coba lagi.',
      },
    },
  },
}

export default id
