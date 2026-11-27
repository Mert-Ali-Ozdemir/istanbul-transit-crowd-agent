"""Agent döngüsü: Claude araç seçer, araç Python'da çalışır, sonuç modele döner."""

import asyncio
import os
from dataclasses import replace
from datetime import datetime
from zoneinfo import ZoneInfo

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    create_sdk_mcp_server,
    query,
    tool,
)
from dotenv import load_dotenv

from araclar import TOOLS, araci_calistir

load_dotenv()
os.environ.pop("ANTHROPIC_API_KEY", None)  # abonelik yerine API kredisi kullanılmasın

MODEL = "claude-haiku-5-5"
MAX_ADIM = 8
SUNUCU = "transit"
GUN_ADLARI = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]

SISTEM = """Sen İstanbul toplu taşıma yoğunluk asistanısın.
Kullanıcı hangi dilde yazdıysa (Türkçe/İngilizce) o dilde, kısa cevap ver. Hat ve durak adlarını Türkçe bırak.
Bugün {gun_adi} ({gun}). Kullanıcı gün belirtmezse bunu kullan.
- İki yer arasındaki yolculukta önce rota_bul ile rotaları bul, sonra rotalardaki hatların yoğunluğuna yogunluk_getir ile bak.
- Tek bir hat sorulursa yogunluk_getir kullan, seviye yüksekse alternatif_bul çağır.
- "Ne zaman gideyim" gibi sorularda en_rahat_saat kullan.
En rahat seçeneği doluluk oranıyla birlikte öner. Rota ve sayı uydurma, sadece araç sonuçlarını kullan."""


def _arac_yap(tanim: dict):
    ad = tanim["name"]

    @tool(ad, tanim["description"], tanim["input_schema"])
    async def _calistir(girdi: dict) -> dict:
        return {"content": [{"type": "text", "text": araci_calistir(ad, girdi)}]}

    return _calistir


_SECENEKLER = ClaudeAgentOptions(
    model=MODEL,
    max_turns=MAX_ADIM,
    effort="low",
    tools=[],  # Claude Code'un yerleşik araçları kapalı, sadece aşağıdaki iki araç var
    mcp_servers={SUNUCU: create_sdk_mcp_server(SUNUCU, tools=[_arac_yap(t) for t in TOOLS])},
    allowed_tools=[f"mcp__{SUNUCU}__{t['name']}" for t in TOOLS],
    strict_mcp_config=True,
    setting_sources=[],
)


def _metne_cevir(icerik) -> str:
    if isinstance(icerik, list):
        return "".join(p.get("text", "") for p in icerik if isinstance(p, dict))
    return icerik or ""


def _sistem_talimati() -> str:
    bugun = datetime.now(ZoneInfo("Europe/Istanbul")).weekday()
    return SISTEM.format(gun_adi=GUN_ADLARI[bugun], gun="hafta_sonu" if bugun >= 5 else "hafta_ici")


async def _sor(soru: str, oturum: str | None) -> tuple[str, list[dict], str | None]:
    adimlar: dict[str, dict] = {}
    metinler: list[str] = []
    cevap = None
    yeni_oturum = oturum
    secenekler = replace(_SECENEKLER, system_prompt=_sistem_talimati(), resume=oturum)

    async for mesaj in query(prompt=soru, options=secenekler):
        if isinstance(mesaj, AssistantMessage):
            if mesaj.error:
                raise RuntimeError(f"Claude hatası: {mesaj.error}")
            for blok in mesaj.content:
                if isinstance(blok, ToolUseBlock):
                    ad = blok.name.removeprefix(f"mcp__{SUNUCU}__")
                    adimlar[blok.id] = {"arac": ad, "girdi": blok.input, "sonuc": ""}
                elif isinstance(blok, TextBlock):
                    metinler.append(blok.text)
        elif isinstance(mesaj, UserMessage) and isinstance(mesaj.content, list):
            for blok in mesaj.content:
                if isinstance(blok, ToolResultBlock) and blok.tool_use_id in adimlar:
                    adimlar[blok.tool_use_id]["sonuc"] = _metne_cevir(blok.content)
        elif isinstance(mesaj, ResultMessage):
            yeni_oturum = mesaj.session_id
            if mesaj.subtype == "error_max_turns":
                cevap = "Adım sınırına ulaşıldı. / Step limit reached."
            elif mesaj.is_error:
                raise RuntimeError(mesaj.result or mesaj.subtype)
            else:
                cevap = mesaj.result

    cevap = cevap or (metinler[-1] if metinler else "(boş cevap / empty response)")
    return cevap, list(adimlar.values()), yeni_oturum


def sor(soru: str, oturum: str | None = None) -> tuple[str, list[dict], str | None]:
    """Soruyu agent'a verir. (cevap, araç adımları, oturum kimliği) döndürür.
    Önceki oturum kimliği verilirse konuşma kaldığı yerden devam eder."""
    return asyncio.run(_sor(soru, oturum))


if __name__ == "__main__":
    oturum = None
    for soru in ["Kadıköy'den Taksim'e 18:00'de gideceğim.", "Peki 23:00'te?"]:
        cevap, adimlar, oturum = sor(soru, oturum)
        print(f"\n### {soru}")
        for a in adimlar:
            print("→", a["arac"], a["girdi"], a["sonuc"])
        print(cevap)
