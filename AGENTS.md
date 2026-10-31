# Pokémon Oberreut – Projektregeln

## Projektziel

- Entwickle ein vollständiges, natives Pokémon-GBA-Spiel mit geografisch wiedererkennbarem Karlsruhe-Oberreut.
- Erhalte die bestehende `pokeemerald-expansion`-Engine, ihre nativen Systeme und die vorhandenen GIS-Masterdaten.
- Verwende `docs/DEVELOPMENT.md` als technische Referenz für Installation, Entwicklung, Tests und Rückführung.

## Effiziente Entwicklung

- Setze ausschließlich den beauftragten Umfang um; ergänze keine ungefragten Features.
- Untersuche nur Dateien, Generatoren und Tests, die für die konkrete Änderung relevant sind.
- Verwende vorhandene Arbeitsverzeichnisse, Abhängigkeiten und die lokale Toolchain erneut.
- Installiere oder klone nichts neu, solange die vorhandene Umgebung funktioniert.
- Vermeide vollständige Clean-Builds; baue inkrementell, sofern das Änderungsrisiko keinen Clean-Build verlangt.
- Wähle Tests risikobasiert: zuerst gezielte Struktur-, Generator- oder Laufzeittests für die betroffene Funktion.
- Wiederhole keine vollständigen Reproduzierbarkeitsprüfungen ohne Änderung am Build- oder Installationsprozess.

## Trennung und Veröffentlichung

- Das Git-Repository ist die öffentliche Overlay-Distribution; der separate Engine-Baum bleibt privat.
- Halte eigene Textquellen, Tests und den Integrationsstand zwischen Distribution und privater Engine synchron.
- Veröffentliche keine ROMs, Saves, generierten Grafiken, fremden Pokémon-Assets oder Upstream-Binärdateien.
- Verändere GIS-Masterdaten, Kartenkollisionen oder Engine-Versionen nur bei ausdrücklichem Auftrag.

## Abschluss

- Committe logisch getrennte Änderungen nachvollziehbar auf Feature-Branches.
- Berichte kurz über geänderte Dateien, ausgeführte Tests, Commit-Hashes und konkrete offene Punkte.
