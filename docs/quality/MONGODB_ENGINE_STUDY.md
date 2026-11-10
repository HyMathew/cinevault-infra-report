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
