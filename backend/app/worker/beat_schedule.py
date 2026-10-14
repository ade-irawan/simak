from celery.schedules import crontab

JADWAL = {
    "periksa-bukti-tiap-jam": {"task": "simak.periksa_bukti", "schedule": crontab(minute=5), "options": {"queue": "periodik"}},
    "hitung-indikator-malam": {"task": "simak.hitung_indikator", "schedule": crontab(hour=1, minute=30), "options": {"queue": "periodik"}},
    "hitung-simulasi-malam": {
        "task": "simak.hitung_simulasi_semua",
        "schedule": crontab(hour=2, minute=0),
        "options": {"queue": "periodik"},
    },
    "ingatkan-tenggat-harian": {"task": "simak.ingatkan_tenggat", "schedule": crontab(hour=7, minute=0), "options": {"queue": "periodik"}},
}
