from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, SmallInteger, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, Berversi, PkUuid, Stempel, pg_enum
from app.modules.bukti.domain.entities import AksesTautan, JenisBukti, StatusCekBukti
from app.modules.instrumen.public import JenisEntitas


class Bukti(PkUuid, Stempel, Berversi, Base):
    __tablename__ = "bukti"
    judul: Mapped[str] = mapped_column(Text)
    jenis: Mapped[JenisBukti] = mapped_column(pg_enum(JenisBukti, "jenis_bukti"))
    objek_key: Mapped[str | None] = mapped_column(Text)
    nama_berkas: Mapped[str | None] = mapped_column(Text)
    mime_type: Mapped[str | None] = mapped_column(Text)
    ukuran_byte: Mapped[int | None] = mapped_column(BigInteger)
    sha256: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    akses_tautan: Mapped[AksesTautan | None] = mapped_column(pg_enum(AksesTautan, "akses_tautan"))
    sumber: Mapped[str | None] = mapped_column(Text)
    tanggal_dokumen: Mapped[date | None]
    deskripsi: Mapped[str | None] = mapped_column(Text)
    status_cek: Mapped[StatusCekBukti] = mapped_column(pg_enum(StatusCekBukti, "status_cek_bukti"), server_default="belum_dicek")
    kode_http: Mapped[int | None] = mapped_column(SmallInteger)
    dicek_pada: Mapped[datetime | None]
    gagal_beruntun: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))
    updated_by: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))
    deleted_at: Mapped[datetime | None]


class BuktiProdi(Base):
    __tablename__ = "bukti_prodi"
    bukti_id: Mapped[UUID] = mapped_column(ForeignKey("bukti.id", ondelete="CASCADE"), primary_key=True)
    prodi_id: Mapped[UUID] = mapped_column(ForeignKey("prodi.id"), primary_key=True)


class BuktiButir(Base):
    __tablename__ = "bukti_butir"
    bukti_id: Mapped[UUID] = mapped_column(ForeignKey("bukti.id", ondelete="CASCADE"), primary_key=True)
    butir_siklus_id: Mapped[UUID] = mapped_column(ForeignKey("butir_siklus.id", ondelete="CASCADE"), primary_key=True)
    keterangan: Mapped[str | None] = mapped_column(Text)
    urutan: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))


class BuktiDataInti(Base):
    __tablename__ = "bukti_data_inti"
    bukti_id: Mapped[UUID] = mapped_column(ForeignKey("bukti.id", ondelete="CASCADE"), primary_key=True)
    jenis_entitas: Mapped[JenisEntitas] = mapped_column(pg_enum(JenisEntitas, "jenis_entitas"), primary_key=True)
    entitas_id: Mapped[UUID] = mapped_column(primary_key=True)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))


class BuktiTahapanPpepp(Base):
    __tablename__ = "bukti_tahapan_ppepp"
    bukti_id: Mapped[UUID] = mapped_column(ForeignKey("bukti.id", ondelete="CASCADE"), primary_key=True)
    tahapan_id: Mapped[UUID] = mapped_column(ForeignKey("tahapan_ppepp.id", ondelete="CASCADE"), primary_key=True)
