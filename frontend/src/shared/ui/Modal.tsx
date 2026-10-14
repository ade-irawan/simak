import { useEffect, type ReactNode } from "react";
import { Button } from "./Button";
import { Icon } from "./Icon";

interface Props {
  judul: ReactNode;
  onTutup: () => void;
  children: ReactNode;
  footer?: ReactNode;
  lebar?: boolean;
}

export function Modal({ judul, onTutup, children, footer, lebar }: Props) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => e.key === "Escape" && onTutup();
    document.addEventListener("keydown", h);
    const awal = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", h);
      document.body.style.overflow = awal;
    };
  }, [onTutup]);
  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onTutup()}>
      <div className={`modal${lebar ? " modal--wide" : ""}`} role="dialog" aria-modal="true">
        <div className="modal__head">
          <h2 className="modal__title">{judul}</h2>
          <Button variant="ghost" size="icon" onClick={onTutup} aria-label="Tutup">
            <Icon name="x" />
          </Button>
        </div>
        <div className="modal__body">{children}</div>
        {footer && <div className="modal__foot">{footer}</div>}
      </div>
    </div>
  );
}

export function Konfirmasi({
  judul,
  pesan,
  onYa,
  onBatal,
  labelYa = "Ya, lanjutkan",
  bahaya,
  memproses,
}: {
  judul: string;
  pesan: ReactNode;
  onYa: () => void;
  onBatal: () => void;
  labelYa?: string;
  bahaya?: boolean;
  memproses?: boolean;
}) {
  return (
    <Modal
      judul={judul}
      onTutup={onBatal}
      footer={
        <>
          <Button variant="ghost" onClick={onBatal}>
            Batal
          </Button>
          <Button variant={bahaya ? "danger" : "primary"} onClick={onYa} disabled={memproses}>
            {memproses && <span className="spinner" />} {labelYa}
          </Button>
        </>
      }
    >
      <div className="muted">{pesan}</div>
    </Modal>
  );
}
