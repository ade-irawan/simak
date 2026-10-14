import { useState } from "react";
import { api } from "@/shared/api/client";
import type { Halaman, Rec } from "@/shared/api/types";
import { useAuth } from "@/shared/auth/AuthProvider";
import { useAksi, useApi, useDebounced } from "@/shared/lib/hooks";
import { tanggal, ukuranBerkas, waktu } from "@/shared/lib/format";
import { Button, Icon, Konfirmasi, KV, Modal, Muat, PageHead, Pager, Pill, StatusPill, Tabel, type Kolom } from "@/shared/ui";
import { TambahBuktiModal } from "./TambahBukti";

export function BuktiPage() {
  const { punya } = useAuth();
  const [q, setQ] = useState("");
  const [jenis, setJenis] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [tambah, setTambah] = useState(false);
  const [detail, setDetail] = useState<string | null>(null);
  const [hapus, setHapus] = useState<Rec | null>(null);
  const cari = useDebounced(q);
  const daftar = useApi<Halaman<Rec>>("/bukti", { q: cari, jenis, status_cek: status, page, per_page: 15 }, { keep: true });
  const bisaTulis = punya("kaprodi", "staf_prodi", "staf_fakultas");
  const cek = useAksi((id: string) => api.post(`/bukti/${id}/cek`), { invalidate: ["/bukti"], sukses: (r) => (r.status_cek === "ok" ? "Bukti terjangkau" : "Bukti TIDAK terjangkau") });
  const hapusAksi = useAksi((id: string) => api.del(`/bukti/${id}`), { invalidate: ["/bukti"], sukses: "Bukti dihapus", onSuccess: () => setHapus(null) });
  const unduh = useAksi(async (id: string) => {
    const r = await api.get(`/bukti/${id}/unduh`);
    window.open(r.url, "_blank", "noopener");
  });

  const kolom: Kolom<Rec>[] = [
    { kunci: "judul", judul: "Bukti", render: (b) => <div><div className="cell-title">{b.judul}</div><div className="cell-sub">{b.sumber ?? "—"}{b.tanggal_dokumen ? ` · ${tanggal(b.tanggal_dokumen)}` : ""}</div></div> },
    { kunci: "jenis", judul: "Jenis", render: (b) => <span><Icon name={b.jenis === "berkas" ? "file" : "link"} size={14} /> {b.jenis === "berkas" ? `Berkas · ${ukuranBerkas(b.ukuran_byte)}` : `Tautan · ${b.akses_tautan}`}</span> },
    { kunci: "prodi", judul: "Berlaku untuk", render: (b) => <div className="chips">{b.berlaku_untuk.length ? b.berlaku_untuk.map((p: Rec) => <Pill key={p.id}>{p.kode}</Pill>) : <Pill>UPPS</Pill>}</div> },
    { kunci: "status", judul: "Keterjangkauan", render: (b) => <div><StatusPill status={b.status_cek} /><div className="cell-sub">{b.dicek_pada ? `dicek ${waktu(b.dicek_pada)}` : "belum pernah dicek"}</div></div> },
    {
      kunci: "aksi", judul: "", render: (b) => (
        <div className="row" style={{ justifyContent: "flex-end", gap: "0.3rem" }} onClick={(e) => e.stopPropagation()}>
          <Button variant="ghost" size="icon" title="Buka" onClick={() => unduh.mutate(b.id)}><Icon name="external" size={15} /></Button>
          {bisaTulis && <Button variant="ghost" size="icon" title="Periksa sekarang" onClick={() => cek.mutate(b.id)}><Icon name="refresh" size={15} /></Button>}
          {punya("kaprodi") && <Button variant="danger" size="icon" title="Hapus" onClick={() => setHapus(b)}><Icon name="trash" size={15} /></Button>}
        </div>
      ),
    },
  ];

  return (
    <div className="stack">
      <PageHead
        judul="Bukti"
        sub="Satu bukti dapat ditautkan ke banyak butir dan banyak prodi. Link-checker memeriksa berkas dan tautan secara berkala; bukti tak terjangkau memblokir validasi final."
        aksi={bisaTulis && <Button onClick={() => setTambah(true)}><Icon name="plus" size={16} /> Tambah bukti</Button>}
      />
      <div className="toolbar">
        <input className="input" placeholder="Cari judul atau sumber…" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} />
        <select className="input" value={jenis} onChange={(e) => { setJenis(e.target.value); setPage(1); }}><option value="">Semua jenis</option><option value="berkas">Berkas</option><option value="tautan">Tautan</option></select>
        <select className="input" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}><option value="">Semua status</option><option value="ok">Terjangkau</option><option value="tidak_terjangkau">Tidak terjangkau</option><option value="belum_dicek">Belum dicek</option></select>
      </div>
      <Muat q={daftar}>
        {(d) => (
          <>
            <Tabel kolom={kolom} baris={d.data} id={(b) => b.id} onKlik={(b) => setDetail(b.id)} kosong="Belum ada bukti" />
            <Pager page={d.meta.page} perPage={d.meta.per_page} total={d.meta.total} onGanti={setPage} />
          </>
        )}
      </Muat>
      {tambah && <TambahBuktiModal onTutup={() => setTambah(false)} onSelesai={() => setTambah(false)} />}
      {detail && <DetailBukti id={detail} onTutup={() => setDetail(null)} onBuka={() => unduh.mutate(detail)} />}
      {hapus && <Konfirmasi judul="Hapus bukti?" bahaya labelYa="Hapus" memproses={hapusAksi.isPending} pesan={<>“{hapus.judul}” akan dihapus (hapus lunak). Bukti yang masih ditautkan ke butir tidak dapat dihapus.</>} onBatal={() => setHapus(null)} onYa={() => hapusAksi.mutate(hapus.id)} />}
    </div>
  );
}

function DetailBukti({ id, onTutup, onBuka }: { id: string; onTutup: () => void; onBuka: () => void }) {
  const q = useApi<Rec>(`/bukti/${id}`);
  return (
    <Modal judul="Rincian bukti" onTutup={onTutup} lebar footer={<><Button variant="ghost" onClick={onTutup}>Tutup</Button><Button onClick={onBuka}><Icon name="external" size={15} /> Buka bukti</Button></>}>
      <Muat q={q}>
        {(b) => (
          <div className="stack">
            <KV item={[
              ["Judul", b.judul], ["Jenis", b.jenis === "berkas" ? `Berkas — ${b.nama_berkas} (${ukuranBerkas(b.ukuran_byte)})` : `Tautan — ${b.url}`],
              ["Sumber", b.sumber], ["Tanggal dokumen", tanggal(b.tanggal_dokumen)], ["Status", <StatusPill key="s" status={b.status_cek} />],
              ["Terakhir dicek", `${waktu(b.dicek_pada)}${b.kode_http ? ` (HTTP ${b.kode_http})` : ""}`],
              ["Berlaku untuk", b.berlaku_untuk.map((p: Rec) => p.kode).join(", ") || "UPPS"],
            ]} />
            <h3 style={{ fontSize: "0.95rem" }}>Dipakai pada butir</h3>
            {b.pemakaian?.butir?.length ? (
              <ul className="reasons">{b.pemakaian.butir.map((x: Rec) => <li key={x.butir_siklus_id}><span className="mono">{x.kode}</span> — {x.elemen}</li>)}</ul>
            ) : <div className="muted">Belum ditautkan ke butir mana pun.</div>}
          </div>
        )}
      </Muat>
    </Modal>
  );
}

/** Pemilih bukti untuk ditautkan ke butir: cari bukti yang sudah ada atau tambah baru. */
export function PilihBuktiModal({ onPilih, onTutup, sudah }: { onPilih: (b: Rec) => void; onTutup: () => void; sudah: string[] }) {
  const [q, setQ] = useState("");
  const [baru, setBaru] = useState(false);
  const cari = useDebounced(q);
  const daftar = useApi<Halaman<Rec>>("/bukti", { q: cari, per_page: 12 }, { keep: true });
  if (baru) return <TambahBuktiModal onTutup={() => setBaru(false)} onSelesai={onPilih} />;
  return (
    <Modal judul="Tautkan bukti ke butir" onTutup={onTutup} lebar footer={<><Button variant="ghost" onClick={onTutup}>Tutup</Button><Button variant="lime" onClick={() => setBaru(true)}><Icon name="plus" size={15} /> Bukti baru</Button></>}>
      <input className="input" placeholder="Cari bukti…" value={q} onChange={(e) => setQ(e.target.value)} autoFocus style={{ marginBottom: "0.8rem" }} />
      <Muat q={daftar}>
        {(d) =>
          d.data.length === 0 ? <div className="empty">Tidak ada bukti yang cocok.</div> : (
            <div className="stack stack--sm">
              {d.data.map((b) => (
                <div key={b.id} className="card row row--between" style={{ padding: "0.7rem 1rem" }}>
                  <div><div className="cell-title">{b.judul}</div><div className="cell-sub">{b.jenis === "berkas" ? b.nama_berkas : b.url}</div></div>
                  <div className="row"><StatusPill status={b.status_cek} />
                    <Button size="sm" disabled={sudah.includes(b.id)} onClick={() => onPilih(b)}>{sudah.includes(b.id) ? "Sudah ditautkan" : "Tautkan"}</Button></div>
                </div>
              ))}
            </div>
          )
        }
      </Muat>
    </Modal>
  );
}
