# Qualification de la recherche rapide Signature

Le 27 novembre 2026, le Web candidat `51b6962f4d983e7fcb22b9bec67387a982274564` et
l’API candidate `f4457ac7a9f0c4d3eecfbeb74f57b5b7e21eb7f0` ont été exécutés
sur boucle locale Windows avec un catalogue JSON v2 synthétique.
Le banc a vérifié les fichiers extraits contre leurs objets Git avant de
démarrer. Le [reçu d’exécution](../../evidence/public/signature-quick-search-20261127.json)
associe les contrôles, captures et durées à ces sources.

## Parcours observés

- Le bouton et Ctrl+K ou ⌘K ouvrent la recherche au clavier. Échap et
  « Fermer » restituent le focus, y compris après saisie. La fermeture
  annule la recherche programmée. Les flèches permettent de quitter le
  champ pour les suggestions, puis de revenir au champ.
- La saisie s’arrête avant le premier appel quand elle compte moins de
  deux caractères. La frappe regroupée émet une seule demande après
  250 ms. Une réponse retardée n’écrase pas la recherche suivante.
- Un jeu de sept films correspondant au même titre partiel donne
  cinq liens. Le lien de film conserve le retour au catalogue filtré.
  Le cas sans résultat et un HTTP 503 injecté au niveau Web ont été exercés.
- Le visiteur, le membre, le gestionnaire et l’administrateur voient les
  destinations correspondant à leur rôle. Un lien vers les réservations
  de gestion déjà ouvert a été refusé après révocation réelle du rôle.
- JavaScript désactivé, le lien d’en-tête mène au champ du catalogue,
  où Entrée affiche la recherche complète.

## Navigateurs et accessibilité

| Moteur exécuté | Largeurs testées | Mesure locale médiane |
| --- | --- | ---: |
| Chrome 158.0.8127.37 | 320, 390, 768, 1280 px | 291,4 ms |
| Firefox 157.0 | 320, 390, 768, 1280 px | 296,5 ms |
| WebKit 27.2 sous Windows | 320, 390, 768, 1280 px | 298,5 ms |

Les mesures relient l’événement de saisie à l’apparition des suggestions
dans le DOM, avec huit observations par moteur et les 250 ms d’attente
volontaire incluses. Elles décrivent ce banc local à neuf films.
Le script pèse 4 721 octets en source et 1 526 octets compressé en gzip.
Aucune mesure de latence du staging ou à grand catalogue n’est déduite.

Douze scans axe du dialogue et de ses résultats ont produit zéro violation
signalée. Neuf vérifications automatiques du contraste sont restées
incomplètes sur un titre. Les couleurs opaques calculées du titre et du
fond donnent 15,21:1 à l’état testé. Le reflow et les cibles d’au moins
44 px ont été vérifiés aux quatre largeurs, avec la préférence de réduction
des animations. Les essais n’incluent ni lecteur d’écran sur appareil
physique ni clavier virtuel iOS. Le banc ne constitue pas une certification
d’accessibilité.

[Catalogue avant à 390 px](../design/screens-signature-search/catalogue-avant-390.png) ·
[recherche rapide à 390 px](../design/screens-signature-search/dialogue-390.png) ·
[recherche rapide à 1 280 px](../design/screens-signature-search/dialogue-1280.png) ·
[recherche de design](../design/REFERENCE_RESEARCH.md)

Les 519 tests Web ont également réussi sous Windows sur le même commit.
Ce lot qualifie l’interface et les échanges HTTP du banc JSON. Le chemin
MongoDB a ses validations de persistance distinctes. Le passage en CI et
la qualification du couple d’images en staging restent à exercer sur ce
commit Web.
