# Portail hébergé — contrôles du 14 novembre 2026

Le [portail documentaire candidat](https://hymathew.github.io/cinevault-infra-report/)
sert l'artefact qualifié du commit `cf026c0`. Son
[reçu de publication](../portal-hosted-20261114.json) rattache le déploiement,
le paquet livré et les vérifications à leurs empreintes.

Les [351 fichiers relus en HTTPS](../portal-hosted-https-20261114.json)
correspondent aux octets qualifiés. Les quatre sources publiques sous répertoires
cachés sont accessibles. Seul le marqueur local de possession est exclu du site.

Le [reçu du navigateur réel](../portal-hosted-browser-20261114.json) comporte
187 contrôles et onze captures avec Chrome 157.0.8103.51 sous Windows :

- Accueil à [320](home-320.png), [390](home-390.png), [768](home-768.png),
  [840](home-840.png), [1024](home-1024.png) et [1280 pixels](home-1280.png).
- Thèmes [clair](home-1280-light.png) et [sombre](home-1280-dark.png).
- [Recherche française](search-1280.png), [menu mobile](menu-390-dark.png)
  et [vraie réponse 404](actual-hosted404.png).

Recherche puis clic, Tab/Entrée/Échap, menu, reflow et défilement clavier sont
exercés sur le site hébergé. Aucune erreur de script, de console ou HTTP
inattendue n'est relevée. Le message console 404 attendu reste classé séparément.
Le navigateur est fermé à la fin.

L'inspection visuelle porte sur l'accueil 320, l'accueil sombre 1280, la recherche
et la 404 : textes lisibles, commandes entières, aucun débordement visible.
Les six états axe ont zéro violation automatique, mais deux résultats de
contraste gardent **102 occurrences non conclusives**. La CI Ubuntu en relevait
104 dans son navigateur différent ; aucune certification globale n'en découle.

Ce site publie la documentation d'un candidat. Les changements ultérieurs de la
branche de développement sont promus séparément après qualification d'un nouvel
artefact. Aucune application du laboratoire n'est déployée par ce workflow.
