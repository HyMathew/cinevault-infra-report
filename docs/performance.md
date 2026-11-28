# Mesures sur JSON et MongoDB

Les mesures API sur RemoteLabz et les navigations Chromium sur Docker
Desktop décrivent deux environnements et deux charges distinctes.

## Campagne API sur RemoteLabz

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

### Latences p95 en millisecondes

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

## Navigation Chromium avec les images du candidat 2.1

La campagne utilise l'API `8205e0c`, le Web `7eb4dc3`, Caddy et
MongoDB 8.0.38, chargés par digest dans Docker Desktop sur un PC Windows
équipé d'un i7-12700H. Le moteur Docker 29.9.3 voit 20 CPU logiques et
15,5 Gio de RAM. Les limites API, Web et MongoDB sont respectivement
1, 1 et 0,75 CPU, et 384, 256 et 768 Mio. Le proxy dispose de
0,5 CPU et 128 Mio. Les réseaux sont internes et le PC ne publie
aucun port. Chromium 156.0.8078.4 vérifie le certificat privé et
utilise TLS 1.3.

Le jeu synthétique de 618 190 octets contient 600 films et 1 798
exemplaires. Les deux moteurs partent du même document vérifié par
SHA-256. Le test charge une page de 20 films, une recherche sur le mot
`festival` donnant 119 résultats, et la fiche du même film avec une
session ouverte. Chaque combinaison scénario, largeur et moteur reçoit
cinq échauffements, puis vingt navigations séquentielles, soit 240
échantillons pour un seul client. Sur vingt mesures de latence, le p95
est la dix-neuvième valeur dans l’ordre croissant. Le reçu réunit
également les médianes et les maxima. Les fenêtres de 390 et 1 280 px
utilisent le même PC.

| Scénario et largeur | JSON premier octet p95 | JSON chargement p95 | MongoDB premier octet p95 | MongoDB chargement p95 |
| --- | ---: | ---: | ---: | ---: |
| Catalogue, 390 px | 88,9 ms | 111,1 ms | 30,8 ms | 55,4 ms |
| Recherche, 390 px | 85,9 ms | 109,7 ms | 32,3 ms | 57,4 ms |
| Fiche, 390 px | 413,5 ms | 440,3 ms | 69,1 ms | 89,2 ms |
| Catalogue, 1 280 px | 89,2 ms | 111,8 ms | 36,4 ms | 61,8 ms |
| Recherche, 1 280 px | 93,3 ms | 121,6 ms | 38,6 ms | 67,3 ms |
| Fiche, 1 280 px | 268,5 ms | 290,4 ms | 101,4 ms | 119,6 ms |

Le premier octet est mesuré depuis `requestStart`. Le chargement court
du début de la navigation à `loadEventEnd`. La réponse HTML représente
15 166 octets pour le catalogue, 15 543 pour la recherche et 4 732 pour
la fiche avec les deux moteurs.

Le maximum mémoire cgroup observé depuis le démarrage de l'API est de
175,5 Mio avec JSON et de 146,1 Mio avec MongoDB. Le conteneur MongoDB
atteint 768 Mio sur son propre cgroup, pour une limite de 768 Mio.
Cette mesure inclut le cache et les fichiers temporaires du conteneur.
La taille apparente après l'essai est de 618 801 octets pour le fichier
JSON et de 210 722 509 octets pour le répertoire MongoDB, qui contient
les fichiers WiredTiger et l’oplog du replica set. L'essai utilise des
tmpfs. Ces tailles décrivent le déploiement de test et sa configuration.

### Rendu et ressources transférées

Une seconde série, exécutée dans l'ordre inverse des moteurs, observe
trois échauffements puis cinq relevés de rendu par scénario, largeur
et moteur, soit 60 échantillons. Elle retient le dernier candidat LCP
reçu 500 ms après le chargement. Le CLS correspond à la plus forte
fenêtre de décalages sans interaction dans cette durée.
[LCP](https://web.dev/articles/lcp) · [CLS](https://web.dev/articles/cls).

| Scénario et largeur | LCP médian JSON | LCP médian MongoDB |
| --- | ---: | ---: |
| Catalogue, 390 px | 116 ms | 68 ms |
| Recherche, 390 px | 116 ms | 64 ms |
| Fiche, 390 px | 256 ms | 96 ms |
| Catalogue, 1 280 px | 116 ms | 68 ms |
| Recherche, 1 280 px | 116 ms | 72 ms |
| Fiche, 1 280 px | 256 ms | 108 ms |

Le CLS est de zéro dans les 60 observations. L'excédent au-delà de 50 ms
des tâches longues commençant après le FCP est également nul dans cette
fenêtre. Après échauffement, le document et les deux ressources
représentent 42 946 octets encodés pour le catalogue, 43 323 pour la
recherche et 32 512 pour la fiche. Les tailles transférées relevées par
le navigateur sont respectivement de 43 846, 44 223 et 33 412 octets.
Le périmètre couvre le chargement sur le PC de test.
Une mesure de TBT Lighthouse, d'INP ou d'usage réel nécessiterait une
campagne distincte. [TBT](https://web.dev/articles/tbt).

[Échantillons et conditions de mesure](../evidence/public/chromium-backend-performance-20261125.json).

## Charge HTTPS mixte à quatre clients

Sur le même PC Windows et le catalogue synthétique de 600 films,
quatre clients HTTP ont exercé Caddy, le Web et l’API sur des réseaux
internes Docker Desktop, avec vérification du certificat TLS 1.3.
Chaque client utilisait une session distincte du même compte et des
films différents pour ses favoris. Deux tours d’échauffement précédaient
dix tours mesurés. Un tour comprenait le catalogue, la recherche, une
fiche, l’ouverture du formulaire et son POST. La latence couvre l’envoi
et la lecture intégrale de la réponse HTTP.

Les deux passes MongoDB ont terminé. Les deux passes JSON de la série
alternée se sont arrêtées sur HTTP 503, l’une sur l’ouverture du
formulaire, l’autre sur une fiche. Le Web a mesuré respectivement
5 092 et 5 009 ms pour ces réponses. Un rejeu instrumenté distinct
avec JSON est allé au bout. Il donne un point de comparaison
exploratoire, avec 40 mesures par ligne et par passe.

| Requête | JSON, p95 du rejeu | MongoDB, p95 des deux passes |
| --- | ---: | ---: |
| Catalogue | 1 799 ms | 163–203 ms |
| Recherche | 708 ms | 177–179 ms |
| Fiche | 1 434 ms | 246–258 ms |
| Ouverture du formulaire | 2 451 ms | 163–173 ms |
| Ajout d’un favori | 1 693 ms | 213–218 ms |

Chaque passe terminée a retrouvé exactement 48 favoris, dont huit
créés pendant l’échauffement. Les journaux Web et API rapprochent
chaque POST de création de sa requête API. Un doublon volontaire
hors mesure a été refusé avec HTTP 409. Les limites CPU et mémoire,
les ressources observées et les données brutes figurent dans le reçu.
L’essai couvre cette charge fermée sur un seul hôte.
[Mesures HTTPS et résultats des passes interrompues](../evidence/public/mixed-https-baseline-20261126.json).

### Verrou de lecture du magasin JSON

L’API `31ee4ea` conserve le verrou pendant la lecture du fichier puis
valide les octets capturés après sa libération. Le test de concurrence
suspend le décodeur. Un écrivain termine entre la capture et la
validation, le lecteur retrouve la révision capturée et la lecture
suivante retrouve la nouvelle révision. Les transactions continuent
à valider et remplacer le fichier sous le verrou d’écriture.

Deux constructions locales sans cache ont donné le même manifeste.
Deux rejeux HTTPS sur cette image ont terminé sans HTTP 503 et
retrouvé chacun les 48 favoris attendus. Le p95 du catalogue est
compris entre 715 et 920 ms, et celui du formulaire entre 989 et
1 162 ms. Le p95 de la fiche et du POST varie dans les deux sens par
rapport au rejeu exploratoire. Ces deux passes sur un seul PC
ne fixent pas de garantie de capacité.
[Mesures sur le candidat JSON](../evidence/public/mixed-https-json-read-lock-20261126.json).

Le build Windows de ces deux premières passes utilisait les fins de
ligne du poste. Avec l’archive Git LF et le BuildKit épinglés en CI,
deux reconstructions locales sans cache ont reproduit le manifeste,
la configuration et toutes les couches de l’image API auditée.
Deux nouvelles passes à quatre clients ont utilisé les manifestes API
et Web exacts des scans CI. Elles ont chacune retrouvé les 48 favoris
attendus et terminé sans HTTP 503. Le p95 du catalogue est de 850 à
876 ms, celui du formulaire de 1 207 à 1 355 ms et celui du POST de
2 131 à 2 872 ms. La stabilisation observée sur ces passes coexiste
avec une latence d’écriture élevée sur cette fixture.
[Rejeu sur les manifestes exacts de la CI](../evidence/public/mixed-https-exact-ci-20261126.json).

## Projections HTTP de Signature

Le 28 novembre, l’API `244cd01` a servi les mêmes 600 films, 1 798
exemplaires et 500 comptes synthétiques avec JSON et MongoDB 8.0.38.
Chaque passe est repartie du même document. Le banc a alterné JSON,
MongoDB, MongoDB, JSON sur le poste Windows. L’API Flask utilisait
HTTP sur boucle locale et MongoDB tournait dans un réplica jetable
d’un membre, limité à 0,75 CPU et 768 Mio.

Pour chaque scénario et niveau de concurrence, cinq requêtes
d’échauffement précèdent 50 GET mesurés. Le temps client comprend
l’envoi, la lecture et le décodage JSON de la réponse. Le débit
compte les succès par seconde sur la fenêtre de chaque lot. L’annuaire
utilise la même session administrateur pour tous les clients de la passe,
avec une horloge applicative fixe. Le reçu
conserve les latences et les statuts des 1 600 requêtes mesurées,
toutes retournées en HTTP 200. Les deux moteurs ont renvoyé le même
corps JSON canonisé pour chaque scénario. Le contrôle initial avait
isolé un écart d’ordre dans les supports. La correction trie les
supports distincts par identifiant, comme dans MongoDB.

| Projection, quatre clients | JSON p95, ms | MongoDB p95, ms | JSON succès/s | MongoDB succès/s |
| --- | ---: | ---: | ---: | ---: |
| Catalogue avec disponibilité | 303–329 | 82–93 | 26–37 | 72–75 |
| Cinq suggestions | 315–561 | 35–50 | 28–40 | 112–180 |
| Fiche avec films apparentés | 309–311 | 35–52 | 30–44 | 116–196 |
| Annuaire filtré avec pagination et session admin | 1 315–2 431 | 416–810 | 9–14 | 27–33 |

Les intervalles correspondent aux deux passes par moteur, arrondies à
l’unité. À un client, le p95 du catalogue avec disponibilité était de
47–49 ms avec JSON et de 52–56 ms avec MongoDB. Les p50 et les durées
de chaque lot figurent dans le reçu. Les 50 observations par lot
donnent trop peu de valeurs dans la queue de distribution pour publier
un p99. La campagne couvre l’API seule et exclut le rendu Web, le TLS
et le réseau de staging.
[Résultats et empreintes des outils](../evidence/public/signature-http-projections-20261128.json).
