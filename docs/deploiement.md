# Déploiement et exploitation

## État actuel

Le socle Compose a été testé localement ; une stack Enterprise distincte a été déployée et contrôlée sur trois VM le 8 novembre2026. Voir la [procédure Enterprise et ses limites](deploiement-swarm-enterprise.md). Les paragraphes qui suivent conservent la procédure pédagogique initiale ; leurs modèles de secrets et d'images ne décrivent pas la stack Enterprise réellement utilisée.

## Préconditions de la procédure pédagogique initiale

Pour une nouvelle installation, relever trois VM distinctes : un manager et deux workers, avec leurs capacités réelles. Vérifier Docker Engine et la méthode de distribution des images avant toute modification. La présence d'une procédure ne prouve pas son exécution sur un autre environnement.

Les deux dépôts `cinevault-api` et `cinevault-web` doivent se trouver à côté de `cinevault-infra-report` pour les chemins relatifs de Compose. Images : API sur 8000 avec `GET /health`, web sur 5000 avec `GET /health`. La sonde web indique le fonctionnement du processus, pas la disponibilité de l'API. L'API n'a aucun port publié par défaut.

## Configuration locale Compose en JSON

`compose.yaml` construit les images depuis les dépôts voisins, monte leur répertoire `app` en lecture seule pour le développement, conserve les données dans un volume nommé et publie le web sur `127.0.0.1:8080`. Le montage du code ne garantit pas un rechargement automatique ; redémarrer ou reconstruire selon les fichiers modifiés. L'API utilise `/data/films.json` et doit pouvoir écrire en UID/GID 10001. Un volume neuf bénéficie normalement du contenu et des permissions initiaux de l'image ; vérifier effectivement les droits, notamment si le volume existe déjà.

Fournir `SECRET_KEY` dans l'environnement du processus à partir d'une source sûre, avec une valeur aléatoire d'au moins 32 octets, stable entre redémarrages. La validation du Web refuse une clé manquante ou trop courte au démarrage. Garder cette valeur hors dépôt, captures et commandes enregistrées. L'environnement d'un conteneur est consultable par un administrateur Docker. Dans cette configuration, le navigateur utilise HTTP sur la boucle locale et `COOKIE_SECURE` vaut `false`. Réserver `COOKIE_SECURE=true` à un point d'accès HTTPS.

Après avoir vérifié les prérequis et la clé, les opérations prévues sont :

```sh
docker compose -f compose.yaml config --quiet
docker compose -f compose.yaml up --build --wait --wait-timeout 90
docker compose -f compose.yaml ps
docker compose -f compose.yaml logs --tail 100
```

Ouvrir `http://127.0.0.1:8080/page-simple`, ajouter un film depuis
`/films/nouveau`, puis le retrouver dans `/films` après une recréation
des services. Docker conserve le volume nommé lors d’un `down` sans
`--volumes`. Identifier et sauvegarder les données avant toute suppression
de volume.

### Développement local Enterprise avec JSON v2

Arrêter le projet pédagogique avant de réutiliser le port 8080.
Employer un nom de projet distinct pour obtenir son propre volume.
Fournir les chemins absolus de trois fichiers privés distincts via
`CINEVAULT_AUTH_KEY_FILE`, `CINEVAULT_WEB_KEY_FILE` et
`CINEVAULT_CLIENT_CONTEXT_KEY_FILE`. Chaque fichier contient une valeur
aléatoire d’au moins 32 octets. Les fichiers doivent rester lisibles
par l’UID 10001 dans les conteneurs concernés. Sous Docker Linux, les
droits et le propriétaire du fichier source s’appliquent au montage.
Sous Docker Desktop, protéger le répertoire par les ACL du poste et
contrôler la lecture depuis les conteneurs. Le profil Enterprise lit
la clé de session depuis son fichier.

Dans un projet neuf, préparer le magasin JSON v2 avant le premier
démarrage. Le bootstrap demande les identifiants de l’administrateur
dans un terminal et masque son mot de passe.

```sh
docker compose -p cinevault-local-v2 -f compose.yaml -f compose.enterprise.yaml build
docker compose -p cinevault-local-v2 -f compose.yaml -f compose.enterprise.yaml run --rm --no-deps cinevault-api python -c "from app.storage_v2 import V2Store; V2Store('/data/enterprise.json').initialize()"
docker compose -p cinevault-local-v2 -f compose.yaml -f compose.enterprise.yaml run --rm --no-deps cinevault-api python -m app.bootstrap --store /data/enterprise.json
docker compose -p cinevault-local-v2 -f compose.yaml -f compose.enterprise.yaml up --wait --wait-timeout 90
```

Pour un volume existant, reprendre avec `up` après vérification de
l’état du magasin. Utiliser la [procédure de staging MongoDB](staging-mongodb.md)
pour le déploiement privé sur Swarm.
[Secrets Compose](https://docs.docker.com/compose/how-tos/use-secrets/).

Le 26 novembre, les deux profils ont démarré sur Docker Desktop
depuis les clones GitHub de l’API `05171fd` et du Web `b6b67aa`.
Chrome a créé un film dans chaque profil. Après `down` puis `up`,
les nouvelles tâches ont repris le volume et affiché le même film.
Les inspections ont confirmé les montages de code en lecture seule
et le seul port Web publié sur la boucle locale.
[Reçu des deux profils Compose](../evidence/public/compose-clean-clone-20261126.json).

## Swarm distribué

Avant toute installation ou jonction, relever pour chaque VM son OS, ressources, interfaces, routes et accès sortants ; mesurer les échanges entre les trois nœuds. Vérifier les flux TCP 2377 pour le contrôle Swarm, TCP et UDP 7946 pour la découverte, et UDP 4789 pour l'Overlay, sans affirmer qu'ils sont ouverts avant mesure. Suivre les règles réseau de l'environnement ; ne pas désactiver globalement les protections. Protéger l'accès au socket Docker : il confère des privilèges élevés.

Construire les deux images à partir du code audité et des dépendances verrouillées, puis les rendre accessibles à chaque worker par un registre autorisé. Idéalement référencer les images par digest immuable dans `CINEVAULT_API_IMAGE` et `CINEVAULT_WEB_IMAGE` ; un tag seul peut évoluer. Le registre doit être joignable depuis les nœuds et toute authentification doit être gérée sans publier de jeton. Les fichiers locaux du poste de développement ne sont pas automatiquement transférés aux nœuds. Vérifier les images et les droits de tirage avant déploiement.

Sur le manager, après identification certaine des nœuds, attribuer le label `cinevault=api` au worker qui gardera les données et `cinevault=web` au worker de présentation. Les contraintes de `stack.yaml` attendent ces labels. Une étiquette manquante laisse la tâche en attente. Ne pas marquer plusieurs nœuds API sans stratégie de stockage partagé contrôlée : un volume Docker `local` est propre à chaque hôte et peut apparaître vide ailleurs. Un seul manager et une seule réplique API ne constituent pas une solution haute disponibilité.

La pile exige `CINEVAULT_API_IMAGE`, `CINEVAULT_WEB_IMAGE` et `SECRET_KEY` dans l'environnement de la commande de déploiement. Les variables d'environnement du service sont visibles aux administrateurs Docker, et la configuration calculée peut afficher la clé ; ne pas enregistrer ou partager la sortie interpolée. Pour une exploitation plus exposée, adapter l'application à la lecture d'un secret Docker depuis un fichier et revalider l'ensemble avant déploiement. Une simple variable d'environnement n'est pas un Docker secret.

```sh
docker stack config -c stack.yaml >/dev/null
docker stack deploy -c stack.yaml cinevault
docker stack services cinevault
docker stack ps cinevault
docker node ls
```

Le port web 8080 est publié en mode `host` sur le worker où la tâche tourne : il peut être accessible sur ses interfaces réseau, selon leur filtrage. Il n'est pas automatiquement limité à localhost. Vérifier l'exposition avant de le rendre accessible ; ajouter une terminaison HTTPS et des contrôles d'accès adaptés avant toute exposition à un réseau non fiable. L'Overlay proposé n'active pas à lui seul le chiffrement applicatif ou l'authentification de l'API. Les services conteneurisés embarquent leur code ; aucun montage de code du poste n'est prévu dans la pile.

## Redéploiement et panne

Une mise à jour utilise des images vérifiées et des références explicitement choisies. L'API reste à une seule réplique et sa stratégie `stop-first` évite le chevauchement des tâches pendant une mise à jour. Vérifier les tâches et les journaux, puis rejouer les tests fonctionnels ; un état `Running` ne prouve pas le parcours complet. Si le nœud API ou son disque disparaît, le service et son volume local ne migrent pas de manière sûre automatiquement : restaurer une sauvegarde contrôlée sur un nœud identifié avant de modifier les labels et de redéployer. Ne jamais initialiser un fichier vide par-dessus un fichier existant ou corrompu.
