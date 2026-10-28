# Danny Duncan: Bull Run

A playable, unofficial fan-game prototype for the original **Nintendo Game Boy**.
The download is a real 32 KiB `.gb` ROM, with original pixel art and sound effects.

## Play

Load **[dist/danny-bull-run.gb](dist/danny-bull-run.gb)** in a Game Boy emulator.
On original hardware, use a compatible Game Boy flash cartridge to load the ROM.
Physical hardware has not yet been tested.

| Button | Action |
| --- | --- |
| Start | Start, pause/resume, retry |
| Left / Right | Move one lane per press |
| A or B | Jump a barrier |

Danny runs automatically. Bulls rush up from behind, while barriers approach from
the front. **Dodge bulls sideways; jumping only clears barriers.** You have three
hearts and a short recovery period after each hit. Survive to grow your score;
the action speeds up at 200 points. The best score survives retries, but resets
when the ROM is reset or powered off. There is no battery save.

## Build

Requires Python 3.9 or newer, with no additional packages:

```sh
python3 src/build.py
```

The source contains a small LR35902 assembler, game logic, font, pixel art,
sound effects, and cartridge header generation. Labels are resolved at build
time. The ROM uses no mapper, cartridge RAM, external assets, or external SDK.
It uses a WRAM sprite buffer and an HRAM DMA routine, updating sprites and the
HUD during VBlank. Hardware background scrolling moves the Spanish street;
a window layer with a scanline cutoff holds the HUD fixed at the top.
All gameplay uses the original 160 × 144 display and four
shades. `dist/symbols.json` maps code labels and RAM for debugging.

## Emulator verification

Install the optional test dependencies in a virtual environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install pyboy==2.8.1 pillow
.venv/bin/python tests/test_rom.py
```

Tests exercise the actual ROM in PyBoy: boot, DMA, lane controls, jumps, pause,
decimal scoring, difficulty, collisions, invulnerability, game over, high score,
restart, and several minutes of spawning. They also produce title, gameplay,
and game-over screenshots in `dist/`.

This is a first playable prototype, with a stylized Danny sprite featuring shaggy
hair, a white festival outfit, neckerchief, and waist sash in four DMG shades.
It is not affiliated with Danny Duncan or Nintendo.
