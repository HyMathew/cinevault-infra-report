# Qualification du candidat Enterprise 2.1

## Paire API et Web

Le 21 novembre 2026, le contrôle HTTP a validé six étapes sur l'API
`4dd5cd9`, le Web `2607907` et le stockage JSON isolé. Chromium a ensuite
validé 45 contrôles sur les deux services réels, dont l'authentification, les
formulaires, les prêts, les réservations et la reprise d'une création dont la
réponse est coupée par le proxy de test. Les deux contrôles ont utilisé
les sources aux révisions déclarées avec données synthétiques.
[Reçu des contrôles](../../evidence/public/enterprise-2.1-candidate-20261121.json).

La campagne Insights est distincte et couvre l'API `22bcecd` avec le Web
`2607907` et JSON. Avant correction, les répartitions entièrement à zéro
masquaient les messages d'état vide. Chromium a ensuite validé 36 navigations
et 24 scans axe sans violation ni résultat incomplet à 320, 390, 768 et 1280 px.
Les cas incluent le clavier, les compteurs vides ou réellement alimentés,
les droits, les données d'un autre membre et une indisponibilité provoquée en
arrêtant l'API isolée. Les temps de navigation observés restent propres au PC.
La qualification des parcours MongoDB et multi-hôtes reste ouverte.

## Données et reprise

La qualification MongoDB à partir d'une archive chiffrée a restauré 393
documents, 12 collections et 40 index avant la quarantaine. La source est
restée identique et le candidat a accepté le nouvel administrateur tout en
refusant deux méthodes d'authentification archivées. La campagne a opéré dans
un replica set isolé depuis le PC par SSH.
[Reçu natif de l'API](https://github.com/HyMathew/cinevault-api/blob/4dd5cd99287fafdc647dead5ce32dbd42a5c457c/docs/evidence/mongodb-quarantine-native-20261121.json).

## Publication documentaire et déploiement

Le portail a été reconstruit deux fois sur chacun des runners Windows et
Ubuntu, avec 5 651 liens vérifiés par runner. Les deux archives ont été
téléchargées et contrôlées, puis leurs inventaires ont été vérifiés par
empreinte. Elles comprennent le PDF Enterprise identifié par son SHA-256.
Le job Chromium Ubuntu a réussi 207 contrôles. Les fichiers et dépendances
natives varient selon les plateformes. Le portail hébergé reste à la révision
indiquée dans le README. [CI documentaire statique](https://github.com/HyMathew/cinevault-infra-report/actions/runs/44911096819).

La branche prépare une livraison. Le dernier contrôle image cité dans le
[rapport Enterprise](../../report/enterprise-2.1/README.md) bloque encore
le déploiement du candidat. La v1 dispose de sa
[qualification historique](../validation-current.md).
