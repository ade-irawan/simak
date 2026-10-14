-- =====================================================================
-- SIMAK — data awal rujukan (jalankan setelah schema.sql)
-- Struktur kriteria dan aturan peringkat diambil dari dokumen instrumen:
--   * IAPS 3.1 LAMSAMA (Matriks & Pedoman Penilaian, Program Sarjana)
--   * IAPS 2.1 LAM INFOKOM (Matriks Penilaian Kinerja Program Studi, Program Sarjana)
-- Butir dan rubrik lengkap dimuat lewat fitur impor instrumen; di sini
-- hanya satu butir contoh per instrumen.
-- Instrumen dimuat berstatus draf; menjadi aktif setelah disetujui Dekan di aplikasi.
-- =====================================================================

INSERT INTO fakultas (kode, nama) VALUES ('FAK', '(isi nama fakultas)');

INSERT INTO lam (kode, nama) VALUES
  ('LAMSAMA',     'Lembaga Akreditasi Mandiri Sains Alam dan Ilmu Formal'),
  ('LAM_INFOKOM', 'Lembaga Akreditasi Mandiri Informatika dan Komputer');

INSERT INTO prodi (fakultas_id, lam_id, kode, nama)
SELECT f.id, l.id, p.kode, p.nama
FROM (VALUES ('ILKOM',    'Ilmu Komputer',  'LAM_INFOKOM'),
             ('KIMIA',    'Kimia',          'LAMSAMA'),
             ('AKTUARIA', 'Sains Aktuaria', 'LAMSAMA')) AS p(kode, nama, lam)
JOIN lam l ON l.kode = p.lam
CROSS JOIN fakultas f;

-- ---------------------------------------------------------------------
-- Versi instrumen
-- ---------------------------------------------------------------------
INSERT INTO instrumen_versi (lam_id, kode_versi, nama, jenjang, status, skor_maks, label_skor, nilai_akhir_maks, dasar_hukum)
SELECT id, '3.1', 'IAPS 3.1 LAMSAMA - Program Sarjana', 'S1', 'draf', 4,
       '{"4":"Baik Sekali","3":"Baik","2":"Cukup","1":"Kurang"}'::jsonb, NULL, NULL
FROM lam WHERE kode = 'LAMSAMA';

INSERT INTO instrumen_versi (lam_id, kode_versi, nama, jenjang, status, skor_maks, label_skor, nilai_akhir_maks, dasar_hukum)
SELECT id, '2.1', 'IAPS 2.1 LAM INFOKOM - Program Sarjana', 'S1', 'draf', 4,
       '{"4":"Sangat Baik","3":"Baik","2":"Cukup","1":"Kurang"}'::jsonb, 400,
       'Peraturan LAM INFOKOM Nomor 11/PERLAM/MA/LAM-INFOKOM/X/2025'
FROM lam WHERE kode = 'LAM_INFOKOM';

-- ---------------------------------------------------------------------
-- Kriteria LAMSAMA 3.1: enam kriteria, tanpa bobot
-- ---------------------------------------------------------------------
INSERT INTO instrumen_kriteria (instrumen_versi_id, kode, nama, bobot, urutan)
SELECT v.id, k.kode, k.nama, NULL, k.urutan
FROM instrumen_versi v
JOIN lam l ON l.id = v.lam_id AND l.kode = 'LAMSAMA'
CROSS JOIN (VALUES
  ('A', 'Tata Kelola dan Penjaminan Mutu',               1),
  ('B', 'Pendidikan dan Pengajaran',                     2),
  ('C', 'Penelitian',                                    3),
  ('D', 'Pengabdian kepada Masyarakat',                  4),
  ('E', 'Capaian dan Luaran',                            5),
  ('F', 'Analisis dan Penetapan Program Pengembangan',   6)
) AS k(kode, nama, urutan)
WHERE v.kode_versi = '3.1';

-- ---------------------------------------------------------------------
-- Kriteria LAM INFOKOM 2.1: bobot dari total 400
-- ---------------------------------------------------------------------
INSERT INTO instrumen_kriteria (instrumen_versi_id, kode, nama, bobot, urutan)
SELECT v.id, k.kode, k.nama, k.bobot, k.urutan
FROM instrumen_versi v
JOIN lam l ON l.id = v.lam_id AND l.kode = 'LAM_INFOKOM'
CROSS JOIN (VALUES
  ('A', 'Kondisi Eksternal',                      4, 1),
  ('B', 'Profil Unit Pengelola Program Studi',    4, 2),
  ('1', 'Budaya Mutu',                           40, 3),
  ('2', 'Relevansi Pendidikan',                 120, 4),
  ('3', 'Relevansi Penelitian',                  72, 5),
  ('4', 'Relevansi PkM',                         60, 6),
  ('5', 'Akuntabilitas',                         40, 7),
  ('6', 'Diferensiasi Misi',                     40, 8),
  ('S', 'Suplemen Program Studi',                20, 9)
) AS k(kode, nama, bobot, urutan)
WHERE v.kode_versi = '2.1';

-- ---------------------------------------------------------------------
-- Peringkat LAM INFOKOM 2.1: rentang nilai akhir + syarat rerata kriteria
-- ---------------------------------------------------------------------
INSERT INTO instrumen_peringkat (instrumen_versi_id, kode, nama, tingkat, masa_berlaku_tahun, nilai_akhir_min, nilai_akhir_maks, syarat)
SELECT v.id, p.kode, p.nama, p.tingkat, p.masa, p.nmin, p.nmaks, p.syarat::jsonb
FROM instrumen_versi v
JOIN lam l ON l.id = v.lam_id AND l.kode = 'LAM_INFOKOM'
CROSS JOIN (VALUES
  ('tidak_terakreditasi', 'Tidak Terakreditasi',      0, NULL::int, NULL::numeric, 200::numeric, '{}'),
  ('terakreditasi',       'Terakreditasi',            1, NULL,      200,           NULL,
     '{"catatan":"Juga berlaku bila nilai akhir >= 321 tetapi syarat Unggul tidak terpenuhi"}'),
  ('unggul_3',            'Unggul (berlaku 3 tahun)', 2, 3,         321,           361,
     '{"kriteria":["1","2","3"],"rerata_kriteria_min":3.20,"skor_butir_min":3.00}'),
  ('unggul_5',            'Unggul (berlaku 5 tahun)', 3, 5,         361,           NULL,
     '{"kriteria":["1","2","3"],"rerata_kriteria_min":3.20,"skor_butir_min":3.00}')
) AS p(kode, nama, tingkat, masa, nmin, nmaks, syarat)
WHERE v.kode_versi = '2.1';

-- ---------------------------------------------------------------------
-- Peringkat LAMSAMA 3.1: ditentukan ambang minimum per butir, bukan nilai akhir
-- ---------------------------------------------------------------------
INSERT INTO instrumen_peringkat (instrumen_versi_id, kode, nama, tingkat, masa_berlaku_tahun)
SELECT v.id, p.kode, p.nama, p.tingkat, p.masa
FROM instrumen_versi v
JOIN lam l ON l.id = v.lam_id AND l.kode = 'LAMSAMA'
CROSS JOIN (VALUES
  ('tidak_terakreditasi', 'Tidak Terakreditasi', 0, NULL::int),
  ('terakreditasi',       'Terakreditasi',       1, NULL),
  ('unggul_2',            'Unggul (2 tahun)',    2, 2),
  ('unggul_5',            'Unggul (5 tahun)',    3, 5)
) AS p(kode, nama, tingkat, masa)
WHERE v.kode_versi = '3.1';

-- ---------------------------------------------------------------------
-- Butir contoh LAMSAMA: indikator 3 (SPMI/PPEPP), syarat perlu di semua peringkat
-- ---------------------------------------------------------------------
INSERT INTO instrumen_butir (instrumen_versi_id, kriteria_id, kode, nomor_urut, elemen, jenis_penilaian, skema_narasi)
SELECT k.instrumen_versi_id, k.id, '3', 3,
       'Keterlaksanaan Sistem Penjaminan Mutu Internal (akademik dan non akademik) pendidikan, penelitian, dan PkM yang merupakan penerapan siklus PPEPP, dibuktikan dengan keberadaan 5 aspek',
       'kualitatif',
       '[{"bagian":"utama","judul":"Uraian keterlaksanaan SPMI dan lima aspeknya"}]'::jsonb
FROM instrumen_kriteria k
JOIN instrumen_versi v ON v.id = k.instrumen_versi_id AND v.kode_versi = '3.1'
JOIN lam l ON l.id = v.lam_id AND l.kode = 'LAMSAMA'
WHERE k.kode = 'A';

INSERT INTO instrumen_butir_ambang (instrumen_butir_id, peringkat_id, skor_min, is_syarat_perlu)
SELECT b.id, p.id, a.skor_min, true
FROM instrumen_butir b
JOIN instrumen_versi v ON v.id = b.instrumen_versi_id AND v.kode_versi = '3.1'
JOIN lam l ON l.id = v.lam_id AND l.kode = 'LAMSAMA'
JOIN instrumen_peringkat p ON p.instrumen_versi_id = v.id
JOIN (VALUES ('unggul_5', 4), ('unggul_2', 4), ('terakreditasi', 3)) AS a(kode, skor_min) ON a.kode = p.kode
WHERE b.kode = '3';

-- ---------------------------------------------------------------------
-- Butir contoh LAM INFOKOM: 1.1.A (Budaya Mutu, tahap Penetapan, jenis Input, bobot 3)
-- ---------------------------------------------------------------------
INSERT INTO instrumen_butir (instrumen_versi_id, kriteria_id, kode, nomor_urut, elemen, jenis_ipo, tahap_ppepp, jenis_penilaian, bobot)
SELECT k.instrumen_versi_id, k.id, '1.1.A', 3,
       'Kebijakan, standar, dan indikator terkait sistem tata kelola internal UPPS dan/atau PT berikut SOP, mencakup administrasi akademik, keuangan, SDM, dan aspek lain dalam siklus PPEPP',
       'input', 'penetapan', 'kualitatif', 3
FROM instrumen_kriteria k
JOIN instrumen_versi v ON v.id = k.instrumen_versi_id AND v.kode_versi = '2.1'
JOIN lam l ON l.id = v.lam_id AND l.kode = 'LAM_INFOKOM'
WHERE k.kode = '1';

-- ---------------------------------------------------------------------
-- Pengaturan bawaan
-- ---------------------------------------------------------------------
INSERT INTO pengaturan_sistem (kunci, nilai, deskripsi) VALUES
  ('login.maks_gagal',        '5',    'Jumlah gagal login berturut-turut sebelum akun dikunci'),
  ('login.menit_kunci',       '15',   'Lama kunci sementara (menit) sebelum terbuka otomatis'),
  ('bukti.maks_mb',           '25',   'Batas ukuran berkas bukti (MB)'),
  ('bukti.jam_antar_cek',     '24',   'Selang pemeriksaan link-checker (jam)'),
  ('bukti.gagal_sebelum_merah','3',   'Jumlah gagal beruntun sebelum bukti ditandai tidak terjangkau');
