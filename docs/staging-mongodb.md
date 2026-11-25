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

Les révisions suivantes ont verrouillé par SHA-256 les archives APK
signées. Leur installation s’effectue hors réseau avec les clés Alpine
de l’image de base épinglée. Les deux images amd64 conservent les mêmes
26 paquets installés. Un build avec une empreinte falsifiée échoue.
[Reçu du candidat avec paquets verrouillés](../evidence/public/enterprise-2.1-alpine-runtime-20261125.json).

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

## Valider la variante HTTPS privée

La [surcouche Swarm](../stack.mongodb-staging.https.yaml) ajoute Caddy sur le
worker Web et active les cookies `Secure`. Seuls Caddy et le Web rejoignent
le réseau `edge`, interne et chiffré. Caddy sert TLS 1.3 pour
`cinevault-stage.test:8443` et relaie les requêtes uniquement à
`web:5000`. L’API garde `front` et `data`. MongoDB garde
`data` seul. Aucun des quatre services ne publie de port. Le point
d’administration et la redirection HTTP automatique de Caddy sont désactivés.
[Configuration de Caddy](../docker/caddy-staging/Caddyfile).

Cette variante annonce `Strict-Transport-Security: max-age=300` pour le
nom privé `cinevault-stage.test`. Un navigateur qui a reçu cette politique
sur une connexion TLS valide réécrit les liens HTTP de ce nom en HTTPS,
en conservant le port explicite 8443. La durée de cinq minutes borne l’effet
côté navigateur après un retour arrière. L’opérateur peut aussi effacer la
politique en servant `max-age=0` par HTTPS. La politique s’applique à ce
nom seul, avec les clients de test qui font confiance à la CA privée.
[RFC 6797, traitement navigateur](https://www.rfc-editor.org/rfc/rfc6797#section-8.3).

L’image officielle Caddy 2.11.9 testée a échoué au scan. La recette de staging
part du commit Caddy `679806f` et de Go 1.26.11 épinglé par digest. Elle
vérifie les sommes des modules avant la compilation sans réseau. L’image
contient le binaire statique et la licence Caddy. Le scan du candidat du
25 novembre compte un constat Medium, aucun High ni Critical.
[Dockerfile](../docker/caddy-staging/Dockerfile) ·
[Reçu de qualification du proxy](../evidence/public/swarm-staging-https-proxy-20261125.json).

Depuis la racine du dépôt, construire avec BuildKit 0.34.2 et Buildx 0.38.1.

```sh
docker buildx build --no-cache --pull --platform linux/amd64 \
  --build-arg SOURCE_DATE_EPOCH=1760000000 --provenance=false --sbom=false \
  --output type=docker,oci-mediatypes=true,rewrite-timestamp=true \
  --iidfile caddy-staging.iid --tag cinevault-caddy-local:staging-679806f \
  docker/caddy-staging
```

Vérifier le manifeste et son digest de configuration avant de scanner
l’archive avec une base à jour. Confirmer l’identité de l’image chargée
sur le worker Web. Utiliser cette référence dans
`CINEVAULT_STAGE_PROXY_IMAGE`. Les images API et Web restent soumises
à leurs contrôles respectifs.

Créer le certificat serveur et sa clé avec une CA de staging. Le nom
`cinevault-stage.test` doit figurer dans le SAN du certificat. Conserver la
clé de la CA hors Swarm et remettre son certificat aux seuls clients de test
autorisés. L’opérateur crée les secrets `cvstage_https_cert_v1` et
`cvstage_https_key_v1` à partir de fichiers PEM privés. La surcouche
les monte en 0400, dans le seul service HTTPS. Elle fournit le Caddyfile
sous forme de config Swarm en lecture seule.

Rendre les deux fichiers sur le manager avec les références d’images
qualifiées. Avec `CINEVAULT_STAGE_APP_REPLICAS=0`, seul MongoDB a un
réplica. Avec la valeur `1`, le proxy démarre avec le Web et l’API.

```sh
docker stack config -c stack.mongodb-staging.yaml -c stack.mongodb-staging.https.yaml
```

Le test local du proxy a utilisé un serveur HTTP synthétique. Il a confirmé
TLS 1.3, la réponse 200 de l’amont et le refus d’une CA inconnue, d’un nom TLS
incorrect, de TLS 1.2 et d’un en-tête Host différent du nom TLS. Le réseau
frontal du test n’a pas résolu le proxy.

Sur RemoteLabz, le même digest et le même Caddyfile ont servi une réponse
HTTPS 200 depuis le proxy sur VM1 vers un serveur synthétique sur VM2.
Les tests ont confirmé TLS 1.3, les refus de certificat et l’absence de
chemin TCP depuis le seul réseau frontal vers le proxy sur `edge`.
L’opération a été conduite par SSH depuis le PC. Swarm n’a publié aucun
port. Les services, réseaux, secrets et configs temporaires ont été retirés.
Les versions de service et les tâches saines de la v1 ont été conservées.
[Reçu HTTPS entre workers](../evidence/public/swarm-https-between-workers-20261125.json).

Pour vérifier un staging démarré, exécuter la
[sonde HTTPS](../scripts/check_staging_https.py) depuis l’espace réseau du
proxy sur le worker Web. Préparer un JSON privé avec `ca` (certificat
PEM de la CA HTTPS), `username`, `password`, `title` et
`movie_id`. Utiliser le compte de démonstration et le film synthétique
issus de la migration. Définir `probe_input` avec le chemin de ce fichier,
puis le transmettre sur l’entrée standard.

```sh
task=$(sudo docker ps --filter label=com.docker.swarm.service.name=cvstage_https --format '{{.ID}}')
pid=$(sudo docker inspect --format '{{.State.Pid}}' "$task")
sudo nsenter --target "$pid" --net python3 -I -B scripts/check_staging_https.py < "$probe_input"
```

La sonde se connecte en boucle locale dans l’espace réseau du proxy et
vérifie le nom TLS. Elle lit le catalogue et exerce la connexion,
le refus du profil anonyme et les attributs des cookies. Chaque réponse
doit contenir un seul en-tête HSTS avec la valeur attendue. La sonde rend un
reçu JSON sans jeton ni identifiant et sort avec le code 1 en cas d’échec.

Sur le PC, les quatre images aux digests attendus ont été exécutées sur
des réseaux Docker internes sans port publié. La migration a produit
12 collections et 40 index, puis le rejeu a confirmé le même instantané.
La sonde a retrouvé le film migré dans le catalogue, refusé le profil
anonyme et vérifié la connexion et les cookies en TLS 1.3.
[Reçu MongoDB et HTTPS de l’essai local](../evidence/public/staging-mongo-authenticated-https-local-20261125.json).

Dans cette configuration, le Web voit l’adresse de son pair réseau. Les tests de charge et de quotas devront
tenir compte de l’adresse partagée derrière Caddy. Le parcours HTTPS avec les
images applicatives qualifiées et les réseaux Overlay reste à valider sur
Swarm.

La mise à jour a révélé que la gestion automatique de Caddy préparait une
CA interne au démarrage. Le Caddyfile désactive désormais cette gestion
avec `auto_https off` et charge les deux secrets PEM explicitement.
Le parcours intégré sur le PC a réussi avec le répertoire temporaire
du proxy monté en lecture seule.

Le client Windows a négocié TLS 1.3 à travers une session SSH vers le
proxy. Le relais de la session ouvrait une seule connexion sur la boucle
locale du conteneur. Le contrôle a refusé une CA inconnue et un nom
incorrect. Aucun port n’a été publié sur la VM ou sur le PC.

Sur la même instance Swarm de test, une mise à jour de la config Caddy
a créé une nouvelle tâche et ajouté un en-tête de réponse observable
depuis le PC. Le retour arrière a restauré la spécification précédente
et une troisième tâche a répondu en HTTPS sans cet en-tête. Le serveur
synthétique sur le second worker a conservé sa tâche durant l’essai.
[Reçu de mise à jour et de retour arrière HTTPS](../evidence/public/swarm-https-pc-rollback-20261125.json).

Le 26 novembre, une nouvelle mise à jour a activé l’en-tête HSTS sur
le proxy temporaire. Depuis Windows, via SSH, l’opérateur a observé
trois réponses TLS 1.3 avec le même certificat et la même réponse
amont. L’en-tête est apparu après l’activation et a disparu après le
retour arrière. Sur Docker Desktop, Chromium a enregistré une
réécriture interne 307 motivée par HSTS pour une URL HTTP au port 8443.
Le catalogue migré était ensuite visible en HTTPS. Les tâches et
versions de la v1 ont été conservées.
[Reçu HSTS et retour arrière](../evidence/public/swarm-https-hsts-20261126.json).

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
