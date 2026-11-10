# Étude MongoDB — capacités élémentaires exécutées

Essai réel du 10 novembre 2026, de 13:32:21 à 13:32:59 UTC. Il répond au préalable de faisabilité de l’[ADR 0001](../adr/0001-json-mongodb.md). Le backend de l’application demeure JSON ; aucun repository MongoDB CineVault n’est annoncé opérationnel par cette étude.

## Dispositif

L’administration s’effectue depuis Windows par SSH à clés épinglées. Un conteneur temporaire neuf utilise MongoDB Community 8.0.34, image `linux/amd64` identifiée par `sha256:1d7a2d487c6465ea022474b90b65d6c91bb600b421b65880d8c6e141d6122200`. Le binaire a confirmé cette version. Le service stable et son volume ne sont pas montés dans cet essai.

Le processus s’exécute sous UID/GID 999, racine en lecture seule, toutes capabilities retirées, `no-new-privileges`, 128 processus maximum, 0,75 CPU et 768 Mio de mémoire sans swap additionnel. La cache WiredTiger est fixée à 0,256 Go. Un volume de données et un volume de keyfile sont neufs, étiquetés et distincts. Le conteneur possède `NetworkMode=none`, écoute sa seule boucle locale et ne publie aucun port hôte.

Les identifiants de maintenance et d’application ainsi que le keyfile sont générés pour l’essai et ne sont pas reproduits dans les journaux. L’identité applicative ne possède que find/insert/update/remove sur la collection synthétique de l’essai. Les opérations utilisent mongosh dans le conteneur, pas le frontend ni un client PyMongo.

## Résultats constatés

| Contrôle exécuté | Résultat |
| --- | --- |
| Version du binaire épinglé | 8.0.34 confirmée |
| Initialisation du replica set et attente du primaire | Un seul membre devenu primaire |
| Lecture anonyme de la collection protégée | Refus code 13 ; un ping public n’est pas utilisé comme preuve d’autorisation |
| Création d’utilisateur par l’identité applicative | Refus code 13 |
| Document ne satisfaisant pas le `$jsonSchema` | Refus code 121 |
| Transaction à deux documents, snapshot et écriture majority | Commit réussi ; les deux documents présents |
| Transaction à deux documents annulée explicitement | Aucun des deux documents annulés présent |
| Redémarrage du même conteneur et volume | Primaire retrouvé ; données persistantes et authentification applicative conservées |
| Nettoyage | Conteneur et deux volumes supprimés après contrôle de leurs étiquettes propriétaires |
| Service API stable avant/après | Même tâche restée healthy |

La consommation relevée en fin d’essai est **118,9 Mio sur 768 Mio et 1,90% CPU**. C’est un échantillon sur quelques documents ; il ne permet aucune conclusion sur la mémoire de pointe, la latence applicative, un catalogue volumineux ou une charge concurrente.

## Provenance et limites

Le programme de contrôle et son reçu JSON original sont retenus hors dépôt public dans la collection d’artefacts du projet. SHA-256 du programme : `5256e39377a016847043a084b68d3955d9488b2f70cdeb0334214c042f045dd0`. Ils décrivent les assertions et les ressources contrôlées ; aucun résultat n’est reconstruit par une capture de terminal.

Cet essai ne couvre pas le client PyMongo, la couche de persistance CineVault, les règles de prêts/FIFO/dernier administrateur, une migration, les sauvegardes/restaurations, les performances de charge, le DNS Swarm ou les contrôles depuis les autres hôtes. Un replica set à un membre ne possède pas de redondance physique. L’image reste à analyser pour les vulnérabilités avant intégration. Ces étapes restent ouvertes dans la mission 2.0.

## Modèle documentaire et client Linux : essais suivants

Le modèle de l’API, commit
[`aa3e41a`](https://github.com/HyMathew/cinevault-api/tree/aa3e41a65684b3920863968b1bf50f0c7a74d486/app/persistence),
possède maintenant un codec BSON, dix validateurs dérivés du schéma académique et
22 spécifications d’index. Un essai réel du 10 novembre, 14:08:44–14:09:21 UTC,
a installé tous ces validateurs et index sur le moteur retenu. Chaque collection
a accepté son entité synthétique, avec références cohérentes prévalidées côté
application. Le serveur a refusé les types/champs invalides (121) et les doublons
username, copie active, prêt ouvert, attente, prêt fulfilled, entrée privée
normalisée et reçu (11000). L’historique d’un prêt retourné pour la même copie
reste accepté, ainsi qu’une expansion Unicode casefold de 240 caractères.

Les premiers essais du harnais ont échoué ; ils ont révélé une lecture EJSON
relaxed perdant les types Int64, puis une portée de fonction dans mongosh.
Le harnais a été corrigé et les reçus d’échec conservés, sans affaiblir le modèle
ou les index. Le résultat réussi n’efface pas ces tentatives.

La distribution officielle PyMongo 4.19.0 ne fournit pas de wheel musllinux.
Deux constructions hors ligne depuis le sdist vérifié ont produit la même wheel
locale CPython 3.13/Linux x86_64, extensions C désactivées, SHA-256
`33798dd77ab3f174cd711b040406422a5f875f28149da335bf27c7bc1aa1dcd7`.
Son installation avec dnspython 2.9.2 et hashes vérifiés, imports, corpus BSON et
`pip check` ont réussi sous Alpine musl et UID 10001. Il ne s’agit pas d’une wheel
universelle officielle. La recette de livraison et ses notices restent à intégrer
au build applicatif avant activation.

Un autre essai réel, 14:09:57–14:11:05 UTC, a connecté ce client PyMongo à MongoDB
8.0.34 dans un conteneur partageant seulement l’espace réseau `none` du serveur.
Aucun port hôte ni accès Internet. Les privilèges applicatifs étaient limités aux
dix collections ; maintenance par identité distincte.

| Contrôle exécuté via PyMongo | Résultat |
| --- | --- |
| Connexion authentifiée, primaire et driver pure Python | Réussis sous CPython 3.13.18/Alpine musl |
| Lecture d’un horodatage de métadonnée égal à 2^53 | Int64 exact, sans arrondi |
| Création d’utilisateur ou d’index par l’application | Refus 13 |
| Écriture d’une année booléenne | Refus natif 121 |
| Transaction film et copie, snapshot/majority | Deux documents commités |
| Nouvelle transaction film et copie annulée | Aucun des deux documents présent |
| Nettoyage | Client, serveur et deux volumes neufs supprimés après contrôle des propriétaires |
| API stable | Même tâche healthy avant/après |

Reçu original du dernier essai : SHA-256
`4f5cde78b52e489a66026c3259d40a96a834be44a6b3c728e1e17f7b0b610c44` ;
programme de contrôle :
`6fb2d70cd22999cb469b88df859d592f108196999d64be38b1b36b44e2e8cf2d`.
Ils sont conservés dans les artefacts privés du projet. Le RSS échantillonné du
serveur était 108,7 Mio sur 768 Mio : toujours aucune mesure de pointe ou de charge.

Ces résultats établissent la compatibilité élémentaire du modèle et du driver.
Les UoW/repositories et contrats REST deux moteurs, les courses FIFO/dernier admin,
les reprises de commit, migrations, sauvegardes/restaurations, performances et
déploiement restent à réaliser selon le [plan dédié](MONGODB_IMPLEMENTATION_PLAN.md).
