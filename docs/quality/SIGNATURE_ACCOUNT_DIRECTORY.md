# Administration des comptes Signature

Un administrateur peut rechercher le début d’un identifiant, choisir un
rôle et filtrer les comptes actifs ou désactivés. Les filtres combinés
s’appliquent au registre avant la pagination. La recherche est littérale
et ignore la casse. Les comptes restent ordonnés par identifiant.

L’enregistrement d’un rôle ou d’un statut conserve la page et les filtres,
y compris si l’API refuse la modification du dernier administrateur actif.
Si l’enregistrement raccourcit la liste et que la page courante disparaît,
le Web ouvre la dernière page valide. La révocation des sessions après
changement conserve le comportement de l’API. Seul un administrateur
connecté peut consulter l’annuaire et modifier un compte.

## Vérifications

API `5a2936bd49e62d168edacaf4501e6a2a18f08228` et Web `1693459f8df0bb0e2a80c7dd613131af7ef87462`.
Le test d’adaptateur utilise des comptes synthétiques. Il a vérifié la
parité JSON/MongoDB pour 108 résultats pertinents, le total filtré, la
seconde page de 50, l’état désactivé et un résultat vide. Le test inclut
un identifiant qui ne correspondrait que si le point du préfixe était
interprété comme un motif. Les réponses ne contiennent que les cinq
champs du profil. Le rejeu RT0705 garde 93 échanges et 44 opérations REST.

Sur les services locaux, le navigateur a affiché 55 résultats après
application des filtres. Depuis la deuxième page, un changement de rôle
a ramené le total à 54 sans perdre les filtres. L’essai a également
vérifié la réorientation depuis une page devenue vide, le statut
désactivé et le contrôle de rôle de la consultation. Sur le banc JSON,
le refus de désactiver le dernier administrateur conserve le contexte.

Les essais ont utilisé Chrome, Firefox et WebKit avec JSON. Chrome a
également utilisé un réplica local MongoDB 8.0.38 avec authentification
SCRAM-SHA-256. Chrome et Firefox ont activé filtres, liens et boutons
par Tab et Entrée. WebKit sous Windows a activé ces contrôles au pointeur.
Le reflow a été vérifié à 320, 390, 768 et 1 280 px.

Les suites locales comptent 638 tests API réussis, neuf ignorés et
44 sous-tests réussis. Les 541 tests Web ont réussi. Les quatre essais
navigateur ont couvert seize configurations de moteur, persistance et
largeur, sans violation axe détectée sur la page d’administration.

[Aperçu à 390 px](../design/screens-signature-directory/administration-390.png) ·
[Aperçu à 1 280 px](../design/screens-signature-directory/administration-1280.png) ·
[Reçu du lot](../../evidence/public/signature-account-directory-20261127.json)

Le candidat Web et l’API avec filtres doivent être qualifiés ensemble pour
le staging. Les anciennes lectures sans filtre conservent leur contrat.
