"""Use case manajemen akun dan penugasan peran.

* Dekan: kebijakan (siapa berperan apa, cakupan prodi, aktivasi asesor) — US-G2, §3.4.
* Admin IT: operasi akun — membuat akun beserta penugasan perannya, mengatur/reset sandi, buka kunci, nonaktif —
  tanpa akses konten (US-A1). Admin IT boleh mengatur sandi sementara akun mana pun (termasuk Dekan yang lupa sandi),
  tetapi tidak menetapkan peran Dekan, dan penugasan asesor darinya hanya berstatus usulan sampai Dekan menyetujui (EC-26/28).
* Kaprodi: hanya mengusulkan asesor untuk prodinya.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.core import audit
from app.core.exceptions import (
    AksesDitolak,
    KonflikStatus,
    LaporanBelumDisetujui,
    TidakDitemukan,
    ValidasiGagal,
)
from app.core.pagination import ParamHalaman, halaman
from app.core.permissions import IT, D, K, Pemanggil, Peran
from app.core.security import hash_sandi, wajib_sandi_kuat
from app.core.unit_of_work import UnitOfWork
from app.modules.laporan import public as laporan_public
from app.modules.pengguna.application import token as tokens
from app.modules.pengguna.domain import rules
from app.modules.pengguna.domain.entities import JenisTokenAkun, StatusPengguna, StatusPenugasan
from app.modules.pengguna.domain.events import AsesorDiaktifkan, TokenAkunDibuat
from app.modules.pengguna.infrastructure.models import Pengguna, PenugasanPeran
from app.modules.referensi import public as referensi


def _sekarang() -> datetime:
    return datetime.now(UTC)


class ManajemenAkun:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
        self.session = uow.session

    # ---------- baca ----------
    async def _muat_penugasan(self, ids: list[UUID]) -> dict[UUID, list[dict[str, Any]]]:
        if not ids:
            return {}
        baris = (
            (
                await self.session.execute(
                    select(PenugasanPeran).where(PenugasanPeran.pengguna_id.in_(ids), PenugasanPeran.status != StatusPenugasan.DICABUT)
                )
            )
            .scalars()
            .all()
        )
        return await self._ke_dict_penugasan(list(baris))

    async def _ke_dict_penugasan(self, baris: list[PenugasanPeran]) -> dict[UUID, list[dict[str, Any]]]:
        prodi = {p.id: p for p in await referensi.daftar_prodi(self.session)}
        ids_pengguna = {b.pengguna_id for b in baris} | {b.disetujui_oleh for b in baris if b.disetujui_oleh}
        nama = dict((await self.session.execute(select(Pengguna.id, Pengguna.nama).where(Pengguna.id.in_(ids_pengguna)))).all())
        hasil: dict[UUID, list[dict[str, Any]]] = {}
        for b in baris:
            p = prodi.get(b.prodi_id) if b.prodi_id else None
            hasil.setdefault(b.pengguna_id, []).append(
                {
                    "id": b.id,
                    "pengguna": {"id": b.pengguna_id, "nama": nama.get(b.pengguna_id, "")},
                    "peran": b.peran,
                    "prodi": {"id": p.id, "kode": p.kode, "nama": p.nama} if p else None,
                    "status": b.status,
                    "berlaku_mulai": b.berlaku_mulai,
                    "berlaku_sampai": b.berlaku_sampai,
                    "disetujui_oleh": ({"id": b.disetujui_oleh, "nama": nama.get(b.disetujui_oleh, "")} if b.disetujui_oleh else None),
                    "catatan": b.catatan,
                }
            )
        return hasil

    async def _ke_out(self, p: Pengguna, penugasan: dict[UUID, list[dict[str, Any]]]) -> dict[str, Any]:
        return {
            "id": p.id,
            "nama": p.nama,
            "email": p.email,
            "status": p.status,
            "wajib_ganti_sandi": p.wajib_ganti_sandi,
            "jumlah_gagal_login": p.jumlah_gagal_login,
            "terkunci_sampai": p.terkunci_sampai,
            "login_terakhir": p.login_terakhir,
            "peran": penugasan.get(p.id, []),
        }

    async def daftar(
        self, param: ParamHalaman, *, peran: Peran | None, prodi_id: UUID | None, status: StatusPengguna | None, terkunci: bool | None
    ) -> dict[str, Any]:
        stmt = select(Pengguna)
        if param.q:
            like = f"%{param.q}%"
            stmt = stmt.where(or_(Pengguna.nama.ilike(like), Pengguna.email.ilike(like)))
        if status:
            stmt = stmt.where(Pengguna.status == status)
        if terkunci is not None:
            kondisi = Pengguna.terkunci_sampai > func.now()
            stmt = stmt.where(kondisi if terkunci else ~kondisi | Pengguna.terkunci_sampai.is_(None))
        if peran or prodi_id:
            sub = select(PenugasanPeran.pengguna_id).where(PenugasanPeran.status != StatusPenugasan.DICABUT)
            if peran:
                sub = sub.where(PenugasanPeran.peran == peran)
            if prodi_id:
                sub = sub.where(PenugasanPeran.prodi_id == prodi_id)
            stmt = stmt.where(Pengguna.id.in_(sub))
        urut = param.urutan(
            {"nama": Pengguna.nama, "email": Pengguna.email, "login_terakhir": Pengguna.login_terakhir}, [Pengguna.nama.asc()]
        )
        hasil = await halaman(self.session, stmt, param, urut, lambda p: p)
        penugasan = await self._muat_penugasan([p.id for p in hasil["data"]])
        hasil["data"] = [await self._ke_out(p, penugasan) for p in hasil["data"]]
        return hasil

    async def rincian(self, pengguna_id: UUID) -> dict[str, Any]:
        p = await self._ambil(pengguna_id)
        return await self._ke_out(p, await self._muat_penugasan([p.id]))

    async def _ambil(self, pengguna_id: UUID) -> Pengguna:
        p = await self.session.get(Pengguna, pengguna_id)
        if p is None:
            raise TidakDitemukan("Akun tidak ditemukan.")
        return p

    # ---------- akun ----------
    async def _memegang_peran(self, pengguna_id: UUID, peran: Peran) -> bool:
        ada = await self.session.execute(
            select(PenugasanPeran.id).where(
                PenugasanPeran.pengguna_id == pengguna_id, PenugasanPeran.peran == peran, PenugasanPeran.status != StatusPenugasan.DICABUT
            )
        )
        return ada.first() is not None

    @staticmethod
    def _tolak_dekan_oleh_it(pemanggil: Pemanggil, peran: Peran) -> None:
        """Peran Dekan hanya ditetapkan Dekan; Admin IT tidak boleh mengangkat Dekan (pemisahan tugas)."""
        if peran == Peran.DEKAN and not pemanggil.punya(D):
            raise AksesDitolak(alasan="admin_it_tidak_menetapkan_dekan")

    async def buat(self, pemanggil: Pemanggil, data: Any) -> dict[str, Any]:
        pemanggil.wajib(D, IT)
        for pa in data.penugasan:
            self._periksa_cakupan(pa.peran, pa.prodi_id)
            self._tolak_dekan_oleh_it(pemanggil, pa.peran)
        async with self.uow:
            sandi = data.password_awal
            if sandi:
                wajib_sandi_kuat(sandi)
            pengguna = Pengguna(
                email=str(data.email).lower(),
                nama=data.nama,
                password_hash=hash_sandi(sandi or secrets.token_urlsafe(24)),
                wajib_ganti_sandi=True,
            )
            self.session.add(pengguna)
            try:
                await self.session.flush()
            except IntegrityError as exc:
                raise ValidasiGagal("Email sudah terdaftar.", details=[{"kolom": "email"}]) from exc
            for pa in data.penugasan:
                if pa.peran == Peran.ASESOR:
                    raise ValidasiGagal("Asesor dibuat lewat penugasan peran (butuh laporan disetujui).")
                self.session.add(
                    PenugasanPeran(
                        pengguna_id=pengguna.id,
                        peran=pa.peran,
                        prodi_id=pa.prodi_id,
                        status=StatusPenugasan.AKTIF,
                        berlaku_mulai=pa.berlaku_mulai,
                        berlaku_sampai=pa.berlaku_sampai,
                        disetujui_oleh=pemanggil.id,
                        disetujui_pada=_sekarang(),
                    )
                )
            try:
                await self.session.flush()
            except IntegrityError as exc:
                raise ValidasiGagal("Penugasan bentrok dengan penugasan aktif yang sudah ada.") from exc
            if not sandi:
                token = await tokens.buat_token_akun(
                    self.session, pengguna.id, JenisTokenAkun.RESET_SANDI, dibuat_oleh=pemanggil.id, menit=60 * 24 * 3
                )
                self.uow.terbitkan(TokenAkunDibuat(pengguna.id, pengguna.email, pengguna.nama, "reset_sandi", token))
            await audit.catat(
                self.session,
                "pengguna.buat",
                pemanggil=pemanggil,
                entitas="pengguna",
                entitas_id=pengguna.id,
                detail={"peran": [p.peran for p in data.penugasan]},
            )
        return await self.rincian(pengguna.id)

    async def ubah(self, pemanggil: Pemanggil, pengguna_id: UUID, data: Any) -> dict[str, Any]:
        pemanggil.wajib(D)
        perubahan = data.model_dump(exclude_unset=True, exclude_none=True)
        if perubahan.get("status") == StatusPengguna.NONAKTIF and pengguna_id == pemanggil.id:
            raise ValidasiGagal("Tidak dapat menonaktifkan akun sendiri.")
        async with self.uow:
            p = await self._ambil(pengguna_id)
            for k, v in perubahan.items():
                setattr(p, k, v)
            if perubahan.get("status") == StatusPengguna.NONAKTIF:
                await tokens.cabut_semua_refresh(self.session, p.id)
            await audit.catat(self.session, "pengguna.ubah", pemanggil=pemanggil, entitas="pengguna", entitas_id=p.id, detail=perubahan)
        return await self.rincian(pengguna_id)

    async def nonaktifkan(self, pemanggil: Pemanggil, pengguna_id: UUID) -> dict[str, Any]:
        pemanggil.wajib(D, IT)
        if pengguna_id == pemanggil.id:
            raise ValidasiGagal("Tidak dapat menonaktifkan akun sendiri.")
        async with self.uow:
            p = await self._ambil(pengguna_id)
            p.status = StatusPengguna.NONAKTIF
            await tokens.cabut_semua_refresh(self.session, p.id)
            await audit.catat(self.session, "pengguna.nonaktifkan", pemanggil=pemanggil, entitas="pengguna", entitas_id=p.id)
        return await self.rincian(pengguna_id)

    async def buka_kunci(self, pemanggil: Pemanggil, pengguna_id: UUID, alasan: str) -> dict[str, Any]:
        pemanggil.wajib(IT)
        async with self.uow:
            p = await self._ambil(pengguna_id)
            p.jumlah_gagal_login, p.terkunci_sampai = 0, None
            await audit.catat(
                self.session, "pengguna.buka_kunci", pemanggil=pemanggil, entitas="pengguna", entitas_id=p.id, detail={"alasan": alasan}
            )
        return {"id": p.id, "status": p.status, "terkunci_sampai": None, "jumlah_gagal_login": 0}

    async def atur_sandi(self, pemanggil: Pemanggil, pengguna_id: UUID, sandi_baru: str) -> None:
        """Admin IT menetapkan sandi sementara; pengguna wajib menggantinya saat masuk. Sesi lama dicabut dan kunci dibuka."""
        pemanggil.wajib(IT)
        if pengguna_id == pemanggil.id:
            raise ValidasiGagal("Untuk akun sendiri gunakan menu Ganti kata sandi.")
        wajib_sandi_kuat(sandi_baru)
        async with self.uow:
            p = await self._ambil(pengguna_id)
            p.password_hash = hash_sandi(sandi_baru)
            p.wajib_ganti_sandi = True
            p.jumlah_gagal_login, p.terkunci_sampai = 0, None
            await tokens.cabut_semua_refresh(self.session, p.id)
            await audit.catat(self.session, "pengguna.atur_sandi", pemanggil=pemanggil, entitas="pengguna", entitas_id=p.id)

    async def atur_email(self, pemanggil: Pemanggil, pengguna_id: UUID, email_baru: str) -> dict[str, Any]:
        """Admin IT mengganti alamat surel akun mana pun, termasuk akunnya sendiri. Tautan lama yang belum dipakai
        dihanguskan; sesi pemilik akun dicabut kecuali bila Admin IT mengubah akunnya sendiri."""
        pemanggil.wajib(IT)
        email_baru = email_baru.strip().lower()
        async with self.uow:
            p = await self._ambil(pengguna_id)
            email_lama = p.email
            if email_baru == email_lama.lower():
                raise ValidasiGagal("Alamat surel sama dengan yang sekarang.", details=[{"kolom": "email"}])
            p.email = email_baru
            try:
                await self.session.flush()
            except IntegrityError as exc:
                raise ValidasiGagal("Email sudah terdaftar.", details=[{"kolom": "email"}]) from exc
            await tokens.hanguskan_token_akun(self.session, p.id)
            if p.id != pemanggil.id:
                await tokens.cabut_semua_refresh(self.session, p.id)
            await audit.catat(
                self.session,
                "pengguna.atur_email",
                pemanggil=pemanggil,
                entitas="pengguna",
                entitas_id=p.id,
                detail={"email_lama": email_lama, "email_baru": email_baru},
            )
        return await self.rincian(pengguna_id)

    async def reset_sandi(self, pemanggil: Pemanggil, pengguna_id: UUID) -> None:
        pemanggil.wajib(IT)
        async with self.uow:
            p = await self._ambil(pengguna_id)
            token = await tokens.buat_token_akun(self.session, p.id, JenisTokenAkun.RESET_SANDI, dibuat_oleh=pemanggil.id)
            self.uow.terbitkan(TokenAkunDibuat(p.id, p.email, p.nama, "reset_sandi", token))
            await audit.catat(self.session, "pengguna.reset_sandi", pemanggil=pemanggil, entitas="pengguna", entitas_id=p.id)

    # ---------- penugasan ----------
    @staticmethod
    def _periksa_cakupan(peran: Peran, prodi_id: UUID | None) -> None:
        pesan = rules.periksa_cakupan(peran, prodi_id is not None)
        if pesan:
            raise ValidasiGagal(pesan)

    async def daftar_penugasan(
        self, pemanggil: Pemanggil, param: ParamHalaman, *, peran: Peran | None, prodi_id: UUID | None, status: StatusPenugasan | None
    ) -> dict[str, Any]:
        pemanggil.wajib(D, K, IT)
        stmt = select(PenugasanPeran)
        if not pemanggil.punya(D, IT):
            # Kaprodi hanya melihat usulan/penugasan asesor di prodinya sendiri (§3.4).
            milik = pemanggil.prodi_dari(K)
            if prodi_id and prodi_id not in milik:
                raise AksesDitolak(alasan="di_luar_cakupan_prodi")
            if peran not in (None, Peran.ASESOR):
                raise AksesDitolak(alasan="kaprodi_hanya_melihat_asesor")
            peran = Peran.ASESOR
            stmt = stmt.where(PenugasanPeran.prodi_id.in_(milik))
        if peran:
            stmt = stmt.where(PenugasanPeran.peran == peran)
        if prodi_id:
            stmt = stmt.where(PenugasanPeran.prodi_id == prodi_id)
        if status:
            stmt = stmt.where(PenugasanPeran.status == status)
        hasil = await halaman(self.session, stmt, param, [PenugasanPeran.created_at.desc()], lambda b: b)
        peta = await self._ke_dict_penugasan(hasil["data"])
        urut = {b.id: i for i, b in enumerate(hasil["data"])}
        hasil["data"] = sorted((x for lst in peta.values() for x in lst), key=lambda x: urut[x["id"]])
        return hasil

    async def calon_asesor(self, pemanggil: Pemanggil, q: str) -> list[dict[str, Any]]:
        """Akun yang dapat diusulkan sebagai asesor: aktif dan belum memegang peran lain (bukan staf/pimpinan).

        Pencarian minimal 3 huruf dan hasil dibatasi agar Kaprodi tidak dapat menelusuri seluruh daftar akun.
        """
        pemanggil.wajib(D, K)
        q = q.strip()
        if len(q) < 3:
            raise ValidasiGagal("Ketik minimal 3 huruf nama atau surel.", details=[{"kolom": "q"}])
        peran_lain = select(PenugasanPeran.pengguna_id).where(
            PenugasanPeran.peran != Peran.ASESOR, PenugasanPeran.status.in_([StatusPenugasan.AKTIF, StatusPenugasan.DIUSULKAN])
        )
        like = f"%{q}%"
        baris = (
            await self.session.execute(
                select(Pengguna)
                .where(
                    Pengguna.status == StatusPengguna.AKTIF,
                    Pengguna.id.not_in(peran_lain),
                    or_(Pengguna.nama.ilike(like), Pengguna.email.ilike(like)),
                )
                .order_by(Pengguna.nama)
                .limit(20)
            )
        ).scalars()
        return [{"id": p.id, "nama": p.nama, "email": p.email} for p in baris]

    async def tambah_penugasan(self, pemanggil: Pemanggil, data: Any) -> dict[str, Any]:
        pemanggil.wajib(D, K, IT)
        self._periksa_cakupan(data.peran, data.prodi_id)
        mengusulkan = False
        if not pemanggil.punya(D):
            if pemanggil.punya(IT):
                # Admin IT mengatur peran akun, tetapi asesor tetap menunggu persetujuan Dekan.
                self._tolak_dekan_oleh_it(pemanggil, data.peran)
                mengusulkan = data.peran == Peran.ASESOR
            else:
                # Kaprodi hanya boleh mengusulkan asesor untuk prodinya sendiri (§3.4).
                mengusulkan = True
                if data.peran != Peran.ASESOR or data.prodi_id not in pemanggil.prodi_dari(K):
                    raise AksesDitolak(alasan="kaprodi_hanya_mengusulkan_asesor_prodi_sendiri")
        pengguna = await self._ambil(data.pengguna_id)
        if pengguna.status != StatusPengguna.AKTIF:
            raise ValidasiGagal("Akun tidak aktif.")
        asesor = data.peran == Peran.ASESOR
        if asesor:
            ganda = (
                await self.session.execute(
                    select(PenugasanPeran.id).where(
                        PenugasanPeran.pengguna_id == data.pengguna_id,
                        PenugasanPeran.peran == Peran.ASESOR,
                        PenugasanPeran.prodi_id == data.prodi_id,
                        PenugasanPeran.status.in_([StatusPenugasan.AKTIF, StatusPenugasan.DIUSULKAN]),
                    )
                )
            ).first()
            if ganda:
                raise ValidasiGagal("Akun ini sudah diusulkan atau aktif sebagai asesor pada prodi tersebut.")
        if asesor and not mengusulkan and not (data.berlaku_mulai and data.berlaku_sampai):
            raise ValidasiGagal("Jendela asesmen (berlaku_mulai dan berlaku_sampai) wajib untuk asesor.")
        if data.berlaku_mulai and data.berlaku_sampai and data.berlaku_sampai <= data.berlaku_mulai:
            raise ValidasiGagal("berlaku_sampai harus setelah berlaku_mulai.")
        belum_disetujui = False
        if asesor and not mengusulkan:
            belum_disetujui = not await laporan_public.prodi_punya_laporan_disetujui(self.session, data.prodi_id)
        status = StatusPenugasan.DIUSULKAN if (mengusulkan or belum_disetujui) else StatusPenugasan.AKTIF
        async with self.uow:
            penugasan = PenugasanPeran(
                pengguna_id=data.pengguna_id,
                peran=data.peran,
                prodi_id=data.prodi_id,
                status=status,
                berlaku_mulai=data.berlaku_mulai,
                berlaku_sampai=data.berlaku_sampai,
                catatan=data.catatan,
                diusulkan_oleh=pemanggil.id if mengusulkan or belum_disetujui else None,
                disetujui_oleh=pemanggil.id if status == StatusPenugasan.AKTIF else None,
                disetujui_pada=_sekarang() if status == StatusPenugasan.AKTIF else None,
            )
            self.session.add(penugasan)
            try:
                await self.session.flush()
            except IntegrityError as exc:
                raise ValidasiGagal("Penugasan bentrok dengan penugasan aktif yang sudah ada.") from exc
            await audit.catat(
                self.session,
                "penugasan.usul" if status != StatusPenugasan.AKTIF else "penugasan.tambah",
                pemanggil=pemanggil,
                entitas="penugasan_peran",
                entitas_id=penugasan.id,
                prodi_id=data.prodi_id,
                detail={"peran": data.peran, "pengguna_id": data.pengguna_id},
            )
            if status == StatusPenugasan.AKTIF and asesor:
                self.uow.terbitkan(AsesorDiaktifkan(penugasan.id, data.pengguna_id, data.prodi_id))
        if belum_disetujui:
            # Usulan tetap tersimpan (sudah di-commit di atas); penolakan sesuai EC-28.
            raise LaporanBelumDisetujui(details=[{"penugasan_id": str(penugasan.id), "status": "diusulkan"}])
        return await self._satu_penugasan(penugasan.id)

    async def setujui_penugasan(self, pemanggil: Pemanggil, penugasan_id: UUID, data: Any) -> dict[str, Any]:
        pemanggil.wajib(D)
        penugasan = await self.session.get(PenugasanPeran, penugasan_id)
        if penugasan is None:
            raise TidakDitemukan("Penugasan tidak ditemukan.")
        if penugasan.status != StatusPenugasan.DIUSULKAN:
            raise KonflikStatus("Hanya usulan yang dapat disetujui.")
        mulai = data.berlaku_mulai or penugasan.berlaku_mulai
        sampai = data.berlaku_sampai or penugasan.berlaku_sampai
        if penugasan.peran == Peran.ASESOR:
            if not (mulai and sampai):
                raise ValidasiGagal("Jendela asesmen wajib ditetapkan saat menyetujui asesor.")
            if sampai <= mulai:
                raise ValidasiGagal("berlaku_sampai harus setelah berlaku_mulai.")
            if not await laporan_public.prodi_punya_laporan_disetujui(self.session, penugasan.prodi_id):
                raise LaporanBelumDisetujui()
        async with self.uow:
            penugasan.berlaku_mulai, penugasan.berlaku_sampai = mulai, sampai
            penugasan.status = StatusPenugasan.AKTIF
            penugasan.disetujui_oleh, penugasan.disetujui_pada = pemanggil.id, _sekarang()
            try:
                await self.session.flush()
            except IntegrityError as exc:
                raise ValidasiGagal("Penugasan bentrok dengan penugasan aktif yang sudah ada.") from exc
            await audit.catat(
                self.session,
                "penugasan.setujui",
                pemanggil=pemanggil,
                entitas="penugasan_peran",
                entitas_id=penugasan.id,
                prodi_id=penugasan.prodi_id,
            )
            if penugasan.peran == Peran.ASESOR and penugasan.prodi_id:
                self.uow.terbitkan(AsesorDiaktifkan(penugasan.id, penugasan.pengguna_id, penugasan.prodi_id))
        return await self._satu_penugasan(penugasan_id)

    async def cabut_penugasan(self, pemanggil: Pemanggil, penugasan_id: UUID) -> dict[str, Any]:
        pemanggil.wajib(D, IT)
        penugasan = await self.session.get(PenugasanPeran, penugasan_id)
        if penugasan is None:
            raise TidakDitemukan("Penugasan tidak ditemukan.")
        if not pemanggil.punya(D):
            self._tolak_dekan_oleh_it(pemanggil, penugasan.peran)
            if penugasan.pengguna_id == pemanggil.id:
                raise ValidasiGagal("Tidak dapat mencabut penugasan milik sendiri.")
        if penugasan.status == StatusPenugasan.DICABUT:
            raise KonflikStatus("Penugasan sudah dicabut.")
        async with self.uow:
            penugasan.status = StatusPenugasan.DICABUT
            penugasan.dicabut_oleh, penugasan.dicabut_pada = pemanggil.id, _sekarang()
            await audit.catat(
                self.session,
                "penugasan.cabut",
                pemanggil=pemanggil,
                entitas="penugasan_peran",
                entitas_id=penugasan.id,
                prodi_id=penugasan.prodi_id,
            )
        return await self._satu_penugasan(penugasan_id)

    async def _satu_penugasan(self, penugasan_id: UUID) -> dict[str, Any]:
        b = await self.session.get(PenugasanPeran, penugasan_id)
        assert b is not None
        peta = await self._ke_dict_penugasan([b])
        return peta[b.pengguna_id][0]
