"""Mengimpor semua model agar terdaftar pada ``Base.metadata`` (dipakai pemetaan FK dan pengujian)."""

from app.core import audit as _audit  # noqa: F401  (tabel log_audit)
from app.modules.asesmen.infrastructure import models as _asesmen  # noqa: F401
from app.modules.bukti.infrastructure import models as _bukti  # noqa: F401
from app.modules.dokumen_eksternal.infrastructure import models as _dokumen_eksternal  # noqa: F401
from app.modules.instrumen.infrastructure import models as _instrumen  # noqa: F401
from app.modules.laporan.infrastructure import models as _laporan  # noqa: F401
from app.modules.llm.infrastructure import models as _llm  # noqa: F401
from app.modules.notifikasi.infrastructure import models as _notifikasi  # noqa: F401
from app.modules.pengguna.infrastructure import models as _pengguna  # noqa: F401
from app.modules.penilaian.infrastructure import models as _penilaian  # noqa: F401
from app.modules.ppepp.infrastructure import models as _ppepp  # noqa: F401
from app.modules.referensi import models as _referensi  # noqa: F401
from app.modules.siklus.infrastructure import models as _siklus  # noqa: F401
from app.modules.tridharma import models as _tridharma  # noqa: F401
