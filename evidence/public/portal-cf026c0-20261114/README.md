# Portail documentaire — captures de la CI cf026c0

Ces dix captures proviennent du [run Ubuntu 43502640262](https://github.com/HyMathew/cinevault-infra-report/actions/runs/43502640262)
au commit `cf026c0b98205af5fcaa4fa6de8e319335c58664`. Leurs empreintes sont
vérifiées dans le [reçu de qualification](../portal-cf026c0-ci-20261114.json).
Le navigateur est le Chromium de Playwright, version 156.0.8078.4.

L'accueil est capturé à [320](home-320.png), [390](home-390.png),
[768](home-768.png), [840](home-840.png), [1024](home-1024.png) et
[1280 pixels](home-1280.png). Les autres états sont :

- [Thème clair sur ordinateur](home-1280-light.png).
- [Thème sombre sur ordinateur](home-1280-dark.png).
- [Recherche française avec résultat](search-1280.png).
- [Menu mobile dans le thème sombre](menu-390-dark.png).

La campagne vérifie 183 contrôles, dix empreintes et six états axe.
Aucune violation automatique n'est relevée ; deux résultats `color-contrast`
restent non conclusifs, représentant 104 occurrences de nœuds dans deux états.
Ces captures ne remplacent pas l'examen de ces résultats ni un audit complet.
L'inspection visuelle humaine attestée ici porte sur l'accueil 320, l'accueil
sombre 1280 et la recherche 1280 : textes et commandes lisibles, marque entière,
aucune coupe horizontale visible.

Ces captures précèdent l'hébergement du portail candidat. La
[qualification du site hébergé](../portal-hosted-20261114/README.md) est séparée ;
aucune de ces campagnes ne qualifie le déploiement applicatif de CineVault.
