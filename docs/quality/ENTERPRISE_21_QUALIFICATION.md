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

La paire API `58b1200` et Web `bdf6063` a repassé les six contrôles HTTP,
les 45 contrôles Chromium et le rejeu des 93 échanges académiques sur le PC.
[Reçu de la paire exacte](../../evidence/public/enterprise-2.1-candidate-20261125.json).

Le 26 novembre, la sonde de la paire a rejoué les mêmes 45 contrôles
sur Firefox 157, Chromium 156 et Chrome 158 sous Windows avec l’API
`05171fd` et le Web `b6b67aa`. Les applications Flask servaient
des données JSON jetables via HTTP local. Les trois passages ont
couvert la connexion, les droits, les formulaires, le prêt, la
réservation et la reprise d’une création dont la réponse a été
coupée. Chaque passage a arrêté ses services et retiré les données
temporaires.

Avec Playwright installé selon `requirements-browser.txt`,
ajouter `--browser firefox` à `scripts/check_browser_pair.py`
après installation de Firefox via Playwright. Sans cette option,
la sonde continue de lancer Chromium. L’option `--browser-channel`
sélectionne un canal Chromium. Le couple Firefox et canal Chromium
est refusé avant le démarrage des services.
[Reçu des trois navigateurs](../../evidence/public/browser-pair-firefox-20261126.json).

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

Sur l'API `58b1200`, le scénario natif a expiré 501 réservations dans une
transaction et inscrit leurs événements d'audit en deux lots. La transaction
mesurée sur le PC a pris 3,18 secondes. Le runner GitHub a vérifié que le
rejet d'un lot avec un identifiant déjà utilisé préserve le journal et le
registre d'identités. La CI de la sauvegarde portable a réussi 47 tests
sous Windows et 46 sous Ubuntu, avec le seul cas propre à Windows ignoré
sous Ubuntu. Chaque runner a exécuté sept tests avec age.
[Reçu des contrôles natifs et de la sauvegarde](../../evidence/public/enterprise-2.1-candidate-20261125.json).

MongoDB 8.0.38 est disponible sous forme d'image Docker officielle. Le
manifest linux/amd64, sa configuration et les références au SBOM et à la
provenance Docker ont été comparés par empreinte. Sur le PC, le contrat natif
avec des privilèges applicatifs limités a réussi sur cette image exacte,
dont les 501 expirations. Le commit API `d02f27f` épingle ce digest pour la CI.
[Reçu de la version MongoDB](../../evidence/public/enterprise-2.1-candidate-20261125.json).

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

## Paire avec paquets Alpine verrouillés

Le 25 novembre, l'API `8205e0c` et le Web `7eb4dc3` ont repassé
les six contrôles HTTP et les 45 contrôles Chrome sur JSON. Le rejeu
académique a couvert 93 échanges et 44 opérations OpenAPI sur l'API.
Dans Docker Desktop, les deux images de ces commits ont démarré avec
MongoDB 8.0.38 et Caddy sur des réseaux internes sans port publié.
La migration de données synthétiques a créé 12 collections et 40
index. Son rejeu a réussi, et le compte applicatif a été refusé pour
l'administration de la base. La sonde HTTPS a confirmé TLS 1.3, le
catalogue migré et l'authentification avec cookies sécurisés.
Chromium a ouvert le catalogue après connexion et constaté les attributs
`Secure`, `HttpOnly` et `SameSite=Lax`. Avec sa vérification de
certificat active, il a refusé la CA inconnue. Le proxy a interrompu
le handshake pour un SNI absent de sa configuration. L’essai du 25
novembre a observé un point d’accès sans HSTS. Le 26 novembre,
Chromium a confirmé l’activation HSTS sur la variante privée, et
un test Swarm a vérifié la mise à jour et le retour arrière.
[Reçu HSTS](../../evidence/public/swarm-https-hsts-20261126.json).

Deux builds Windows et un build GitHub Actions Ubuntu par image
ont reproduit les mêmes digests OCI. Les contrôles d'image restent
bloqués par cinq CVE OpenSSL classées High par Grype. La publication
applicative et la qualification de la paire sur Swarm restent ouvertes.
La v1 dispose de sa [qualification historique](../validation-current.md).
[Reçu de la paire verrouillée](../../evidence/public/enterprise-2.1-alpine-runtime-20261125.json) ·
[Contrôle image API](https://github.com/HyMathew/cinevault-api/actions/runs/45667428307) ·
[Contrôle image Web](https://github.com/HyMathew/cinevault-web/actions/runs/45668181740).

## Restauration chiffrée et parcours HTTP sur le candidat actuel

Le 26 novembre, l’API `05171fd` a écrit un film et un favori dans
MongoDB 8.0.38. Après authentification de l’archive age depuis
Windows et retrait de la source, une nouvelle instance MongoDB a
retrouvé exactement l’inventaire de 15 documents et 40 index. L’API
a retrouvé le même film et le même favori. Le Web `b6b67aa` a
affiché le film et le profil après connexion HTTPS. L’essai a utilisé
des données synthétiques et des réseaux internes sur Docker Desktop.
[Reçu de la restauration et des sondes HTTP](../../evidence/public/mongodb-backup-http-20261126.json).

## Reprise MongoDB avec quarantaine des anciens comptes

La CLI de l’image API `05171fd` a copié une source MongoDB 8.0.38
vers deux bases provisionnées séparément. Elle a conservé le catalogue,
le prêt actif, le favori, le reçu d’idempotence et l’audit historique.
Chaque cible est passée de la révision source 13 à la révision 14.
Les trois anciens comptes et leurs sessions ont été révoqués et la
réservation en attente a été annulée. L’API a refusé l’ancien mot de
passe et le jeton archivé avec HTTP 401. Le nouvel administrateur a
pu se connecter, consulter son profil et retrouver le film.

Le second essai a simulé une perte d’accusé au niveau Python après
l’écriture effective. La CLI a rendu le code 3 avec l’empreinte du
candidat. La réconciliation en lecture seule a confirmé cette
empreinte et en a refusé une autre. Sur les deux cibles, une empreinte
source erronée a laissé la cible vide et un nouvel `apply` a laissé
la cible remplie intacte. Les connexions MongoDB utilisaient TLS et
SCRAM-SHA-256. L’essai portait sur des données synthétiques et un
réplica local à un membre. Il n’a pas testé le basculement entre
plusieurs membres.
[Reçu de la reprise native](../../evidence/public/mongodb-quarantine-current-20261126.json).

## Élection MongoDB pendant une transaction d’écriture

Deux essais indépendants ont utilisé l’API `05171fd` et un réplica
MongoDB 8.0.38 de trois membres votants sur Docker Desktop. L’API
a envoyé une création d’exemplaire avec clé d’idempotence. Une sonde
du pilote a suspendu le traitement
après le premier accusé de l’insertion, avant le commit. À cet
instant, une lecture distincte ne voyait ni l’exemplaire ni le reçu.
Une connexion de maintenance a demandé au primaire de céder sa place
avec `replSetStepDown`, sans utiliser l’option de forçage.

La transaction a rencontré une erreur transitoire et a été rejouée
sur le nouveau primaire. L’appel HTTP d’origine a renvoyé 201 et la
base contenait un seul exemplaire et un seul reçu. Une nouvelle
soumission avec la même clé a rendu le même corps avec
`Idempotency-Replayed: true`. Les enregistrements métier sont restés
identiques lors de ce rejeu, qui a fait avancer la révision interne de
coordination. L’API a retrouvé sa santé et la session existante dans
le même processus.

Les trois membres utilisaient TLS et SCRAM. Ils partageaient un seul
hôte physique. Cet essai mesure une élection contrôlée, sans panne
d’hôte ni perte de quorum. Le réplica mono-membre du lab conserve
ses limites de redondance.
[Reçu de l’élection et du rejeu](../../evidence/public/mongodb-election-idempotency-20261126.json) ·
[Élections MongoDB 8.0](https://www.mongodb.com/docs/v8.0/core/replica-set-elections/).
