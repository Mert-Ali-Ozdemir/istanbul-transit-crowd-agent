"""Veri ve araçlar. Hesaplama Python'da yapılır, model sadece kısa JSON sonucu görür."""

import json
from pathlib import Path

import pandas as pd

CSV_YOLU = Path(__file__).parent / "yogunluk.csv"
SAATLER = ["08:00", "13:00", "18:00", "23:00"]
GUNLER = ["hafta_ici", "hafta_sonu"]

# Saatlik yaklaşık kapasite (örnek değerler). Seviye = yolcu / kapasite.
KAPASITE = {
    "Marmaray": 45000, "Metrobüs": 30000, "M2": 35000, "M4": 30000,
    "T1": 12000, "F1": 6000, "Vapur": 8000,
}

# Her hattın durakları (sadeleştirilmiş, aktarma noktaları dahil)
HATLAR = {
    "Marmaray": ["Gebze", "Pendik", "Bostancı", "Söğütlüçeşme", "Ayrılıkçeşmesi", "Üsküdar",
                 "Sirkeci", "Yenikapı", "Bakırköy", "Halkalı"],
    "Metrobüs": ["Söğütlüçeşme", "Zincirlikuyu", "Mecidiyeköy", "Cevizlibağ", "Avcılar", "Beylikdüzü"],
    "M2":       ["Yenikapı", "Vezneciler", "Şişhane", "Taksim", "Mecidiyeköy", "Gayrettepe",
                 "Levent", "Hacıosman"],
    "M4":       ["Kadıköy", "Ayrılıkçeşmesi", "Ünalan", "Kozyatağı", "Kartal", "Tavşantepe"],
    "T1":       ["Kabataş", "Karaköy", "Eminönü", "Sirkeci", "Sultanahmet", "Beyazıt", "Aksaray",
                 "Cevizlibağ", "Bağcılar"],
    "F1":       ["Kabataş", "Taksim"],
    "Vapur":    ["Kadıköy", "Üsküdar", "Karaköy", "Eminönü", "Kabataş", "Beşiktaş"],
}
DURAKLAR = sorted({d for duraklar in HATLAR.values() for d in duraklar})

# Aynı bölgeye/geçişe hizmet eden hatlar
ALTERNATIFLER = {
    "Marmaray": ["Vapur", "Metrobüs"],
    "Metrobüs": ["Marmaray", "Vapur"],
    "Vapur":    ["Marmaray", "Metrobüs"],
    "M2":       ["F1", "Metrobüs"],
    "F1":       ["M2"],
    "T1":       ["Marmaray", "M2"],
    "M4":       ["Marmaray", "Metrobüs"],
}

# Örnek veri: her hat için [08:00, 13:00, 18:00, 23:00] saatlik yolcu sayısı
ORNEK = {
    "hafta_ici": {
        "Marmaray": [38000, 18000, 40000, 7000],
        "Metrobüs": [28500, 15000, 29000, 6000],
        "M2":       [30000, 14000, 31000, 9000],
        "M4":       [26000, 11000, 25000, 4000],
        "T1":       [9500, 10500, 10000, 2500],
        "F1":       [4000, 2500, 4200, 1500],
        "Vapur":    [5200, 3000, 4800, 900],
    },
    "hafta_sonu": {
        "Marmaray": [15000, 22000, 26000, 9000],
        "Metrobüs": [12000, 17000, 20000, 8000],
        "M2":       [11000, 16000, 22000, 12000],
        "M4":       [9000, 12000, 15000, 5000],
        "T1":       [6000, 11000, 10500, 3500],
        "F1":       [2000, 3500, 4500, 2000],
        "Vapur":    [3500, 6500, 7000, 1500],
    },
}


def veri_yukle() -> pd.DataFrame:
    """yogunluk.csv'yi okur; dosya yoksa ya da eski biçimdeyse örnek veriyle oluşturur."""
    if CSV_YOLU.exists():
        df = pd.read_csv(CSV_YOLU, encoding="utf-8")
        if "gun" in df.columns:
            return df
    satirlar = [
        {"gun": gun, "hat": hat, "saat": saat, "yolcu": yolcu}
        for gun, hatlar in ORNEK.items()
        for hat, sayilar in hatlar.items()
        for saat, yolcu in zip(SAATLER, sayilar)
    ]
    df = pd.DataFrame(satirlar)
    df.to_csv(CSV_YOLU, index=False, encoding="utf-8")
    return df


DF = veri_yukle()


def en_yakin_saat(saat: str) -> str:
    """'18:40' gibi bir saati verideki en yakın dilime yuvarlar (ör. '18:00')."""
    try:
        s, d = saat.strip().split(":")
        dakika = int(s) * 60 + int(d)
    except ValueError:
        dakika = 18 * 60
    return min(SAATLER, key=lambda x: abs(int(x[:2]) * 60 - dakika))


def _olc(hat: str, saat: str, gun: str) -> dict:
    satir = DF[(DF.gun == gun) & (DF.hat == hat) & (DF.saat == saat)]
    yolcu = int(satir.yolcu.iloc[0])
    oran = yolcu / KAPASITE[hat]
    seviye = "düşük" if oran < 0.5 else "orta" if oran < 0.8 else "yüksek"
    return {"hat": hat, "yolcu": yolcu, "seviye": seviye, "doluluk": f"%{round(oran * 100)}"}


def yogunluk_getir(hat: str, saat: str, gun: str = "hafta_ici") -> dict:
    """Bir hattın verilen saatteki yoğunluğu."""
    dilim = en_yakin_saat(saat)
    return {"gun": gun, "saat": dilim, **_olc(hat, dilim, gun)}


def alternatif_bul(hat: str, saat: str, gun: str = "hafta_ici") -> dict:
    """Alternatif hatlar, en az yoğundan en çoğa sıralı."""
    dilim = en_yakin_saat(saat)
    sonuc = [_olc(h, dilim, gun) for h in ALTERNATIFLER.get(hat, [])]
    sonuc.sort(key=lambda r: r["yolcu"] / KAPASITE[r["hat"]])
    return {"gun": gun, "saat": dilim, "alternatifler": sonuc}


def en_rahat_saat(hat: str, gun: str = "hafta_ici") -> dict:
    """Bir hattın tüm saat dilimleri, en rahattan en kalabalığa sıralı."""
    saatler = [{"saat": s, **_olc(hat, s, gun)} for s in SAATLER]
    saatler.sort(key=lambda r: r["yolcu"])
    return {"hat": hat, "gun": gun,
            "saatler": [{k: r[k] for k in ("saat", "seviye", "doluluk")} for r in saatler]}


def rota_bul(nereden: str, nereye: str, en_fazla_aktarma: int = 2) -> dict:
    """İki durak arasındaki rotalar (hat sırası ve aktarma durakları), en az aktarmalıdan başlayarak."""
    if nereden == nereye:
        return {"rotalar": [], "not": "Başlangıç ve varış aynı durak."}

    rotalar: dict[tuple, list[str]] = {}
    # Her yol: [(hat, biniş durağı), ...]
    kuyruk = [[(hat, nereden)] for hat, duraklar in HATLAR.items() if nereden in duraklar]
    while kuyruk:
        yol = kuyruk.pop(0)
        hat, binis = yol[-1]
        hat_sirasi = tuple(h for h, _ in yol)
        if nereye in HATLAR[hat]:
            rotalar.setdefault(hat_sirasi, [d for _, d in yol[1:]])
            continue
        if len(yol) > en_fazla_aktarma:
            continue
        for durak in HATLAR[hat]:
            if durak == binis:
                continue
            for diger, duraklar in HATLAR.items():
                if diger not in hat_sirasi and durak in duraklar:
                    kuyruk.append(yol + [(diger, durak)])

    secilen: list[tuple[tuple, list[str]]] = []
    for hatlar, aktarma in sorted(rotalar.items(), key=lambda r: len(r[0])):
        # Daha kısa bir rotanın hatlarını içeren dolambaçlı rotaları ele (ör. Vapur→T1→F1 yerine Vapur→F1)
        if not any(_alt_dizi_mi(kisa, hatlar) for kisa, _ in secilen):
            secilen.append((hatlar, aktarma))
    return {"nereden": nereden, "nereye": nereye,
            "rotalar": [{"hatlar": list(h), "aktarma": a} for h, a in secilen[:4]]}


def _alt_dizi_mi(kisa: tuple, uzun: tuple) -> bool:
    kalan = iter(uzun)
    return all(h in kalan for h in kisa)


_HAT = {"type": "string", "enum": list(KAPASITE)}
_SAAT = {"type": "string", "description": "HH:MM, ör. 18:00"}
_GUN = {"type": "string", "enum": GUNLER, "description": "Belirtilmezse hafta_ici"}
_DURAK = {"type": "string", "enum": DURAKLAR}


def _sema(**alanlar) -> dict:
    zorunlu = [k for k in alanlar if k != "gun"]
    return {"type": "object", "properties": alanlar, "required": zorunlu,
            "additionalProperties": False}


TOOLS = [
    {
        "name": "rota_bul",
        "description": "İki durak arasındaki olası rotaları (binilecek hatlar ve aktarma durakları) döndürür.",
        "input_schema": _sema(nereden=_DURAK, nereye=_DURAK),
    },
    {
        "name": "yogunluk_getir",
        "description": "Bir hattın verilen saatteki yolcu sayısını ve yoğunluk seviyesini (düşük/orta/yüksek) döndürür.",
        "input_schema": _sema(hat=_HAT, saat=_SAAT, gun=_GUN),
    },
    {
        "name": "alternatif_bul",
        "description": "Aynı bölgeye hizmet eden alternatif hatları en az yoğundan başlayarak döndürür.",
        "input_schema": _sema(hat=_HAT, saat=_SAAT, gun=_GUN),
    },
    {
        "name": "en_rahat_saat",
        "description": "Bir hattın tüm saat dilimlerini en rahattan en kalabalığa sıralı döndürür.",
        "input_schema": _sema(hat=_HAT, gun=_GUN),
    },
]

_FONKSIYONLAR = {
    "rota_bul": rota_bul,
    "yogunluk_getir": yogunluk_getir,
    "alternatif_bul": alternatif_bul,
    "en_rahat_saat": en_rahat_saat,
}


def araci_calistir(ad: str, girdi: dict) -> str:
    """Modelin seçtiği aracı çalıştırır, sonucu kompakt JSON olarak döndürür."""
    sonuc = _FONKSIYONLAR[ad](**girdi)
    return json.dumps(sonuc, ensure_ascii=False, separators=(",", ":"))
