from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    ForeignKeyConstraint,
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, PkUuid, Stempel, pg_enum
from app.modules.instrumen.domain.entities import (
    JenisEntitas,
    JenisIpo,
    JenisPenilaian,
    StatusInstrumen,
    TahapPpepp,
)


class InstrumenVersi(PkUuid, Stempel, Base):
    __tablename__ = "instrumen_versi"
    lam_id: Mapped[UUID] = mapped_column(ForeignKey("lam.id"))
    kode_versi: Mapped[str] = mapped_column(Text)
    nama: Mapped[str] = mapped_column(Text)
    jenjang: Mapped[str] = mapped_column(Text, server_default="S1")
    dasar_hukum: Mapped[str | None] = mapped_column(Text)
    berlaku_mulai: Mapped[date | None] = mapped_column(Date)
    status: Mapped[StatusInstrumen] = mapped_column(pg_enum(StatusInstrumen, "status_instrumen"), server_default="draf")
    skor_maks: Mapped[int] = mapped_column(SmallInteger, server_default=text("4"))
    label_skor: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    nilai_akhir_maks: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    disusun_oleh: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))
    disetujui_oleh: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))
    disetujui_pada: Mapped[datetime | None]
    __table_args__ = (UniqueConstraint("lam_id", "jenjang", "kode_versi"),)


class InstrumenKriteria(PkUuid, Base):
    __tablename__ = "instrumen_kriteria"
    instrumen_versi_id: Mapped[UUID] = mapped_column(ForeignKey("instrumen_versi.id", ondelete="CASCADE"))
    kode: Mapped[str] = mapped_column(Text)
    nama: Mapped[str] = mapped_column(Text)
    bobot: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    urutan: Mapped[int] = mapped_column(SmallInteger)


class InstrumenButir(PkUuid, Stempel, Base):
    __tablename__ = "instrumen_butir"
    instrumen_versi_id: Mapped[UUID] = mapped_column(ForeignKey("instrumen_versi.id", ondelete="CASCADE"))
    kriteria_id: Mapped[UUID]
    kode: Mapped[str] = mapped_column(Text)
    nomor_urut: Mapped[int] = mapped_column(SmallInteger)
    elemen: Mapped[str] = mapped_column(Text)
    deskriptor: Mapped[str | None] = mapped_column(Text)
    jenis_ipo: Mapped[JenisIpo | None] = mapped_column(pg_enum(JenisIpo, "jenis_ipo"))
    tahap_ppepp: Mapped[TahapPpepp | None] = mapped_column(pg_enum(TahapPpepp, "tahap_ppepp"))
    jenis_penilaian: Mapped[JenisPenilaian] = mapped_column(pg_enum(JenisPenilaian, "jenis_penilaian"), server_default="kualitatif")
    bobot: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    rumus: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    skema_narasi: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    panduan: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        ForeignKeyConstraint(["kriteria_id", "instrumen_versi_id"], ["instrumen_kriteria.id", "instrumen_kriteria.instrumen_versi_id"]),
    )


class InstrumenButirRubrik(Base):
    __tablename__ = "instrumen_butir_rubrik"
    instrumen_butir_id: Mapped[UUID] = mapped_column(ForeignKey("instrumen_butir.id", ondelete="CASCADE"), primary_key=True)
    skor: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    deskriptor: Mapped[str] = mapped_column(Text)


class InstrumenPeringkat(PkUuid, Base):
    __tablename__ = "instrumen_peringkat"
    instrumen_versi_id: Mapped[UUID] = mapped_column(ForeignKey("instrumen_versi.id", ondelete="CASCADE"))
    kode: Mapped[str] = mapped_column(Text)
    nama: Mapped[str] = mapped_column(Text)
    tingkat: Mapped[int] = mapped_column(SmallInteger)
    masa_berlaku_tahun: Mapped[int | None] = mapped_column(SmallInteger)
    nilai_akhir_min: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    nilai_akhir_maks: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    syarat: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))


class InstrumenButirAmbang(Base):
    __tablename__ = "instrumen_butir_ambang"
    instrumen_butir_id: Mapped[UUID] = mapped_column(ForeignKey("instrumen_butir.id", ondelete="CASCADE"), primary_key=True)
    peringkat_id: Mapped[UUID] = mapped_column(ForeignKey("instrumen_peringkat.id", ondelete="CASCADE"), primary_key=True)
    skor_min: Mapped[Decimal] = mapped_column(Numeric(3, 2))
    is_syarat_perlu: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))


class InstrumenButirPadanan(Base):
    __tablename__ = "instrumen_butir_padanan"
    butir_lama_id: Mapped[UUID] = mapped_column(ForeignKey("instrumen_butir.id", ondelete="CASCADE"), primary_key=True)
    butir_baru_id: Mapped[UUID] = mapped_column(ForeignKey("instrumen_butir.id", ondelete="CASCADE"), primary_key=True)
    catatan: Mapped[str | None] = mapped_column(Text)


class IndikatorInti(PkUuid, Base):
    __tablename__ = "indikator_inti"
    kode: Mapped[str] = mapped_column(Text, unique=True)
    nama: Mapped[str] = mapped_column(Text)
    satuan: Mapped[str | None] = mapped_column(Text)
    deskripsi: Mapped[str | None] = mapped_column(Text)
    rumus: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    makin_tinggi_makin_baik: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))


class PemetaanButir(PkUuid, Stempel, Base):
    __tablename__ = "pemetaan_butir"
    instrumen_butir_id: Mapped[UUID] = mapped_column(ForeignKey("instrumen_butir.id", ondelete="CASCADE"))
    sumber: Mapped[JenisEntitas] = mapped_column(pg_enum(JenisEntitas, "jenis_entitas"))
    indikator_inti_id: Mapped[UUID | None] = mapped_column(ForeignKey("indikator_inti.id"))
    aturan: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    keterangan: Mapped[str | None] = mapped_column(Text)
    is_aktif: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    menggantikan_id: Mapped[UUID | None] = mapped_column(ForeignKey("pemetaan_butir.id", ondelete="SET NULL"))
    disetujui_oleh: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))
    disetujui_pada: Mapped[datetime | None]
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))
    updated_by: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))
