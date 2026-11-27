"""Streamlit arayüzü (TR/EN). Çalıştırma: streamlit run app.py"""

import json

import altair as alt
import pandas as pd
import streamlit as st

from agent import sor

MAX_SORU = 8  # bu kadar sorudan sonra yeni konuşma başlar (hafıza büyümesin)

METIN = {
    "TR": {
        "baslik": "🚇 İstanbul Toplu Taşıma Yoğunluk Agent'ı",
        "aciklama": "Nereye, ne zaman gideceğini yaz; agent rotayı bulup yoğunluğu kontrol etsin, gerekirse alternatif önersin.",
        "giris": "Örn: Kadıköy'den Taksim'e 18:00'de gideceğim",
        "ornekler": ["Kadıköy'den Taksim'e 18:00'de gideceğim", "Sabah 8'de Marmaray kalabalık mı?",
                     "Cumartesi vapura ne zaman binsem rahat olur?"],
        "ornek_baslik": "Sık sorulan sorular",
        "dusunuyor": "Agent düşünüyor...",
        "hata": "Hata (Claude Code'a giriş yaptın mı? `claude` ya da `claude setup-token`)",
        "temizle": "Sohbeti temizle",
        "yeni": "Hafıza sınırına ulaşıldı, yeni bir konuşma başladı.",
        "doluluk": "Doluluk (%)",
        "seviye": "Seviye",
        "seviyeler": {"düşük": "düşük", "orta": "orta", "yüksek": "yüksek"},
    },
    "EN": {
        "baslik": "🚇 Istanbul Transit Crowd Agent",
        "aciklama": "Tell me where and when you're going; the agent finds the route, checks crowding and suggests alternatives.",
        "giris": "e.g. I'm going from Kadıköy to Taksim at 18:00",
        "ornekler": ["I'm going from Kadıköy to Taksim at 18:00", "Is the Metrobüs busy at 8 am?",
                     "When is the ferry least crowded on Saturday?"],
        "ornek_baslik": "Frequently asked questions",
        "dusunuyor": "Agent is thinking...",
        "hata": "Error (are you logged in to Claude Code? `claude` or `claude setup-token`)",
        "temizle": "Clear chat",
        "yeni": "Memory limit reached, a new conversation started.",
        "doluluk": "Occupancy (%)",
        "seviye": "Level",
        "seviyeler": {"düşük": "low", "orta": "medium", "yüksek": "high"},
    },
}
RENKLER = {"düşük": "#0aac23", "orta": "#fbb315", "yüksek": "#f18a59"}

st.set_page_config(page_title="Istanbul Transit Agent", page_icon="🚇",
                   menu_items={"Get help": None, "Report a bug": None, "About": None})
# Menüde sadece tema seçimi ve yazdırma kalsın
st.markdown("<style>[data-testid='stMainMenuItem-recordScreencast'],"
            "[data-testid='stMainMenuList'] ~ *{display:none}"
            "[data-testid='stSidebar'] .stButton button{justify-content:flex-start;text-align:left}"
            "[data-testid='stSidebar'] .stButton button div,"
            "[data-testid='stSidebar'] .stButton button p{width:100%;text-align:left;justify-content:flex-start}"
            "</style>", unsafe_allow_html=True)
st.sidebar.subheader("Dil / Language")
dil = st.sidebar.radio("Dil / Language", ["TR", "EN"], horizontal=True, label_visibility="collapsed")
t = METIN[dil]

st.title(t["baslik"])
st.caption(t["aciklama"])

if "gecmis" not in st.session_state:
    st.session_state.gecmis = []
    st.session_state.oturum = None
    st.session_state.soru_sayisi = 0

st.sidebar.subheader(t["ornek_baslik"])
secilen = None
for ornek in t["ornekler"]:
    if st.sidebar.button(ornek, width="stretch"):
        secilen = ornek
st.sidebar.divider()
if st.sidebar.button(t["temizle"], width="stretch"):
    st.session_state.gecmis = []
    st.session_state.oturum = None
    st.session_state.soru_sayisi = 0


def grafik_verisi(adimlar: list[dict]) -> pd.DataFrame:
    """Araç sonuçlarından grafik tablosu: hat başına son doluluk, yoksa saat başına doluluk."""
    hatlar, saatler = {}, []
    for a in adimlar:
        try:
            sonuc = json.loads(a["sonuc"])
        except (ValueError, TypeError):
            continue
        if a["arac"] == "yogunluk_getir":
            hatlar[sonuc["hat"]] = sonuc
        elif a["arac"] == "alternatif_bul":
            for r in sonuc["alternatifler"]:
                hatlar.setdefault(r["hat"], r)
        elif a["arac"] == "en_rahat_saat":
            saatler = [{**r, "hat": r["saat"]} for r in sorted(sonuc["saatler"], key=lambda r: r["saat"])]
    satirlar = list(hatlar.values()) or saatler
    return pd.DataFrame(
        [{"etiket": r["hat"], "doluluk": int(r["doluluk"].lstrip("%")), "seviye": r["seviye"]}
         for r in satirlar]
    )


def grafik_goster(adimlar: list[dict]):
    df = grafik_verisi(adimlar or [])
    if df.empty:
        return
    saat_mi = df.etiket.str.contains(":").all()
    df["seviye_adi"] = df.seviye.map(t["seviyeler"])
    df["etiket_metni"] = "%" + df.doluluk.astype(str)
    sira = df.etiket.tolist() if saat_mi else df.sort_values("doluluk", ascending=False).etiket.tolist()
    y = alt.Y("etiket:N", title=None, sort=sira, scale=alt.Scale(paddingInner=0.4))
    renk = alt.Color(
        "seviye_adi:N", title=t["seviye"],
        scale=alt.Scale(domain=[t["seviyeler"][s] for s in RENKLER], range=list(RENKLER.values())),
        legend=alt.Legend(orient="bottom"),
    )
    cubuk = alt.Chart(df).mark_bar(cornerRadiusEnd=4).encode(
        x=alt.X("doluluk:Q", title=t["doluluk"], scale=alt.Scale(domain=[0, 100]),
                axis=alt.Axis(grid=False, values=[0, 50, 80, 100])),
        y=y, color=renk,
        tooltip=[alt.Tooltip("etiket:N", title=""), alt.Tooltip("etiket_metni:N", title=t["doluluk"]),
                 alt.Tooltip("seviye_adi:N", title=t["seviye"])],
    )
    yazi = cubuk.mark_text(align="left", dx=4, color="gray").encode(text="etiket_metni:N", color=alt.value("gray"))
    esikler = alt.Chart(pd.DataFrame({"x": [50, 80]})).mark_rule(strokeDash=[4, 4], color="gray", opacity=0.5).encode(x="x:Q")
    # fit-x: genişlik sayfaya uyar, yükseklik sadece çubuk alanına uygulanır (lejant/eksen ezmesin)
    grafik = (esikler + cubuk + yazi).properties(
        height=30 * len(df), autosize=alt.AutoSizeParams(type="fit-x", contains="padding"))
    st.altair_chart(grafik, width="stretch")


for m in st.session_state.gecmis:
    with st.chat_message(m["rol"]):
        st.markdown(m["metin"])
        if m["rol"] == "assistant":
            grafik_goster(m.get("adimlar"))

soru = st.chat_input(t["giris"]) or secilen
if soru:
    if st.session_state.soru_sayisi >= MAX_SORU:
        st.session_state.oturum = None
        st.session_state.soru_sayisi = 0
        st.info(t["yeni"])
    with st.chat_message("user"):
        st.markdown(soru)
    with st.chat_message("assistant"):
        try:
            with st.spinner(t["dusunuyor"]):
                cevap, adimlar, st.session_state.oturum = sor(soru, st.session_state.oturum)
            st.session_state.soru_sayisi += 1
        except Exception as e:
            cevap, adimlar = f"{t['hata']}: {e}", []
        st.markdown(cevap)
        grafik_goster(adimlar)
    st.session_state.gecmis += [
        {"rol": "user", "metin": soru},
        {"rol": "assistant", "metin": cevap, "adimlar": adimlar},
    ]
