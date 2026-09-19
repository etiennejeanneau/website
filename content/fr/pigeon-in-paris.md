---
title: Pigeon in Paris
slug: pigeon-in-paris
tagline: Flappy Bird, sauf que l'oiseau est un pigeon parisien très bête.
session: "Jeudi soir, de 21h05 à 22h12"
---

## Le prompt

Une heure, du début à la fin. Tout juste sorti de Desktop Tycoon, j'ai demandé
(mes messages sont en anglais, les voici tels quels) :

> Now I'd like to make a game in html the same way that look like flappy bird and is also smartphone friendly. What theme do you suggest? I'd love it if the theme was funny

Quatre propositions sont revenues : une baguette qui s'échappe d'une boulangerie, un gros pigeon parisien, une abeille bourrée qui dérive au hasard, et un camping-car qui rebondit sous les ponts trop bas. Les préférées de Claude étaient la baguette ou l'abeille. J'ai pris le pigeon quand même, et j'ai ajouté deux contraintes :

> Make a plan for a similar technical architecture for a flappy bird like in a Paris decor a la Ratatouille. The pigeon must also look like it is stupid

Puis : « Fais-le morceau par morceau et laisse-moi essayer. » Une feuille de route en quatre étapes est arrivée : le cœur jouable, le décor parisien, le pigeon stupide, puis le peaufinage (croissants, sons, bouton de partage).

## Les itérations

Sept versions publiées. Mes messages, dans l'ordre (tapés en anglais, traduits ici) :

1. Le cœur est jouable. « La chute me paraît un peu lourde, normalement un oiseau peut rester un peu en l'air, non ? » Gravité adoucie, et un temps de suspension en haut de chaque battement d'ailes.
2. « C'est bien pour l'instant. On continue. » Paris arrive : tour Eiffel et Sacré-Cœur sur l'horizon, façades haussmanniennes, cheminées, parasols de café, colonnes Morris et lampadaires en guise d'obstacles.
3. « C'est ok. Allons-y pour le pigeon. » Tête surdimensionnée, yeux globuleux qui partent chacun de leur côté, langue pendante, bulles de dialogue (« bread? », « is this Lyon? », « I am bird »).
4. « Continue, j'aime bien. » Des croissants qui font grossir, des sons, un tremblement d'écran, un bouton de partage.
5. « Le jeu est un peu trop difficile pour le moment. Est-ce que les obstacles sont trop proches horizontalement ? » Mauvais diagnostic de ma part : le vrai coupable était l'écart vertical possible entre deux obstacles successifs. Claude m'a expliqué, puis a corrigé les deux.
6. « J'aimerais bien voir les ailes battre. Et le son du battement n'est pas très agréable. » Deux ailes à plumes avec un vrai mouvement, et un « fwup » plus doux.

## Ce que j'ai appris

Demander un plan d'abord, puis « morceau par morceau », ne coûte rien et fait que chaque essai sur mon téléphone porte sur une seule chose. Et quand j'ai mal diagnostiqué la difficulté, on m'a corrigé plutôt qu'obéi, ce qui m'a évité de réparer le mauvais problème.
