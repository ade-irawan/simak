import { useSyncExternalStore } from "react";

export type Tema = "gelap" | "terang";

const KUNCI = "simak.tema";
const WARNA_BAR: Record<Tema, string> = { gelap: "#05080f", terang: "#f3f6fb" };
const pendengar = new Set<() => void>();

/** Tema awal: pilihan tersimpan, bila tidak ada maka gelap (bahasa visual cdscan). Skrip di index.html menerapkannya sebelum cat pertama. */
function baca(): Tema {
  try {
    return localStorage.getItem(KUNCI) === "terang" ? "terang" : "gelap";
  } catch {
    return "gelap";
  }
}

function terapkan(t: Tema) {
  document.documentElement.dataset.tema = t;
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", WARNA_BAR[t]);
}

export function setTema(t: Tema) {
  try {
    localStorage.setItem(KUNCI, t);
  } catch {
    /* penyimpanan diblokir: tema tetap berlaku untuk sesi ini */
  }
  terapkan(t);
  pendengar.forEach((f) => f());
}

function langganan(f: () => void) {
  pendengar.add(f);
  return () => pendengar.delete(f);
}

const snapshot = (): Tema => (document.documentElement.dataset.tema === "terang" ? "terang" : "gelap");

export function useTema() {
  const tema = useSyncExternalStore(langganan, snapshot, () => "gelap" as Tema);
  return { tema, ubah: () => setTema(tema === "gelap" ? "terang" : "gelap") };
}

terapkan(baca());
