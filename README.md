# RAK3401 Legion

Firmware experimental para el **RAK3401 1W con RAK13302**, basado en Meshtastic.
Primera versión: **Legion 0.1.0**, sobre la base **2.8.2 de develop/nightly**,
commit [`04cb888`](https://github.com/meshtastic/firmware/commit/04cb8885118b959a9f538cd5881bd7d595758911).
Es una base de código concreta de 2.8.2, no el binario de una nightly oficial publicada.

El repositorio contiene una capa pequeña de parches y un perfil de compilación.
La compilación descarga el código oficial fijado en `upstream.json`, aplica los
cambios y genera el firmware completo. Esto permite revisar los cambios propios
y trasladarlos a nuevas versiones de Meshtastic.

## Cambio incluido

Legion transfiere los buffers de RadioLib al SX1262 por bloques mediante la API
SPI síncrona del core nRF52, que utiliza EasyDMA. La base envía esos buffers byte
a byte. Se conserva la frecuencia SPI de **4 MHz**, el bloqueo del bus y los límites
de cada transacción. La optimización se activa únicamente en `rak3401-legion`.

Esto busca reducir la sobrecarga de CPU durante las transferencias. **El ahorro de
batería y la estabilidad en el equipo todavía no están medidos.** En recepción
continua, el consumo del frontal RF seguirá siendo una parte importante del total.

Se conservan las correcciones de AGC y recuperación de radio de la base elegida.
No se cambian potencia TX, región, canales, rol, Bluetooth, tiempos de escucha ni
valores predeterminados de la configuración. No se implementa bypass del LNA.
El perfil hereda los pines y la identificación RAK3401 del firmware oficial.

## Descargar la compilación

En [Actions](https://github.com/ethan1980/RAK3401-Legion/actions/workflows/build.yml),
abre una ejecución terminada correctamente y descarga sus artefactos:

| Artefacto | Perfil | Uso |
| --- | --- | --- |
| `RAK3401-legion-…` | `rak3401-legion` | SPI por bloques habilitado |
| `RAK3401-baseline-…` | `rak3401-1watt` | Referencia con el comportamiento original |

Cada paquete contiene el **UF2**, el **ZIP DFU**, ELF, HEX, metadatos,
`SHA256SUMS` y un archivo con las fuentes usadas. El ZIP del artefacto de Actions
contiene otro ZIP, que es el paquete DFU. Los artefactos se conservan 30 días.

Esta versión necesita pruebas en hardware antes de usarse en un nodo desatendido.
El nombre del archivo y el perfil distinguen Legion; la versión mostrada por la
aplicación conserva la versión y el commit de Meshtastic (`2.8.2.04cb888`).

## Compilar localmente

Requisitos: Git y Python 3.12, con acceso a las dependencias de PlatformIO.

```bash
git clone https://github.com/ethan1980/RAK3401-Legion.git
cd RAK3401-Legion
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/build.py --target legion
python scripts/build.py --target baseline
```

Los paquetes quedan en `dist/legion` y `dist/baseline`. Las fuentes preparadas
quedan en `.work/firmware`. Los scripts preparan y compilan; no flashean un equipo.
La preparación se puede repetir y rechaza una base distinta o cambios locales.
Para usar un destino alternativo: `python scripts/build.py --dest /ruta/nueva`.

## Comprobar en el RAK

Comparar referencia y Legion con la misma batería, configuración, tráfico y
condiciones RF. Comprobar arranque, Bluetooth, lectura de configuración, mensajes
en ambas direcciones, ACK, retransmisiones y recepción durante varias horas.
Medir corriente en reposo RX y energía por mensajes enviados y recibidos con un
medidor externo. El porcentaje de batería por sí solo no demuestra un ahorro.

## Actualizar la base

Cambiar el commit completo y la versión en `upstream.json` y preparar un destino
nuevo. Revisar las correcciones upstream, las APIs de RadioLib y del core nRF52,
la aplicabilidad del parche y la compilación de ambos perfiles. Repetir las pruebas
de hardware; que el parche se aplique no demuestra compatibilidad funcional.

## Licencia y procedencia

Meshtastic procede de [meshtastic/firmware](https://github.com/meshtastic/firmware).
Se conserva su licencia **GPL-3.0** en `LICENSE`, también aplicable a los cambios
Legion. Las dependencias conservan sus licencias propias y sus referencias de
origen en la configuración de PlatformIO de la base.
