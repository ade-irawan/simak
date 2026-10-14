import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./layout/AppShell";
import type { Peran } from "./shared/api/types";
import { RequireAuth, RequirePeran } from "./shared/auth/Guards";
import { Empty } from "./shared/ui";
import { AsesmenButir, AsesmenButirDaftar, AsesmenDaftar } from "./features/asesmen/AsesmenPages";
import { BukaKunciPage, LupaSandiPage, MasukPage, ProfilPage, ResetSandiPage } from "./features/auth/AuthPages";
import { UsulanAsesorPage } from "./features/admin/UsulanAsesorPage";
import { AuditPage, LlmPage, PengaturanPage, PenggunaPage } from "./features/admin/AdminPages";
import { BuktiPage } from "./features/bukti/BuktiPage";
import { AnalisisPage } from "./features/dasbor/AnalisisPage";
import { Beranda, DasborProdi } from "./features/dasbor/Dasbor";
import { DataIntiPage } from "./features/data/DataIntiPage";
import { DokumenEksternalPage } from "./features/eksternal/EksternalPages";
import { InstrumenDetail, InstrumenList } from "./features/instrumen/InstrumenPages";
import { PpeppPage, TahapanPage } from "./features/ppepp/PpeppPages";
import { ButirPage } from "./features/siklus/ButirPage";
import { PapanKerjaPage, SiklusDetailPage, SiklusListPage } from "./features/siklus/SiklusPages";

const KONTEN: Peran[] = ["dekan", "kaprodi", "staf_prodi", "staf_fakultas"];
const Batas = ({ peran, children }: { peran: Peran[]; children: React.ReactNode }) => <RequirePeran peran={peran}>{children}</RequirePeran>;

export default function App() {
  return (
    <Routes>
      <Route path="/masuk" element={<MasukPage />} />
      <Route path="/lupa-sandi" element={<LupaSandiPage />} />
      <Route path="/reset-sandi" element={<ResetSandiPage />} />
      <Route path="/buka-kunci" element={<BukaKunciPage />} />

      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          <Route index element={<Beranda />} />
          <Route path="profil" element={<ProfilPage />} />
          <Route path="papan-kerja" element={<Batas peran={["staf_prodi", "staf_fakultas"]}><PapanKerjaPage /></Batas>} />
          <Route path="dasbor/prodi/:prodiId" element={<Batas peran={KONTEN}><DasborProdi /></Batas>} />
          <Route path="analisis" element={<Batas peran={["dekan"]}><AnalisisPage /></Batas>} />

          <Route path="siklus" element={<Batas peran={KONTEN}><SiklusListPage /></Batas>} />
          <Route path="siklus/:id" element={<Batas peran={KONTEN}><SiklusDetailPage /></Batas>} />
          <Route path="butir/:id" element={<Batas peran={KONTEN}><ButirPage /></Batas>} />
          <Route path="laporan/:id" element={<Navigate to="/siklus" replace />} />

          <Route path="ppepp" element={<Batas peran={KONTEN}><PpeppPage /></Batas>} />
          <Route path="ppepp/penetapan/:id" element={<Batas peran={KONTEN}><TahapanPage /></Batas>} />

          <Route path="data/:sumber" element={<Batas peran={KONTEN}><DataIntiPage /></Batas>} />
          <Route path="bukti" element={<Batas peran={KONTEN}><BuktiPage /></Batas>} />
          <Route path="dokumen-eksternal" element={<Batas peran={KONTEN}><DokumenEksternalPage /></Batas>} />

          <Route path="instrumen" element={<Batas peran={KONTEN}><InstrumenList /></Batas>} />
          <Route path="instrumen/:id" element={<Batas peran={KONTEN}><InstrumenDetail /></Batas>} />
          <Route path="llm" element={<Batas peran={["dekan", "staf_fakultas"]}><LlmPage /></Batas>} />

          <Route path="usulan-asesor" element={<Batas peran={["kaprodi"]}><UsulanAsesorPage /></Batas>} />
          <Route path="asesmen" element={<Batas peran={["asesor"]}><AsesmenDaftar /></Batas>} />
          <Route path="asesmen/butir/:id" element={<Batas peran={["asesor"]}><AsesmenButir /></Batas>} />
          <Route path="asesmen/:siklusId" element={<Batas peran={["asesor"]}><AsesmenButirDaftar /></Batas>} />

          <Route path="pengguna" element={<Batas peran={["dekan", "admin_it"]}><PenggunaPage /></Batas>} />
          <Route path="audit" element={<Batas peran={["dekan", "admin_it"]}><AuditPage /></Batas>} />
          <Route path="pengaturan" element={<Batas peran={["admin_it"]}><PengaturanPage /></Batas>} />
          <Route path="*" element={<Empty judul="Halaman tidak ditemukan" ikon="search" />} />
        </Route>
      </Route>
    </Routes>
  );
}
