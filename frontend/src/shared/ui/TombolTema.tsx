import { useTema } from "@/shared/lib/tema";
import { Button } from "./Button";
import { Icon } from "./Icon";

/** Tombol ikon pengalih tema. Ikon menunjukkan tema tujuan (matahari saat gelap, bulan saat terang); label hanya untuk pembaca layar. */
export function TombolTema({ className }: { className?: string }) {
  const { tema, ubah } = useTema();
  const tujuan = tema === "gelap" ? "terang" : "gelap";
  return (
    <Button variant="ghost" size="icon" className={className} onClick={ubah} aria-label={`Ganti ke tema ${tujuan}`} title={`Tema ${tujuan}`}>
      <Icon name={tema === "gelap" ? "sun" : "moon"} />
    </Button>
  );
}
