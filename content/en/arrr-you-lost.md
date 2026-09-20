---
title: Arrr You Lost?
slug: arrr-you-lost
date: 2026-09-20
tagline: An endless sea, a torn map, and a Navy with no sense of humour.
game: games/arrr-you-lost/index.html
iterations: 11
tags: [adventure, exploration, mobile]
---

## The prompt

After three small arcade games I wanted something bigger: a world you could
actually *visit*. An endless sea, islands, a story to keep you sailing, enemies
to fight or avoid. Mobile first, one file, nothing to install.

I asked for a plan before any code. It came back with the trick that makes it
work: the sea is cut into invisible squares, and each square's islands come
from its coordinates and a single number. Nothing is stored, so sail a hundred
leagues away and back and the same island is still there, under the same name. The map is a captain's, torn into seven pieces.

The working title was *Dead Reckoning*. I preferred the pun.

## The iterations

Eleven versions, in five chapters.

1. **Just sailing.** Islands called *Isle of Mild Regret* and *Damp Biscuits
   Cay*, a minimap, a ship's log. One flaw: I could move, but there was no boat
   on screen. It had been drawn off in the corner; one line fixed it.
2. **A reason to stop.** Docking, buried treasure, messages in bottles, and a
   trader selling sails, cannons and hull plating. I asked whether the gold
   pace was fair; it was.
3. **The Navy.** Sloops that patrol, spot you, circle and shoot, nastier the
   further out you go. Your cannons fire on their own: steering *and* aiming
   with one thumb is too much. My one complaint was the kraken, a purple blob
   in a world of sand and teal; it came back as whirlpool water with proper
   tentacles.
4. **The story.** Seven islands, seven characters — a hermit who owes the
   captain money, a lighthouse keeper whose light is decorative, four hundred
   parrots repeating secrets. The Admiral's flagship guards the last piece. It
   is also where I got stuck, literally: docking froze the boat. Three messages
   to pin down, one word to fix.
5. **Atmosphere.** Every sound invented on the spot — cannon, coins, gulls,
   surf — and not one audio file. The music too: *Drunken Sailor*, free to use
   since the 1830s (the tune is; famous recordings are not), played note by
   note by the same little synth. Day and night, and fog that hides the Navy
   until you hear it.

## What I learned

Ask for the plan first when the game is big, and test how the core loop
*feels* — here, steering — before piling on. And when something breaks on my
phone but not on the other side, be precise: "the button is there but does
nothing" found the bug. "It's stuck" didn't.
