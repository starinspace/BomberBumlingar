# Bomber och Bumlingar (Engine)

Detta är en ny engine/port som kan läsa in banor, grafik och ljud från originalspelets filer.
Själva engine-koden är ny och skriven i Python/Pygame. Originalets datafiler används externt, men ingen originalkod är direkt kopierad.

Porten återskapar spelets funktioner, fysik, ljudlägen, intro, grafikvisning, joystickstöd (och handkontroll) och flera detaljer från originalet.

## Funktioner

- Läser originalets banor från `LVLS.LVL`
- Läser originalets grafik från `.PIC`-filer
- Läser originalets SoundBlaster-ljud från `.OUT`-filer
- Har återskapat “Original”-ljudläge via en liten ADPCM-baserad ljudfil
- Joystick/handkontroll stöds
- Fullscreen med korrekt aspect ratio
- Musikstöd via `MUSIC.OUT`
- Topplista/highscore
- Debug-läge
- Demo-läge

Demo-läget innehåller en tidigare ej visad variant med gula byxor (de gula byxorna är kvar i en av introbilderna), ett monster är i sin originalfärg (innan han blev lila, fanns även kvar spår i originalet) och en blå nyckel. Den blå nyckeln finns som grafik i originalmaterialet men verkar inte användas i slutversionens banor.

## Ljudlägen

Spelet har flera ljudlägen:

```text
Original      Rekommenderat ljudläge. Återskapade ljudeffekter i kompakt format.
SoundBlaster  Använder originalets .OUT-samplefiler från originalet.
PC Speaker    Emulerat/återskapat PC-speaker-läge. (Låter inte helt korrekt ännu. Använd Original)
````

Rekommendation: använd **Original**.

SoundBlaster-ljuden fanns i originalspelets filer men verkar inte ha använts normalt. I denna engine kan de användas.

## Snabb och enkel installation med EXE

Ladda ner EXE-versionen.

Lägg sedan följande originalfiler i samma mapp som `BomberOchBumlingar.exe`:

```text
LVLS.LVL
OBJECTS.PIC
3DTOP.PIC
INTRO.PIC
NAMES.PIC
EOF.PIC
TOPTEN.DAT
STEP.OUT
CNARRING.OUT
MUNCH.OUT
DAVEVOC.OUT
POCK.OUT
STARSNAR.OUT
BURPA.OUT
```

Engine-filer som också behövs eller kan ligga bredvid:

```text
sprite_map.json
DEM.PIC
original.out
MUSIC.OUT        valfri, behövs bara för musik (ej original eget komponerat till annat projekt)
font.json        valfri, ger original-text
joystick.json    skapas automatiskt om joystickmappning sparas
```

Starta sedan:

```text
BomberOchBumlingar.exe
```

Du kan också starta med kommandon från CMD:

```bat
BomberOchBumlingar.exe --demo
BomberOchBumlingar.exe --fullscreen
BomberOchBumlingar.exe --sound original
BomberOchBumlingar.exe --music MUSIC.OUT
BomberOchBumlingar.exe --music MUSIC.OUT --music-mode soundblaster
BomberOchBumlingar.exe -D
```

<img width="962" height="704" alt="Skärmbild 2026-06-30 184116" src="https://github.com/user-attachments/assets/8ee4f55a-f7bf-4cd0-9430-6412b9120f08" />
<img width="962" height="704" alt="Skärmbild 2026-06-30 184118" src="https://github.com/user-attachments/assets/0a4f6b65-f1c9-4039-a278-c7bb00d03267" />
<img width="962" height="704" alt="Skärmbild 2026-06-30 183336" src="https://github.com/user-attachments/assets/7bf77392-f771-419d-9a6e-a58b54a5f5a4" />


# Avancerat om man gillar det

Flaggorna fungerar alltså både med EXE och med Python-versionen.

## Installation med Python

Installera Python eller Conda.

Exempel med Conda:

```bat
conda create -n bob python
conda activate bob
pip install pygame
```

Ladda ner engine:

```text
https://github.com/starinspace/BomberBumlingar
```

Ladda ner originalspelet:

```text
https://archive.org/details/BomberOchBumlingar
```

Extrahera engine-filerna:

```text
main.py
pic_decoder.py
sprite_map.json
font.json
DEM.PIC
original.out
joystick.json
MUSIC.OUT
```

Extrahera dessa filer från originalspelet och lägg dem i samma mapp:

```text
LVLS.LVL
OBJECTS.PIC
3DTOP.PIC
INTRO.PIC
NAMES.PIC
EOF.PIC
TOPTEN.DAT

STEP.OUT
CNARRING.OUT
MUNCH.OUT
DAVEVOC.OUT
POCK.OUT
STARSNAR.OUT
BURPA.OUT
```

Starta spelet:

```bat
python main.py
```

Starta demo:

```bat
python main.py --demo
```

Starta fullscreen:

```bat
python main.py --fullscreen
```

Starta debug-läge:

```bat
python main.py -D
```

eller:

```bat
python main.py --debug
```

<img width="962" height="704" alt="Skärmbild 2026-06-30 183859" src="https://github.com/user-attachments/assets/91521a35-c317-4a19-8e02-6aa1f6bf6712" />
<img width="962" height="704" alt="Skärmbild 2026-06-30 183921" src="https://github.com/user-attachments/assets/8a05fd43-c429-4cd6-a3e9-f8d8adb9c35f" />


## Kommandoradsflaggor

Dessa fungerar både med `python main.py` och med EXE-filen via CMD.

```text
--demo
    Startar demo-versionen.

-D
--debug
    Startar debug-läge.

--fullscreen
    Startar direkt i fullscreen.

--sound original
    Startar med återskapat original-ljudläge.

--sound soundblaster
    Startar med SoundBlaster-ljud från originalets .OUT-filer.

--sound speaker
    Startar med PC-speaker-läge.

--music MUSIC.OUT
    Laddar musikfil.

--music-mode soundblaster
    Spelar musik med SoundBlaster-liknande ljud.

--music-mode speaker
    Spelar musik med PC-speaker-liknande ljud.

--music-mode c64
    Spelar musik med snabb arpeggio/time-slicing.

--music-on
    Startar med musik aktiverad direkt.
    Annars är musik avstängd från början.
```

## Tangenter och funktioner

```text
Piltangenter
    Flytta spelaren.

Shift + piltangent
    Gräv utan att flytta.

F1
    Visa Tio-i-topp-lista.
    Ej aktiv i demo-läge.

F2
    Ljud på/av.

F3
    Växla ljudläge.

F4
    Musik på/av.
    Musik är avstängd när spelet startar.

F5
    Mappa om joystick/handkontrollens grävknapp.

F11
    Växla fullscreen på/av.

Alt + Enter
    Växla fullscreen på/av.

Esc
    Avsluta eller gå tillbaka beroende på läge.
```

Debug-läge:

```text
N
    Hoppa till nästa bana.

P
    Visa/debugga objekt och saker på banan.

F9
    Debugfunktion.
```

Debugfunktionerna är bara aktiva om spelet startas med:

```bat
python main.py -D
```

eller:

```bat
BomberOchBumlingar.exe -D
```

## Musik

Musik är avstängd när spelet startar. Tryck `F4` för att slå på den.

## Demo-läge

Starta demo-läget med:

```bat
python main.py --demo
```

eller med EXE:

```bat
BomberOchBumlingar.exe --demo
```

Demo-läget har:

```text
gul byxfärg
blå nyckel
blå slutdörr
DEMO-märkning på titelskärmen
ingen Tio-i-topp
ingen highscore efter slutet
```

## Kommentar om originalfiler

Originalspelet, dess grafik, ljud, banor och övriga originalfiler tillhör Robert Gustavsson och Björn Andersson.

Det här projektet är ett fristående fan-projekt. Jag har ingen koppling till originalprojektet eller originalskaparna, utan är bara ett fan av spelet. **Bomber och Bumlingar** gav mig många timmar framför datorn, och målet med den här porten är att bevara spelet och ge det nytt liv på moderna system.

Engine-koden i detta projekt är nyskriven. Originalets filer används endast som externa datafiler och ingår inte i själva engine-koden.

## Copyright och distribution

Just nu distribueras endast den nyskrivna engine-koden. Originalfilerna måste hämtas separat av användaren från sin egen kopia av spelet.

Om originalskaparna ger sitt godkännande kan projektet i framtiden även inkludera originalfilerna direkt, samt byggas ut med exempelvis en level editor, förbättrad grafik, fler enemies, enklare installation och fler verktyg för att skapa nytt innehåll.

Tills dess hålls engine och originaldata separerade.
