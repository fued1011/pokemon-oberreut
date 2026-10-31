# Phase 1.3 – Julius-Leber-Platz

Die Wiederherstellung der öffentlichen Baseline und ihre echten mGBA-Tests
wurden vor den Änderungen abgeschlossen. `phase12.py` bleibt als reproduzierbare
Vorher-Stufe erhalten. `phase13.py` setzt darauf auf; die Installation verwendet
nun dessen Ergebnisse. Native Engine und Integrationspatch bleiben unverändert.

## Sichtbare Änderungen

- Hell verputzte Fassaden behalten ihre Lage, Fenster und Balkone erhalten
  deutlichere Glas-/Rahmen-/Geländerkontraste; der Sockel wird zusammenhängender.
- Dunkle, horizontal durchlaufende Dachflächen ersetzen die wiederholten
  schrägen Texturstreifen. Giebelmodule bleiben gestalterische Interpretation.
- Betonpflaster erhält feinere Fugen, dunkle Inlays und Randsteine entlang der
  vorhandenen Platzmaske. Grünflächen verwenden sparsamer verteilte Halme.
- Sechs bestehende symbolische Baumbeete erhalten aus vier Metatiles aufgebaute
  Kronen mit runden Beetkanten. Alle Zellen liegen im bisherigen grünen Raster.
- Die beiden archivierten OSM-Gleislinien bestimmen die zwei Gleisspalten; der
  Zwischenbereich zeigt Schotter. Die frühere dritte Gleistextur entfällt.
- OSM-Bahnsteiglinien werden auf ihre vorhandenen 2-m-Zellen projiziert, mit
  heller Tastkante zum Gleis. Ein illustratives H-Schild macht den Halt lesbar.
- Gehwegzellen an Straßen bekommen seitliche Bordsteine. Kein neuer Durchgang,
  kein neuer Übergang und keine Änderung von Höhen-/Kollisionsbits.

## Quellen und Genauigkeit

| Element | Grundlage | Einordnung |
| --- | --- | --- |
| Platzumriss | unverändertes OSM, Way 4940191 | geografisch übernommen, Rastervereinfachung bleibt |
| Gebäudegrundrisse | bestehende Phase-1.1b-Maske | vollständig unverändert |
| Gleisverlauf | OSM Ways 138293860, 138293880 | auf Rasterzellen projiziert |
| Bahnsteiglage | OSM Ways 35995211, 35995212 | Linienlage belegt; dargestellte Breite angenähert |
| Rundbeete, helle Fassaden, dunkle Pflasterbänder | [Stadtlexikon und Ortsfoto von 2014](https://stadtlexikon.karlsruhe.de/index.php/De:Lexikon:top-1414) | visuelle Referenz; keine Foto-Bytes übernommen |
| Baumzahl/-größe, Fassadenmodule, Inlay-Positionen, H-Schild | eigener Zeichencode | künstlerische Interpretation, nicht vermessen |

Das Stadtlexikon beschreibt zwölf Rosskastanien in Rundbeeten. Die sechs
symbolischen Gruppen des bestehenden Rasters bilden diese Zahl **nicht** exakt
ab. Eine Ergänzung weiterer Beete ohne gesicherte Einzelpositionen wurde nicht
vorgenommen. OSM-Grundklasse 1 ist nicht überall ein Nachweis realer Vegetation.
Die aktuellen Kollisionsregeln sind Spielregeln, keine Bestätigung sicherer
realer Gleisquerungen. Die Stadt berichtete am 16.10.2026, dass die geplante
[Umgestaltung des Platzes nicht umgesetzt wurde](https://www.karlsruhe.de/stadt-rathaus/aktuelles/meldungen/entwicklung-in-oberreut);
es wurden deshalb keine geplanten Neubauten als Bestand dargestellt.

## Ausgeführte Qualitätssicherung

- 23 pytest-Tests bestanden in einer frischen Installation (8,12 s).
- Vier neue Tests prüfen alle Kollisionsbits, Gebäudezellen, Kartenränder,
  Ostkarte, beide Gleise, geometrische Bahnsteigzuordnung, vollständige
  Generator-Reproduzierbarkeit, installierte Assets und Hardwaregrenzen.
- ROM gebaut: EWRAM 226420 Bytes, IWRAM 28380 Bytes, ROM-Linkbereich
  26750444 Bytes. Das sind lediglich 896 zusätzliche ROM-Bytes zur Baseline.
- Sekundäratlas: 384 von 512 Hardware-Tiles, 195 Sekundär-Metatiles;
  16 Farben, Palette 6; originale Stock-Tiles/Metatile-Präfixe bleiben erhalten.
- Frischinstallation: alle 22 Phase-1.3-Ergebnisdateien bytegleich mit dem
  Entwicklungsbaum. Alle GIS-Masterdateien unverändert.
- mGBA 0.10.5: New Game, Bewegung, Gebäudekollision, West → Ost,
  Speichern auf beiden Karten und Laden jeweils in einem neuen Prozess,
  Ost → West tatsächlich ausgeführt und bestanden.
- Tages-/Nachtaufnahme sowie Dachkamera bestanden. Zusätzlich vier Kameras
  zu gleicher Tageszeit auf Baseline und Phase 1.3 per Tasten erreicht:
  Platz `(30,28)`, Fassade `(30,17)`, Tram `(44,24)`, Süden `(38,36)`.
- Porymap-relevante Layout-, Tileset- und Map-Verknüpfungen automatisch geprüft;
  kein manueller Porymap-GUI-Test. CI-Konfiguration hinzugefügt, ein GitHub-Run
  wird erst nach Veröffentlichung ausgeführt und ist hier nicht als bestanden
  gezählt.

## Private Ergebnisse und Vorher/Nachher

Private ROM: `/home/fuchs/oberreut-private/phase13/pokeemerald.gba`.
Baseline: `/home/fuchs/oberreut-private/phase12b/pokeemerald.gba`.
Unveränderte echte Emulatorbilder liegen jeweils unter `logs/`:

| Bildname | Vergleich |
| --- | --- |
| `slice-plaza-day.png` | große Fugen → feineres Pflaster mit Inlays |
| `slice-facade-day.png` | repetitive Grünpunkte → ruhiges Grün, größere Kronen |
| `slice-tram-day.png` | drei Gleistexturen → zwei Gleise und erkennbare Bahnsteige |
| `slice-south-day.png` | Beet-/Platzkante im südlichen Bereich |
| `phase12c-roof-day.png` | Baseline-Dateiname beibehalten; Dachflächenvergleich |
| `phase12c-building-night.png` | Lesbarkeit bei Nacht |

`scripts/capture_provenance.py` erfasst private Ergebnis- und Screenshot-Hashes
in `phase13-provenance.json`. Die Bilder und ROMs selbst bleiben außerhalb von Git.

## Verbleibende Grenzen

Die alte lokale ROM ist nicht vorhanden; Gleichheit mit dem historischen Commit
`f088918c` bleibt unbeweisbar. Die heutige öffentliche Baseline ist dagegen
zweimal bytegleich gebaut. Die Grenze des begrenzten Grafikbereichs bleibt
sichtbar, insbesondere westlich/nördlich der Fassade; eine Erweiterung über den
vereinbarten Ausschnitt wurde vermieden. Nicht vermessene Fassadendetails,
Baumbeete und Bahnsteigbreiten bleiben dokumentierte Annäherungen. Der Abschnitt
ist ein spielbarer Vertical-Slice auf der nativen Engine, kein fertiges
vollständiges Oberreut-Abenteuer mit Handlung und allen Stadtteilkarten.

## Abschließender sauberer Build

Auch `/home/fuchs/oberreut-private/phase13-clean` wurde ohne übernommene
Build-Artefakte vollständig kompiliert. Entwicklungs-ROM und frische ROM sind
bytegleich, SHA-256:
`b99002d5120fd3e2970f03d99c227a2e3be93c380706c13da9b62135056f3e29`.

Der kontrollierte Export verweigerte in separat ausgeführten Negativprüfungen
sowohl veränderte GIS-Masterdaten als auch ein bereits bestehendes Ausgabeziel,
ohne dort Dateien zu schreiben.
