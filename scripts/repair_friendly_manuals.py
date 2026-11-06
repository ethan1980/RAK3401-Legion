#!/usr/bin/env python3
"""Update the existing 29-page illustrated Legion 0.6.5 PDF manuals in-place.
Preserve all original illustrations, visual layout and the two added 0.6.5 pages.
"""
from pathlib import Path
import re
import fitz

ROOT=Path(__file__).resolve().parents[1]
EXPR=re.compile(rb"\((?:\\.|[^\\)])*\)")

def replace_text(t, lang, i):
    # Only PDF text operands: drawing paths, illustrations and coordinates are untouched.
    t=t.replace(b"Desde 0.6.1",b"Desde HISTV").replace(b"From 0.6.1",b"From HISTV")
    for old,new in (
        (b"0.6.1",b"0.6.5"),(b"1.1",b"1.2"),
        (b"28 OCT 2026",b"06 NOV 2026"),
        (b"28/10/2026",b"06/11/2026"),
        (b"26/10/2026",b"06/11/2026"),
        (b"28 de octubre de 2026",b"6 de noviembre de 2026"),
        (b"26 de octubre de 2026",b"6 de noviembre de 2026"),
        (b"28 October 2026",b"6 November 2026"),
        (b"26 October 2026",b"6 November 2026"),
        (b"c39728e",b"d5f1619"),
    ):
        t=t.replace(old,new)
    t=t.replace(b"Desde HISTV",b"Desde 0.6.1").replace(b"From HISTV",b"From 0.6.1")
    if i==1:
        t=t.replace(b"16-18",b"16-18,28").replace(b"25-26",b"25-29")
        if t==b"13": t=b"13,29"
    changes={}
    if lang=="es":
        changes={
          1:[
            (b"comandos y el funcionamiento de APC se han comprobado en hardware.",
             b"comandos se probaron en placa; el orden final de /guard solo tiene pruebas de software."),
            (b"Entender y manejar APC",b"Entender APC S1 y S2"),
            (b"Gestionar nodos ignorados",b"Ignorados y antispam"),
            (b"Consultar la chuleta de comandos",b"Chuleta y novedades")],
          15:[
            (b"Adaptive Power Control: la etapa S1 adapta ciertos reenv\004os a la bater\004a.",
             b"APC S1 limita reenv\004os opcionales; S2 adapta potencia RF de relays."),
            (b"Elige una orden. S1 requiere rol CLIENT. La recepci\001n y la potencia RF siguen nominales; esta etapa no",
             b"Elige una orden. APC requiere rol CLIENT. S1 no cambia potencia RF; S2 se describe al final."),
            (b"selecciona una potencia adaptativa.",
             b"Los mensajes propios mantienen la potencia configurada.")],
          17:[(b"Seis p",b"Siete p"),(b"2-6",b"2-7")],
          20:[(b"Se ha confirmado la instalaci\001n OTA desde la alpha anterior.",
               b"La candidata 0.6.5 se instal\001 mediante OTA.")],
          21:[(b"El Legion recuerda su estado de APC y backup en el canal privado LegionRF.",
               rb"El aviso resume APC, antispam y backup en LegionRF \(ejemplo compacto\)."),
              (b"APC:OFF",b"APC:OFF  SPAM:OBSERVE simQ:0")],
          25:[(b"puedes pedir 2-6.",b"puedes pedir 2-7."),
              (b"aviso DAILY resume APC/backup",b"aviso DAILY resume APC/spam/backup")],
          26:[(b"Sintaxis y comportamiento contrastados con la documentaci\001n y el c\001digo de",
               b"Sintaxis y comportamiento contrastados con las pruebas y el c\001digo de")],
        }
    else:
        changes={
          1:[(b"Command operation and APC have been checked on hardware.",
              b"Candidate tested on hardware; final /guard syntax checked automatically."),
             (b"Understand and control APC",b"Understand APC S1 and S2"),
             (b"Manage ignored nodes",b"Ignore nodes and antispam"),
             (b"Use the command cheat sheet",b"Cheat sheet and changes")],
          15:[(b"Adaptive Power Control: S1 adapts selected relays to battery conditions.",
               b"APC S1 limits optional relays. S2 adds adaptive relay TX power."),
              (b"Choose one command. S1 requires CLIENT role. Reception and RF output remain nominal; this stage does",
               b"Choose one command. APC requires CLIENT role. S1 does not change RF power; S2 is explained later."),
              (b"not select adaptive RF power.",b"Own traffic keeps normal RF power.")],
          17:[(b"Six pages",b"Seven pages"),(b"pages 2-6",b"pages 2-7")],
          20:[(b"OTA installation from the previous alpha has been confirmed.",
               b"The 0.6.5 candidate was installed successfully via OTA.")],
          21:[(b"Legion reports its APC and backup state in the private LegionRF channel.",
               rb"Legion reports APC, antispam and backup in LegionRF \(compact example\)."),
              (b"APC:OFF",b"APC:OFF  SPAM:OBSERVE simQ:0")],
          25:[(b"then request 2-6.",b"then request 2-7."),
              (b"DAILY summarizes APC/backup",b"DAILY summarizes APC/spam/backup")],
          26:[(b"Syntax and behaviour checked against 0.6.5 documentation and source.",
               b"Syntax verified against 0.6.5 tests and source; final Guard awaits HW check.")],
        }
    for a,b in changes.get(i,[]):
        for n in range(1,14):
            o=bytes([n]); marker=b"\\"+format(n,"03o").encode()
            a=a.replace(o,marker); b=b.replace(o,marker)
        t=t.replace(a,b)
    return t

def repair(lang):
    path=ROOT/"docs"/f"Legion-{'Spanish' if lang=='es' else 'English'}-friendly-user-manual.pdf"
    doc=fitz.open(path)
    if len(doc)!=29: raise RuntimeError(f"Unexpected manual page count for {path}: {len(doc)}")
    print("CURRENT PAGE 27:",repr(doc[26].get_text()[:1700]),flush=True)
    cover=doc[0].get_text()
    if "Legion 0.6.5  /  Manual 1.2" in cover:
        print(path.name,"already updated")
        return
    if "Legion 0.6.1" not in cover: raise RuntimeError(f"Unexpected source cover {path}")
    count=0
    for i,p in enumerate(doc):
        for xref in p.get_contents():
            before=doc.xref_stream(xref)
            def amend(m):
                chunk=m.group(0)
                pos=chunk.rfind(b")")
                t=replace_text(chunk[1:pos],lang,i)
                return b"("+t+chunk[pos:]
            after=EXPR.sub(amend,before)
            if before!=after:
                doc.update_stream(xref,after)
                count+=1
    p=doc[17]
    p.draw_rect(fitz.Rect(42,624,553,685),fill=(.967,.951,.957),color=(.89,.05,.16),width=.8,overlay=True)
    p.insert_font(fontname="LegionGuideSans",fontfile="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    p.insert_font(fontname="LegionGuideBold",fontfile="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    if lang=="es":
        head="PÁGINA 7 · APC STAGE 2"
        sub="Potencia de los reenvíos, ajustes S2 y estadísticas de ahorro estimado."
    else:
        head="PAGE 7 · APC STAGE 2"
        sub="Relay power settings, S2 operation and estimated savings counters."
    p.insert_text((54,645),head,fontname="LegionGuideBold",fontsize=9.3,color=(.88,.05,.13),overlay=True)
    p.insert_text((54,667),sub,fontname="LegionGuideSans",fontsize=9.1,color=(.16,.15,.17),overlay=True)
    print("AFTER PAGE 27:",repr(doc[26].get_text()[:1400]),flush=True)
    content="\n".join(p.get_text() for p in doc)
    for required in ("0.6.5","06 NOV 2026","2.8.2.Legion0.6.5","d5f1619"):
        if required not in content: raise RuntimeError(f"{path}: missing required {required}")
    for stale in ("LEGIONFW · 0.6.1","2.8.2.Legion0.6.1","28/10/2026"):
        if stale in content: raise RuntimeError(f"{path}: stale metadata {stale}")
    if "2-6" in doc[17].get_text() or "2-6" in doc[25].get_text():
        raise RuntimeError("APC status page count still stale")
    temp=path.with_suffix(".fresh.pdf")
    meta=doc.metadata
    meta["title"]=("LegionFW 0.6.5 - Manual endiabladamente amigable" if lang=="es" else
                   "LegionFW 0.6.5 - Devilishly friendly user manual")
    doc.set_metadata(meta)
    doc.save(temp,garbage=4,deflate=True,deflate_fonts=True,deflate_images=True)
    doc.close()
    temp.replace(path)
    print("Repaired",path.name,"page streams",count)

if __name__=="__main__":
    repair("es")
    repair("en")
