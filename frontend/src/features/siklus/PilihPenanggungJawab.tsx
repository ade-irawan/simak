import type { Halaman, Rec } from "@/shared/api/types";
import { useApi } from "@/shared/lib/hooks";

/** Pilihan penanggung jawab: Staf Prodi (untuk prodi tertentu) dan/atau Staf Fakultas. */
export function PilihPenanggungJawab({ prodiId, pengelola, nilai, onUbah }: { prodiId: string; pengelola: string; nilai: string; onUbah: (v: string) => void }) {
  const sp = useApi<Halaman<Rec>>("/pengguna", { peran: "staf_prodi", prodi_id: prodiId, status: "aktif", per_page: 100 }, { enabled: pengelola === "prodi" });
  const sf = useApi<Halaman<Rec>>("/pengguna", { peran: "staf_fakultas", status: "aktif", per_page: 100 });
  return (
    <select value={nilai} onChange={(e) => onUbah(e.target.value)}>
      <option value="">— Belum ditugaskan —</option>
      {pengelola === "prodi" && (
        <optgroup label="Staf Admin Prodi">
          {sp.data?.data.map((u) => <option key={u.id} value={u.id}>{u.nama}</option>)}
        </optgroup>
      )}
      <optgroup label="Staf Admin Fakultas">
        {sf.data?.data.map((u) => <option key={u.id} value={u.id}>{u.nama}</option>)}
      </optgroup>
    </select>
  );
}
