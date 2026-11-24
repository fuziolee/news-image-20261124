# The World in One Day — Tuesday, 24 November 2026

[![GitHub](https://img.shields.io/badge/GitHub-fuziolee%2Fnews--image--20261124-181717?logo=github)](https://github.com/fuziolee/news-image-20261124)
[![Bounty](https://img.shields.io/badge/make.fun-news--image--20261124-orange)](https://make.fun/bounty/news-image-20261124)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Entry for the make.fun bounty
[news-image-20261124](https://make.fun/bounty/news-image-20261124):
sum up 24 November 2026's world news in one image.

## The image

A dense newspaper front page (1024×1024) on cream paper:

- **Masthead** — "TUESDAY, 24 NOVEMBER 2026", with the kicker
  "ONE DAY OF WORLD NEWS, ONE PICTURE" and "50 STORIES · 7 REGIONS".
- **THE DAY IN UTC** — a six-entry timeline of the day's key moments.
- **4 hero stories** — numbered, colour-coded by region, with a CLAIM tag
  where the story is one side's account, not independently confirmed:
  Iran's tanker claim in the Strait of Hormuz, the Russian strike on
  Zaporizhzhia, the car bomb in Villavicencio, Colombia, and Russian
  warplanes entering South Korea's air defence zone.
- **12 small stories** in two rows of six, from Ukraine and Estonia to
  Nepal's earthquake and Kiribati's evacuation of Kanton Island.
- **WHERE IT HAPPENED** — a drawn world map with numbered dots for the
  four hero stories and a region-colour legend.
- **ALSO ON TUESDAY 24 NOVEMBER** — the remaining 34 stories as
  one-liners in three columns.
- **DATE CHECK** banner and footer: every story here happened or was
  first reported on 24 November 2026.

50 stories across 7 regions: Europe 10, Middle East 9, Asia 8,
Americas 8, Africa 8, Oceania 5, Global 2. Sources include Reuters,
Bloomberg, Al Jazeera, AP, BBC, Xinhua, The Hindu, SCMP and others.

## How to run

Standard library only — no Pillow, no network, no fonts from disk.
The program draws the page with a bitmap font defined in the code and
encodes the PNG by hand, so two runs produce byte-identical output.

```sh
python3 main.py
```

Writes `entry.png` to `$MAKEFUN_OUTPUT_DIR` (or `/output/entry.png`,
falling back to `./entry.png`).

## Files

- `main.py` — the renderer (stdlib-only Python 3)
- `entry.png` — the rendered front page (1024×1024, also reproducible
  by running `main.py`)
- `LICENSE` — MIT

## License

MIT — see [LICENSE](LICENSE).
