import { unduhBerkas } from "@/shared/api/client";
import { useAksi } from "@/shared/lib/hooks";
import { Button } from "./Button";
import { Icon } from "./Icon";

/** Mengunduh templat impor (XLSX atau CSV) dari API. `path` = alamat endpoint templat, tanpa awalan /api/v1. */
export function TombolTemplat({ path, namaDasar }: { path: string; namaDasar: string }) {
  const unduh = useAksi((format: "xlsx" | "csv") => unduhBerkas(path, `${namaDasar}.${format}`, { format }), { diam: false });
  return (
    <span className="row" style={{ gap: "0.4rem" }}>
      <Button variant="ghost" disabled={unduh.isPending} onClick={() => unduh.mutate("xlsx")}><Icon name="download" size={15} /> Unduh templat XLSX</Button>
      <Button variant="ghost" disabled={unduh.isPending} onClick={() => unduh.mutate("csv")}>CSV</Button>
    </span>
  );
}
