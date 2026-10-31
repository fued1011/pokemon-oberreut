# Oberreut – eigenständige Quellcode-Distribution

Dieses Repository enthält **nur den Oberreut-Overlay, eigene Generatoren/Tests und GIS-Quellen**. Es ist kein Fork und enthält weder Pokémon-Engine/Assets noch ROM, Save oder Referenzfotos. Der native GBA-Spielstand entsteht erst lokal durch Anwendung auf separat bezogenes [`rh-hideout/pokeemerald-expansion` 1.17.1](https://github.com/rh-hideout/pokeemerald-expansion), exakt Commit `bb1093a7c72d3961d9a37d8e02ad2abc2c866682`. Based off RHH's pokeemerald-expansion 1.17.1; die Upstream-Rechte bleiben unberührt.

## Installation (Linux)

Benötigt: `git`, `tar`, Bash, Python 3, `make`, ARM-GBA-Toolchain (`arm-none-eabi-gcc` und die übrigen im [Upstream-Setup](https://github.com/rh-hideout/pokeemerald-expansion/wiki/Getting-Started) genannten Build-Werkzeuge). Python-Pakete werden in **einer lokalen venv außerhalb des Repositorys** installiert:

```bash
python3 -m venv /pfad/zu/oberreut-venv
/pfad/zu/oberreut-venv/bin/python -m pip install -r tools/oberreut/requirements-phase1.txt
export PHASE1_PYTHON=/pfad/zu/oberreut-venv/bin/python
bash install.sh /pfad/zu/neuem-upstream-arbeitsverzeichnis
```

`install.sh DEST [LOCAL_UPSTREAM_GIT_REPO]` erstellt ausschließlich ein **noch nicht existierendes** Ziel: ohne zweiten Parameter klont es das getaggte Upstream-Repository, prüft den vollen Commit-Hash und extrahiert dessen Quellstand; mit zweitem Parameter verwendet es den angegebenen lokalen Git-Objektspeicher (`git archive` des gepinnten Commits). Der Overlay-Patch wird kontextgeprüft; die GIS-Generatoren prüfen SHA-256 von OSM-, Grenz- und Rasterquellen. Keine Dateien des Ursprungsprojekts werden überschrieben. Die temporäre Upstream-Kopie im Ziel wird entfernt. **Die generierten `map.bin`, `tiles.png`, Metatiles und Paletten liegen nur im separaten Build-Verzeichnis** und enthalten auch Upstream-Bytes; sie dürfen nicht zurück in dieses öffentliche Repository kopiert werden.

```bash
cd /pfad/zu/neuem-upstream-arbeitsverzeichnis
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 "$PHASE1_PYTHON" -m pytest tests_phase0 -q
make -j4
# Nur für persönliche lokale Tests: pokeemerald.gba im GBA-Emulator starten.
```

Bei einer vorhandenen Toolchain an anderem Ort `PATH` entsprechend setzen. `make` produziert ein ROM **nur im privaten Arbeitsverzeichnis**. Zum Entwickeln Generatoren unter `tools/oberreut/` und den textuellen `overlay.patch` aktualisieren; die Byte-Artefakte ausschließlich neu erzeugen. `install.sh` verweigert ein bestehendes Ziel, statt Änderungen zu überschreiben.

Vor einem Release `python3 verify_distribution.py` ausführen; es prüft die Git-Dateiliste auf ROMs, Grafiken und andere Build-Artefakte sowie GIS-Hashes und Patch-Umfang.

## Umfang / Stand

Die westliche und östliche Karte (je 64×64 Zellen) benutzen die native Emerald-Map- und Save-Engine; Startpunkt West `(30,28)` und wechselseitiger Übergang. Der 2-m-GIS-Raster ist kein Nachweis legal begehbarer Wege. Die Phase-1.3-Darstellung um Julius-Leber-Platz ist eine illustrative, nicht vermessene Architektur; Collision- und Höhenbits bleiben erhalten. Die `phase12.py`- und `phase13.py`-Zeichenregeln erzeugen die eigenen Motive und erweitern **erst bei der lokalen Installation** einen Petalburg-Atlas mit Upstream-Bits. `phase1_map.py` und `phase1b.py` erzeugen die vorherigen semantischen Rasterstufen. Die `tests_phase0` sind Struktur- und Generatorprüfungen; Emulator-Tests erfordern zusätzliche mGBA-Python-Bindings. Weder visuelle Erkennbarkeit noch reale Verkehrssicherheit sind damit belegt.

## Rechte / offene Punkte

Siehe [RECHTE.md](RECHTE.md). Das Roh-OSM-JSON ist unverändert, unter ODbL samt Herkunft/Attribution, die amtliche Stadtteilgrenze ist laut archivierten CKAN-Metadaten CC0. Eigenes Programmwerk im Overlay wird nur soweit rechtlich möglich unter GPL-3.0-or-later angeboten; der Patch ist **keine Neulizenzierung** von Upstream-Kontextzeilen. Die Distribution enthält keine Referenzbilder. Trotz dieses Zuschnitts ist eine rechtliche Einzelfallprüfung für öffentliche Nutzung, Marken, Datennachnutzung und Verbreitung selbst gebauter ROMs erforderlich. **ROMs nicht veröffentlichen.**

Die Build-Reproduzierbarkeit hängt zusätzlich von einer geeigneten GBA-Toolchain und Python-Distribution ab; die Python-Versionen sind gepinnt, native Compiler und Upstream-Buildwerkzeuge nicht in diesem Repository vendort. Upstream-Tag/Commit und GIS-Eingangsdateien sind gepinnt. Ein unabhängiger nativer Build und mGBA-/Save-Regressionen wurden ausgeführt; siehe [Wiederherstellung](docs/RESTORATION.md) und [Phase 1.3](docs/PHASE13.md). Eine rechtliche Fachprüfung ist davon unabhängig.

## Entwicklungsworkflow und Wiederherstellung

Siehe [DEVELOPMENT.md](docs/DEVELOPMENT.md) für Make-Ziele, sicheren Rückexport,
Emulator-Tests und die Trennung zwischen öffentlicher Distribution und privatem
Engine-Baum. `distribution.json` ist die gemeinsame Dateiliste für Installation
und Export. `scripts/capture_provenance.py ENGINE OUTPUT.json` protokolliert die
Hashes privater Build-Ergebnisse, ohne deren Inhalte zu veröffentlichen.
