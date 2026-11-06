#!/usr/bin/env python3
"""Append the illustrated Legion 0.6.5 update to the existing bilingual manuals.

The existing pages and their artwork are left intact. This intentionally does
not rebuild the original manuals or introduce replacement illustrations.
"""
from __future__ import annotations

from pathlib import Path
import fitz

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
VERSION_MARKER = "LEGION 0.6.5 - UPDATE"
RED = (0.89, 0.055, 0.15)
BLACK = (0.10, 0.10, 0.12)
GREY = (0.36, 0.37, 0.39)
PALE = (0.975, 0.94, 0.95)
WHITE = (1, 1, 1)
LIGHT = (0.96, 0.96, 0.96)

CONTENT = {
    "es": {
        "tag": "GUÍA DE ACTUALIZACIÓN / 0.6.5",
        "title_apc": "El poder de APC,\nsegunda etapa.",
        "intro_apc": "Legion 0.6.5 conserva S1 y añade S2: el nodo sigue escuchando, pero puede reducir temporalmente la potencia de ciertas retransmisiones. No cambia la potencia configurada ni los ajustes guardados.",
        "intro2": "Estas dos páginas actualizan las explicaciones de APC y comandos de la edición anterior. Las ilustraciones y el resto de capítulos se mantienen.",
        "head_modes": "COMANDOS: EL MISMO MANDO, MÁS CAPACIDADES",
        "mode_rows": [
            ("/apc on !abcdef01", "Activa S1 y S2; arranca siempre OFF."),
            ("/apc shadow !abcdef01", "Simula las reducciones; emite a potencia nominal."),
            ("/apc status !abcdef01 7", "Consulta la nueva página 7: objetivo RF y contadores."),
            ("/apc off !abcdef01", "Desactiva APC sin cambiar la configuración."),
        ],
        "head_power": "EJEMPLO DE POTENCIA CON P0 = 27 dBm",
        "power_rows": [
            ("Paquete retransmitido", "CONSERVE", "RESERVE"),
            ("Posición / telemetría de terceros", "24 dBm", "21 dBm"),
            ("NodeInfo periódico sin cambios", "24 dBm", "21 dBm"),
            ("Texto y PKI de terceros", "24 dBm", "24 dBm"),
            ("Tráfico propio y de control", "27 dBm", "27 dBm"),
        ],
        "apc_warning": "IMPORTANTE: los valores son objetivos del firmware, no mediciones de laboratorio. No se han medido el ahorro de batería, el alcance ni la potencia RF real.",
        "title_spam": "Guard: un demonio\ncontra el spam.",
        "intro_spam": "El antispam analiza textos broadcast del canal primario. Al arrancar está en OBSERVE: vigila y simula, pero no bloquea. ON se activa solo cuando tú lo ordenas; OFF lo detiene. La cuarentena es temporal y se guarda solo en RAM.",
        "head_commands": "COMANDOS ANTISPAM EN EL CANAL PRIVADO LEGIONRF",
        "spam_rows": [
            ("/guard status !abcdef01", "Estado, contadores y cuarentenas."),
            ("/guard observe !abcdef01", "Observa y simula sin bloquear."),
            ("/guard on !abcdef01", "Activa el bloqueo automático."),
            ("/guard off !abcdef01", "Desactiva la protección automática."),
            ("/guard clear !abcdef01 !12345678", "Libera la evidencia temporal de ese nodo."),
            ("/spamlist !abcdef01", "Enumera las cuarentenas por páginas."),
        ],
        "head_rules": "CÓMO FUNCIONA",
        "rules": "Cada origen dispone de 8 tokens y recupera 1 cada 5 segundos. Cuatro excesos o seis textos idénticos con IDs nuevos en 20 segundos generan una cuarentena fija de 10 minutos. No altera la lista manual /ignore. Los duplicados no añaden evidencias.",
        "head_daily": "EL DAILY AHORA TAMBIÉN AVISA DEL SPAM",
        "daily": "!abcdef01 DAILY\nAPC:ON CONSERVE\nSPAM:ON Q:1\nBACKUP:UP TO DATE",
        "daily_note": "Si está en OBSERVE, verás SPAM:OBSERVE simQ:n. No significa que haya bloqueado a nadie.",
        "footer": "Legion - manual endiabladamente amigable - actualización 0.6.5",
    },
    "en": {
        "tag": "USER GUIDE UPDATE / 0.6.5",
        "title_apc": "APC grows horns:\nstage two.",
        "intro_apc": "Legion 0.6.5 retains S1 and adds S2. The node keeps receiving, while selected third-party relays may use temporarily reduced TX power. Configured transmit power and saved settings do not change.",
        "intro2": "These two pages supersede older APC and command descriptions. All existing illustrations and chapters remain unchanged.",
        "head_modes": "COMMANDS: SAME CONTROLS, NEW CAPABILITIES",
        "mode_rows": [
            ("/apc on !abcdef01", "Enables S1 and S2; every boot starts OFF."),
            ("/apc shadow !abcdef01", "Models RF reductions but transmits at nominal power."),
            ("/apc status !abcdef01 7", "Shows new page 7: RF target and counters."),
            ("/apc off !abcdef01", "Stops APC without saving new radio settings."),
        ],
        "head_power": "EXAMPLE POWER TARGETS WITH P0 = 27 dBm",
        "power_rows": [
            ("Relayed packet", "CONSERVE", "RESERVE"),
            ("Third-party position / telemetry", "24 dBm", "21 dBm"),
            ("Unchanged periodic NodeInfo", "24 dBm", "21 dBm"),
            ("Third-party text and opaque PKI", "24 dBm", "24 dBm"),
            ("Own traffic and control", "27 dBm", "27 dBm"),
        ],
        "apc_warning": "IMPORTANT: these are firmware targets, not laboratory measurements. Battery savings, RF output and practical range have not been measured.",
        "title_spam": "Guard: a demon\nagainst spam.",
        "intro_spam": "Antispam watches broadcast text on the primary channel. It boots in OBSERVE: detection runs without blocking. ON enforces the policy only when you enable it; OFF disables it. Quarantines are temporary and RAM-only.",
        "head_commands": "ANTISPAM COMMANDS ON PRIVATE LEGIONRF",
        "spam_rows": [
            ("/guard status !abcdef01", "Mode, counters and quarantines."),
            ("/guard observe !abcdef01", "Simulate detection without blocking."),
            ("/guard on !abcdef01", "Enable automatic blocking."),
            ("/guard off !abcdef01", "Disable automatic protection."),
            ("/guard clear !abcdef01 !12345678", "Clear that peer's temporary evidence."),
            ("/spamlist !abcdef01", "List quarantines with pagination."),
        ],
        "head_rules": "HOW IT WORKS",
        "rules": "Each origin starts with 8 tokens and regains 1 every 5 seconds. Four excesses or six identical texts with new IDs in 20 seconds trigger a fixed 10-minute quarantine. Manual /ignore remains unchanged. Duplicate packets add no evidence.",
        "head_daily": "DAILY NOW REPORTS SPAM TOO",
        "daily": "!abcdef01 DAILY\nAPC:ON CONSERVE\nSPAM:ON Q:1\nBACKUP:UP TO DATE",
        "daily_note": "In OBSERVE, you will see SPAM:OBSERVE simQ:n. This means a simulated quarantine, not a real block.",
        "footer": "Legion - friendly user manual - 0.6.5 update",
    }
}


def text(page, x0, y0, x1, y1, value, size=10, color=BLACK, bold=False, align=fitz.TEXT_ALIGN_LEFT):
    font = "hebo" if bold else "helv"
    r = fitz.Rect(x0, y0, x1, y1)
    remain = page.insert_textbox(r, value, fontsize=size, fontname=font, color=color, align=align, lineheight=1.2)
    if remain < 0:
        raise RuntimeError(f"Text does not fit in {r}, size={size}: {value[:50]!r}, overflow={remain:.1f}")


def line(page, y, x0=43, x1=552, color=RED, width=1):
    page.draw_line(fitz.Point(x0, y), fitz.Point(x1, y), color=color, width=width)


def shell(page, d, num):
    w, h = page.rect.width, page.rect.height
    page.draw_rect(fitz.Rect(0, 0, w, 5), fill=RED, color=RED)
    text(page, 43, 30, 375, 46, d["tag"], size=8, color=RED, bold=True)
    text(page, 417, 30, 552, 46, "LEGIONFW · 0.6.5", size=8, color=GREY, align=fitz.TEXT_ALIGN_RIGHT)
    line(page, 53, color=(0.81, 0.81, 0.81), width=0.6)
    line(page, h - 52, color=(0.81, 0.81, 0.81), width=0.6)
    text(page, 43, h - 42, 475, h - 24, d["footer"], size=7.2, color=GREY)
    text(page, 515, h - 42, 552, h - 24, f"+{num:02d}", size=9, color=RED, bold=True, align=fitz.TEXT_ALIGN_RIGHT)


def hero(page, source):
    if len(source) < 6:
        return
    orig = source[5]
    clip = fitz.Rect(440, 63, 563, 177) & orig.rect
    if clip.is_empty:
        return
    pix = orig.get_pixmap(matrix=fitz.Matrix(2, 2), clip=clip, alpha=False)
    page.insert_image(fitz.Rect(430, 74, 552, 187), stream=pix.tobytes("png"), keep_proportion=True)


def section(page, y, title):
    text(page, 43, y, 552, y+20, title, size=10, color=RED, bold=True)
    line(page, y+22, color=(0.82,0.82,0.82),width=0.5)


def command_rows(page, y, rows, rh=43, cmdw=270):
    for i, (cmd, desc) in enumerate(rows):
        top=y+i*rh
        page.draw_rect(fitz.Rect(43,top,552,top+rh-2),fill=LIGHT if i%2==0 else WHITE,color=(0.89,0.89,0.89),width=0.35)
        page.draw_rect(fitz.Rect(43,top,46,top+rh-2),fill=RED,color=RED)
        text(page,54,top+8,43+cmdw,top+rh-5,cmd,size=9.2,bold=True)
        text(page,43+cmdw+8,top+5,548,top+rh-5,desc,size=9)


def apc_page(doc, source, lang):
    d=CONTENT[lang]
    page=doc.new_page(width=595.2756,height=841.89)
    shell(page,d,1)
    hero(page,source)
    text(page,43,75,423,155,d["title_apc"],size=24,bold=True)
    text(page,43,156,418,218,d["intro_apc"],size=10.2,color=GREY)
    page.draw_rect(fitz.Rect(43,231,552,269),fill=PALE,color=PALE)
    text(page,54,237,540,265,d["intro2"],size=9.2,color=BLACK)
    section(page,284,d["head_modes"])
    command_rows(page,311,d["mode_rows"],rh=42,cmdw=269)
    section(page,487,d["head_power"])
    rows=d["power_rows"]
    y=513
    for i,(a,b,c) in enumerate(rows):
        yy=y+i*29
        bg=BLACK if i==0 else (LIGHT if i%2==0 else WHITE)
        page.draw_rect(fitz.Rect(43,yy,552,yy+29),fill=bg,color=(0.88,0.88,0.88),width=0.4)
        co=WHITE if i==0 else BLACK
        text(page,54,yy+6,310,yy+26,a,size=9, color=co,bold=i==0)
        text(page,326,yy+6,423,yy+26,b,size=9,color=co,bold=i==0,align=fitz.TEXT_ALIGN_CENTER)
        text(page,424,yy+6,545,yy+26,c,size=9,color=co,bold=i==0,align=fitz.TEXT_ALIGN_CENTER)
    page.draw_rect(fitz.Rect(43,680,552,746),fill=PALE,color=PALE)
    text(page,54,689,540,736,d["apc_warning"],size=10,color=RED,bold=True)


def antispam_page(doc, source, lang):
    d=CONTENT[lang]
    page=doc.new_page(width=595.2756,height=841.89)
    shell(page,d,2)
    hero(page,source)
    text(page,43,74,423,154,d["title_spam"],size=24,bold=True)
    text(page,43,191,542,239,d["intro_spam"],size=10.2,color=GREY)
    section(page,246,d["head_commands"])
    command_rows(page,272,d["spam_rows"],rh=41,cmdw=270)
    section(page,528,d["head_rules"])
    text(page,43,554,552,617,d["rules"],size=9.5)
    section(page,623,d["head_daily"])
    page.draw_rect(fitz.Rect(43,649,292,755),fill=BLACK,color=BLACK)
    text(page,55,656,286,752,d["daily"],size=10.5,color=WHITE,bold=True)
    text(page,307,669,550,750,d["daily_note"],size=10,color=GREY)


def update(path: Path, lang: str) -> str:
    if not path.is_file():
        raise FileNotFoundError(path)
    source=fitz.open(path)
    if any(VERSION_MARKER in p.get_text() for p in source):
        return f"already updated: {path.name}"
    doc=fitz.open(path)
    count=len(doc)
    apc_page(doc,source,lang)
    antispam_page(doc,source,lang)
    # Marker in the searchable PDF text prevents duplicate append on reruns.
    for page in (doc[-2], doc[-1]):
        text(page,43,766,360,784,VERSION_MARKER,size=6.5,color=GREY)
    if len(doc)!=count+2:
        raise RuntimeError("Unexpected page count")
    temp=path.with_name(path.stem + '.new.pdf')
    doc.save(temp,garbage=4,deflate=True,clean=True)
    doc.close()
    source.close()
    temp.replace(path)
    return f"updated: {path.name}: {count} -> {count+2} pages"


def main():
    for lang,name in (("es","Legion-Spanish-friendly-user-manual.pdf"),("en","Legion-English-friendly-user-manual.pdf")):
        print(update(DOCS/name,lang))

if __name__ == "__main__":
    main()
