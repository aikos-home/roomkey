# RoomKey

**Eine Taste für jedes Zimmer: ein kleiner Touchscreen auf einem mechanischen Tastatur-Schalter,
eingesetzt in einen ganz normalen deutschen Lichtschalter-Rahmen. Klingel, Gegensprechanlage,
Alarmanlage und Licht, einen Tastendruck entfernt. Gebaut mit ESP32-C6, ESPHome und Home Assistant.**

[English](README.md)

> Stand: Prototyp. Die Firmware läuft auf einem nackten Entwicklungsboard auf dem Schreibtisch,
> das Mikrofon ist verifiziert, die übrigen Teile sind bestellt. Noch ist nichts in einer Wand
> verbaut. Stand dieser Seite: 29. September 2026.

<p align="center">
  <img src="docs/north-star.jpg" width="360" alt="KI-generiertes Konzeptbild: weißer Lichtschalter-Rahmen, in der Mitte eine hochkant stehende Touchscreen-Taste, Lautsprecher- und Mikrofonlöcher in den weißen Seitenflächen, warmes Leuchten um die Taste">
  <br><em>Zieldesign – ein KI-generiertes Konzeptbild (Google Gemini), kein Foto eines gebauten Geräts.</em>
</p>

## Was es ist

- **Zuerst ein Lichtschalter.** Die weiße Wippe um die Taste schaltet weiterhin das Zimmerlicht,
  ganz ohne Software – also auch ohne WLAN, ohne Home Assistant und selbst dann, wenn der ESP32
  abgestürzt ist.
- **Eine Taste mit Bildschirm.** Ein 1,47″-Touch-Display auf einem mechanischen Tastatur-Schalter.
  **Drücken** macht das Naheliegende, **Halten** das Bewusste, und der Bildschirm sagt immer,
  was was ist. Tippen und Wischen für den Rest.
- **Die Klingel in jedem Schlafzimmer.** Es klingelt, der Bildschirm zeigt es an, abgenommen wird
  mit der Taste: halten zum Sprechen, loslassen zum Hören.
- **Die Alarmanlage im Zimmer.** Nachts scharf geschaltet? Taste 1,5 s halten zum
  Entschärfen – Home Assistant entscheidet, ob dieses Zimmer das darf.
- **Lokal und standardkonform.** ESPHome-API: Home Assistant findet das Gerät automatisch, mit
  ganz normalen Entitäten, Ereignissen und Aktionen. Keine Cloud, keine eigene Integration.

RoomKey ist das Gegenstück im Haus zur [Klingelbox](https://github.com/martinkadauke/intercom),
der Open-Hardware-Türsprechanlage.

## Stand

| Bereich | Stand |
|---|---|
| Oberfläche und Bedienlogik (Licht, Alarm, Klingel, Gespräch, Menü, Info) | ✅ läuft auf dem Board, geprüft im Simulator und auf der Hardware |
| Home-Assistant-Schnittstelle | ✅ **11/11** End-to-End-Prüfungen gegen ein simuliertes Home Assistant |
| Demo-Modus (alles funktioniert ohne Home Assistant) | ✅ ab Werk an |
| Mikrofon (INMP441) | ✅ **auf der Hardware verifiziert** – Testton +30 dB, Sprache +18 dB über dem Raumpegel; 120-Hz-Hochpass gegen Trittschall und Kabelgeräusche |
| Gegensprechen (RTP/L16 16 kHz, Push-to-Talk) | 🟡 **in Arbeit** – funktioniert Simulator ⇄ simulierte Tür; auf der Hardware noch nicht getestet |
| Sicherheit Gegensprechen | ✅ eingehendes Audio nur während eines Gesprächs, alles andere wird ungehört verworfen |
| Lautsprecher und Klingelton (MAX98357A + Waveshare-2030-Lautsprecher) | 🟡 **in Arbeit** – kompiliert, Teile bestellt |
| Touch-Board (Tippen / Wischen) | 🟡 **in Arbeit** – vom Zieldesign vorausgesetzt, 1× bestellt, nur im Simulator getestet |
| Zusatzsensoren: VEML7700 Licht, SHT31-D Klima, LD2410C mmWave-Präsenz | 🟡 gekauft; Licht + Klima am gemeinsamen I²C-Bus (keine zusätzlichen Pins), Radar an einem Pin – Platz für das Radar hinter der Wippe noch offen |
| Gehäuse / Wandeinsatz | 🟡 Passungsmodell + Toleranz-Probekörper fertig ([hardware/](hardware/)); Tisch-Prüfstand (v0) → Wandmaß (v1) als Nächstes |

![Alle Bildschirme, vom Desktop-Simulator aus demselben Code erzeugt, der auf dem Board läuft](docs/screens/contact_sheet.png)

## Bedienung

| Bildschirm | Tippen | Wischen ↑ | Wischen ↓ | Taste drücken | Taste halten |
|---|---|---|---|---|---|
| Start | weckt, zeigt einen Hinweis – nie eine Aktion | Menü | – | alle Lichter | Menü · **entschärfen**, wenn scharf |
| Es klingelt | abnehmen | – | hier stummschalten | abnehmen (beim Herunterdrücken) | abnehmen + sprechen |
| Gespräch | Kreis halten = sprechen | – | auflegen | auflegen | Push-to-Talk |
| Menü | wählen | – | schließen | weiter | wählen |
| Alarm | – | – | – | Hinweis | **entschärfen** (1,5 s) |
| **Weiße Wippe** | schaltet das Zimmerlicht, ohne Software | | | | |

- Tippen schaltet auf dem Startbildschirm nie etwas: Die Wippe liegt um die Taste herum, Finger
  streifen den Bildschirm ständig.
- Ein mechanischer Tastendruck beginnt immer als Berührung; das Herunterdrücken bricht diese
  Berührung ab, ein Druck löst also nie zweimal aus.
- Die Taste funktioniert auch bei dunklem Bildschirm – im Dunkeln einfach draufdrücken.

## Hardware

Der Tisch-Prototyp läuft auf einem **Waveshare ESP32-C6-LCD-1.47** (ohne Touch). Ziel ist das
**ESP32-C6-Touch-LCD-1.47** – derselbe Chip mit Touch-Schicht, aber andere Größe und
Pinbelegung; die Firmware wechselt mit einer Zeile. Verkabelung, Maße und Home-Assistant-Details
stehen in der [englischen README](README.md#hardware).

## Datenschutz

- Das Mikrofon läuft nur, während im Gespräch die Taste gehalten wird, oder während der
  Bildschirm *Rauminfo* seinen Pegel anzeigt. Sonst wird nichts aufgenommen oder gesendet.
- Eingehendes Audio wird nur während eines Gesprächs angenommen. RoomKeys gehören wie die
  Türgeräte ins IoT-VLAN.

## Sicherheit

- Alles an 230 V – das Netzteil in der Dose, das Relais für das Zimmerlicht – ist Sache einer
  Elektrofachkraft. Der Tisch-Prototyp läuft nur über USB.
- In vielen älteren Schalterdosen fehlt der Neutralleiter; das vor jeder Netzteil-Planung prüfen.

## Lizenzen

- Code (Firmware, Skripte): [MIT](LICENSE), außer dem AXS5106L-Touchtreiber in
  `esphome/components/axs5106l/`, der seine eigene [MIT-Lizenz](LICENSES/MIT-axs5106l-Olivier-Latignies.txt) behält
- Icon-Schrift (Material Design Icons): [Pictogrammers Free License](LICENSES/MDI-Pictogrammers-Free-License.txt)
- Hardware-Entwürfe (CAD-Skripte, STL, STEP): [CERN-OHL-P-2.0](LICENSES/CERN-OHL-P-2.0.txt)
- Dokumentation und Bilder: [CC BY 4.0](LICENSES/CC-BY-4.0.txt)

Entworfen und geschrieben mit [Claude Code](https://claude.com/claude-code).
