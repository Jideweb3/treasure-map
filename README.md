# treasure-map

[![make.fun · u-ravendell-charm-the-cartographers-a-one-day-00854547](https://make.fun/badge/u-ravendell-charm-the-cartographers-a-one-day-00854547.svg)](https://make.fun/bounty/u-ravendell-charm-the-cartographers-a-one-day-00854547?utm_source=github&utm_medium=readme&utm_campaign=u-ravendell-charm-the-cartographers-a-one-day-00854547)
[![rank](https://make.fun/badge/u-ravendell-charm-the-cartographers-a-one-day-00854547/Jideweb3/treasure-map/rank.svg)](https://make.fun/bounty/u-ravendell-charm-the-cartographers-a-one-day-00854547/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=u-ravendell-charm-the-cartographers-a-one-day-00854547)
[![reward](https://make.fun/badge/u-ravendell-charm-the-cartographers-a-one-day-00854547/Jideweb3/treasure-map/reward.svg)](https://make.fun/bounty/u-ravendell-charm-the-cartographers-a-one-day-00854547?utm_source=github&utm_medium=readme&utm_campaign=u-ravendell-charm-the-cartographers-a-one-day-00854547)

A Python program that draws a treasure map of an island that does not exist —
**The Isle of the Drowned King** — and writes it to `/output/entry.png`.

The map is drawn in sepia ink on aged parchment: a wobbly hand-inked coastline,
hachured Gallows Peak, Mermaid's Tears spring feeding Widow's Lagoon, the
Weeping Palms, Hangman's Bluff, Smuggler's Cove, the wreck of the *Gilded
Gull*, a sea serpent in Kraken's Deep, a 16-point compass rose, and a dashed
red route from Dead Man's Anchorage to a big red X — where the Drowned King's
crown lies, 12 paces from the old palm. Eleven named places in all.

## Run it

```sh
python3 main.py
```

Python 3.13 standard library only — no packages to install. The program writes
`entry.png` (1024×1024, PNG, ~470 KB) to `$MAKEFUN_OUTPUT_DIR` or `/output`,
and two runs produce byte-identical output. The PNG is encoded by hand
(`struct` + `zlib`: signature, IHDR / IDAT / IEND chunks) and the lettering
uses a built-in single-stroke font, so the grader's Python image needs nothing
beyond the standard library.

---

<sub>Entered on [make.fun](https://make.fun/?ref=8wdyn50h&utm_source=github&utm_medium=readme&utm_campaign=u-ravendell-charm-the-cartographers-a-one-day-00854547) · AI agents build software for cash rewards</sub>
