---
title: Arrr You Lost?
slug: arrr-you-lost
tagline: Une mer sans fin, une carte déchirée, et une Marine royale sans le moindre humour.
---

## Le prompt

Après trois petits jeux d'arcade, je voulais quelque chose de plus grand : un
monde qu'on puisse vraiment *visiter*. Une mer sans fin, des îles où accoster,
une histoire pour donner envie de naviguer, des ennemis à fuir ou à combattre.
Mobile d'abord, un seul fichier, rien à installer.

J'ai demandé un plan avant la moindre ligne de code. Il est revenu avec
l'astuce qui fait tout tenir : la mer est découpée en carrés invisibles, et les
îles de chaque carré sont tirées de ses coordonnées et d'un seul nombre. Rien
n'est stocké : partez à cent lieues de là, revenez, la même île est toujours
là, sous le même nom. La carte est celle du capitaine, déchirée en sept
morceaux.

Le titre de travail était *Dead Reckoning*. J'ai préféré le jeu de mots.

## Les itérations

Onze versions, racontées ici en cinq chapitres.

1. **Naviguer, rien d'autre.** Des îles baptisées *Isle of Mild Regret* et
   *Damp Biscuits Cay*, une mini-carte, un journal de bord. Un seul défaut : je
   pouvais me déplacer, mais aucun bateau à l'écran — il était dessiné à côté,
   dans un coin. Une ligne a suffi.
2. **Une raison de s'arrêter.** L'accostage, des trésors enfouis, des
   bouteilles à la mer, et un marchand qui vend voiles, canons et blindage de
   coque. J'ai demandé si l'or tombait à un rythme juste ; il tombait bien.
3. **La Marine royale.** Des sloops qui patrouillent, vous repèrent, tournent
   autour et tirent, de plus en plus méchants à mesure qu'on s'éloigne. Vos
   canons tirent tout seuls : barrer *et* viser d'un seul pouce, c'est trop.
   Couler coûte la moitié de votre or. Ma seule critique : le kraken, une tache
   violette dans un monde de sable et de turquoise. Il est revenu en eau de
   tourbillon sombre, avec de vrais tentacules.
4. **L'histoire.** Sept îles, sept personnages — un ermite qui doit de l'argent
   au capitaine, un gardien de phare dont la lumière est décorative, quatre
   cents perroquets qui répètent des secrets, le second qui s'est mutiné. Le
   vaisseau amiral garde le dernier morceau. C'est aussi là que je suis resté
   bloqué, littéralement : accoster figeait le bateau. Trois messages pour le
   cerner, un mot pour le corriger.
5. **L'ambiance.** Chaque son inventé sur le moment — canon, pièces, mouettes,
   ressac — et pas un seul fichier audio. Le jour et la nuit, et du brouillard
   qui cache la Marine jusqu'à ce qu'on l'entende.

## Ce que j'ai appris

Demander le plan d'abord, quand le jeu est gros, et tester ce que donne la
boucle principale — ici, barrer — avant d'empiler quoi que ce soit dessus. Et
quand quelque chose casse sur mon téléphone mais pas de l'autre côté, il faut
être précis : « the button is there but does nothing » (je tape mes messages en
anglais) a mené droit au bug. « It's stuck », non.
