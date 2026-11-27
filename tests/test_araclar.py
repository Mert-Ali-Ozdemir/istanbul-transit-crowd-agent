import json

import pytest

from araclar import (
    DURAKLAR,
    HATLAR,
    KAPASITE,
    SAATLER,
    TOOLS,
    alternatif_bul,
    araci_calistir,
    en_rahat_saat,
    en_yakin_saat,
    rota_bul,
    yogunluk_getir,
)


@pytest.mark.parametrize("saat, beklenen", [
    ("08:00", "08:00"), ("18:40", "18:00"), ("21:00", "23:00"), ("10:30", "08:00"), ("anlamsız", "18:00"),
])
def test_en_yakin_saat(saat, beklenen):
    assert en_yakin_saat(saat) == beklenen


def test_yogunluk_seviyesi():
    sonuc = yogunluk_getir("Marmaray", "18:00")
    assert sonuc == {"gun": "hafta_ici", "saat": "18:00", "hat": "Marmaray",
                     "yolcu": 40000, "seviye": "yüksek", "doluluk": "%89"}
    assert yogunluk_getir("Vapur", "23:00")["seviye"] == "düşük"
    assert yogunluk_getir("Vapur", "18:00")["seviye"] == "orta"


def test_hafta_sonu_farkli():
    assert yogunluk_getir("Marmaray", "08:00", "hafta_sonu")["yolcu"] < yogunluk_getir("Marmaray", "08:00")["yolcu"]


def test_alternatifler_siralı():
    oranlar = [r["yolcu"] / KAPASITE[r["hat"]] for r in alternatif_bul("Marmaray", "18:00")["alternatifler"]]
    assert oranlar == sorted(oranlar)


def test_en_rahat_saat_tum_dilimler_sirali():
    sonuc = en_rahat_saat("Vapur", "hafta_sonu")
    assert {r["saat"] for r in sonuc["saatler"]} == set(SAATLER)
    dolulukler = [int(r["doluluk"].lstrip("%")) for r in sonuc["saatler"]]
    assert dolulukler == sorted(dolulukler)


def test_rota_direkt():
    rotalar = rota_bul("Üsküdar", "Sirkeci")["rotalar"]
    assert rotalar[0] == {"hatlar": ["Marmaray"], "aktarma": []}


def test_rota_aktarmali_ve_gecerli():
    rotalar = rota_bul("Kadıköy", "Taksim")["rotalar"]
    assert rotalar[0] == {"hatlar": ["Vapur", "F1"], "aktarma": ["Kabataş"]}
    for rota in rotalar:
        assert "Kadıköy" in HATLAR[rota["hatlar"][0]]
        assert "Taksim" in HATLAR[rota["hatlar"][-1]]
        for hat_once, durak, hat_sonra in zip(rota["hatlar"], rota["aktarma"], rota["hatlar"][1:]):
            assert durak in HATLAR[hat_once] and durak in HATLAR[hat_sonra]


def test_rota_dolambacli_rotalari_eler():
    rotalar = [r["hatlar"] for r in rota_bul("Kadıköy", "Taksim")["rotalar"]]
    assert ["Vapur", "T1", "F1"] not in rotalar


def test_rota_ayni_durak():
    assert rota_bul("Taksim", "Taksim")["rotalar"] == []


def test_araclar_semalarla_uyumlu():
    for arac in TOOLS:
        sema = arac["input_schema"]
        assert set(sema["required"]) <= set(sema["properties"])
    assert set(TOOLS[0]["input_schema"]["properties"]["nereden"]["enum"]) == set(DURAKLAR)


def test_araci_calistir_json_doner():
    cikti = araci_calistir("yogunluk_getir", {"hat": "M2", "saat": "08:00"})
    assert json.loads(cikti)["hat"] == "M2"
    assert " " not in cikti.replace("hafta_ici", "")  # kompakt JSON
