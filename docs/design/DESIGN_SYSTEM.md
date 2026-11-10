# CineVault 2.0 — système de présentation

Date : 10 novembre 2026. Spécification à implémenter dans Flask/Jinja et CSS local ; aucune conformité globale déjà démontrée. Sources : [conception](../../DESIGN.md), [produit](../../PRODUCT.md), [concept et provenance](concepts/README.md).

## Tokens de couleur

La base est **noir chaud**, jamais blanc ni un gradient décoratif. Les valeurs fixent une palette explicite ; le grain et les variations de la maquette générée ne sont pas des textures à reproduire.

| Token | Valeur | Usage |
|---|---|---|
| background | `#111011` | Fond global |
| surface | `#1b1919` | Zone de formulaire, ligne développée, fallback |
| text | `#f5eee5` | Texte principal ivoire |
| muted | `#c9beb5` | Métadonnées et aide, jamais texte invisible |
| accent | `#f2a838` | Action principale, focus, soulignement actif |
| line | `#48413d` | Séparateur décoratif, pas seule limite d'un contrôle |
| control-border | `#887b70` | Limite de champ/bouton sur fond sombre |
| danger | `#ffb4ab` | Erreur + texte/indicateur, pas couleur seule |
| success | `#a9d6b0` | Confirmation + texte/indicateur |

Ratios calculés le 10 novembre par luminance relative sRGB WCAG, couleurs opaques exactes : text/background **16,49:1**, text/surface **15,21:1**, muted/surface **9,60:1**, accent/background **9,43:1**, background/accent **9,43:1**, control-border/surface **4,26:1**, danger/surface **10,31:1**, success/surface **10,78:1**. `line/background` vaut seulement **1,90:1** : ce token ne sert ni contour indispensable d'un champ ni focus. Ces calculs de palette ne vérifient pas les styles calculés, états hover/disabled, opacités ou contenus réels.

Texte normal cible ≥4,5:1 ; grands textes ≥3:1 ; composants et indicateurs nécessaires ≥3:1 selon applicabilité. Référence : [WCAG 2.2 — aide à la mise en œuvre](https://www.w3.org/WAI/WCAG22/quickref/). Le bouton ambre porte du texte `background`, jamais ivoire. Les liens de corps sont soulignés ; un statut garde toujours son libellé.

## Typographie

| Rôle | Famille | Taille / interligne | Règle |
|---|---|---|---|
| Marque | Georgia, Times New Roman, serif | 30/36 desktop, 26/32 mobile ; gras | Texte réel, pas raster |
| H1 membre | Georgia, Times New Roman, serif | 44/50 desktop, 32/38 mobile ; gras | Pas de taille 80 px en tête d'outil |
| H1 gestion | Georgia, Times New Roman, serif | 32/38 desktop, 28/34 mobile ; gras | Tâche courte, sans hero |
| H2 / titre film | Georgia, Times New Roman, serif | 26/32 desktop, 23/29 mobile ; gras | Titre complet, retour à la ligne |
| Corps/UI | Arial, Helvetica, sans-serif | 16/24 | Champs, navigation, boutons, tableaux explicitement définis |
| Métadonnées/aide | Arial, Helvetica, sans-serif | 15/22 | Jamais unique support d'une instruction critique |

Les proportions de la maquette sont une direction ; sa navigation en apparence serif et ses glyphes générés ne doivent pas imposer un défaut d'accessibilité. Décision intentionnelle : UI sans-serif explicite, titres serif ; pas de police distante. Pas de capitales espacées en surtitre systématique. Prévoir `overflow-wrap` pour identifiants et titres extrêmes ; ne jamais tronquer l'identité d'un compte à côté d'une action destructive.

## Géométrie et rythme

- Contenu centré : largeur utile maximale **1184 px** ; marges latérales **48 px à 1280**, **24 px à 768**, **16 px à 390 et 320**. Largeur fluide entre ces repères.
- Espacement partagé : **4, 8, 12, 16, 24, 32, 48 px**. Gestion : rangées plus compactes, espaces 8–16 ; membre : blocs 24–32, aucun vide gratuit avant les résultats.
- En-tête desktop environ **70 px**, mobile fermé cible **≤120 px** à 390. Pas d'en-tête sticky par défaut qui cache le focus ou réduit le viewport.
- Contrôles et boutons : hauteur cible **44 px minimum**, padding horizontal 16, rayon **6 px**, bordure 1 px adaptée ; zone de contact et espacement vérifiés sur mobile. Aucun bouton icône seul par défaut.
- Fallback/affiche : proportion **2:3**, largeur de référence desktop **160 px**, mobile environ **96 px** ; taille stable pour éviter le saut au chargement. À 320, empiler si le titre/l'action n'ont plus une largeur lisible.
- Pas d'ombre diffuse ni de wrapper arrondi autour de chaque section. Séparateur fin entre résultats ; surfaces réservées aux formulaires/groupes nécessitant une limite.
- Le pied de page suit le contenu avec un minimum de hauteur de page ; il ne recouvre ni contrôles ni messages.

## Composants et variantes

| Famille | Anatomie / variants | États obligatoires |
|---|---|---|
| Shell | Marque, contexte, navigation, compte, main et footer | Visiteur, membre, gestion, admin, legacy ; courant et ouvert/fermé |
| Bouton / lien d'action | Ambre principal ; contour secondaire ; danger avec texte explicite | Repos, hover, focus, occupé si implémenté, indisponible avec raison |
| Recherche | Label visible, champ, bouton ; tri ; `details` Filtres | Aucun critère, critères actifs, vide, erreur de saisie |
| Résultat membre | Affiche/fallback, titre lié, métadonnées réelles, quantité/supports, Voir le film | Sans affiche, titre long, zéro/plusieurs exemplaires ; pas de faux disponible |
| Tableau de gestion | Caption/titre, en-têtes, identifiant de ligne et actions | Desktop compact ; cellules étiquetées/liste équivalente sur mobile |
| Formulaire | Groupes nommés, label, aide, contrôle, erreur et actions | Valeurs initiales, obligatoire, invalide, conflit, succès |
| Divulgation | `details` et `summary` natifs, indicateur navigateur | Fermé, ouvert, focus ; contenu atteignable au clavier |
| Notice | Libellé + message + récupération | Info, succès, avertissement/conflit, erreur ; statut ARIA adapté |
| Statut métier | Texte exact de l'état, date/unité lorsque pertinente | Attente, actif, retourné, annulé ; réservation selon contrat réel |
| Pagination | Navigation nommée, liens précédent/suivant, critères conservés | Première/dernière page, aucun résultat ; liens absents si non applicables |

Les macros Jinja partagées peuvent centraliser champ, message, action et ligne de résultat. Ne créer que celles réellement réutilisées. Le shell connaît le contexte d'affichage ; les macros ne décident pas de permissions.

## Affiches et fallback

Utiliser l'API batch d'affiches existante et ses validations de source/URL, sans N+1. Donner dimensions et aspect ratio stables ; charger paresseusement hors premier viewport si adapté. Respecter intégrité du visuel et attribution nécessaire ; ne pas créer de film connu ni d'affiche non autorisée.

Sans affiche, composer un rectangle typographique local (fond surface, titre ivoire et accent fin) en HTML/CSS, avec mention « Affiche non disponible ». C'est un état produit intentionnel, pas un faux poster ou une image cassée. Le titre complet existe dans le contenu principal ; si le fallback répète ce titre purement décoratif, éviter sa répétition inutile dans l'arbre accessible. Une affiche adjacente à un titre lié peut avoir un alt vide si elle n'apporte aucune information supplémentaire ; sinon une alternative brève pertinente. Ne pas annoncer une image absente comme « Affiche de… ».

## Icônes, focus et mouvement

Garder l'inventaire petit : indicateurs natifs de `details` et `select` ; éventuels chevrons SVG locaux de 16–20 px, trait cohérent 2 px, `currentColor`, décoratifs avec texte adjacent. Pas de police d'icônes, étoiles ou badge sans fonction. Les triangles/glyphes ImageGen ne sont pas des assets à extraire.

Focus visible : contour ambre **3 px**, décalage **3 px**, sans suppression de l'outline navigateur avant remplacement équivalent. Vérifier qu'il n'est pas coupé par overflow ni masqué ; le focus ne repose pas sur la couleur seule. La navigation courante reçoit soulignement et sémantique, pas seulement ambre.

Mouvement : aucun autoplay, carousel ou parallaxe. Transitions locales éventuelles 120–160 ms sur couleur/contour, jamais nécessaires pour comprendre un état ; les supprimer sous `prefers-reduced-motion: reduce`. Les messages d'erreur ne clignotent pas.

## Accessibilité et récupération

Un seul main et H1 ; hiérarchie de titres ordonnée, labels visibles, aides et erreurs associées. Lien « Aller au contenu » visible au focus. Succès non urgent via `role=status` ; erreurs importantes via résumé pertinent, sans transformer toute la page en région live. Après soumission complète, titre/message/erreurs ont un ordre compréhensible ; si focus programmatique ajouté, tester le parcours réel avant/après.

Les confirmations n'altèrent ni CSRF, ni ETag/version, ni refus serveur. 412 : relire/comparer ; 503 : disponibilité inconnue ; import incertain : vérifier l'issue avant renvoi. Les noms accessibles des actions identifient l'objet lorsqu'une liste répète les mêmes boutons. Sur mobile, les étiquettes de cellules doivent être réellement exposées : le texte généré CSS seul ne suffit pas à prouver leur lecture.

## Contrôle de fidélité et statut

Pour chaque surface critique : comparer capture réelle au concept ou à la spécification applicable ; relever palette, copie, typographie UI et contenu, containers/espaces, densité, fallback, focus et responsive. Documenter tout écart intentionnel. Comparer avant/après sur le même état de données et les mêmes dimensions ; vérifier séparément les scénarios synthétiques riches.

Vérifications encore nécessaires : styles calculés et ratios des états, axe-core, Tab/Shift+Tab avec élément actif observé, erreurs et concurrence, zoom 200/400 % selon contexte, reflow sans débordement à 320/390/768/1280, menus/filtres ouverts, reduced motion et contrôle assisté ciblé. Les tokens ci-dessus sont une base calculée ; ils ne constituent pas une certification WCAG.
