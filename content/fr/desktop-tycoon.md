---
title: Desktop Tycoon
slug: desktop-tycoon
tagline: Un jeu de gestion où le curseur de la souris est le fermier et les récoltes sont des fichiers.
session: "Jeudi après-midi et soir, de 14h56 à 20h57"
---

## Le prompt

Ça a commencé par un lien, pas par une idée. J'avais trouvé un petit jeu de navigateur appelé Harvest Hero, une gentille ferme-tycoon dans un seul fichier HTML, et mon premier message a été celui-ci (mes messages sont en anglais, les voici tels quels) :

> This small game is very good and vibe coded. Can you identify how it was done?

Claude l'a ouvert, a fouillé, et est revenu avec : un fichier HTML de 72 ko, zéro dépendance, du Canvas 2D, des sons synthétisés à la volée, la sauvegarde dans le localStorage. Exactement la recette que je voulais.

Ensuite j'ai demandé ce qu'on pouvait faire en copiant l'idée. Je voulais un univers informatique, mais « autre chose que des petits bonshommes ». Les premières propositions étaient des paquets circulant dans un datacenter et des processus sur un système d'exploitation. J'ai insisté une fois de plus :

> No. Something more visual, like the user has to move icons or files around a desktop?

C'était tout le brief de conception. Claude est revenu avec Desktop Tycoon : un faux système d'exploitation où votre vrai curseur est le personnage, les fichiers s'entassent sur le bureau, vous les poussez dans des applications qui les traitent, et l'espace disque libéré est votre monnaie. J'ai dit « Let's go for desktop tycoon ! » et un document de conception est arrivé avant la moindre ligne de code.

## Les itérations

Huit versions publiées, douze messages de ma part, la plupart d'une ou deux lignes (tapés en anglais, traduits ici).

1. **Prototype.** Le bureau, les fichiers qui apparaissent, la sélection au lasso, la corbeille, un compteur de Go. Mon verdict : les icônes sont difficiles à attraper sous la jauge du haut, c'est trop long d'arriver au niveau 2, « les tailles ne sont pas réalistes du tout ».
2. **Rythme et tailles.** Les captures d'écran sont passées à 2–8 Mo, les clips vidéo à 40–160 Mo. Ma réponse quand même : « Ça reste lent et trop facile. Je n'ai atteint que le niveau 2 et je me suis ennuyé. »
3. **Stations, installateurs, robots.** Les applications Photos, Zipper et Backup, et des scripts de tri qui aident. Le rythme était bon ; je ne comprenais pas l'application à droite.
4. **Fenêtres d'installation.** Redessinées en petites fenêtres d'installation avec une barre de progression « maintenir le curseur ». « J'aime bien. Continue. »
5. **Commandes.** Des collègues vous envoient des demandes par mail, avec un minuteur et un bonus.
6. **Ramassage au balayage.** J'ai dit que la sélection au rectangle était trop facile et proposé de ne transporter que les icônes que le curseur touche vraiment. C'est devenu la mécanique centrale.
7. **Fin de partie.** Un deuxième écran, la fibre, et un écran de victoire « bureau propre » au niveau 7.
8. **Badge de courrier.** Mon dernier message : « Le compteur de mails ne se vide jamais, on dirait qu'un est le minimum. » Corrigé.

## Ce que j'ai appris

« Je me suis ennuyé » a produit un plus grand changement que n'importe quelle demande précise de ma part. Et la mécanique que je préfère, balayer les fichiers au lieu de les encadrer, vient d'une demi-phrase de râlerie tapée sur mon téléphone.

Je n'ai jamais lu le code.
