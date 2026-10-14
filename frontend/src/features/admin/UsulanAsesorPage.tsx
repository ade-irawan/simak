import { useState } from "react";
import { api } from "@/shared/api/client";
import type { Halaman, Rec } from "@/shared/api/types";
import { useAuth } from "@/shared/auth/AuthProvider";
import { useAksi, useApi, useDebounced } from "@/shared/lib/hooks";
import { tanggal } from "@/shared/lib/format";
import { Alert, Button, ErrorBox, Field, Icon, Modal, Muat, PageHead, Pill, StatusPill, Tabel, type Kolom } from "@/shared/ui";

const INV = ["/penugasan-peran", "/pengguna"];

/** Kaprodi mengusulkan asesor untuk prodinya; Dekan yang menyetujui dan menetapkan jendela asesmen (SKPL §3.4). */
export function UsulanAsesorPage() {
  const { aktif } = useAuth();
  const [baru, setBaru] = useState(false);
  const q = useApi<Halaman<Rec>>("/penugasan-peran", { peran: "asesor", per_page: 50 });
  const kolom: Kolom<Rec>[] = [
    { kunci: "p", judul: "Calon asesor", render: (t) => <div className="cell-title">{t.pengguna.nama}</div> },
    { kunci: "status", judul: "Status", render: (t) => <StatusPill status={t.status} /> },
    { kunci: "jendela", judul: "Jendela asesmen", render: (t) => (t.berlaku_mulai ? `${tanggal(t.berlaku_mulai)} – ${tanggal(t.berlaku_sampai)}` : <span className="faint">ditetapkan Dekan</span>) },
    { kunci: "cat", judul: "Catatan", render: (t) => t.catatan ?? <span className="faint">—</span> },
  ];
  return (
    <div className="stack">
      <PageHead
        judul="Usulan asesor"
        sub={`Usulkan asesor untuk Prodi ${aktif?.prodi?.nama ?? ""}. Hanya Dekan yang mengaktifkan akses, dan hanya setelah laporan prodi berstatus Disetujui.`}
        aksi={<Button onClick={() => setBaru(true)}><Icon name="plus" size={16} /> Usulkan asesor</Button>}
      />
      <Alert jenis="info" judul="Cara kerja">
        Akses asesor bersifat hanya-baca, terikat satu prodi, berjendela waktu, dan hanya melihat versi laporan yang sudah disetujui Dekan. Usulan Anda tersimpan walau
        laporan belum disetujui; Dekan dapat mengaktifkannya kemudian.
      </Alert>
      <Muat q={q}>{(d) => <Tabel kolom={kolom} baris={d.data} id={(t) => t.id} kosong="Belum ada usulan asesor untuk prodi Anda." />}</Muat>
      {baru && <UsulModal prodiId={aktif!.prodi!.id} onTutup={() => setBaru(false)} />}
    </div>
  );
}

function UsulModal({ prodiId, onTutup }: { prodiId: string; onTutup: () => void }) {
  const [cari, setCari] = useState("");
  const [pilih, setPilih] = useState<Rec | null>(null);
  const [catatan, setCatatan] = useState("");
  const kata = useDebounced(cari.trim());
  const calon = useApi<Rec[]>(kata.length >= 3 ? "/pengguna/calon-asesor" : null, { q: kata });
  const simpan = useAksi(() => api.post("/penugasan-peran", { pengguna_id: pilih!.id, peran: "asesor", prodi_id: prodiId, catatan: catatan || null }), {
    sukses: "Usulan terkirim; menunggu persetujuan Dekan", invalidate: INV, onSuccess: onTutup,
  });
  return (
    <Modal judul="Usulkan asesor" onTutup={onTutup} footer={<><Button variant="ghost" onClick={onTutup}>Batal</Button><Button disabled={!pilih || simpan.isPending} onClick={() => simpan.mutate()}>{simpan.isPending && <span className="spinner" />} Kirim usulan</Button></>}>
      <Field label="Cari akun asesor" bantuan="Ketik minimal 3 huruf nama atau surel. Hanya akun yang belum memegang peran lain yang muncul; akun asesor dibuat oleh Dekan.">
        <input value={cari} onChange={(e) => { setCari(e.target.value); setPilih(null); }} placeholder="mis. prof atau nama@kampus.ac.id" autoFocus />
      </Field>
      {kata.length >= 3 && (
        <Muat q={calon}>
          {(d) => d.length === 0 ? <div className="muted" style={{ marginBottom: "1rem" }}>Tidak ada akun yang cocok. Minta Dekan membuat akun asesor lebih dulu.</div> : (
            <div className="stack stack--sm" style={{ marginBottom: "1rem" }}>
              {d.map((u) => (
                <label key={u.id} className="card row" style={{ padding: "0.6rem 0.9rem", cursor: "pointer", borderColor: pilih?.id === u.id ? "var(--blue)" : undefined }}>
                  <input type="radio" name="calon" checked={pilih?.id === u.id} onChange={() => setPilih(u)} />
                  <div><div className="cell-title">{u.nama}</div><div className="cell-sub">{u.email}</div></div>
                </label>
              ))}
            </div>
          )}
        </Muat>
      )}
      {pilih && <div style={{ marginBottom: "1rem" }}><Pill warna="lime" dot>{pilih.nama}</Pill></div>}
      <Field label="Catatan untuk Dekan (opsional)"><textarea style={{ minHeight: 70 }} value={catatan} onChange={(e) => setCatatan(e.target.value)} placeholder="mis. Asesor lapangan, jadwal 10–14 November" /></Field>
      {simpan.error && <ErrorBox error={simpan.error} />}
    </Modal>
  );
}
