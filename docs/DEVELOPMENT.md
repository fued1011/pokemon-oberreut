# Entwicklung ohne Verlust des Overlays

Die öffentliche Distribution ist die Quelle; der separate Engine-Baum ist privat.
`distribution.json` listet eigene Textdateien, unveränderliche GIS-Dateien und
zulässige Patch-Ziele auf. Neue eigene Dateien ausdrücklich dort eintragen.
Engine 1.17.1 bleibt auf `bb1093a7c72d3961d9a37d8e02ad2abc2c866682` gepinnt.

## Frische Installation

Python 3 mit den Paketen aus `tools/oberreut/requirements-phase1.txt`, Git, Bash,
GNU Make, C/C++-Compiler, libpng-Entwicklungsdateien sowie ARM GCC, Binutils und
Newlib werden benötigt. Die native Engine benötigt keinen Browser.

```sh
python3 -m venv ../oberreut-venv
../oberreut-venv/bin/pip install -r tools/oberreut/requirements-phase1.txt
export PHASE1_PYTHON="$(realpath ../oberreut-venv/bin/python)"
make install PYTHON="$PHASE1_PYTHON" ENGINE="$(realpath ..)/oberreut-engine"
make test PYTHON="$PHASE1_PYTHON" ENGINE="$(realpath ..)/oberreut-engine"
make build ENGINE="$(realpath ..)/oberreut-engine" JOBS=8
```

Ein zweiter lokaler Upstream-Gitbaum kann als `UPSTREAM=/absoluter/pfad` angegeben
werden. Er muss den gepinnten Commit enthalten; seine Arbeitskopie wird nicht
verändert. `install.sh` überschreibt kein vorhandenes Ziel.

## Änderungen und Rückführung

1. Feature-Branch im öffentlichen Repository anlegen; eigene Generatoren und Tests
   bevorzugt hier editieren und die geänderten Textdateien in den privaten Baum
   kopieren. Änderungen dort nicht versehentlich durch eine Kopie überschreiben.
2. `make regenerate PYTHON="$PHASE1_PYTHON" ENGINE=/privater/baum` erzeugt Karten,
   Grafiken und Paletten aus den Generatoren **im privaten Baum** neu.
3. `make test`, `make build` und die unten beschriebenen Laufzeittests ausführen.
4. Bei Änderungen direkt im Engine-Baum:
   `make export ENGINE=/privater/baum UPSTREAM=/upstream/git EXPORT=/neuer/export`.
   Dies schreibt ausschließlich eigene Textquellen und einen neuen `overlay.patch`
   in einen neuen Ordner. GIS-Änderungen werden zurückgewiesen. Neue Dateien und
   Änderungen außerhalb der Allowlist müssen ausdrücklich geprüft/registriert
   werden; der Export behauptet nicht, diese automatisch zu erfassen.
5. Export mit dem Repository vergleichen, die beabsichtigten Änderungen übernehmen
   und `git diff` prüfen. Niemals den gesamten privaten Baum zurückkopieren.
6. Eine frische Installation aus der Distribution testen. Erst dann committen und
   den Feature-Branch veröffentlichen. Alte Stände bleiben durch Commits erhalten.

`verify_distribution.py` prüft versionierte Dateien, GIS-Hashes und Patch-Ziele.
Vor dem Commit die gewünschten Textdateien gezielt stagen und erneut prüfen;
ungeprüftes `git add .` im Engine-Baum vermeiden. ROMs, Screenshots mit Upstream-
Grafiken, Saves, Paletten und generierte Binärdaten bleiben privat.

## Echte Emulator-Regression

Die Skripte benutzen den offiziellen mGBA-Kern mit Python-CFFI-Bindings, echte
ROM-Ausführung und simulierte Tasten. Screenshots stammen unverändert aus dessen
240×160-Framebuffer. Flash-Saves liegen in temporären Verzeichnissen; Laden
startet einen neuen Prozess. Es werden keine Spielkoordinaten in RAM geschrieben.

```sh
cd /privater/engine-baum
python tests_phase0/runtime_mgba.py
python tests_phase0/runtime_phase1.py
python tests_phase0/runtime_phase12_visual.py 12
python tests_phase0/runtime_phase12_visual.py 1
```

Dafür die Python-Umgebung mit mGBA verwenden; gegebenenfalls `PYTHONPATH` auf dessen
gebautes Python-Verzeichnis setzen. Der zweite Test prüft beide Kartenrichtungen.
`logs/` wird automatisch erstellt. Das grafische mGBA-Fenster ist für diese
headless ausgeführten Funktionstests nicht erforderlich. Porymap-Strukturtests
ersetzen keinen manuellen Editortest.
