# Wiederherstellung am 31.10.2026

Ausgang: öffentlicher Commit `f8716a5fda3c237d432c5e26c18f2061c9a5aa7c`.
Der vorhandene saubere Klon wurde mit origin abgeglichen; Arbeitsbranch
`codex/restore-phase12b`. `/home/kevin/oberreut-gba-phase0` ist auf diesem Rechner
nicht vorhanden. Die Suche unter `/home/fuchs` und `/opt` bis Tiefe 4 ergab keinen
weiteren Oberreut-Baum und kein passendes Git-Bundle. Der historische Commit
`f088918c`, frühere ROMs und Referenzscreenshots standen nicht zur Verfügung.
Eine Byte-/Bildgleichheit mit jener historischen ROM ist deshalb **nicht belegt**.

## Tatsächlich wiederhergestellt

Unveränderte Engine 1.17.1, Commit `bb1093a7c72d3961d9a37d8e02ad2abc2c866682`,
mit dem öffentlichen Overlay in `/home/fuchs/oberreut-private/phase12b` installiert.
Alle Generatoren erfolgreich ausgeführt, native ROM gebaut. Ein zweiter frischer
Installationsbaum `reproduce` erzeugte 46 verglichene Karten-, Tileset- und
Phase-1.2-Ergebnisdateien bytegleich. Hashes stehen in `phase12b-provenance.json`.
Die Distribution enthält bereits den zusätzlichen Dachtest
`test_northern_roof_ridge_and_plane_use_only_existing_building_cells` und ein
Skript mit `phase12c`-Bildnamen; diese wurden als vorhandene Baseline übernommen.

## Ausgeführte Prüfungen

- Vorhandene pytest-Suite: **19 bestanden**, 4,95 s; nicht 21 wie in der Übergabe.
- Nativer Build: EWRAM 226420 / 262144 Bytes; IWRAM 28380 / 32768;
  ROM-Linkbereich 26749548 / 33554432 Bytes. ROM wird auf 32 MiB aufgefüllt.
- mGBA 0.10.5, offizieller Kern und CFFI-Bindings, headless:
  neues Spiel West `(30,28)`, Bewegung rechts bis `(32,28)`;
  Flash-Save 131072 Bytes; frischer Prozess lädt diesen Stand;
  erneute Bewegung und Gebäudekollision stoppen bei West `(30,17)`.
- West → Ost erreicht `(0,27)`; dort gespeichert; frischer Prozess lädt Ost;
  Rückweg erreicht West `(55,27)`. Rückwegprüfung wurde explizit ergänzt.
- Tages-/Nacht-Framebuffer bei fester Emulator-RTC 12/1 Uhr erzeugt;
  Tages-Dachkamera bei `(19,14)` erreicht. Keine RAM-Teleportation oder Bildfilter.
- Native Layout-/Tileset-Verknüpfungen für Porymap automatisch geprüft.
  Ein manueller Porymap-GUI-Test wurde noch nicht durchgeführt.
- Distributionsprüfung bestanden. Export-Rundlauf reproduziert alle acht
  gepatchten Engine-Dateien exakt. GIS-Master unverändert.

Echte Screenshots bleiben privat unter `phase12b/logs/` (u. a.
`phase12c-building-day.png`, `phase12c-roof-day.png`, `phase12c-building-night.png`,
`phase1-mgba-east.png`, `phase1-return-west.png`). Die Testlogs liegen im privaten
Elternverzeichnis. Es wurden keine fremden Bild-/ROM-Dateien in Git aufgenommen.

## Lokale Werkzeuge

Python 3.14, Pakete gemäß requirements-phase1.txt; ARM GCC 16.2.0,
Binutils 2.47, Newlib 4.6.0.20260123, GNU Make. ARM-Pakete wurden ohne root aus dem
konfigurierten Arch/Omarchy-Mirror nach `oberreut-private/toolchain` entpackt.
`PATH=/home/fuchs/oberreut-private/toolchain/usr/bin:$PATH make -j8`.

mGBA-Quellcommit `26b7884bc25a5933960f3cdcd98bac1ae14d42e2` (Tag 0.10.5):
CMake mit `BUILD_QT=OFF`, `BUILD_SDL=OFF`, `BUILD_PYTHON=ON`, `USE_FFMPEG=ON`,
`USE_LUA=OFF`, `CMAKE_POLICY_VERSION_MINIMUM=3.5`,
`PYTHON_EXECUTABLE=/home/fuchs/oberreut-private/venv/bin/python` und
`CMAKE_C_FLAGS=-Wno-error=incompatible-pointer-types` gebaut. Dasselbe CFLAGS
beim Build setzen. Hintergrund: ältere CFFI-va_list-Deklaration wird von GCC 16
als Fehler behandelt. FFmpeg bleibt aktiviert, da die Bindings eReader-Symbole
referenzieren. Keine Änderungen am Emulator-Quellcode oder der Engine nötig.
Für Tests `PYTHONPATH=/home/fuchs/oberreut-private/mgba-build/python/lib.linux-x86_64-cpython-314`
setzen. Diese Build-Schritte sind systemabhängig, kein plattformübergreifender
Toolchain-Lock.
