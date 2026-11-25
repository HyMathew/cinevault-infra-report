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
- Construire et analyser l'image MongoDB décrite ci-dessous. Fixer
  `CINEVAULT_STAGE_MONGO_IMAGE` sur la référence chargée et vérifiée sur VM2.
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

Pour un candidat, déclencher le workflow `tests.yml` de chacun des dépôts
applicatifs sur `quality/cinevault-v2` avec l’entrée `candidate_commit`
égale au SHA complet souhaité. GitHub Actions exige que le SHA du job
corresponde à cette entrée. Le job de publication exige les suites
habituelles, dont le contrat MongoDB pour l’API, puis le build, le contrôle
de santé et le scan de l’image du même job. Il publie sous
`sha-<commit>` et enregistre le digest rendu par le registre.
Les workflows des dépôts officiels attestent ce digest, puis un job en
lecture seule vérifie la signature Sigstore et les identités de source et
de workflow. Conserver `image-audit` et `image-verified-provenance` du
même run. Le reçu de publication, l'inventaire Syft, le rapport Grype et
le sujet signé doivent correspondre avant de préparer les workers.
[Vérification GitHub CLI](https://cli.github.com/manual/gh_attestation_verify).

Les révisions comparées le 25 novembre ont produit un inventaire Syft de
50 composants pour l’API et de 48 pour le Web. Leurs rapports Grype se
rattachent aux mêmes digests de configuration. La publication reste bloquée
sur cinq CVE OpenSSL classées High par Grype.
[Qualification initiale des inventaires et des scans](../evidence/public/image-sbom-qualification-20261125.json).

Pour chacune des révisions API et Web qualifiées le 25 novembre, deux
constructions sans cache sur le PC Windows et une sur GitHub Actions Ubuntu
ont donné les mêmes digests de l’archive source, du manifeste OCI, de la
configuration et des couches décompressées. Les jobs utilisent BuildKit
0.34.2 épinglé par digest, Buildx 0.38.1 et l’archive du commit exact avec
des fins de ligne LF. Le manifeste comparé est celui produit par BuildKit
avant l’importation dans Docker. Chaque reçu enregistre le SHA du commit,
le digest de configuration vérifié par Grype et le résultat du scan.
Le résultat de reconstruction vaut pour les entrées amont mesurées.
[Reçu de comparaison PC et GitHub Actions](../evidence/public/application-image-cross-environment-20261125.json).

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

## Reproduire une image applicative en local

Utiliser Git, Python, Docker en mode conteneurs Linux et Buildx 0.38.1.
Dans un clone de l’API ou du Web, se placer sur le commit complet indiqué
par le reçu, puis lancer ces commandes dans un shell compatible POSIX.
Si Python 3 est accessible sous `python`, définir `PYTHON=python`. Les
commandes utilisent un builder dédié et chargent une image de test dans
le moteur Docker local.

```sh
commit="$(git rev-parse HEAD)"
app=cinevault-api  # cinevault-web dans le clone Web
builder="cinevault-repro-$$"

docker buildx create --name "$builder" --driver docker-container \
  --driver-opt image=moby/buildkit:v0.34.2@sha256:c5f8862f52499773af85bc07695b2379ef08e8002352b0df2c4864c91d78dabe
docker buildx inspect "$builder" --bootstrap

"${PYTHON:-python3}" scripts/check_image.py --builder "$builder" --source-commit "$commit" \
  --image "$app:repro-$commit"
```

Après le contrôle, lire `reports/image-check.json`. Comparer
`build_provenance.source_tar_digest`, `manifest_digest` et `config_digest`
au reçu du même commit. Le script sort avec le code 1 si la santé, le scan
ou le nettoyage échoue. Le scan dépend de la base Grype disponible au
moment du contrôle. Pour retirer le builder de cette session, exécuter
`docker buildx rm "$builder"`.

## Construire l'image MongoDB de staging

L'image officielle MongoDB 8.0.38 de base fournit les correctifs de MongoDB.
Elle contient encore une version de `js-yaml` signalée par Grype dans le
script d'entrée Docker. Le [Dockerfile](../docker/mongodb-staging/Dockerfile)
remplace cette bibliothèque par la version 3.15.2 et conserve sa licence.
BuildKit vérifie l'archive npm à partir de son SHA-256 épinglé.
[Image Docker amont](https://github.com/docker-library/mongo/blob/5fd7eb19024b73c9ec84644f1b23acbb33bee8b0/8.0/Dockerfile) ·
[Version js-yaml](https://github.com/nodeca/js-yaml/releases/tag/3.15.2).

```sh
docker build --network none --provenance=false --platform linux/amd64 \
  --build-arg SOURCE_DATE_EPOCH=1795219200 \
  --iidfile staging-mongo-image.txt \
  --tag cinevault-mongo-local:8.0.38-staging docker/mongodb-staging
```

Conserver la référence et les digests de ce build dans le reçu de staging.
Analyser cette image avec une base de vulnérabilités à jour et vérifier le
digest de configuration du rapport. Charger l'image contrôlée sur VM2 si
elle est transférée par archive. Recalculer l'empreinte de l'archive
à l'arrivée et vérifier le digest de configuration sur VM2 avant d'utiliser
la référence locale. Les deux images applicatives restent des références
GHCR par digest, téléchargées à l'avance sur leur worker.

La construction a été reproduite deux fois sans cache sur Docker Desktop.
Grype a relevé zéro constat High ou Critical sur l'image dérivée avec la
base du 24 novembre 2026 à 06 h 22 UTC. Le contrat natif a réussi sur le
même manifeste, avec les privilèges applicatifs limités. Le contrôle de
prédéploiement associe l'image chargée au digest de manifeste ou de
configuration attendu, selon le stockage d'images du moteur Docker.
[Reçu de l'image MongoDB](../evidence/public/mongodb-staging-image-20261125.json).

## Démarrer par étapes

Valider la configuration sur le manager. Avec
`CINEVAULT_STAGE_APP_REPLICAS=0`, seule la tâche MongoDB démarre.

```sh
docker stack config -c stack.mongodb-staging.yaml
docker stack deploy --resolve-image never -c stack.mongodb-staging.yaml cvstage
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

## Mettre à jour et revenir à une révision précédente

Avant la mise à jour, relever pour chaque service le manifeste d'image
effectif, l'identifiant de tâche, l'état de santé et la version Swarm du
service. Garder le manifeste résolu et instancier les mêmes entrées
privées depuis le poste opérateur. Pour une intervention qui touche les
données, produire une sauvegarde vérifiée et répétable avant le changement.

Les services de staging utilisent `stop-first` avec une fenêtre de
surveillance de 45 secondes. Le service peut donc être indisponible
pendant le remplacement. Swarm met en pause la mise à jour en cas d'échec.
Vérifier d'abord le digest, la tâche démarrée et son état de santé, puis
exercer une requête depuis le consommateur du service.

```sh
docker service ps --no-trunc cvstage_api
docker service inspect --format '{{json .UpdateStatus}}' cvstage_api
```

Pour revenir à la spécification immédiatement précédente, contrôler
`PreviousSpec` avant d'exécuter la commande. Si une intervention inverse
plusieurs changements ou si la spécification précédente ne correspond plus
au point de reprise, réappliquer le manifeste résolu conservé.

```sh
docker service inspect --format '{{.PreviousSpec.TaskTemplate.ContainerSpec.Image}}' cvstage_api
docker service rollback cvstage_api
docker service inspect --format '{{json .UpdateStatus}}' cvstage_api
```

Attendre la santé de la tâche de remplacement et vérifier de nouveau les
requêtes avant de réouvrir les écritures. La commande Swarm revient à une
spécification de service. Les données exigent soit une restauration isolée
compatible, soit l'export inverse si MongoDB a reçu de nouvelles écritures
depuis le basculement JSON. Les archives issues de MongoDB 8.0.38 exigent
une cible 8.0.38. [Sauvegarde et compatibilité](operations/MONGODB_BACKUP.md).

Le 25 novembre 2026, un service jetable sur VM2 a remplacé une tâche saine,
mis en pause une mise à jour dont la sonde échouait et démarré une tâche
saine après `docker service rollback`. Le manager a confirmé l'état
`rollback_completed`. L'essai a utilisé un processus inerte sur un réseau
Overlay privé et chiffré, sans port publié. Le service, ses tâches et son
réseau ont été retirés. Les spécifications et les tâches des deux services
stables ont conservé leur identité et leur état de santé. Le retour arrière
du staging applicatif reste à éprouver avec le couple qualifié.
[Reçu du retour arrière Swarm](../evidence/public/swarm-service-rollback-20261125.json).

### Revenir à JSON après de nouvelles écritures

1. Mettre le Web puis l'API hors service. Vérifier sur le manager que
   leurs réplicas désirés sont à zéro, puis sur chaque nœud qu'aucun
   conteneur d'écriture ne tourne encore. Laisser le réplica MongoDB
   disponible à l'identité de migration.
2. Garder le fichier d'origine et sa sauvegarde. Inspecter l'instantané
   MongoDB après le gel et exporter vers un nouveau chemin JSON avec les
   empreintes de l'original et de cet instantané. Refaire l'inspection si
   le digest attendu diffère. Suivre les commandes du
   [guide de migration API](https://github.com/HyMathew/cinevault-api/blob/f78fe323f291c3303aeafd107ac9b8c7a51ed399/docs/mongodb-migration.md).
3. Vérifier l'empreinte de l'export. Ouvrir le candidat JSON dans une
   instance isolée sans accès à MongoDB. Vérifier l'ancien catalogue,
   les données écrites après la bascule, l'authentification et les droits.
   Garder MongoDB et l'original intacts jusqu'à la validation du candidat.

Le 25 novembre, l'API exécutée depuis ses sources exactes sur le PC a
servi JSON, puis MongoDB 8.0.38, puis le fichier JSON exporté. La dernière
instance a retrouvé le film et le favori créés dans MongoDB, ainsi que les
sessions ouvertes avant et après la bascule. L'export a refusé l'empreinte d'un instantané
antérieur et a produit les mêmes octets au rejeu. Le contrôleur de
staging a aussi rejoué ses opérations d'export et de vérification dans
cet environnement local.

Sur Swarm, deux tâches inertes représentant les services d'écriture
se sont arrêtées et une troisième représentant la base est restée en
service. Le contrôle intégré des images API et Web sur Swarm reste
à exécuter avec le couple qualifié.
[Reçu de la reprise des données](../evidence/public/swarm-rollback-data-20261125.json).

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

Le 22 novembre, les trois VM ont répondu en SSH depuis le PC. Le contrôle a
confirmé les labels, les deux workers prêts, le manager en Drain et l’absence
de ressources portant les noms de staging. VM2 disposait d’environ 1 466 Mio
de mémoire disponible à cet instant. La stack stable était saine, avec HTTP
200 sur la sonde Web. Les connexions PC vers les ports API et MongoDB ont
expiré. Ce contrôle porte sur les flux depuis le PC et la capacité observée
à cet instant.
[Reçu des contrôles SSH](../evidence/public/enterprise-2.1-candidate-20261122.json).

Le 25 novembre, une instance MongoDB 8.0.38 sur VM2 a élu son primaire
sur le réseau de données chiffré. Un client jetable sur VM1 a vérifié le
certificat du serveur, ouvert une session TLS avec SCRAM-SHA-256 et lu un
document synthétique. Le serveur a refusé l'accès à une autre base et la
consultation des comptes d'administration. Le mot de passe invalide, l'autorité
de certification inconnue, le nom absent du certificat et la connexion en
clair ont échoué. Sur le seul réseau frontal, le client n'a pu ni résoudre
le nom de MongoDB ni joindre son adresse interne sur TCP 27017.

Le service n'a publié aucun port. Les deux réseaux, les secrets, le volume
et les conteneurs temporaires ont été retirés. Les deux services CineVault
stables sont restés sains avec les mêmes versions Swarm et les mêmes tâches.
Cet essai couvre MongoDB et le réseau entre workers. Les parcours avec
les images API et Web qualifiées restent à vérifier.
[Reçu MongoDB entre workers](../evidence/public/swarm-mongodb-overlay-tls-20261125.json).
