# Fiche film et films apparentés

La fiche place les supports, la disponibilité et l’action de prêt en
tête. Le synopsis reste proche de ces informations, et l’ajout à la
collection a sa propre action. La réservation reste possible quand le
catalogue n’a encore aucun exemplaire. L’en-tête tient sur une ligne à
320 px dans les trois moteurs testés.

La lecture du film accepte une projection `include=related`. Elle
renvoie jusqu’à quatre films différents, classés par nombre de genres en
commun, puis par réalisateur commun, titre sans distinction de casse,
année et identifiant. Chaque proposition explique le rapprochement.
Le navigateur préserve le retour au catalogue filtré. Une API antérieure
qui ignore l’option sert la fiche sans suggestions.

Le champ `_etag` reste la version d’édition du film. L’ETag de
la réponse avec projection change lorsque les suggestions changent.
La projection n’utilise que les métadonnées publiques du catalogue.
Le banc MongoDB a tracé trois commandes de lecture pour la projection,
avec un jeu qui exerce la frontière de quatre résultats et le départage
par réalisateur, titre Unicode, année et identifiant.

## Preuves

API `3adf53b0f3b2a4a8523998543074508c97443c47`, Web `7203e25942dac689a112810dea89364af2fdb5e7`, bancs locaux du
27 novembre 2026. Chrome, Firefox et WebKit ont exercé les fiches à
320, 390, 768 et 1 280 px avec JSON. Le contrôle natif MongoDB 8.0.38
et le parcours Chrome sur ce moteur ont aussi réussi. Chrome et Firefox
ont activé les liens et boutons par parcours Tab et Entrée. WebKit sous
Windows a exercé les mêmes parcours au pointeur.

Pour une fiche publique sans affiche, les trois appels HTTP existants
ont été observés. La représentation enrichie a été demandée dans celui
du film. Les essais du lot affichent le repli sans affiche et utilisent
des films fictifs. Les détails et les deux révisions sont consignés dans
le [reçu navigateur et natif](../../evidence/public/signature-film-detail-20261127.json).
OpenAPI a passé sa validation. Le rejeu académique en mémoire couvre
93 échanges, 44 opérations et dix contrôles d’exécution, avec réseau
désactivé.

La suite locale a réussi 637 tests API, 44 sous-tests et 537 tests Web.
Neuf tests API sont ignorés dans cette suite locale. Le banc natif est
présenté séparément dans le reçu.

[Fiche à 320 px](../design/screens-signature-detail/fiche-320.png) ·
[Fiche à 1 280 px](../design/screens-signature-detail/fiche-1280.png) ·
[Suggestions à 390 px](../design/screens-signature-detail/films-apparentes-390.png)

Les essais de ce lot portent sur un petit catalogue synthétique et sur
les comportements indiqués. La mesure sous charge du calcul de
similarité et le staging signé restent ouverts.
