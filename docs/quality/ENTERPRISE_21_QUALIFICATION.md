# Qualification du candidat Enterprise 2.1

## Paire API et Web

Le 21 novembre 2026, le contrôle HTTP a validé six étapes sur l'API
`4dd5cd9`, le Web `2607907` et le stockage JSON isolé. Chromium a ensuite
validé 45 contrôles sur les deux services réels, dont l'authentification, les
formulaires, les prêts, les réservations et la reprise d'une création dont la
réponse est coupée par le proxy de test. Les deux contrôles ont utilisé
les sources aux révisions déclarées avec données synthétiques. Les workflows
ont ensuite réussi pour le même couple sur les runners déclarés.
[Reçu des contrôles](../../evidence/public/enterprise-2.1-candidate-20261121.json) ·
[CI de la paire JSON](https://github.com/HyMathew/cinevault-infra-report/actions/runs/44912210123) ·
[CI Chromium](https://github.com/HyMathew/cinevault-infra-report/actions/runs/44912210105).

La campagne Insights est distincte et couvre l'API `22bcecd` avec le Web
`2607907` et JSON. Avant correction, les répartitions entièrement à zéro
masquaient les messages d'état vide. Chromium a ensuite validé 36 navigations
et 24 scans axe sans violation ni résultat incomplet à 320, 390, 768 et 1280 px.
Les cas incluent le clavier, les compteurs vides ou réellement alimentés,
les droits, les données d'un autre membre et une indisponibilité provoquée en
arrêtant l'API isolée. Les temps de navigation observés restent propres au PC.

Le couple exact `4dd5cd9` et `2607907` a rejoué ces écrans avec MongoDB
8.0.34 dans Docker Desktop. Les tests ont validé 36 navigations aux mêmes
largeurs, 32 contrôles de mise en page, 24 scans axe sans résultat négatif
et les parcours clavier. Le moteur a conservé les comptes, sessions, films et
entrées privées observés, avec 12 collections et 40 index. Après arrêt réel de
MongoDB, l'API encore active a renvoyé 503 en 10,3 s. Les écrans Web ont répondu
503 en environ 5,1 s. Le conteneur, son réseau et les données temporaires ont
été retirés. La campagne couvre la boucle locale sans TLS. La qualification
multi-hôtes reste ouverte.

La revue produit sur `4dd5cd9` et `2607907` a observé 56 états et trois
problèmes dans le parcours clavier de recherche, les filtres des favoris et
l'identification des contrôles d'administration. Après correction Web
`bdf6063`, Chromium a vérifié 20 états aux quatre largeurs. Le décompte
reçoit le focus après une recherche et un seul Tab atteint le premier résultat.
Les favoris ne transmettent plus de filtre de liste nommée. Les contrôles de
rôle et de statut identifient le compte. Les 20 scans axe ciblés n'ont
rapporté aucune violation. Les 495 tests Web locaux ont réussi.

La campagne de circulation a exécuté 264 échanges HTTP sur les deux moteurs,
avec quatre tours par moteur. Chaque tour a présenté deux demandes concurrentes
pour le dernier exemplaire, puis une course entre le premier et le dernier de
la file. Elle a aussi rejoué en parallèle une même création de réservation.
Le premier cas a produit une seule approbation. La file a conservé la priorité
du premier en attente et les appels répétés ont conservé une seule réservation.
Les états persistés ont été relus sur chaque moteur.
[Reçu de circulation biomoteur](../../evidence/public/enterprise-2.1-candidate-20261121.json).

## Données et reprise

La qualification MongoDB à partir d'une archive chiffrée a restauré 393
documents, 12 collections et 40 index avant la quarantaine. La source est
restée identique et le candidat a accepté le nouvel administrateur tout en
refusant deux méthodes d'authentification archivées. La campagne a opéré dans
un replica set isolé depuis le PC par SSH.
[Reçu natif de l'API](https://github.com/HyMathew/cinevault-api/blob/4dd5cd99287fafdc647dead5ce32dbd42a5c457c/docs/evidence/mongodb-quarantine-native-20261121.json).

Une autre campagne a suspendu le seul conteneur Mongo local pendant
environ 10,4 secondes. L'API et l'écran Insights ont suivi la séquence
200 → 503 → 200. Le premier 200 de la santé a été observé 196 ms après
l'acquittement de la reprise Docker. Le film, le favori et la session
étaient toujours accessibles. L'API a conservé son processus et son pool
PyMongo. La sonde porte sur une pause locale du même processus Mongo.
[Reçu de reprise après pause](../../evidence/public/enterprise-2.1-candidate-20261121.json).

## Publication documentaire et déploiement

Le portail a été reconstruit deux fois sur chacun des runners Windows et
Ubuntu, avec 5 651 liens vérifiés par runner. Les deux archives ont été
téléchargées et contrôlées, puis leurs inventaires ont été vérifiés par
empreinte. Elles comprennent le PDF Enterprise identifié par son SHA-256.
Le job Chromium Ubuntu a réussi 207 contrôles. Les fichiers et dépendances
natives varient selon les plateformes. Le portail expose son propre reçu
de construction. [CI documentaire statique](https://github.com/HyMathew/cinevault-infra-report/actions/runs/44911096819).

La première édition 2.1, d'empreinte `9c891e53…`, possède une attestation
Sigstore vérifiée par un job en lecture seule. Le contrôle lie ce PDF, le
workflow, la branche et le commit `6c983f0`. Le PDF corrigé par la revue
universitaire a été reproduit sur Windows et Ubuntu et possède sa propre
attestation au commit `c26b506`. Deux jobs distincts y ont rejoué le corpus
académique sur l'API candidate. Les huit archives de ce run ont été vérifiées.
[Premier run de signature](https://github.com/HyMathew/cinevault-infra-report/actions/runs/44954701826) ·
[Rejeu et signature du rapport corrigé](https://github.com/HyMathew/cinevault-infra-report/actions/runs/44956333500).

La branche prépare une livraison. Le dernier contrôle image cité dans le
[rapport Enterprise](../../report/enterprise-2.1/README.md) bloque encore
le déploiement du candidat. La v1 dispose de sa
[qualification historique](../validation-current.md).
