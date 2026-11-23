#!/usr/bin/env python3
"""Integrate 0.7.2 into the existing illustrated manuals (requires PyMuPDF).

The committed 0.7.1 editions are the reproducible source. Reuse their cover and
chapter illustrations; insert Drakarys after /msg, before channel management.
Do not use the older append-only 0.6.5 maintenance scripts for this edition.
"""
from pathlib import Path
import re
import subprocess
import fitz

ROOT = Path(__file__).resolve().parents[1]
SOURCE = '8372118c424e7698736f98de3fb069c0dc664959'
FONT_ROOT = Path('/usr/share/fonts/truetype/dejavu')
FONTS = {n: fitz.Font(fontfile=str(FONT_ROOT / f)) for n, f in {
    'Sans': 'DejaVuSans.ttf', 'Bold': 'DejaVuSans-Bold.ttf', 'Mono': 'DejaVuSansMono.ttf'
}.items()}
RED = (0.89, 0.035, 0.14)
BLACK = (0.12, 0.12, 0.14)
GREY = (0.36, 0.36, 0.39)
PALE = (0.974, 0.947, 0.953)
WHITE = (1, 1, 1)


def command_syntax(value, lang):
    """Use placeholders in syntax; concrete names belong to labelled examples."""
    short = 'nombrecorto' if lang == 'es' else 'shortname'
    value = re.sub(r'\b(observe\|shadow\|on\|off|status\|observe\|on\|off)\b',
                   lambda match: '(' + match[0].replace('|', ' | ') + ')', value)
    matches = list(re.finditer(r'!abcdef01\b|!12345678\b|\bPSVR\b|\bRLY1\b', value))
    for match in reversed(matches):
        node = '!peerid' if match[0] in ('!12345678', 'RLY1') else '!nodeid'
        selector = f'{node} | {short}'
        if value[match.end():].strip() or len(matches) > 1 or '|' in value[:match.start()]:
            selector = '(' + selector + ')'
        value = value[:match.start()] + selector + value[match.end():]
    channel = '<canal>' if lang == 'es' else '<channel>'
    message = '<mensaje>' if lang == 'es' else '<message>'
    for sample in ('SFNarrow Hola, prueba desde Legion', 'SFNarrow Hola desde Legion',
                   'SFNarrow Hello from Legion', 'SFNarrow Mensaje', 'SFNarrow Message'):
        value = value.replace(sample, channel + ' ' + message)
    for sample in ('"Mi canal"', '"My channel"'):
        value = value.replace(sample, channel)
    for sample in ('"Nodo de ejemplo"', '"Nombre largo"', '"Example node"', '"Long name"'):
        value = value.replace(sample, '"<nombre_largo>"' if lang == 'es' else '"<long_name>"')
    value = value.replace('PSK_BASE64', '<psk_base64>')
    return value


def lines(text, font, size, width):
    result = []
    for paragraph in text.split('\n'):
        line = ''
        for word in paragraph.split(' '):
            candidate = (line + ' ' + word).strip()
            if line and FONTS[font].text_length(candidate, fontsize=size) > width:
                result.append(line)
                line = word
            else:
                line = candidate
        result.append(line)
    return result


def font_setup(page):
    for name, font in FONTS.items():
        page.insert_font(fontname=name, fontbuffer=font.buffer)


def text(page, x, y, content, size=9.5, font='Sans', width=511, color=BLACK, leading=None):
    leading = leading or size * 1.35
    for line in lines(content, font, size, width):
        page.insert_text((x, y + size), line, fontsize=size, fontname=font, color=color)
        y += leading
    return y


class Chapter:
    def __init__(self, out, source, old, number, lang, tag, title, intro, new_art=False):
        self.lang = lang
        self.page = out.new_page(width=595.276, height=841.89)
        p = self.page
        font_setup(p)
        p.draw_rect(fitz.Rect(0, 0, p.rect.width, 9), color=RED, fill=RED)
        text(p, 42, 28, f'{number:02d} / {tag}', 8, 'Bold', color=RED)
        text(p, 466, 28, 'LEGIONFW · 0.7.2', 7.2, width=90, color=GREY)
        if new_art:
            p.insert_image(fitz.Rect(360, 64, 556, 248), filename=str(ROOT / 'assets/drakarys-demon.png'))
            title_width = 310
        else:
            image = source[old-1].get_images()[0]
            pix = fitz.Pixmap(source, image[0])
            if image[1]:
                pix = fitz.Pixmap(pix, fitz.Pixmap(source, image[1]))
            p.insert_image(fitz.Rect(439, 71, 554, 181), pixmap=pix)
            title_width = 389
        text(p, 42, 74, title, 26.5, 'Bold', width=title_width, leading=31)
        intro_width = 307 if new_art else 511
        end = text(p, 42, 169, intro, 10.1, width=intro_width, color=GREY)
        self.y = max(210, end + 12, 254 if new_art else 0)
        footer(p, number, lang)

    def choose(self, es, en):
        return es if self.lang == 'es' else en

    def para(self, es, en, size=9.5):
        value = self.choose(es, en)
        # Behaviour prose uses the command name; full syntax is in its box.
        if '/' in value:
            value = value.replace(' PSVR', '')
        self.y = text(self.page, 42, self.y, value, size) + 9
        self.check()

    def heading(self, es, en):
        self.y += 3
        self.y = text(self.page, 42, self.y, self.choose(es, en), 11.2, 'Bold') + 7
        self.check()

    def code(self, es, en=None, size=9.5, literal=False):
        value = es if en is None else self.choose(es, en)
        is_command = any(line.startswith('/') for line in value.splitlines())
        if is_command and not literal:
            value = '\n'.join(dict.fromkeys(command_syntax(line, self.lang) if line.startswith('/') else line
                                            for line in value.splitlines()))
        label = self.choose('EJEMPLO - SUSTITUYE LOS DATOS', 'EXAMPLE - REPLACE THE VALUES') if literal else (
            self.choose('SINTAXIS - ELIGE ID O NOMBRE CORTO', 'SYNTAX - CHOOSE ID OR SHORT NAME') if is_command else
            self.choose('RESPUESTA', 'REPLY'))
        rows = lines(value, 'Mono', size, 487)
        h = len(rows) * size * 1.4 + 27
        self.page.draw_rect(fitz.Rect(42, self.y, 553, self.y+h), fill=PALE, color=None)
        text(self.page, 54, self.y+6, label, 6.5, 'Bold', width=487, color=RED)
        text(self.page, 54, self.y+19, value, size, 'Mono', width=487, leading=size*1.4)
        self.y += h + 10
        self.check()

    def example(self, es, en=None, size=9.5):
        self.code(es, en, size=size, literal=True)

    def callout(self, title_es, title_en, es, en):
        title = self.choose(title_es, title_en)
        body = self.choose(es, en)
        h = len(lines(title, 'Bold', 8.8, 487))*12 + len(lines(body, 'Sans', 9.1, 487))*12.3 + 23
        self.page.draw_rect(fitz.Rect(42, self.y, 553, self.y+h), fill=PALE, color=RED, width=.6)
        text(self.page, 54, self.y+9, title, 8.8, 'Bold', width=487, color=RED)
        text(self.page, 54, self.y+24, body, 9.1, width=487, leading=12.3)
        self.y += h+11
        self.check()

    def table(self, es, en, widths=None, size=9.2):
        rows = self.choose(es, en)
        widths = widths or [180, 331]
        for row_index, row in enumerate(rows):
            row = tuple(command_syntax(value, self.lang) if value.startswith('/') or ('PSVR' in value and '/' in value)
                        else value for value in row)
            header = row_index == 0
            font = 'Bold' if header else 'Sans'
            row_lines = [lines(value, font, size, width-18) for value, width in zip(row, widths)]
            height = max(map(len, row_lines)) * size * 1.35 + 13
            fill = BLACK if header else ((.962,.953,.96) if row_index % 2 else WHITE)
            self.page.draw_rect(fitz.Rect(42,self.y,553,self.y+height),color=fill,fill=fill)
            x = 42
            for value,width in zip(row,widths):
                text(self.page,x+9,self.y+6,value,size,font,width-18,WHITE if header else BLACK)
                x += width
            self.y += height
        self.y += 10
        self.check()

    def check(self):
        if self.y > 773:
            raise ValueError(f'Page overflow ({self.lang}, page {self.page.number+1}): {self.y:.1f}')


def footer(p, number, lang):
    p.draw_line((42, 785), (553, 785), color=(.86,.85,.86), width=.5)
    label = 'Legion · manual amigable · edición 1.7 · ID o nombre corto' if lang == 'es' else 'Legion · friendly user manual · edition 1.7 · ID or short name'
    text(p, 42, 801, label, 7, color=GREY)
    text(p, 534, 801, f'{number:02d}', 8, 'Bold', width=22, color=RED)


def copy_page(out, source, old, number, lang):
    out.insert_pdf(source, from_page=old-1, to_page=old-1)
    p = out[-1]
    font_setup(p)
    if old == 1:
        for phrase in ('Legion 0.7.1  /  Manual 1.5', '20 NOV 2026'):
            for rect in p.search_for(phrase):
                p.add_redact_annot(rect + (-1,-1,1,1), fill=(.035,.035,.04))
        p.apply_redactions(images=0, graphics=0)
        font_setup(p)
        text(p, 42, 790, 'Legion 0.7.2  /  Manual 1.7', 9, color=(.78,.78,.8))
        text(p, 498, 790, '23 NOV 2026', 8, width=60, color=(.78,.78,.8))
        return
    tag = next((line for line in p.get_text().splitlines() if re.match(r'^\d{2} / ',line)), '')
    for rect in (fitz.Rect(41,25,556,44), fitz.Rect(40,787,557,820)):
        p.add_redact_annot(rect, fill=WHITE)
    p.apply_redactions(images=0, graphics=0)
    font_setup(p)
    if tag:
        text(p, 42, 28, re.sub(r'^\d{2}', f'{number:02d}', tag), 8, 'Bold', color=RED)
    text(p, 466, 28, 'LEGIONFW · 0.7.2', 7.2, width=90, color=GREY)
    footer(p, number, lang)


def build(lang):
    name = 'Spanish' if lang == 'es' else 'English'
    relative = f'docs/Legion-{name}-friendly-user-manual.pdf'
    data = subprocess.check_output(['git','show',f'{SOURCE}:{relative}'],cwd=ROOT)
    source = fitz.open(stream=data, filetype='pdf')
    assert len(source) == 28
    out = fitz.open()
    T = lambda es,en: es if lang == 'es' else en
    def chapter(old, tag_es, tag_en, title_es, title_en, intro_es, intro_en):
        return Chapter(out,source,old,len(out)+1,lang,T(tag_es,tag_en),T(title_es,title_en),T(intro_es,intro_en))
    for old in range(1,29):
        if old == 2:
            c=chapter(old,'EMPIEZA AQUÍ','START HERE','Tus demonios,\nbien explicados.','Your demons,\nclearly explained.',
                      'Una guía para consultar, manejar y recuperar tu Legion.','A guide to querying, controlling and recovering your Legion.')
            c.para('Para RAK3401 1W + RAK13302. Puedes enviar las órdenes desde un nodo con Meshtastic estándar; el que las ejecuta debe llevar Legion.',
                   'For RAK3401 1W + RAK13302. The requesting node can run standard Meshtastic; the executing node must run Legion.')
            c.code('/telemetry !abcdef01\n/telemetry PSVR')
            c.para('Sustituye !nodeid o nombrecorto por los datos reales de tu nodo. La barra | significa «o»; no se escribe. PSVR y AZTH son solo nombres cortos de ejemplo.',
                   'Replace !nodeid or shortname with your actual node details. The | bar means “or”; do not type it. PSVR and AZTH are only example short names.')
            c.example('/telemetry PSVR\n/telemetry AZTH',size=9)
            c.table([('Quiero…','Página'),('Preparar LegionRF y elegir nodo','3–4'),('Consultar telemetría, posición, arranque y componentes','5–7'),('Enviar texto o invocar Drakarys','8–9'),('Gestionar canales y reiniciar','10–11'),('Explorar rutas, ignorar y filtrar spam','12–15'),('Guardar y recuperar ajustes','16–17'),('Usar APC, incluido armado permanente','18–20'),('Entender voltajes y recuperación','21–22'),('Actualizar y consultar DAILY','23–24'),('Recetas, dudas, chuletas y créditos','25–29')],
                    [('I want to…','Page'),('Set up LegionRF and select a node','3–4'),('Query telemetry, position, boot and components','5–7'),('Send text or invoke Drakarys','8–9'),('Manage channels and restart','10–11'),('Explore routes, ignore nodes and filter spam','12–15'),('Save and restore settings','16–17'),('Use APC, including permanent arming','18–20'),('Understand voltage and energy recovery','21–22'),('Update and query DAILY','23–24'),('Recipes, questions, cheat sheets and credits','25–29')],widths=[444,67],size=9)
            c.callout('ESTADO EN HW','HW STATUS','Funciones heredadas de 0.7.1: probadas en HW. Base y novedades de 0.7.2: pendientes de HW. Véase la ficha final.',
                      'Inherited 0.7.1 functions: tested on HW. The 0.7.2 base and new capabilities: pending HW. See the final edition page.')
        elif old == 3:
            c=chapter(old,'PREPARACIÓN','SETUP','La puerta de entrada:\nLegionRF.','The gateway:\nLegionRF.',
                      'Un canal privado compartido con los nodos desde los que quieras manejar tu Legion.','A private channel shared with the nodes you use to control your Legion.')
            c.table([('Paso','Qué configurar'),('01','Un canal SECONDARY habilitado llamado exactamente LegionRF, respetando mayúsculas.'),('02','Una PSK privada aleatoria propia de 16 o 32 bytes. No sirven clave pública, alias corto, clave vacía ni ceros.'),('03','Comparte canal y clave con nodos de confianza; necesitan ajustes LoRa compatibles.'),('04','Envía la orden completa como mensaje al canal LegionRF, también si tu teléfono está conectado al propio Legion.')],
                    [('Step','Set this up'),('01','One enabled SECONDARY channel named exactly LegionRF, including case.'),('02','Your own random private 16- or 32-byte PSK. Public/default keys, short aliases, empty and all-zero keys do not work.'),('03','Share channel and key with trusted nodes; compatible LoRa settings are required.'),('04','Send the complete command as a LegionRF channel message, including when your phone is connected to that Legion.')],widths=[55,456],size=9.5)
            c.heading('Comprueba la puerta','Check the gateway')
            c.code('/telemetry !abcdef01\n/telemetry PSVR')
            c.para('Usa el ID completo o el nombre corto del nodo. No es el nombre largo de la app. La página siguiente explica la selección y los nombres repetidos.',
                   'Use the full ID or the node’s short name, not the app’s long name. The next page explains selection and duplicate names.')
            c.callout('QUIEN TIENE LA CLAVE, TIENE EL CONTROL','THE KEY GRANTS CONTROL','El acceso al canal autoriza las órdenes. No hay una segunda contraseña. No se invocan por mensaje directo.',
                      'Channel access authorizes commands. There is no second password. Do not send them as direct messages.')
        elif old == 4:
            c=chapter(old,'ANTES DE ESCRIBIR','BEFORE YOU TYPE','Un ID o un nombre.\nLa misma orden.','An ID or a name.\nThe same command.',
                      'Todas las órdenes dirigidas aceptan ambas formas. Los IDs siguen disponibles.','Every targeted command accepts both forms. Existing ID syntax remains available.')
            c.code('/telemetry !abcdef01\n/telemetry PSVR\n/trace PSVR RLY1\n/backup status PSVR')
            c.para('!nodeid | nombrecorto significa elegir uno y sustituirlo. No escribas barras, paréntesis ni los marcadores. El nombre corto se compara completo sin distinguir mayúsculas ASCII. Si contiene espacios, ponlo entre comillas: /boot "AB C". Escribe el comando en minúsculas; cada línea se envía por separado en LegionRF.',
                   '!nodeid | shortname means choose one and replace it. Do not type bars, parentheses or placeholders. Short names match in full without ASCII case differences. Quote spaces: /boot "AB C". Commands are lowercase; send each line separately in LegionRF.')
            c.callout('NOMBRES REPETIDOS','DUPLICATE NAMES','Cada Legion reconoce su propio nombre. Si varios comparten nombre y canal, pueden actuar todos. El ID completo elige uno de forma inequívoca.',
                      'Each Legion recognizes its own name. Several Legions sharing that name and channel can all act. A full ID selects one uniquely.')
            c.para('En trace, ignore, unignore y guard clear, el segundo nodo también admite nombre corto. Debe existir una sola coincidencia en la NodeDB del ejecutor; si falta o es ambiguo, responde un error y pide el ID. La selección pendiente se vuelve a comprobar. En /ignore name, el nombre largo entre comillas sigue siendo la regla literal de filtrado.',
                   'In trace, ignore, unignore and guard clear, the second node also accepts a short name. It must match one named NodeDB entry on the executor; missing or ambiguous names return an error asking for the ID. Pending selection is rechecked. In /ignore name, the quoted long name remains the literal filter rule.')
            c.table([('Familia','Espera'),('Herramientas, APC y antispam','Pausa de 5 s al procesar; deja al menos 6 s tras la respuesta.'),('Telemetría y backup','Comparten 60 s tras un intento de respuesta.'),('Traceroute','Una ruta activa; 60 s entre inicios; hasta 90 s para el resultado.')],
                    [('Family','Wait'),('Tools, APC and antispam','Five-second cooldown after processing; allow six seconds after a reply.'),('Telemetry and backup','Shared 60 seconds after a response attempt.'),('Traceroute','One active trace; 60 seconds between starts; up to 90 seconds for a result.')],widths=[172,339])
            c.para('queued confirma cola local, no entrega remota. [página] es opcional: no escribas los corchetes.',
                   'queued confirms local queuing, not remote delivery. [page] is optional; omit the brackets.',size=9)
        elif old == 5:
            c=chapter(old,'CONSULTAR · TELEMETRÍA Y POSICIÓN','QUERY · TELEMETRY AND POSITION','¿Cómo está?\n¿Dónde está?','How is it doing?\nWhere is it?',
                      'Dos consultas de solo lectura. No cambian ajustes ni solicitan un nuevo posicionamiento.','Two read-only queries. They do not change settings or request a new position fix.')
            c.code('/telemetry !abcdef01\n/telemetry PSVR')
            c.code('2.8.3.Legion0.7.2 !abcdef01 up:194400s\nCPU:29.25 / max 34.50C BAT:82% 4.01 / min 3.96V\nN:-116 peak:-88dBm n:600\nRX:450 BAD:7 TX:32 REL:24 DROP:2',size=8.8)
            c.table([('Campo','Cómo leerlo'),('up / CPU / BAT','Segundos desde arranque; temperatura actual/máxima del chip; batería estimada, voltaje físico y mínimo.'),('N / peak / n','Ruido RF medio, pico RSSI y muestras en la frecuencia actual.'),('RX / BAD / TX / REL / DROP','Recepciones, malas recepciones, TX, reenvíos y TX descartados. REL está incluido en TX; BAD no es solo CRC.')],
                    [('Field','Read it this way'),('up / CPU / BAT','Seconds since boot; current/max chip temperature; estimated battery, physical voltage and minimum.'),('N / peak / n','Mean RF noise, peak RSSI and samples at the current frequency.'),('RX / BAD / TX / REL / DROP','Receptions, bad receptions, TX, relays and dropped TX. REL is included in TX; BAD is not only CRC.')],size=8.8)
            c.para('/telemetry sin selector consulta a todos los Legion alcanzables del canal. Los contadores y extremos se reinician al arrancar; la programación periódica de Meshtastic y DAILY es independiente.',
                   '/telemetry without a selector asks all reachable Legions on the channel. Counters and extrema reset at boot; scheduled Meshtastic telemetry and DAILY are separate.',size=9)
            c.heading('Posición local y publicación configurada','Local position and configured publication')
            c.code('/position !abcdef01\n/position PSVR')
            c.para('Devuelve FIXED/LIVE, valid:0/1, latitud y longitud; LoRa_cfg, canal (desde 1), precisión efectiva en bits, intervalo configurado y smart; MQTT_cfg, uplink del canal y map. Son datos locales y configuración: no confirman un fix reciente ni que LoRa o MQTT hayan entregado una posición.',
                   'Returns FIXED/LIVE, valid:0/1, latitude and longitude; LoRa_cfg, channel (from 1), effective precision in bits, configured interval and smart; MQTT_cfg, channel uplink and map. These are local data and configuration, not confirmation of a recent fix or LoRa/MQTT delivery.',size=9.3)
        elif old == 6:
            c=chapter(old,'CONSULTAR · /boot','QUERY · /boot','¿Qué pasó\nal arrancar?','What happened\nat boot?',
                      'Una foto del arranque y pistas sobre el reinicio anterior.','A boot snapshot and clues about the previous restart.')
            c.code('/boot !abcdef01')
            c.table([('Campo','Qué te dice'),('reset','Motivo del reset de hardware y máscara completa. Sin evidencia queda desconocido.'),('prev','Parada protectora anterior registrada, como batería/VDD bajos, temperatura o Scramble. No es un historial.'),('VBAT / VDD','Primeras muestras físicas del arranque, en milivoltios.'),('USB','Detección USB en aquella muestra.'),('NA','Dato no disponible.')],
                    [('Field','What it tells you'),('reset','Hardware reset reason and full mask. Missing evidence stays unknown.'),('prev','Previous recorded protective stop, such as low battery/VDD, temperature or Scramble. Not a history.'),('VBAT / VDD','First physical samples at boot, in millivolts.'),('USB','USB detection at that sample.'),('NA','Unavailable reading.')],widths=[105,406],size=9.4)
            c.heading('Los voltajes pertenecen al arranque','These voltages belong to boot')
            c.para('No son lecturas en directo ni necesariamente los valores que había cuando ocurrió un fallo. Para voltaje actual consulta telemetría.',
                   'They are not live readings or necessarily the voltage when a fault happened. Query telemetry for current voltage.')
            c.heading('Componentes y contadores, por separado','Components and counters are separate')
            c.code('/components !abcdef01')
            c.para('CC310, SPI, REG1 y SAVE se explican en la página siguiente. En todas las consultas usa el ID o nombre corto real del nodo.',
                   'CC310, SPI, REG1 and SAVE are explained on the next page. Every targeted query accepts the actual node ID or short name.')
            c.callout('CONSULTAR NO CAMBIA EL NODO','QUERYING DOES NOT CHANGE THE NODE','boot y components son de solo lectura. No guardan ajustes ni reinicializan componentes.',
                      'boot and components are read-only. They do not save settings or reinitialize components.')
        elif old == 7:
            c=chapter(old,'CONSULTAR · /components','QUERY · /components','Los demonios,\npor dentro.','The demons,\nfrom the inside.',
                      'Criptografía, radio, regulador y guardados de preferencias en un informe corto.','Cryptography, radio, regulator and preference saves in one short report.')
            c.code('/components !abcdef01\n/components PSVR')
            c.code('!abcdef01 COMPONENTS\nCC310 SHA:1357 MAC:2 SW:0\nSPI:ON 8MHz BULK:ON\nDC/DC:ON REG1\nSAVE C:20 U:14 S:6 F:0')
            c.table([('Campo','Qué significa'),('CC310 SHA / MAC','SHA-256 y HMAC de prueba de ACK completados por hardware desde el arranque.'),('SW','Intentos del acelerador resueltos por software tras un fallo.'),('SPI / BULK','Disponibilidad, frecuencia configurada y transferencias por bloques.'),('DC/DC … REG1','Estado actual del regulador REG1 del microcontrolador.'),('SAVE C / U / S / F','Guardados de preferencias comprobados / idénticos omitidos / completados / fallidos desde el arranque.')],
                    [('Field','Meaning'),('CC310 SHA / MAC','Hardware SHA-256 and ACK-proof HMAC completions since boot.'),('SW','Accelerator attempts completed in software after failure.'),('SPI / BULK','Availability, configured frequency and bulk transfers.'),('DC/DC … REG1','Current state of the MCU’s REG1 regulator.'),('SAVE C / U / S / F','Preference saves checked / identical saves skipped / completed / failed since boot.')],size=9)
            c.para('SAVE cuenta la ruta de guardado protobuf, no todas las escrituras del sistema. CC310 y SAVE se reinician con el nodo. SHA/MAC no cuentan las firmas XEdDSA de la nueva base.',
                   'SAVE covers protobuf preference saves, not every filesystem write. CC310 and SAVE reset with the node. SHA/MAC do not count XEdDSA signing in the new base.')
            c.callout('CONSULTAR NO CAMBIA EL NODO','READING DOES NOT CHANGE THE NODE','MAC:0 puede ser normal. 8MHz es un ajuste, no una medición física. El informe no activa ni reinicializa componentes, no guarda ajustes y no mide ahorro energético.',
                      'MAC:0 can be normal. 8MHz is a setting, not a physical measurement. The report does not activate or reinitialize components, save settings or measure energy savings.')
        elif old == 8:
            c=chapter(old,'ACTUAR · /msg','ACT · /msg','Que hable\nese Legion.','Let that\nLegion speak.',
                      'Envía texto desde el nodo elegido, aunque estés conectado a otro.','Send text from the selected node, even while connected to another.')
            c.code('/msg !abcdef01 SFNarrow Hola desde Legion', '/msg !abcdef01 SFNarrow Hello from Legion')
            c.table([('Marcador','Qué debes poner'),('!nodeid | nombrecorto','El ID completo o nombre corto real del Legion que emitirá.'),('<canal>','Un canal habilitado en ese nodo. Entre comillas si lleva espacios.'),('<mensaje>','El texto que publicará el nodo en ese canal.')],
                    [('Placeholder','What to supply'),('!nodeid | shortname','The full ID or actual short name of the transmitting Legion.'),('<channel>','An enabled channel on that node. Quote spaces.'),('<message>','The text the node will publish on that channel.')],widths=[166,345],size=9.5)
            c.heading('Ejemplo con nombre corto','Short-name example')
            c.example('/msg AZTH "Mi canal" Hola a todos','/msg AZTH "My channel" Hello everyone')
            c.para('AZTH es solo un ejemplo de nombre corto; sustitúyelo por el de tu nodo. La orden viaja por LegionRF y el texto sale por el canal indicado. El nombre de canal admite hasta 11 bytes UTF-8 y toda la orden hasta 199 bytes. Una tilde puede ocupar varios bytes.',
                   'AZTH is only an example short name; replace it with your node’s name. The command travels in LegionRF and the text is sent on the selected channel. Channel names allow 11 UTF-8 bytes and the complete command 199 bytes. Accented characters can use several bytes.')
            c.callout('QUÉ CONFIRMA LA RESPUESTA','WHAT THE REPLY CONFIRMS','queued confirma la cola local, no entrega remota. Un canal inválido no se sustituye por otro y no se reenvía automáticamente la orden.',
                      'queued confirms local queuing, not remote delivery. An invalid channel is not replaced with another and the command is not automatically retried.')
        elif old == 9:
            c=chapter(old,'GESTIONAR · CANALES','MANAGE · CHANNELS','Ver los canales.\nCrear o borrar.','See the channels.\nCreate or delete.',
                      'Consulta la lista o edita canales secundarios sin reiniciar el nodo.','List channels or edit secondary channels without restarting the node.')
            c.code('/listchannels !abcdef01\n/listchannels PSVR\n!abcdef01: 1:SFNarrow, 2:Iberia, 3:Madrid, 4:LegionRF',size=8.9)
            c.para('La lista incluye los canales configurados y habilitados, también primario y LegionRF. Numera desde 1 según su posición real: si hay un hueco, lo conserva. No muestra las claves.',
                   'The list includes enabled configured channels, including primary and LegionRF. Numbering starts at 1 and keeps real positions, including gaps. It does not display keys.')
            c.code('/createch PSVR "Mi canal" PSK_BASE64\n/deletech PSVR "Mi canal"',
                   '/createch PSVR "My channel" PSK_BASE64\n/deletech PSVR "My channel"')
            c.table([('Orden','Qué hace'),('createch','Primer slot secundario deshabilitado (índices internos 1–7). Nombre nuevo; MQTT empieza deshabilitado.'),('deletech','Vacía el secundario con ese nombre, sin mover otros índices. No lleva clave.'),('Nombre y PSK','Nombre: hasta 11 bytes UTF-8; comillas con espacios. PSK: Base64 estándar con padding; decodifica a 1, 16 o 32 bytes.')],
                    [('Command','Effect'),('createch','First disabled secondary slot (internal indices 1–7). New name; MQTT starts disabled.'),('deletech','Clears that named secondary without moving other indices. No key argument.'),('Name and PSK','Name: up to 11 UTF-8 bytes; quote spaces. PSK: standard padded Base64 decoding to 1, 16 or 32 bytes.')],size=9)
            c.para('Para privacidad usa una clave aleatoria propia de 16 o 32 bytes. No se sobrescriben nombres habilitados ni se aceptan coincidencias ambiguas. Primario y LegionRF están protegidos; un slot usado por Mesh Beacon también puede impedir la edición.',
                   'For privacy use your own random 16- or 32-byte key. Enabled names are not overwritten and ambiguous matches fail. Primary and LegionRF are protected; a slot in use by Mesh Beacon can also block editing.')
            c.callout('ESPERA LA CONFIRMACIÓN DE GUARDADO','WAIT FOR THE SAVED CONFIRMATION','Crear o borrar deja APC OFF y puede volver OUTDATED el backup. Reactiva APC expresamente y usa backup replace solo si quieres conservar los ajustes. La preferencia de armado permanente sigue guardada.',
                      'Creating or deleting sets APC OFF and may make the backup OUTDATED. Reactivate APC explicitly; use backup replace only to keep the new settings. The permanent-arm preference remains saved.')
        elif old == 10:
            c=chapter(old,'ACTUAR · /reboot','ACT · /reboot','Reiniciar,\nsin subir al tejado.','Restart,\nwithout climbing up.',
                      'Un reinicio normal programado a distancia.','A normal restart scheduled remotely.')
            c.code('/reboot !abcdef01\n/reboot PSVR')
            c.para('Al aceptar, programa un reinicio normal 20 segundos después por la vía habitual de guardado y reinicio.',
                   'On acceptance, schedules a normal restart 20 seconds later through the usual save/restart path.')
            c.table([('Paso','Qué hacer'),('1','Envía la orden por LegionRF y espera respuesta.'),('2','Deja pasar los 20 s y el tiempo de arranque.'),('3','Consulta /telemetry PSVR: up reflejará el nuevo arranque.'),('4','Pide /boot PSVR por separado para ver las pistas del arranque.')],
                    [('Step','What to do'),('1','Send the command in LegionRF and wait for the reply.'),('2','Allow 20 seconds plus boot time.'),('3','Query /telemetry PSVR: up will reflect the new boot.'),('4','Request /boot PSVR separately for boot evidence.')],widths=[55,456],size=9.5)
            c.heading('Si está ocupado','If it is busy')
            c.para('Una edición de ajustes, transferencia, recuperación bloqueada o alimentación insuficiente puede rechazar la orden. Espera a que termine o mejore la alimentación.',
                   'A settings transaction, transfer, blocked recovery or unsafe supply can reject the request. Wait for completion or an adequate supply.')
            c.callout('ARMADO Y CUENTA DIARIA','ARMING AND DAILY CLOCK','Sin permanencia, APC vuelve OFF y antispam OBSERVE. Con /arm permanent guardado, ambos se restauran tras las comprobaciones. Estadísticas y calentamiento empiezan de nuevo; DAILY vuelve a contar 24 h.',
                      'Without saved arming, APC returns OFF and antispam OBSERVE. Saved /arm permanent restores both after checks. Statistics and warmup begin again; DAILY starts another 24-hour count.')
            c.para('Un reinicio normal no restaura un backup por sí solo. Una configuración sana conserva prioridad.',
                   'A normal restart does not by itself restore a backup. Healthy current settings retain priority.')
        elif old == 11:
            c=chapter(old,'EXPLORAR · /zerohop','EXPLORE · /zerohop','¿A quién oye\ndirectamente?','Who can it hear\ndirectly?',
                      'Vecinos observados por radio sin intermediarios.','Neighbours observed over radio without intermediaries.')
            c.code('/zerohop !abcdef01\n/zerohop !abcdef01 2')
            c.para('Lista las observaciones RF directas desde el arranque, con nombre corto y SNR, de mayor a menor SNR. La primera forma abre la lista; el número opcional selecciona otra página. Usa Next: para seguir y deja al menos 6 s tras cada respuesta.',
                   'Lists direct RF observations since boot, with short name and SNR, from highest to lowest SNR. The first form opens the list; the optional number selects another page. Follow Next: and allow six seconds after each reply.')
            c.table([('Lo que ves','Cómo interpretarlo'),('SNR cero o negativo','Es válido; no significa que la fila esté vacía.'),('Falta un nodo','Puede no haber sido observado directamente en este arranque.'),('partial','La captura superó su capacidad de hasta 128 filas.')],
                    [('What you see','How to read it'),('Zero or negative SNR','Valid; the row is not empty.'),('Missing node','It may not have been heard directly during this boot.'),('partial','The snapshot exceeded its capacity of up to 128 rows.')],widths=[150,361],size=9.5)
            c.callout('UNA LIBRETA DE OBSERVACIONES','A NOTEBOOK OF OBSERVATIONS','No es un escaneo activo ni demuestra comunicación en los dos sentidos. Para probar una ruta, usa trace.',
                      'This is not an active scan or proof of two-way communication. Use trace to test a route.')
            c.para('Las páginas comparten una captura fija de 15 min ligada al solicitante y al canal. Repetir la página 1 la reutiliza aunque esté vacía. Al caducar se crea otra; cambiar la radio la invalida.',
                   'Pages share a frozen 15-minute snapshot bound to requester and channel. Repeating page 1 reuses it even when empty. Expiry creates another; a radio change invalidates it.')
        elif old == 12:
            c=chapter(old,'EXPLORAR · /trace','EXPLORE · /trace','¿Por dónde\nviaja el mensaje?','Which way does\nthe message travel?',
                      'Pide una ruta hacia otro nodo y recibe ambos caminos en LegionRF.','Request a route to another node and receive both paths in LegionRF.')
            c.code('/trace !abcdef01 !12345678\n/trace PSVR RLY1\n/trace PSVR !12345678')
            c.para('El primer nodo inicia el traceroute; el segundo es el destino y puede usar Meshtastic estándar. Un nombre corto de destino debe ser único en la NodeDB del ejecutor; si no, usa su ID. Para un ID desconocido se usa el canal primario; para uno conocido, su canal registrado.',
                   'The first node starts the trace; the second is the destination and can run standard Meshtastic. A destination short name must be unique in the executor’s NodeDB; otherwise use its ID. Unknown IDs use the primary channel; known nodes use their recorded channel.')
            c.table([('Respuesta','Lectura'),('1/2 out','Camino de ida.'),('2/2 back','Camino de vuelta, que puede ser diferente.'),('? / 0 reported relays','Salto no informado / no constan relays en los metadatos.'),('NO_ROUTE','El sistema de rutas informa que no es alcanzable.'),('reachability unknown','Sin respuesta en 90 s; no demuestra que esté apagado.')],
                    [('Reply','Meaning'),('1/2 out','Outbound path.'),('2/2 back','Return path, which can differ.'),('? / 0 reported relays','Unreported hop / no relays reported in the metadata.'),('NO_ROUTE','Routing reports the destination unreachable.'),('reachability unknown','No reply within 90 seconds; does not prove it is off.')],size=9.3)
            c.callout('UNA RUTA CADA VEZ','ONE TRACE AT A TIME','Una ruta activa; mínimo 60 s entre inicios y hasta 90 s para responder. Las demás herramientas siguen disponibles con sus pausas. Los cambios de radio, canal o identidad pendiente pueden cancelar la operación.',
                      'One active trace; at least 60 seconds between starts and up to 90 seconds for a result. Other tools remain available with their cooldowns. Radio, channel or pending identity changes can cancel the operation.')
        elif old == 13:
            c=chapter(old,'GESTIONAR · /ignore','MANAGE · /ignore','Este Legion\nignora a ese nodo.','This Legion\nignores that node.',
                      'El primer selector elige quién actúa; el segundo, el nodo afectado.','The first selector chooses who acts; the second chooses the affected node.')
            c.code('/ignore PSVR RLY1\n/unignore !abcdef01 !12345678\n/ignorelist PSVR\n/ignorelist PSVR 2')
            c.para('ID y nombre corto se pueden mezclar. El nombre del peer debe ser único en la NodeDB del ejecutor. Solo ese Legion modifica su lista; las formas antiguas sin ejecutor no se aceptan.',
                   'IDs and short names can be mixed. The peer name must be unique in the executor’s NodeDB. Only the selected Legion changes its list; old forms without an executor are rejected.')
            c.para('Los cambios usan NodeDB persistente e incluyen entradas antiguas. in RAM; persistence pending significa que aún no se ha guardado. Ignorar filtra orígenes; no impide emitir RF ni silencia todo el tráfico ajeno reenviado por ese peer. Los flags quedan fuera del rescate.',
                   'Changes use persistent NodeDB state and include older entries. in RAM; persistence pending means not yet saved. Ignoring filters origins; it does not stop RF transmission or all other traffic forwarded by that peer. Flags are outside the rescue snapshot.')
            c.heading('Ignorar por nombre largo','Ignore by long name')
            c.code('/ignore name PSVR "Nodo de ejemplo"\n/unignorename PSVR "Nodo de ejemplo"\n/ignorelist names PSVR',
                   '/ignore name PSVR "Example node"\n/unignorename PSVR "Example node"\n/ignorelist names PSVR')
            c.para('Aquí las comillas contienen la regla: nombre largo exacto, incluidas mayúsculas. Hasta 8 reglas de 39 bytes UTF-8, guardadas en flash. Bloquea el anuncio coincidente antes de responder o reenviar; aprende hasta 24 IDs en RAM, que caducan tras 1 h sin actividad. Tras reiniciar los aprende otra vez.',
                   'Here the quoted value is the rule: exact long name, including case. Up to eight 39-byte UTF-8 rules are saved in flash. A matching announcement is blocked before reply/relay; up to 24 IDs are learned in RAM and expire after one inactive hour. They are learned again after restart.')
            c.callout('LAS LISTAS SON CAPTURAS','LISTS ARE SNAPSHOTS','ignorelist usa una captura fija de 15 min, hasta 128 filas. Sigue Next:. El filtro automático de ráfagas se explica en la página 15; sus cuarentenas son independientes.',
                      'ignorelist uses a frozen 15-minute snapshot, up to 128 rows. Follow Next:. Automatic burst filtering is on page 15; its quarantines are separate.')
        elif old == 14:
            c=chapter(old,'GESTIONAR · ANTISPAM Y SCRAMBLE','MANAGE · ANTISPAM AND SCRAMBLE','Un demonio\ncontra el spam.','A demon\nagainst spam.',
                      'Guard vigila el texto broadcast del canal primario recibido por LoRa.','Guard watches primary-channel broadcast text received over LoRa.')
            c.table([('Orden en LegionRF','Resultado'),('/guard status PSVR','Modo, contadores y cuarentenas.'),('/guard observe PSVR','Simula sin bloquear. Es el valor de arranque por defecto.'),('/guard on PSVR','Aplica bloqueos automáticos.'),('/guard off PSVR','Detiene el detector y limpia la evidencia temporal.'),('/guard clear PSVR RLY1','Limpia indicios y cuarentena de ese peer.'),('/spamlist PSVR [página]','Lista paginada de cuarentenas. Empieza por 1.')],
                    [('Command in LegionRF','Result'),('/guard status PSVR','Mode, counters and quarantines.'),('/guard observe PSVR','Models without blocking. Default startup mode.'),('/guard on PSVR','Enforces automatic blocking.'),('/guard off PSVR','Stops detection and clears temporary evidence.'),('/guard clear PSVR RLY1','Clears that peer’s evidence and quarantine.'),('/spamlist PSVR [page]','Paginated quarantines. Start with page 1.')],widths=[223,288],size=8.9)
            c.para('Cada origen tiene 8 créditos y recupera 1 cada 5 s. En ON se descarta el exceso. Cuatro excesos o seis textos idénticos con IDs nuevos en 20 s producen 10 min de cuarentena. Incluye texto comprimido; los duplicados no suman. Evidencias y cuarentenas son RAM; /ignore es independiente.',
                   'Each origin has eight tokens and regains one every five seconds. ON drops excess traffic. Four excesses or six identical texts with new IDs in 20 seconds trigger a ten-minute quarantine. Includes compressed text; duplicates do not count. Evidence and quarantines stay in RAM; /ignore is separate.',size=9.2)
            c.para('/arm permanent PSVR guarda el armado conjunto para próximos arranques. /arm PSVR y /disarm PSVR borran esa permanencia. Los cambios individuales de guard solo afectan a la sesión. DAILY distingue SPAM:OBSERVE simQ:n de SPAM:ON Q:n.',
                   '/arm permanent PSVR saves joint arming for later boots. /arm PSVR and /disarm PSVR clear it. Individual guard changes affect this run only. DAILY distinguishes SPAM:OBSERVE simQ:n from SPAM:ON Q:n.',size=9.2)
            c.heading('Scramble · silencio temporal','Scramble · temporary silence')
            c.code('/scramble !abcdef01\n/scramble PSVR')
            c.para('Corta el tráfico habitual al recibir la orden. Intenta el aviso Entering hibernation for Scramble. durante hasta 4 s; apaga LoRa, Bluetooth y datos USB. A los 60 min reinicia e intenta Hibernation ended. Scramble complete. El armado permanente se aplica tras arrancar; un reset o corte de alimentación puede acortar el silencio.',
                   'Stops normal traffic on receipt. Attempts Entering hibernation for Scramble. for up to four seconds, then turns off LoRa, Bluetooth and USB data. After 60 minutes it restarts and attempts Hibernation ended. Scramble complete. Saved arming applies after boot; reset or power loss can shorten the silence.',size=9)
        elif old == 15:
            c=chapter(old,'RESCATE · /backup','RESCUE · /backup','Guarda un punto\nal que volver.','Save a point\nto return to.',
                      'Crear y reemplazar son acciones explícitas. Instalar o reiniciar no actualiza el backup.','Creating and replacing are explicit actions. Installing or restarting does not refresh the backup.')
            c.code('/backup !abcdef01\n/backup status !abcdef01\n/backup replace !abcdef01')
            c.para('backup crea si no existe; status consulta sin cambiarlo; replace guarda expresamente los ajustes actuales y omite la escritura si coinciden. El selector es siempre el ID o nombre corto real del ejecutor.',
                   'backup creates if absent; status reads without changing it; replace explicitly saves current settings and skips an identical write. Always select the executor by its actual ID or short name.')
            c.callout('ESPERA LA CONFIRMACIÓN','WAIT FOR CONFIRMATION','saved and verified; recovery armed confirma guardado verificado y rescate armado. Telemetría y backup comparten una pausa de 60 s.',
                      'saved and verified; recovery armed confirms a verified save and armed recovery. Telemetry and backup share a 60-second cooldown.')
            c.table([('Estado','Significado'),('up to date; recovery armed','Los bloques guardados coinciden con los actuales.'),('OUTDATED: owner,channels','Esos bloques difieren; el punto anterior sigue utilizable.'),('freshness unavailable','No se puede comparar con fiabilidad ahora.'),('no rescue point','No hay punto de rescate activo.'),('invalid or incompatible','El registro no puede utilizarse.')],
                    [('State','Meaning'),('up to date; recovery armed','Saved blocks match current settings.'),('OUTDATED: owner,channels','Those blocks differ; the earlier point remains usable.'),('freshness unavailable','Reliable comparison is unavailable now.'),('no rescue point','No active rescue point.'),('invalid or incompatible','The record cannot be used.')],widths=[212,299],size=9.1)
            c.para('Puede señalar owner, config, modules, channels y position, sin mostrar secretos. GPS dinámico no lo vuelve obsoleto; editar canales puede hacerlo. DAILY compara sin guardar otro backup. Tras un cambio que quieras conservar, consulta status y decide si usar replace.',
                   'May identify owner, config, modules, channels and position without exposing secrets. Dynamic GPS does not make it stale; channel edits can. DAILY compares without saving another backup. After a change you want to keep, query status and decide whether to replace.')
        elif old == 16:
            c=chapter(old,'RESCATE · RESTAURAR Y BORRAR','RESCUE · RESTORE AND DELETE','Que renazca\ncon su identidad.','Let it rise again\nwith its identity.',
                      'El rescate actúa ante pérdida o corrupción confirmada de preferencias esenciales.','Rescue acts on confirmed loss or corruption of essential preferences.')
            c.heading('Qué vuelve y qué no','What returns and what does not')
            c.para('Guarda nombres, identidad privada y clave pública/ID coherentes, claves de canal, ajustes del dispositivo y radio, módulos y posición fija. Excluye conversaciones, peers, GPS dinámico, contadores, colas y emparejamientos BLE. Ham/licensed y cannot be messaged vuelven a sus valores normales.',
                   'Saves names, private identity and coherent public key/ID, channel keys, device/radio settings, modules and fixed position. Excludes chats, peers, dynamic GPS, counters, queues and BLE bonds. Ham/licensed and cannot be messaged return to normal values.')
            c.para('Las reglas de nombre ignorado y la preferencia de armado permanente se guardan por separado y no forman parte del rescate. Una configuración sana actual tiene prioridad; un reinicio o actualización normal no fuerza restauración.',
                   'Name-ignore rules and the permanent-arm preference are saved separately, outside the rescue snapshot. Healthy current settings retain priority; a normal restart or update does not force restoration.')
            c.code('/backup delete !abcdef01\n/backup delete PSVR')
            c.callout('ANTES DE UN RESET DE FÁBRICA VOLUNTARIO','BEFORE AN INTENTIONAL FACTORY RESET','Un reset de fábrica puede restaurar un rescate armado. Para quedar en blanco, borra el punto, espera deleted; recovery disabled y solicita después el reset.',
                      'A factory reset can restore an armed rescue point. For a blank configuration, delete the point, wait for deleted; recovery disabled, then request the reset.')
            c.heading('El aviso del regreso','The return notice')
            c.code('Ashes to ashes, dust to dust, the node [node_name] has risen again',size=8.4)
            c.para('Se pone en cola en el LegionRF restaurado. Un fallo del aviso no deshace el rescate. Una restauración incompleta mantiene la radio en silencio y tiene reintentos limitados. El registro tiene integridad, no cifrado de secretos; conserva una exportación externa.',
                   'Queued on the restored LegionRF. A failed notice does not undo rescue. Incomplete restoration keeps the radio silent with bounded retries. The record has integrity protection, not secret encryption; keep an external export.')
        elif old == 17:
            c=chapter(old,'APC · MODOS Y ARMADO','APC · MODES AND ARMING','Cuidar la batería.\nRecordar el armado.','Care for the battery.\nRemember arming.',
                      'APC combina S1 y S2 y mantiene la recepción. Requiere rol CLIENT.','APC combines S1 and S2 and keeps reception active. CLIENT role is required.')
            c.table([('Modo','Qué hace'),('OBSERVE','Recoge voltajes y estadísticas, sin recortar reenvíos.'),('SHADOW','Simula presupuestos S1 y objetivos S2; transmite nominal.'),('ON','Aplica S1 y S2 tras calentamiento y persistencia de estado.'),('OFF','Devuelve admisión y potencia a su funcionamiento normal.')],
                    [('Mode','Effect'),('OBSERVE','Collects voltage and statistics without limiting relays.'),('SHADOW','Models S1 budgets and S2 targets; transmits nominally.'),('ON','Applies S1 and S2 after warmup and state persistence.'),('OFF','Restores normal admission and power.')],widths=[100,411],size=9)
            c.code('/apc observe PSVR\n/apc shadow PSVR\n/apc on PSVR\n/apc off PSVR',size=9)
            c.heading('APC y antispam con una orden','APC and antispam in one command')
            c.table([('Orden','Respuesta / duración'),('/arm PSVR','APC ON (S1+S2). SPAM ON. Solo esta ejecución; borra permanencia previa.'),('/arm permanent PSVR','APC ON (S1+S2). SPAM ON. AUTOARM saved. Guarda y verifica flash para restaurar tras reinicio.'),('/disarm PSVR','APC OFF. SPAM OFF. Limpia la preferencia permanente.')],
                    [('Command','Reply / duration'),('/arm PSVR','APC ON (S1+S2). SPAM ON. This run only; clears prior permanent arming.'),('/arm permanent PSVR','APC ON (S1+S2). SPAM ON. AUTOARM saved. Saves and verifies flash for restoration after reboot.'),('/disarm PSVR','APC OFF. SPAM OFF. Clears permanent arming.')],widths=[185,326],size=9)
            c.para('Todas admiten también !nodeid. Si no puede armar o guardar, responde un error y conserva los modos. Sin preferencia válida arranca APC OFF y spam OBSERVE; con permanencia restaura ambos tras las comprobaciones de configuración y activación. Cada arranque abre sesión y calentamiento nuevos. Contadores y cuarentenas no se guardan.',
                   'All also accept !nodeid. If arming or saving fails, an error is returned and modes remain unchanged. Without a valid preference, boot uses APC OFF and spam OBSERVE; saved arming restores both after configuration and activation checks. Each boot starts a fresh session and warmup. Counters and quarantines are not saved.',size=9.1)
            c.para('Los cambios individuales /apc y /guard afectan a esta ejecución; no borran AUTOARM. Repetir modo conserva sesión. Modos heredados: probados en HW. Permanencia: pendiente de HW.',
                   'Individual /apc and /guard changes affect this run; they do not clear AUTOARM. Repeating a mode preserves the session. Inherited modes: tested on HW. Permanent arming: pending HW.',size=9)
        elif old == 19:
            c=chapter(old,'APC · /apc status','APC · /apc status','El informe,\npágina a página.','The report,\npage by page.',
                      'Siete páginas de una captura; S2 en la séptima y AUTOARM en la primera.','Seven pages in one snapshot; S2 on page seven and AUTOARM on page one.')
            c.code('/apc status !abcdef01\n/apc status PSVR\n/apc status PSVR 7')
            c.para('Empieza por 1 para abrir una captura fija de 15 min. Después pide 2–7. Repetir 1 reemplaza la captura. Deja al menos 6 s tras cada respuesta. Sesión e informe identifican el conjunto.',
                   'Start with page 1 to open a frozen 15-minute snapshot. Then request 2–7. Repeating page 1 replaces it. Allow six seconds after each reply. Session and report IDs identify the set.')
            c.table([('Pág.','Contenido'),('1','Modo/estado, AUTOARM:saved u OFF, inhibición, VBAT bruto/filtrado y decisiones.'),('2','Duración, muestras, USB, estadísticas de batería y VDD.'),('3','Inicios, finales, abortos y tiempo de aire estimado TX.'),('4','IRQ, IDs repetidos, fallos, TX abiertos, huecos y cambios.'),('5','Radio, potencia configurada y ajuste compensado del chip.'),('6','Presupuestos S1, admisiones, transiciones y tiempo rechazado.'),('7','Objetivos RF S2, fallos y TX nominales, reducidos y simulados.')],
                    [('Page','Contents'),('1','Mode/state, AUTOARM:saved or OFF, inhibition, raw/filtered VBAT and decisions.'),('2','Duration, samples, USB, battery statistics and VDD.'),('3','TX starts, completions, aborts and estimated airtime.'),('4','IRQ, repeated IDs, failures, open TXs, gaps and changes.'),('5','Radio, configured power and compensated chip drive.'),('6','S1 budgets, admissions, transitions and refused airtime.'),('7','S2 RF targets, failures and nominal/reduced/shadow TXs.')],widths=[55,456],size=9.1)
            c.para('eligible cuenta intentos elegibles; would, rechazos simulados; skip, los aplicados en ON. OBSERVE puede tenerlos a cero aunque reenvíe. evict son sustituciones en el rastreador de 32 IDs, no descartes de paquetes. TX completado es evidencia local, no entrega remota.',
                   'eligible counts eligible attempts; would modeled refusals; skip refusals applied in ON. OBSERVE can show zero while forwarding. evict counts replacements in the 32-ID tracker, not dropped packets. Completed TX is local evidence, not remote delivery.',size=9.2)
            c.callout('CAPTURA Y ARMADO','SNAPSHOT AND ARMING','Cambios relevantes de ajustes/canal desarman APC en esta sesión; reactívalo. AUTOARM refleja la preferencia para próximos arranques. RF, alcance y ahorro siguen sin medición.',
                      'Relevant settings/channel changes disarm APC for this run; reactivate it. AUTOARM reports the preference for later boots. RF output, range and savings remain unmeasured.')
        elif old == 20:
            c=chapter(old,'ENERGÍA · QUÉ SE MIDE','ENERGY · WHAT IS MEASURED','Dos voltajes.\nDos historias.','Two voltages.\nTwo stories.',
                      'La recuperación energética es automática e independiente de APC y del backup.','Energy recovery is automatic and independent of APC and the backup.')
            c.table([('Dato','Qué mide','Cuándo'),('VBAT','Voltaje físico por el divisor RAK19007.','Cada 5 s, al arrancar y antes de TX.'),('VDD','Alimentación interna del nRF52840.','Cada 1 s y en guardias de arranque, TX y flash.'),('USB / VBUS','USB detectado en el nodo.','En las decisiones que lo usan.')],
                    [('Reading','What it measures','When'),('VBAT','Physical voltage through the RAK19007 divider.','Every 5 s, at boot and before TX.'),('VDD','Internal nRF52840 supply.','Every 1 s and in boot, TX and flash guards.'),('USB / VBUS','USB detected on the node.','In decisions that use it.')],widths=[75,218,218],size=9.3)
            c.para('La política es para RAK3401 + RAK13302 con batería y RAK19007: una celda Li-Ion/LiPo o celdas en paralelo. Cuatro 18650 en paralelo siguen teniendo el voltaje de una celda.',
                   'This policy targets RAK3401 + RAK13302 with battery and RAK19007: one Li-Ion/LiPo cell or parallel cells. Four parallel 18650 cells still have single-cell voltage.')
            c.heading('La lectura física de batería','Physical battery readings')
            c.para('VBAT promedia 15 lecturas ADC de 12 bits con referencia de 3,0 V. R3 = 1 MΩ y R4 = 1,5 MΩ: el ADC recibe aproximadamente el 60 % de VBAT. VDD se mide aparte con el rango interno de 3,6 V.',
                   'VBAT averages fifteen 12-bit ADC readings with a 3.0 V reference. R3 = 1 MΩ and R4 = 1.5 MΩ: the ADC sees about 60% of VBAT. VDD is measured separately using the internal 3.6 V range.')
            c.para('El voltaje físico no depende del multiplicador ADC de la app. Por eso la protección y el porcentaje estimado pueden discrepar.',
                   'Physical voltage does not depend on the app’s ADC multiplier. Supply protection and estimated battery percentage can therefore disagree.')
            c.callout('UN PANEL SOLAR NO TIENE POR QUÉ PARECER USB','A SOLAR PANEL NEED NOT LOOK LIKE USB','El cargador puede cargar mientras el nodo muestra USB:0. Estas lecturas no miden corriente solar, capacidad ni energía almacenada.',
                      'The charger may charge while the node shows USB:0. These readings do not measure solar current, capacity or stored energy.')
            c.code('/telemetry PSVR\n/boot PSVR\n/apc status PSVR')
            c.para('Telemetría: VBAT actual/mínimo. Boot: primeras muestras. APC: estadísticas de una sesión activa. Cada consulta admite también el ID completo.',
                   'Telemetry: current/minimum VBAT. Boot: first samples. APC: active-session statistics. Each query also accepts the full node ID.')
        elif old == 22:
            c=chapter(old,'MANTENIMIENTO','MAINTENANCE','Lo que hace solo.\nY cómo actualizar.','What it does itself.\nAnd how to update.',
                      'Legion 0.7.2 usa la nightly 2.8.3.d0f4096. Las mejoras automáticas no requieren órdenes.','Legion 0.7.2 uses nightly 2.8.3.d0f4096. Automatic improvements need no commands.')
            c.table([('Mejora','Qué aporta'),('CC310','SHA/HMAC por hardware, con fallback. La nueva base acelera firmas XEdDSA y evita reinicializaciones costosas del RNG; conserva bloqueo de sesión y autoprueba.'),('SPI de radio','8 MHz y transferencias por bloques SPI/EasyDMA del nRF52.'),('Persistencia','Omite guardados idénticos; comprueba CRC32/tamaño; limpia temporales fallidos cuando la alimentación lo permite.'),('REG1 DC/DC','Activa el regulador eficiente tras inicializar SoftDevice y comprueba el estado.'),('Posición fija inválida','Con coordenadas 0,0 avisa tras 5 min y cada 12 h; cesa al corregirlas.'),('Cambios de la nightly','Valida el preset LoRa tras cargar canales y permite reiniciar transferencias XModem interrumpidas.')],
                    [('Improvement','What it provides'),('CC310','Hardware SHA/HMAC with fallback. The new base accelerates XEdDSA signing and avoids costly RNG reinitialization; session locking and self-test remain.'),('Radio SPI','8 MHz with nRF52 SPI/EasyDMA bulk transfers.'),('Persistence','Skips identical saves; checks CRC32/length; cleans failed temporary files when supply permits.'),('REG1 DC/DC','Enables the efficient regulator after SoftDevice initialization and checks its state.'),('Invalid fixed position','With 0,0 coordinates, warns after five minutes and every 12 hours; stops after correction.'),('Nightly changes','Validates the LoRa preset after loading channels and restarts interrupted XModem transfers.')],widths=[133,378],size=9.1)
            c.heading('Actualizar sin borrar','Update without erasing')
            c.para('Usa UF2 por USB u OTA ZIP con nRF Connect. Son paquetes de aplicación; no actualizan bootloader ni SoftDevice y conservan la reserva de rescate. Un cambio normal no exige factory reset. Conserva una copia externa de los ajustes.',
                   'Use UF2 over USB or the OTA ZIP with nRF Connect. These are application packages; they do not update the bootloader/SoftDevice and preserve the rescue reserve. A normal update does not require a factory reset. Keep an external settings export.')
            c.para('Tras arrancar consulta /telemetry PSVR, /components PSVR y /backup status PSVR respetando las pausas. El backup no se refresca solo. El armado permanente, si existe, restaura ambos modos con comprobaciones y un calentamiento nuevo.',
                   'After boot, query /telemetry PSVR, /components PSVR and /backup status PSVR with their cooldowns. The backup does not refresh itself. Saved permanent arming restores both modes with checks and a fresh warmup.')
            c.callout('PENDIENTE DE HW EN 0.7.2','PENDING HW IN 0.7.2','Base, firmas aceleradas y capacidades nuevas pendientes de pruebas en placa. Las funciones heredadas de 0.7.1 fueron probadas en HW. Consumo, autonomía y potencia RF real no medidos.',
                      'The base, accelerated signing and new capabilities await board tests. Inherited 0.7.1 functions were tested on HW. Consumption, battery life and actual RF output are unmeasured.')
        elif old == 23:
            c=chapter(old,'DAILY · AVISO Y CONSULTA','DAILY · REMINDER AND QUERY','Un corte al día.\nTambién a petición.','One cut a day.\nAlso on request.',
                      'El informe automático y /daily comparten el último corte cerrado de MeshHealth.','The automatic report and /daily share the latest closed MeshHealth cut.')
            c.para('LegionRF recibe DAILY cada 24 h desde el arranque, también con APC OFF. Reiniciar vuelve a contar. Prioridad de fondo, sin ACK, sin refrescar backup ni reiniciar capturas APC. Una ventana de 15 min permite un intento por minuto; no acumula atrasos.',
                   'LegionRF receives DAILY every 24 hours from boot, even with APC OFF. Reboot restarts the clock. Background priority, no ACK, no backup refresh or APC snapshot reset. A 15-minute window permits one attempt per minute; no backlog accumulates.',size=9.1)
            c.code('!abcdef01 DAILY\nAPC:ON NORMAL  SPAM:ON Q:0  BACKUP:UP TO DATE\nBAT:78% (-5pp) 4.01V (-60mV)\nMeshHealth 60/100\nHeard:258 Direct:18 2+ hops:59\nRelayed:120 Sources:54\nDM targets:5 Confirmed:3',size=8.5)
            c.para('BAT compara con el corte anterior en puntos porcentuales y mV; 24h:NA indica que falta referencia. MeshHealth compara Heard, Direct y Sources con la mediana de hasta 7 cortes completos comparables: pesos 40/25/35. Una referencia cero excluye esa métrica y reajusta el peso. Mide actividad LoRa observada, no cobertura garantizada.',
                   'BAT compares with the previous cut in percentage points and mV; 24h:NA means no reference. MeshHealth compares Heard, Direct and Sources against the median of up to seven comparable full cuts: weights 40/25/35. Zero references omit that metric and rescale the weight. It measures observed LoRa activity, not guaranteed coverage.',size=9)
            c.para('Heard cuenta orígenes; Direct, directos; 2+ hops, caminos mínimos observados de dos relays o más. Relayed son retransmisiones completadas; Sources, sus orígenes. DM targets y Confirmed cuentan destinos de textos locales y destinos con ACK explícito en el corte. Excluye MQTT. Hasta 768 nodos es exacto; después ~ marca estimaciones.',
                   'Heard counts origins; Direct direct origins; 2+ hops shortest observed paths of two or more relays. Relayed counts completed retransmissions; Sources their origins. DM targets and Confirmed count local text destinations and destinations with explicit ACKs in the cut. MQTT is excluded. Exact up to 768 nodes; then ~ marks estimates.',size=8.9)
            c.heading('Consultar el último corte cerrado','Read the last closed cut')
            c.code('/daily !abcdef01\n/daily PSVR\n!abcdef01 DAILY age:3600s\nMeshHealth 60/100\n...',size=8.8)
            c.para('Devuelve la parte MeshHealth y age en segundos desde el cierre; no una nueva lectura de batería. Antes de 24 h responde unavailable. NA: sin referencia; PARTIAL: corte incompleto/cambio de configuración; ~: estimación en datos o referencia. No crea cortes ni cambia el horario. El primer corte comparable suele ser NA.',
                   'Returns MeshHealth and age in seconds since closure, not a new battery reading. Before 24 hours it replies unavailable. NA: no reference; PARTIAL: incomplete cut/configuration change; ~: estimated data or reference. Does not create a cut or move the schedule. The first comparable cut normally shows NA.',size=8.9)
            c.para('Si DAILY automático supera 199 bytes usa 1/2 (APC, SPAM, BACKUP, BAT) y 2/2 (MeshHealth). Ambos son del mismo corte. El historial se reinicia al arrancar.',
                   'Automatic DAILY over 199 bytes uses 1/2 (APC, SPAM, BACKUP, BAT) and 2/2 (MeshHealth). Both share the cut. History restarts at boot.',size=8.8)
        elif old == 25:
            c=chapter(old,'SI ALGO NO CUADRA','TROUBLESHOOTING','Antes de invocar\nmás demonios…','Before summoning\nmore demons…',
                      'Comprueba la orden y conserva la respuesta literal.','Check the command and keep the exact reply.')
            c.table([('Me ocurre esto','Comprueba esto'),('No contesta.','LegionRF SECONDARY, PSK privada, LoRa compatible, comando en minúsculas, ID o nombre corto propio y pausa.'),('Hay varios con ese nombre.','Usa !nodeid. Un nombre de ejecutor repetido puede activar varios Legion.'),('El peer falta o es ambiguo.','Usa su ID. El nombre debe ser único en la NodeDB del ejecutor.'),('DAILY unavailable.','Todavía no ha cerrado el primer periodo de 24 h desde el arranque.'),('DAILY NA / PARTIAL / ~.','Sin referencia / corte incompleto o cambio / estimación. La consulta no genera otro corte.'),('APC vuelve OFF al reiniciar.','Es el valor por defecto. /arm permanent guarda ambos modos; /arm normal y /disarm borran la preferencia.'),('AUTOARM está saved pero APC OFF.','Un cambio individual o de ajustes puede apagarlo esta sesión. La preferencia sigue para el próximo arranque; deben cumplirse las comprobaciones.'),('queued, pero no se ve.','Solo se confirmó la cola local. Revisa canal, cobertura y tráfico.'),('Backup OUTDATED.','Hay diferencias; replace solo si quieres conservar el estado nuevo.'),('Mis ajustes vuelven tras factory reset.','Había rescate armado. Borra el punto y espera confirmación antes del reset.'),('El panel carga, pero USB es 0.','La carga solar externa puede no activar VBUS detectado.')],
                    [('What happens','Check this'),('No reply.','LegionRF SECONDARY, private PSK, compatible LoRa, lowercase command, full ID/own short name and cooldown.'),('Several nodes share a name.','Use !nodeid. A duplicate executor name can activate several Legions.'),('Peer missing or ambiguous.','Use its ID. The name must be unique in the executor’s NodeDB.'),('DAILY unavailable.','The first 24-hour period since boot has not closed yet.'),('DAILY NA / PARTIAL / ~.','No reference / incomplete cut or change / estimate. Querying does not create another cut.'),('APC OFF after restart.','Default behavior. /arm permanent saves both modes; normal /arm and /disarm clear the preference.'),('AUTOARM saved but APC OFF.','An individual or settings change can disable it this run. The preference remains for the next boot; checks must pass.'),('queued, but nothing appears.','Only local queuing was confirmed. Check channel, range and traffic.'),('Backup OUTDATED.','Settings differ; replace only to keep the new state.'),('Settings return after factory reset.','Rescue was armed. Delete the point and await confirmation before reset.'),('Solar charges, but USB is 0.','External solar charging may not trigger detected VBUS.')],widths=[173,338],size=8.6)
            c.para('Anota versión, orden y respuesta. Añade telemetry, boot, components e informe APC si estaba activo. zerohop usa captura de 15 min; trace unknown solo indica ausencia de respuesta en 90 s.',
                   'Record version, command and reply. Add telemetry, boot, components and APC status if active. zerohop uses a 15-minute snapshot; trace unknown only means no reply within 90 seconds.',size=9)
        elif old == 26:
            c=chapter(old,'CHULETA · CONSULTAR Y ACTUAR','CHEAT SHEET · QUERY AND ACT','Lo que más vas\na escribir.','What you will\ntype most often.',
                      'Sintaxis general: sustituye los marcadores por el ID o nombre corto real. No escribas |.','General syntax: replace placeholders with the actual ID or short name. Do not type |.')
            c.heading('Estado, posición y último DAILY','Status, position and last DAILY')
            c.code('/telemetry PSVR\n/boot PSVR\n/components PSVR\n/position PSVR\n/daily PSVR',size=9)
            c.heading('Mensajes, canales y reinicio','Messages, channels and restart')
            c.code('/msg PSVR SFNarrow Hola desde Legion\n/drakarys PSVR SFNarrow Hola desde Legion\n/listchannels PSVR\n/createch PSVR "Mi canal" PSK_BASE64\n/deletech PSVR "Mi canal"\n/reboot PSVR',
                   '/msg PSVR SFNarrow Hello from Legion\n/drakarys PSVR SFNarrow Hello from Legion\n/listchannels PSVR\n/createch PSVR "My channel" PSK_BASE64\n/deletech PSVR "My channel"\n/reboot PSVR',size=9)
            c.para('Drakarys envía a la máxima potencia disponible y 7 saltos: evalúa su legalidad en tu región y úsalo bajo tu responsabilidad. Detalles en la página 9.',
                   'Drakarys sends at maximum available power and seven hops: assess legality in your region and use it under your responsibility. Details on page 9.',size=9)
            c.heading('Vecinos, rutas e ignorados','Neighbours, routes and ignored nodes')
            c.code('/zerohop PSVR [página]\n/trace PSVR RLY1\n/ignore PSVR !12345678\n/unignore PSVR RLY1\n/ignorelist PSVR [página]',
                   '/zerohop PSVR [page]\n/trace PSVR RLY1\n/ignore PSVR !12345678\n/unignore PSVR RLY1\n/ignorelist PSVR [page]',size=9)
            c.para('El segundo nodo admite ID o nombre corto único en la NodeDB del ejecutor. No escribas los corchetes: la página es opcional. Nombres cortos con espacios, entre comillas. Antispam y nombres largos: página siguiente.',
                   'The second node accepts an ID or a short name unique in the executor’s NodeDB. Omit brackets: page is optional. Quote short names with spaces. Antispam and long names: next page.',size=9)
        elif old == 27:
            c=chapter(old,'CHULETA · RESCATE, APC Y ANTISPAM','CHEAT SHEET · RESCUE, APC AND ANTISPAM','Guardar, armar\ny volver.','Save, arm\nand return.',
                      'Elige ID o nombre corto real en cada orden; no escribas las barras ni los paréntesis.','Choose the actual ID or short name in each command; omit bars and parentheses.')
            c.heading('Punto de rescate','Rescue point')
            c.code('/backup PSVR\n/backup status PSVR\n/backup replace PSVR\n/backup delete PSVR',size=8.8)
            c.para('Crear si no existe; consultar; refrescar expresamente; borrar y desarmar rescate. Antes de factory reset en blanco, espera deleted; recovery disabled.',
                   'Create if absent; inspect; explicitly refresh; delete and disarm rescue. For a blank factory reset, wait for deleted; recovery disabled.',size=8.8)
            c.heading('APC S1+S2 y armado conjunto · CLIENT','APC S1+S2 and joint arming · CLIENT')
            c.code('/apc observe|shadow|on|off PSVR\n/apc status PSVR [1–7]\n/arm PSVR\n/arm permanent PSVR\n/disarm PSVR',size=8.8)
            c.para('Elige un solo modo, sin |. status abre primero página 1. permanent guarda el armado de ambos tras reinicio; /arm normal y /disarm borran la permanencia. Cada arranque reinicia sesión y calentamiento.',
                   'Choose one mode, without |. Open status page 1 first. permanent saves both modes across reboot; normal /arm and /disarm clear it. Every boot restarts session and warmup.',size=8.8)
            c.heading('Antispam, nombres largos y silencio','Antispam, long names and silence')
            c.code('/guard status|observe|on|off PSVR\n/guard clear PSVR RLY1\n/spamlist PSVR [página]\n/ignore name PSVR "Nombre largo"\n/unignorename PSVR "Nombre largo"\n/ignorelist names PSVR [página]\n/scramble PSVR',
                   '/guard status|observe|on|off PSVR\n/guard clear PSVR RLY1\n/spamlist PSVR [page]\n/ignore name PSVR "Long name"\n/unignorename PSVR "Long name"\n/ignorelist names PSVR [page]\n/scramble PSVR',size=8.8)
            c.callout('PAUSAS DE BOLSILLO','POCKET COOLDOWNS','Telemetry/backup: 60 s. Herramientas/APC/guard: al menos 6 s tras respuesta. Trace: 60 s entre inicios y hasta 90 s para el resultado. Envía una sola línea por mensaje.',
                      'Telemetry/backup: 60 s. Tools/APC/guard: six seconds after a reply. Trace: 60 seconds between starts, up to 90 seconds for a result. Send one line per message.')
        elif old == 28:
            c=chapter(old,'SOBRE ESTA EDICIÓN','ABOUT THIS EDITION','Muchos demonios.\nUn mismo manual.','Many demons.\nOne shared manual.',
                      'Ediciones española e inglesa con la misma organización.','Spanish and English editions share the same organization.')
            c.table([('Dato','Referencia'),('Manual','Edición 1.7 · 23 de noviembre de 2026.'),('Firmware','Legion 0.7.2 · 2.8.3.Legion0.7.2.'),('Base Meshtastic','Nightly 2.8.3.d0f4096 · commit d0f4096788545fb3c5e22d2a7e52ac6c268caac1.'),('Hardware','RAK3401 1W + RAK13302; batería y RAK19007.')],
                    [('Item','Reference'),('Manual','Edition 1.7 · 23 November 2026.'),('Firmware','Legion 0.7.2 · 2.8.3.Legion0.7.2.'),('Meshtastic base','Nightly 2.8.3.d0f4096 · commit d0f4096788545fb3c5e22d2a7e52ac6c268caac1.'),('Hardware','RAK3401 1W + RAK13302; battery and RAK19007.')],widths=[118,393],size=9)
            c.heading('Probado en HW / pendiente de HW','Tested on HW / pending HW')
            c.para('Javier confirmó las funciones de Legion 0.7.1 probadas en HW el 23/11/2026, incluidos comandos, DAILY, limpieza de temporales y aviso de posición fija. Esta observación pertenece a la versión anterior.',
                   'Javier confirmed Legion 0.7.1 functions tested on HW on 23 November 2026, including commands, DAILY, temporary cleanup and fixed-position warning. This observation belongs to the previous version.',size=9.2)
            c.para('Pendientes en 0.7.2: migración de base y firmas CC310, nombres cortos, /daily, /position, /listchannels, contadores SAVE, armado permanente y Drakarys. La compilación y pruebas de software no equivalen a pruebas físicas. Potencia RF, alcance y ahorro no medidos.',
                   'Pending in 0.7.2: base migration and CC310 signing, short names, /daily, /position, /listchannels, SAVE counters, permanent arming and Drakarys. Compilation and software tests are not physical tests. RF output, range and savings remain unmeasured.',size=9.2)
            c.heading('Proyecto y fuentes','Project and sources')
            c.para('Legion es el proyecto de Ethan (Javier), basado en Meshtastic y su comunidad; conserva GPL-3.0. Reconoce la inspiración de NavaTastic en resiliencia y de Nexus/Jentastic en comandos. Se conservan el logo y los demonios originales, con una ilustración nueva para Drakarys.',
                   'Legion is Ethan (Javier)’s project, based on Meshtastic and its community, retaining GPL-3.0. It acknowledges NavaTastic for resilience inspiration and Nexus/Jentastic for commands. The original logo and demons remain, with a new Drakarys illustration.',size=9.2)
            c.code('github.com/ethan1980/RAK3401-Legion\nCOMMANDS.md · APC.md · ANTISPAM.md\nRECOVERY.md · ENERGY-RECOVERY.md\nAUTOMATIC-FEATURES.md · CHANGELOG.md',size=8.6)
            c.para('Unleash your demons.','Unleash your demons.')
        else:
            copy_page(out,source,old,len(out)+1,lang)
        if old == 8:
            c=Chapter(out,source,old,len(out)+1,lang,T('ACTUAR · /drakarys','ACT · /drakarys'),
                      T('Drakarys.\nUn mensaje de fuego.','Drakarys.\nA message of fire.'),
                      T('Envía a la máxima potencia disponible y a 7 saltos.','Sends at the maximum available power and seven hops.'),new_art=True)
            c.code('/drakarys !abcdef01 SFNarrow Mensaje\n/drakarys PSVR SFNarrow Mensaje',
                   '/drakarys !abcdef01 SFNarrow Message\n/drakarys PSVR SFNarrow Message',size=9.2)
            c.para('Envía la orden por LegionRF. El nodo publica el texto por el canal indicado a la máxima potencia disponible y a 7 saltos. Puedes usar el ID o el nombre corto del ejecutor.',
                   'Send the command in LegionRF. The node publishes the text on the selected channel at the maximum available power and seven hops. Select the executor by ID or short name.')
            c.para('Es un envío puntual: después se usan los ajustes normales. No guarda otra configuración de potencia o saltos. Como en /msg, el canal debe estar habilitado, el nombre admite comillas y hasta 11 bytes UTF-8, y toda la orden debe caber en 199 bytes.',
                   'This is a one-off transmission: subsequent traffic uses normal settings. No different power or hop configuration is saved. As with /msg, the channel must be enabled, names can be quoted and use up to 11 UTF-8 bytes, and the entire command must fit 199 bytes.')
            c.heading('El grito, al completar la transmisión','The cry, after transmission completes')
            c.code('Dracarys! Pōntes valar! - Dracarys!, flame them all!',size=9.2)
            c.para('El aviso vuelve a LegionRF después de completar la transmisión local. No confirma entrega a todos los nodos ni usa la potencia especial del mensaje.',
                   'The notice returns to LegionRF after local transmission completes. It does not confirm delivery to all nodes and does not use the message’s special power.')
            c.callout('RESPONSABILIDAD DEL USUARIO','USER RESPONSIBILITY',
                      'Usar este comando bajo responsabilidad del usuario. Es el usuario el que debe evaluar si la máxima potencia disponible es legal en su región y si puede o no usar el comando.',
                      'Use this command under the user’s responsibility. The user must assess whether the maximum available power is legal in their region and whether they may use the command.')
            c.para('Funcionamiento pendiente de pruebas en HW en Legion 0.7.2.','Operation pending HW tests in Legion 0.7.2.',size=9)
    assert len(out)==29
    full='\n'.join(p.get_text() for p in out)
    for required in ('2.8.3.Legion0.7.2','/daily','/position','/listchannels','/arm permanent','SAVE C:','Pōntes valar!','d0f4096'):
        assert required in full, (lang,required)
    for stale in ('LEGIONFW · 0.7.1','Manual 1.5','2.8.3.Legion0.6.6','30 dBm','rc.2','rc2','arranca siempre','Every boot starts OFF'):
        assert stale not in full,(lang,stale)
    out.set_metadata({'title':T('Legion 0.7.2 · Manual endiabladamente amigable','Legion 0.7.2 · Devilishly friendly user manual'),
                      'author':'Ethan (Javier) · RAK3401 Legion','subject':'Legion 0.7.2 / manual 1.7',
                      'creationDate':'D:20261123000000Z','modDate':'D:20261123000000Z'})
    out.subset_fonts()
    target=ROOT/relative
    temp=target.with_suffix('.new.pdf')
    out.save(temp,garbage=4,deflate=True)
    out.close();source.close()
    temp.replace(target)
    print(f'Updated {relative}: 29 pages')


if __name__=='__main__':
    build('es')
    build('en')
