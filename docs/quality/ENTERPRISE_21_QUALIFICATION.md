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

Le 22 novembre, la paire API `15a894e` et Web `bdf6063` a repassé sur
le PC les six contrôles HTTP et les 45 contrôles Chromium avec JSON.
Les deux services réels ont utilisé des données synthétiques retirées
après l’essai. Le rejeu académique sur cette API a aussi vérifié 93 échanges,
44 opérations OpenAPI et dix contrôles d’exécution.
La révision API `6f2e90d` modifie la vérification de traces du job MongoDB.
Elle a repassé les mêmes contrôles sur le PC avec le Web `bdf6063`.
[Reçu de la paire](../../evidence/public/enterprise-2.1-candidate-20261122.json).

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

Sur l’API `15a894e`, les plafonds de sessions, d’entrées privées, de prêts
et de réservations s’appliquent désormais aux deux moteurs. Dans MongoDB,
un dépassement renvoie HTTP 503 et annule la transaction. Les 62 tests
ciblés sur le commit exact ont exercé les frontières avec MongoDB 8.0.34
et une identité applicative SCRAM limitée. La suite complète du contenu
commité totalise 627 tests et 35 sous-tests réussis. Il faut encore disposer
d’une place dans le registre pour créer le compte de reprise à la limite
de 10 000 utilisateurs.
[Reçu des contrôles de capacité](../../evidence/public/enterprise-2.1-candidate-20261122.json).

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

Le commit documentaire `55cab7b` a été reconstruit deux fois sur chacun
des runners Windows et Ubuntu. Les deux archives ont passé 5 974 vérifications
de liens chacune, avec 60 pages HTML et le PDF Enterprise de même empreinte.
Le job Chromium Ubuntu a réussi 213 contrôles. Après publication, les
415 fichiers publics servis en HTTPS ont tous correspondu aux octets
qualifiés. Chrome a réussi 217 contrôles sur le portail hébergé.
[CI documentaire](https://github.com/HyMathew/cinevault-infra-report/actions/runs/45034193153) ·
[Publication](https://github.com/HyMathew/cinevault-infra-report/actions/runs/45034848105) ·
[Reçu du portail](https://hymathew.github.io/cinevault-infra-report/build-receipt.json).

La première édition 2.1, d'empreinte `9c891e53…`, possède une attestation
Sigstore vérifiée par un job en lecture seule. Le contrôle lie ce PDF, le
workflow, la branche et le commit `6c983f0`. Le PDF corrigé par la revue
universitaire a été reproduit sur Windows et Ubuntu et possède sa propre
attestation au commit `c26b506`. Deux jobs distincts y ont rejoué le corpus
académique sur l'API candidate. Les huit archives de ce run ont été vérifiées.
[Premier run de signature](https://github.com/HyMathew/cinevault-infra-report/actions/runs/44954701826) ·
[Rejeu et signature du rapport corrigé](https://github.com/HyMathew/cinevault-infra-report/actions/runs/44956333500).

Une sonde locale sur l’API `4882c7f` et le Web `bdf6063` a vérifié TLS 1.3
et les attributs des cookies à travers Caddy avec une CA privée. Les clients
natifs ont refusé une CA et un nom d’hôte incorrects. Un Chromium isolé,
sur l’API `15a894e` et le Web `bdf6063`, a également refusé ces deux cas.
Avec la CA privée chargée dans le conteneur jetable, la connexion
et l’accès au catalogue ont réussi en TLS 1.3. Chromium a reçu des
cookies de session `Secure`, `HttpOnly` et `SameSite=Lax`.
La qualification Swarm et la promotion applicative restent ouvertes.
[Reçu HTTPS local](../../evidence/public/enterprise-2.1-candidate-20261122.json).

Cinq CVE OpenSSL de gravité haute bloquent le contrôle image Web au commit
`bdf6063`. La v1 dispose de sa
[qualification historique](../validation-current.md).
[Contrôle image Web](https://github.com/HyMathew/cinevault-web/actions/runs/45033494493).
