---
title: Pigeon in Paris
slug: pigeon-in-paris
date: 2026-09-17
tagline: Flappy Bird, except the bird is a very stupid Parisian pigeon.
game: games/pigeon-in-paris/index.html
iterations: 7
prompts: 9
session: "Thursday evening, 21:05 to 22:12"
tags: [arcade, flappy, mobile]
---

## The prompt

One hour, start to finish. Fresh from Desktop Tycoon, I asked:

> Now I'd like to make a game in html the same way that look like flappy bird and is also smartphone friendly. What theme do you suggest? I'd love it if the theme was funny

Four suggestions came back: a flying baguette escaping a bakery, a fat Paris pigeon, a drunk bee with random drift, and a camper van bouncing under low bridges. Claude's own picks were the baguette or the bee. I took the pigeon anyway, and added the two constraints that define the game:

> Make a plan for a similar technical architecture for a flappy bird like in a Paris decor a la Ratatouille. The pigeon must also look like it is stupid

Then: "Make it piece by piece and let me try it." A four-step roadmap came back: playable core, Paris decor, stupid pigeon, then juice (croissants, sounds, share button).

## The iterations

Seven published versions. My messages, in order:

1. Core is playable. "It feels a little heavy on the fall, usually a bird can stay a little bit in the air, no?" Gravity softened, a bit of hang time near the top of each flap.
2. "Feels good for now. Let's continue." Paris arrives: Eiffel Tower and Sacré-Cœur on the skyline, Haussmann façades, chimneys, café umbrellas, Morris columns and lampposts as obstacles.
3. "It's ok. Let's go for the pigeon." Oversized head, googly eyes that wander independently, tongue out, speech bubbles ("bread?", "is this Lyon?", "I am bird").
4. "Continue I like it." Croissants that make you fatter, sounds, screen shake, a share button.
5. "The game is a bit too difficult at the moment. Are the obstacles too close horizontally?" Wrong guess on my part: the real culprit was how far the gap could jump vertically between two obstacles. Claude explained, then fixed both.
6. "I'd love to see the wings flap. And the sound for the flap is not so nice." Two feathered wings with a proper stroke, and a softer "fwup".

## What I learned

Asking for a plan first and then "piece by piece" cost nothing and made each test on my phone about one thing. And when I diagnosed the difficulty wrongly, I got corrected rather than obeyed, which is the whole point of having a collaborator instead of a compiler.
