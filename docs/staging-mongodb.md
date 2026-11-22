# Staging MongoDB sur Swarm

La [stack de staging](../stack.mongodb-staging.yaml) vise des données synthétiques.
Utiliser le nom de stack `cvstage`. Le manager du laboratoire reste en Drain.
Le web est placé sur VM1. L'API et MongoDB occupent VM2. Cette topologie conserve
un replica set à un seul membre. Le volume local ne suit pas la tâche sur un autre
nœud.

Le réseau Overlay `front` relie le web à l'API. Le réseau Overlay `data` relie
l'API à MongoDB. Ils sont internes et chiffrés. MongoDB n'a aucune publication
de port. L'accès de vérification au web passe par une connexion SSH au worker
et un relais temporaire sur boucle locale. Le provider externe reste désactivé
dans ce staging isolé. [Réseaux Swarm](https://docs.docker.com/engine/swarm/networking/).

## Préparer les entrées

- Vérifier les labels de placement, le budget mémoire, CPU et disque, et la santé
  de la stack déjà en service. Les limites de MongoDB et de l'API de staging
  totalisent 1 152 Mio sur VM2. La disponibilité mémoire varie avec la charge.
- Geler les références des deux images qualifiées dans `CINEVAULT_STAGE_API_IMAGE`
  et `CINEVAULT_STAGE_WEB_IMAGE`. Pour une image de registre, utiliser le digest
  de manifeste dont le digest de configuration correspond au reçu de scan.
  [Vérifier le manifeste dans le registre](#vérifier-les-images-du-registre).
- Préparer les deux volumes neufs sur VM2. `cvstage_mongo_data_v1` est réservé
  à UID 999. `cvstage_api_sidecars_v1` appartient à UID 10001. Ce dernier contient
  uniquement la fenêtre locale d'admission et le cache éventuel. Garder un seul
  réplica API avec ce volume.
- Préparer une CA de staging et un certificat serveur dont les SAN DNS incluent
  `mongo.cv-stage.internal` et `localhost`. Monter uniquement le certificat
  public de la CA et le PEM serveur. Conserver la clé de CA hors Swarm. L'option
  qui autorise les clients sans certificat client maintient le TLS côté serveur.
  L'identité du client repose sur SCRAM-SHA-256.
  [MongoDB et TLS](https://www.mongodb.com/docs/manual/tutorial/configure-ssl/).
- Créer les sept secrets du manifeste à partir d'entrées privées. Injecter les
  valeurs par entrée standard ou depuis des fichiers privés. Le secret URI
  applicatif désigne `mongo.cv-stage.internal:27017` avec
  `authSource=admin`, `authMechanism=SCRAM-SHA-256`,
  `replicaSet=cv-stage-rs`, `tls=true` et
  `tlsCAFile=/run/secrets/mongo_ca`. Le fichier d'URI contient le seul compte
  CRUD. La base configurée dans l'API s'appelle `cinevault_stage`.

## Vérifier les images du registre

Utiliser le digest de configuration `scan_provenance.archive_config_digest`
de chaque reçu. La [vérification GHCR](../scripts/verify_registry_image.py)
demande uniquement les manifestes publics par digest, recalcule leurs
empreintes et compare la configuration au scan. Si le reçu contient un digest
OCI de plateforme, le fournir aussi avec `--platform-manifest-digest`.

```sh
python3 scripts/verify_registry_image.py \
  --reference "$CINEVAULT_STAGE_API_IMAGE" --config-digest "$CINEVAULT_STAGE_API_CONFIG_DIGEST"
python3 scripts/verify_registry_image.py \
  --reference "$CINEVAULT_STAGE_WEB_IMAGE" --config-digest "$CINEVAULT_STAGE_WEB_CONFIG_DIGEST"
```

Un écart de digest entraîne le code de sortie 1. Le contrôle s'ajoute au
scan et à la vérification ultérieure du tirage et de l'identité sur les
workers. Les deux références v1 sont les seuls exemples déjà contrôlés en
ligne avec ce script. [Reçu GHCR v1](../evidence/public/registry-manifest-check-20261122.json) ·
[Spécification OCI Distribution](https://github.com/opencontainers/distribution-spec/blob/main/spec.md).

## Démarrer par étapes

Valider la configuration sur le manager. Avec
`CINEVAULT_STAGE_APP_REPLICAS=0`, seule la tâche MongoDB démarre.

```sh
docker stack config -c stack.mongodb-staging.yaml
docker stack deploy --resolve-image always -c stack.mongodb-staging.yaml cvstage
docker stack services cvstage
```

Depuis le conteneur MongoDB neuf, initialiser le replica set avec
`mongo.cv-stage.internal:27017` comme membre unique. La session locale
d'initialisation utilise TLS, `localhost` et la CA montée. Attendre l'élection
avant de créer le premier administrateur de maintenance. La sonde MongoDB du
manifeste teste le processus et la négociation TLS. L'état primaire et
l'authentification restent des contrôles séparés.

Le réseau `data` accepte le conteneur opérateur temporaire. Lui seul reçoit
l’URI de maintenance pendant le provisionnement.

Provisionner la base vide avec `app.persistence.mongo_maintenance.provision`
depuis le compte de maintenance. Préparer des identités séparées pour l'API et
la migration. Accorder à l'application `find`, `insert`, `update` et
`remove` sur la seule base de staging. Maintenir les écrivains arrêtés pendant
l'import et le contrôle de l'inventaire. Utiliser le
[pilote de migration et retour arrière](https://github.com/HyMathew/cinevault-api/blob/quality/cinevault-v2/docs/mongodb-migration.md).

Une fois la base cohérente, appliquer le même manifeste avec
`CINEVAULT_STAGE_APP_REPLICAS=1`. Contrôler l'ID d'image de chaque tâche, son
placement et les montages effectifs des secrets. Comparer les services et le
stockage de la stack stable à leur état initial.

## Critères de vérification

- Depuis l'API, vérifier le DNS, le certificat du serveur, SCRAM et `/health`.
  Tester également refus de CA, de nom de serveur et de privilèges insuffisants.
- Depuis le web, vérifier HTTP vers l'API sur `front` et l'absence de chemin
  direct vers MongoDB. Contrôler les ports depuis les trois VM et le PC.
- Exercer les parcours métier après la migration. Vérifier les refus d'accès,
  l'idempotence, la persistance après redémarrage et le retour JSON avec les
  écritures réalisées pendant le basculement.
- Relever la mémoire, le CPU, le trafic Overlay et le disque autour des essais.
  Conserver les résultats avec les identifiants exacts des références testées.

Le 21 novembre 2026, le CLI du manager a rendu cette configuration avec zéro
puis un réplica de chaque application. Les deux rendus contiennent trois
services, deux réseaux internes chiffrés, zéro port publié et des secrets montés
en 0400. Cette vérification de configuration précède le déploiement du staging.
