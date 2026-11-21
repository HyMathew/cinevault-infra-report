# Mesures API sur JSON et MongoDB

Le 21 novembre 2026, le même code API `a500e245` a été testé sur VM3 x86_64
avec deux CPU logiques, Python 3.12.3, Flask 3.1.3, Werkzeug 3.1.9 et
PyMongo 4.19.0 sans extension C. MongoDB 8.0.34 tournait dans un conteneur
isolé sans port hôte, limité à 0,75 CPU et 768 Mio. Les deux modes ont
utilisé successivement un serveur WSGI multithread sur la boucle locale
de cet espace réseau. L'API s'exécutait sous UID 1000 côté hôte.

Les jeux synthétiques comprennent respectivement 120 films et 358
exemplaires, puis 600 films et 1 798 exemplaires. Les fichiers source
contenant le même état par paire pesaient 124 458 et 618 190 octets.
La campagne a utilisé un espace de qualification dédié. L'import transactionnel
a produit la cible MongoDB depuis le même document initial. La source et
sa copie de sauvegarde ont été comparées à l'octet près à la fin.

## Latences p95 en millisecondes

Chaque ligne représente un groupe de requêtes mesurées, avec une phase
d'échauffement exclue. La latence inclut la connexion HTTP locale, la
réponse et sa lecture. Les écritures sont 24 créations de favoris distinctes.
Les quatre autres scénarios contiennent 40 requêtes chacun. Les 736 réponses
mesurées ont passé leurs assertions de statut, contenu et effectifs.

| Scénario | Clients concurrents | JSON 120 films | MongoDB 120 films | JSON 600 films | MongoDB 600 films |
|---|---:|---:|---:|---:|---:|
| Page de 20 films | 1 | 10,8 | 13,2 | 39,8 | 12,6 |
| Page de 20 films | 4 | 267,9 | 42,1 | 819,0 | 47,1 |
| Recherche filtrée | 4 | 284,1 | 40,6 | 829,5 | 43,7 |
| Fiche film | 4 | 272,2 | 19,6 | 810,1 | 20,2 |
| Création d'un favori | 4 | 1 038,9 | 574,2 | 2 141,3 | 708,9 |

À un client sur la petite fixture, la page JSON a le p95 le plus faible.
Sous quatre clients, les centiles élevés du JSON augmentent avec la taille
du document. Les écritures restent plus coûteuses que les lectures pour les
deux moteurs. Les données indiquent où approfondir l'analyse des attentes
en concurrence. Les résultats ne séparent pas le coût de chaque verrou,
validation ou opération de disque.

Le pic RSS du seul processus API était de 100,8 et 103,8 Mio pour JSON,
contre 109,7 et 109,9 Mio pour MongoDB. Cette mesure inclut la connexion
initiale du membre avec Argon2 et exclut la mémoire du processus MongoDB.
Le rapport conserve aussi le temps CPU cumulé de l'API.

Une seule campagne par jeu a été réalisée. Cette mesure ne fixe pas de
SLO et ne couvre ni le réseau Overlay, ni le navigateur, ni le débit de
sauvegarde ou la consommation totale des deux moteurs. Les écritures sont
synthétiques et le moteur, ses volumes et les dossiers sont tous retirés
après l'essai. [Reçu et résultats détaillés](../evidence/public/mongodb-performance-observability-20261121.json).
