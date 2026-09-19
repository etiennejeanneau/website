---
title: Desktop Tycoon
slug: desktop-tycoon
date: 2026-09-17
tagline: An idle tycoon where your mouse cursor is the farmer and the crops are files.
game: games/desktop-tycoon/index.html
iterations: 8
prompts: 12
session: "Thursday afternoon and evening, 14:56 to 20:57"
tags: [idle, tycoon, mobile]
---

## The prompt

It started with a link, not an idea. I had found a small browser game called Harvest Hero, a cosy farm tycoon in a single HTML file, and my first message was:

> This small game is very good and vibe coded. Can you identify how it was done?

Claude opened it, poked around, and came back with: one 72 KB HTML file, zero dependencies, Canvas 2D, sounds synthesised on the fly, save in localStorage. Which is exactly the recipe I wanted.

Then I asked what we could make by copying the idea. I wanted an IT universe, but "something other than little people". The first suggestions were packets running through a datacenter and processes on an operating system. I pushed once more:

> No. Something more visual, like the user has to move icons or files around a desktop?

That was the whole design brief. Claude came back with Desktop Tycoon: a fake OS where your real cursor is the character, files pile up on the desktop, you sweep them into apps that process them, and freed disk space is your currency. I said "Let's go for desktop tycoon!" and it wrote a design document before touching any code.

## The iterations

Eight published versions, twelve messages from me, most of them one or two lines.

1. **Prototype.** Desktop, files spawning, lasso select, Trash, a GB counter. My verdict: icons hard to grab under the top gauge, too slow to reach level 2, "the sizes are not realistic at all".
2. **Pacing and sizes.** Screenshots became 2 to 8 MB, video clips 40 to 160 MB. Still my reply: "It still feels slow and too easy. I only reached level 2 and felt bored."
3. **Stations, installers, bots.** Photos, Zipper and Backup apps, sorting-script helpers. Pace was right; I didn't understand the app on the right.
4. **Installer panels.** Redrawn as little install windows with a "hold cursor" progress bar. "I like it. Continue."
5. **Orders.** Coworkers email you requests with a timer and a bonus.
6. **Sweep pickup.** I said the select box was too easy and suggested only carrying the icons the cursor actually passes over. That became the core mechanic.
7. **Endgame.** Second monitor, fibre upgrade, a clean-desk win screen at level 7.
8. **Mail badge.** My last message: "The mail count never gets cleared it seems one is the minimum." Fixed.

## What I learned

"I felt bored" produced a bigger change than any precise request I gave. And the mechanic I like best, sweeping files instead of box-selecting them, came from a half-sentence complaint typed on my phone.

I never read the code.
