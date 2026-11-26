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

Le [précontrôle Swarm](../scripts/check_swarm_readiness.py) associe les
relevés Docker à leurs rôles. Il vérifie les trois nœuds, le manager
Leader en Drain, les labels, la santé et les digests des tâches stables,
la mémoire et l’absence de noms de staging déjà utilisés. Il relève
également le CPU et l’espace disponible sur le système de fichiers de
Docker. Utiliser Python 3.11 ou supérieur.

Depuis une session SSH administrateur sur chaque VM Linux, lancer le
script avec le rôle de cette VM, `web`, `api` ou `manager`. L’accès au
moteur Docker doit être disponible à travers les droits administrateur
déjà configurés. La collecte interroge le socket Docker local
`/var/run/docker.sock`. Pour dimensionner le disque, comparer l’espace
relevé aux tailles des images et volumes prévues pour cette campagne.
Voici la commande pour le worker web.

```sh
sudo python3 check_swarm_readiness.py collect web > web.json
```

Rapatrier les trois relevés via SSH et les assembler depuis le clone.
Ils doivent dater de moins de quinze minutes. La commande renvoie 1
si un contrôle échoue et 2 si la collecte ou le format est invalide.
Le JSON agrégé sert aussi de relevé pour la sonde d’exploitation.

```sh
python scripts/check_swarm_readiness.py assess \
  --web web.json --api api.json --manager manager.json > readiness.json
```

Appliquer ensuite les contrôles d’images ci-dessous. Le précontrôle
interroge la stack stable et l’environnement du staging sans créer de
ressource. Le 26 novembre, le relevé depuis le PC a confirmé les
trois nœuds prêts et les deux tâches stables saines. Les mêmes mesures
ont été acceptées par la sonde de capacité.
[Reçu du précontrôle sur les trois VM](../evidence/public/swarm-predeployment-readiness-20261126.json).

- Les limites de MongoDB et de l'API de staging totalisent 1 152 Mio
  sur VM2. Évaluer le budget disponible au moment du déploiement.
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

### Créer les entrées externes du premier démarrage

Effectuer le précontrôle avant de créer les entrées `cvstage_*`. Le manifeste
exige les références d’images et de secrets même quand les écrivains ont
zéro réplica. Après validation des images, préparer les fichiers suivants
dans un répertoire privé sur le manager. Ordonner les noms de fichiers comme
dans le tableau permet de créer les secrets sans passer leur contenu en
argument.

| Fichier sous `STAGE_SECRET_DIR` | Secret Swarm | Contenu |
| --- | --- | --- |
| `mongo_server_tls` | `cvstage_mongo_server_tls_v1` | Certificat serveur suivi de sa clé privée, au format PEM |
| `mongo_replica_key` | `cvstage_mongo_replica_key_v1` | Clé de réplication encodée en base64, générée ci-dessous |
| `mongo_ca` | `cvstage_mongo_ca_v1` | Certificat PEM public de la CA MongoDB |
| `mongo_app_uri` | `cvstage_mongo_app_uri_v1` | URI TLS décrite ci-dessus. Encoder les identifiants en URL et conserver le même compte et mot de passe pour sa création dans `admin`. |
| `auth_throttle` | `cvstage_auth_throttle_v1` | Clé aléatoire indépendante pour les compteurs API |
| `web_session` | `cvstage_web_session_v1` | Clé aléatoire indépendante de session Flask |
| `client_context` | `cvstage_client_context_v1` | Une même clé aléatoire, montée par le Web et l’API |
| `https_cert` | `cvstage_https_cert_v1` | Certificat serveur PEM de la variante HTTPS |
| `https_key` | `cvstage_https_key_v1` | Clé privée PEM de la variante HTTPS |

Définir `STAGE_SECRET_DIR` sur un répertoire existant de mode 0700.
Créer le PEM MongoDB et le fichier URI de façon privée, puis produire
les quatre clés aléatoires. Le mode `xb` refuse de remplacer un fichier
existant. Les trois clés applicatives sont des octets bruts.

```sh
umask 077
python3 - "$STAGE_SECRET_DIR" <<'PY'
import base64
import secrets
import sys
from pathlib import Path

directory = Path(sys.argv[1])
keys = {"mongo_replica_key": base64.b64encode(secrets.token_bytes(72))}
for name in ("auth_throttle", "web_session", "client_context"):
    keys[name] = secrets.token_bytes(48)
for name, content in keys.items():
    with (directory / name).open("xb") as destination:
        destination.write(content)
PY
```

Dans un shell sur le manager, vérifier la présence des sept fichiers avant
toute création. Pour la variante HTTPS, ajouter `https_cert https_key` à
la liste avant d’exécuter les deux boucles.

```sh
inputs="mongo_server_tls mongo_replica_key mongo_ca mongo_app_uri auth_throttle web_session client_context"
for input in $inputs; do
  test -s "$STAGE_SECRET_DIR/$input" || exit 1
done
for input in $inputs; do
  docker secret create "cvstage_${input}_v1" - < "$STAGE_SECRET_DIR/$input" || exit 1
done
```

Sur VM2, créer les deux volumes locaux après le précontrôle et vérifier
leur appartenance à cette opération. Utiliser la référence API
qualifiée et déjà chargée. Le conteneur opérateur refuse les montages
manquants et les volumes non vides avant de régler le mode et les UID.

```sh
stage_run="$(openssl rand -hex 8)" || exit 1
for volume in cvstage_mongo_data_v1 cvstage_api_sidecars_v1; do
  docker volume create --label "cinevault.bootstrap=$stage_run" "$volume" || exit 1
  owner="$(docker volume inspect --format '{{index .Labels "cinevault.bootstrap"}}' "$volume")" || exit 1
  test "$owner" = "$stage_run" || exit 1
done

docker run --rm -i --pull never --network none --read-only --no-healthcheck \
  --user 0:0 --cap-drop ALL --cap-add CHOWN --security-opt no-new-privileges \
  --mount type=volume,src=cvstage_mongo_data_v1,dst=/mnt/mongo,volume-nocopy \
  --mount type=volume,src=cvstage_api_sidecars_v1,dst=/mnt/sidecars,volume-nocopy \
  --entrypoint python "$CINEVAULT_STAGE_API_IMAGE" -I -B - <<'PY'
import os
from pathlib import Path

directories = {"/mnt/mongo": 999, "/mnt/sidecars": 10001}
mounts = {line.split()[4] for line in Path("/proc/self/mountinfo").read_text().splitlines()}
for name in directories:
    path = Path(name)
    if name not in mounts or path.is_symlink() or any(path.iterdir()):
        raise SystemExit("Montage absent ou volume déjà utilisé")
for name, uid in directories.items():
    path = Path(name)
    path.chmod(0o700)
    os.chown(path, uid, uid)
    info = path.stat()
    if (info.st_uid, info.st_gid, info.st_mode & 0o777) != (uid, uid, 0o700):
        raise SystemExit("Propriétaire ou mode incorrect")
PY
```

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

Pour le précontrôle d’une livraison, utiliser chaque reçu `image-audit`
vérifié. Relever le digest de configuration
`scan_provenance.archive_config_digest`, le digest de manifeste OCI
`scan_provenance.archive_oci_manifest_digest`, le SHA source, le ref
Git complet et le numéro du run Actions. La
[vérification GHCR](../scripts/verify_registry_image.py) recalcule
les empreintes des manifestes publics et compare leur configuration
au scan. Les trois options de provenance sont fournies ensemble.
Elles nécessitent GitHub CLI authentifié en lecture sur GitHub.

```sh
python3 scripts/verify_registry_image.py \
  --reference "$CINEVAULT_STAGE_API_IMAGE" --config-digest "$API_CONFIG_DIGEST" \
  --platform-manifest-digest "$API_PLATFORM_DIGEST" \
  --source-commit "$API_SOURCE_SHA" --source-ref "$API_SOURCE_REF" --run-id "$API_RUN_ID"
python3 scripts/verify_registry_image.py \
  --reference "$CINEVAULT_STAGE_WEB_IMAGE" --config-digest "$WEB_CONFIG_DIGEST" \
  --platform-manifest-digest "$WEB_PLATFORM_DIGEST" \
  --source-commit "$WEB_SOURCE_SHA" --source-ref "$WEB_SOURCE_REF" --run-id "$WEB_RUN_ID"
```

GitHub CLI vérifie la signature Sigstore du sujet OCI. Le script exige
ensuite le dépôt officiel, le workflow de publication `tests.yml`,
le commit, le ref et le run attendus, ainsi qu’un runner hébergé par
GitHub. En cas d’échec, il sort avec le code 1 et un diagnostic sans
sortie brute du CLI. Conserver le reçu qui contient
`provenance.signature_verified=true` avant le déploiement. Le contrôle
s’ajoute au scan et à l’inspection des images chargées sur les workers.
Sans les trois options, le script vérifie uniquement le manifeste,
comme lors du contrôle des images historiques de la v1.
[Reçu GHCR v1](../evidence/public/registry-manifest-check-20261122.json) ·
[Spécification OCI Distribution](https://github.com/opencontainers/distribution-spec/blob/main/spec.md).

Le 26 novembre, GitHub CLI 2.105.0 a vérifié la signature réelle du
rapport universitaire et le script a retrouvé son run. Un autre
commit et un autre run ont été refusés. GHCR a servi les manifestes v1
attendus, dont la provenance n’a pas satisfait ce contrôle. Les images
Enterprise 2.1 doivent encore passer le scan, être publiées et obtenir
leurs propres attestations.
[Reçu du précontrôle de provenance](../evidence/public/image-release-provenance-preflight-20261126.json).

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

## Préparer une mise à jour OpenSSL des images applicatives

Le [générateur de verrous](../scripts/prepare_openssl_locks.py) lit les
commits courants des deux clones. À partir d’une version publiée dans
Alpine 3.24, il récupère `libcrypto3` et `libssl3` pour les architectures
répertoriées dans ces commits. Il valide les signatures avec les clés de
l’image Alpine épinglée pour chaque architecture, puis contrôle le nom,
la version, l’architecture et la dépendance entre les deux paquets. La
commande utilise Git, Python 3.11 ou supérieur et un moteur Docker Linux
capable d’exécuter ces architectures nativement ou par émulation.

```sh
python3 scripts/prepare_openssl_locks.py \
  --api "$API_CLONE" --web "$WEB_CLONE" \
  --version "$ALPINE_OPENSSL_VERSION" --output "$PROPOSAL_DIR"
```

Choisir un répertoire de sortie absent. La commande refuse le lot si
une architecture manque ou si une signature échoue. Les propositions
conservent les autres paquets et laissent les clones intacts. Examiner
`receipt.json` et comparer les deux arbres proposés avant d’appliquer
les seuls fichiers de verrou sur leurs branches de qualification.
Les nouveaux commits suivent ensuite les builds reproductibles, les
tests, le scan et la vérification de provenance habituels.

Le 26 novembre, le contrôle a authentifié les seize paquets déjà
verrouillés sur huit architectures. Les neuf fichiers proposés sont
identiques aux verrous Git. L’essai a refusé un paquet altéré, une
architecture incohérente et un paquet candidat indisponible.
[Reçu des contrôles Alpine](../evidence/public/openssl-lock-preflight-20261126.json).

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
Lancer depuis la racine du clone Infra sur le manager pour que le
Caddyfile soit disponible au chemin de la surcouche.

```sh
docker stack config -c stack.mongodb-staging.yaml -c stack.mongodb-staging.https.yaml
docker stack deploy --resolve-image never \
  -c stack.mongodb-staging.yaml -c stack.mongodb-staging.https.yaml cvstage
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

### Renouveler le certificat du proxy

Pour un renouvellement sous la même CA, préparer un nouveau certificat et
une nouvelle clé qui lui correspond. Vérifier leur date de début, leur
date d’expiration et le SAN `cinevault-stage.test` avant de créer les
secrets. Calculer le SHA-256 du certificat public pour le contrôle depuis
le PC. La CA doit rester valide pendant la période prévue de service.
Si elle change, distribuer et vérifier la nouvelle chaîne de confiance
sur les postes autorisés avant le basculement.

Sur le manager, examiner les secrets actuellement montés dans
`cvstage_https` et conserver la spécification de départ. L’exemple
suivant passe de `v1` à `v2` dans une seule mise à jour, avec les mêmes
cibles lues par le Caddyfile. `CERT_PEM` et `KEY_PEM` désignent les
chemins de fichiers privés fournis par l’opérateur.

```sh
docker secret create cvstage_https_cert_v2 - < "$CERT_PEM"
docker secret create cvstage_https_key_v2 - < "$KEY_PEM"
docker service update --no-resolve-image \
  --secret-rm cvstage_https_cert_v1 --secret-rm cvstage_https_key_v1 \
  --secret-add source=cvstage_https_cert_v2,target=https_cert,uid=10001,gid=10001,mode=0400 \
  --secret-add source=cvstage_https_key_v2,target=https_key,uid=10001,gid=10001,mode=0400 \
  cvstage_https
```

Le proxy mono-réplique utilise `stop-first`. Prévoir une fenêtre de
maintenance. Vérifier depuis le PC la validation TLS, l’empreinte du
nouveau certificat et la réponse du service derrière le proxy. Garder
les deux secrets précédents pendant la fenêtre de retour arrière.
Si le contrôle échoue et que l’ancien certificat reste utilisable,
exécuter `docker service rollback cvstage_https`, puis vérifier
l’empreinte précédente et le rétablissement du service depuis le PC.
Après validation d’une rotation, reporter les nouvelles références dans
la surcouche de déploiement avant de redéployer la stack. Retirer les
anciens secrets après la fenêtre de retour et après avoir vérifié leurs
usages restants.
[Gestion des secrets Swarm](https://docs.docker.com/engine/swarm/secrets/#example-rotate-a-secret).

Le 26 novembre, un proxy temporaire sur VM1 a servi une réponse
synthétique de VM2. Depuis Windows via SSH, trois connexions validées
en TLS 1.3 ont observé le certificat initial, le nouveau certificat
avec une clé distincte, puis le certificat initial après retour
arrière. Les montages ont conservé les droits 0400 et les cibles
prévues. Les trois tâches ont conservé la réponse HTTP 200 et HSTS
aux points de mesure. Les ressources de l’essai ont été retirées.
[Reçu du renouvellement et du retour arrière](../evidence/public/swarm-https-certificate-rotation-20261126.json).

## Remplacer la CA MongoDB

Cette séquence s’applique au replica set mono-nœud de staging, avec
authentification cliente SCRAM et secrets Swarm immuables. Le
redémarrage du seul membre crée une fenêtre d’indisponibilité.
Prévoir cette fenêtre, sauvegarder les données et vérifier l’état de
la sauvegarde avant la mise à jour.

1. Préparer la CA B et un nouveau PEM serveur signé par B. Garder
   les SAN `mongo.cv-stage.internal` et `localhost`. Conserver
   l’ancienne paire, les deux CA publiques et la spécification
   de départ pendant la fenêtre de retour arrière.
2. Faire charger le bundle A+B à tous les clients qui doivent suivre
   la rotation, dont l’API et le poste de sauvegarde. Recréer les
   processus concernés pour ouvrir de nouvelles connexions. Vérifier
   leurs connexions pendant que MongoDB sert encore le certificat A.
3. Sur le service MongoDB uniquement, remplacer dans la même mise à
   jour le PEM serveur et le fichier CA par la paire B. Garder le
   volume de données et la clé du replica set. Attendre le primaire,
   vérifier le certificat servi avec une nouvelle connexion et
   rejouer les contrôles de santé et de lecture. La sonde `mongosh`
   du manifeste lit le fichier CA monté par le service MongoDB.
4. Ramener la confiance des clients à B après validation, puis
   recréer les processus clients. Vérifier qu’une connexion neuve
   avec la seule CA A échoue et que les clients avec B retrouvent
   les données attendues.

Sur le manager, créer les trois secrets suivants depuis les fichiers
préparés. Confirmer les références actuellement montées avant chaque
commande de mise à jour.

```sh
docker secret create cvstage_mongo_ca_bridge_v2 - < "$MONGO_CA_AB"
docker secret create cvstage_mongo_ca_v2 - < "$MONGO_CA_B"
docker secret create cvstage_mongo_server_tls_v2 - < "$MONGO_SERVER_PEM_B"
```

La colonne « Source » donne la valeur de `--secret-add source=…`.
Ajouter `,target=…`, `,uid=…`, `,gid=…` et `,mode=0400` comme dans la
commande de rotation HTTPS. Utiliser `--secret-rm` avec la référence
retirée. Appliquer les deux lignes MongoDB dans le même
`docker service update --no-resolve-image`, puis valider le service
avant de passer à la phase suivante.

| Phase | Service | Référence retirée | Source | Cible | UID/GID |
| --- | --- | --- | --- | --- | --- |
| 2 | `cvstage_api` | `cvstage_mongo_ca_v1` | `cvstage_mongo_ca_bridge_v2` | `mongo_ca` | 10001 |
| 3 | `cvstage_mongo` | `cvstage_mongo_server_tls_v1` | `cvstage_mongo_server_tls_v2` | `server_tls` | 999 |
| 3 | `cvstage_mongo` | `cvstage_mongo_ca_v1` | `cvstage_mongo_ca_v2` | `mongo_ca` | 999 |
| 4 | `cvstage_api` | `cvstage_mongo_ca_bridge_v2` | `cvstage_mongo_ca_v2` | `mongo_ca` | 10001 |

Pour revenir à A après l’étape 4, recharger A+B côté clients, restaurer
le PEM serveur et la CA A côté MongoDB, attendre son retour à l’état
primaire, puis vérifier les connexions et les données avant de
ramener les clients à A. Valider les sources de secrets dans la
surcouche déployée avant de réappliquer la stack. Réserver les
changements d’identité SCRAM ou de clé de réplication à une campagne
distincte.
[Configuration TLS MongoDB 8.0](https://www.mongodb.com/docs/v8.0/tutorial/configure-ssl/).

Le 26 novembre, la séquence a été exécutée sur Docker Desktop avec
MongoDB 8.0.38 et l’API `05171fd`. Le membre unique a redémarré
sur le même volume. Le script a contrôlé le fichier CA effectivement
monté, le certificat servi et les connexions neuves sous A, A+B et B.
Après le basculement, la seule CA A a été refusée. L’API a répondu 503
pendant les deux arrêts, puis 200. Le même film et le même favori
ont été relus à chaque étape avec authentification.
[Reçu du renouvellement de la CA MongoDB](../evidence/public/mongodb-ca-rollover-20261126.json).

## Remplacer l’identité SCRAM de l’API

Préparer une fenêtre de maintenance. L’API a un seul réplica et sa
mise à jour est en `stop-first`. Vérifier la sauvegarde et conserver
la référence du secret monté avant l’opération. MongoDB et son volume
restent en service.

1. Depuis le réseau de données, ouvrir une session `mongosh` en TLS avec
   l’identité de maintenance. Vérifier le rôle de l’utilisateur courant
   dans `admin`. Le rôle applicatif doit limiter les actions `find`,
   `insert`, `update` et `remove` à la seule base `cinevault_stage`.
2. Créer un autre utilisateur dans `admin` avec le même rôle et un
   mot de passe neuf fourni par `passwordPrompt()`. Remplacer
   `ROLE_CRUD_VERIFIE` par le rôle vérifié. Depuis un nouveau client,
   contrôler la lecture permise et le refus des opérations de
   maintenance avant le basculement.

   ```javascript
   db.getSiblingDB("admin").runCommand({
     createUser: "cinevault_app_v2",
     pwd: passwordPrompt(),
     roles: [{ role: "ROLE_CRUD_VERIFIE", db: "admin" }],
     mechanisms: ["SCRAM-SHA-256"],
     writeConcern: { w: "majority", wtimeout: 5000 }
   })
   ```

3. Préparer en privé le nouveau fichier URI. Encoder les identifiants
   dans l’URI et conserver le nom MongoDB, la CA, la validation TLS,
   `authSource=admin`, `authMechanism=SCRAM-SHA-256` et
   `replicaSet=cv-stage-rs`. Créer le secret Swarm depuis ce fichier
   sans recopier l’URI dans la ligne de commande. Régler
   `CURRENT_MONGO_APP_SECRET` sur le nom de la source actuellement montée
   sous `mongo_app_uri`.

   ```sh
   docker secret create cvstage_mongo_app_uri_v2 - < "$NEW_MONGO_APP_URI_FILE"
   docker service update --no-resolve-image \
     --secret-rm "$CURRENT_MONGO_APP_SECRET" \
     --secret-add "source=cvstage_mongo_app_uri_v2,target=mongo_app_uri,uid=10001,gid=10001,mode=0400" \
     cvstage_api
   ```

4. Attendre la nouvelle tâche et vérifier `/health`, une connexion MongoDB
   neuve avec l’URI effectivement montée et une lecture authentifiée
   des données attendues. Garder l’ancien compte pendant cette
   validation si le motif de rotation permet de le conserver.
5. Retirer l’ancien utilisateur avec `dropUser` dans `admin`, puis
   confirmer que ses identifiants échouent sur une nouvelle connexion.
   Valider de nouveau l’API et reporter le nom du secret actif dans
   la configuration de déploiement. Supprimer l’ancien secret Swarm
   lorsque les tâches qui le montaient ont toutes été arrêtées.

Avant le retrait, le retour arrière peut remonter le secret précédent
si son compte reste autorisé. Après le retrait, créer un compte de
repli avec un nouveau mot de passe et publier un nouveau secret
avant de relancer l’API. En cas de soupçon de compromission, planifier
la révocation immédiate et traiter les connexions existantes dans le
cadre de l’incident. La vérification de cette procédure porte sur
de nouvelles connexions.
[Créer un utilisateur MongoDB](https://www.mongodb.com/docs/v8.0/reference/command/createuser/) ·
[Retirer un utilisateur MongoDB](https://www.mongodb.com/docs/v8.0/reference/command/dropuser/) ·
[Mettre à jour un service Swarm](https://docs.docker.com/reference/cli/docker/service/update/).

Sur Docker Desktop, l’API `05171fd` a retrouvé le même film et le même
favori à chacune des six étapes avec MongoDB 8.0.38. Le compte de
remplacement avait le même rôle CRUD, et les tentatives d’administration
et d’accès à une autre base ont été refusées. Après retrait, l’ancien mot
de passe a été refusé même lorsque le nom du compte a été recréé avec un
secret neuf. MongoDB a conservé le même conteneur. L’essai a recréé les
conteneurs API avec des fichiers d’URI montés en lecture seule.
[Reçu de rotation de l’identité SCRAM](../evidence/public/mongodb-scram-rotation-20261126.json).

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
   [guide de migration API](https://github.com/HyMathew/cinevault-api/blob/05171fd6cb8f8607b7832f7a997e07509db4139c/docs/mongodb-migration.md).
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

Le 26 novembre, l’essai a été rejoué avec l’API `05171fd` et
MongoDB 8.0.38 sur le PC. Une empreinte erronée du fichier d’origine
et une empreinte historique de MongoDB ont chacune été refusées sans
création du JSON demandé. L’export valide a produit les mêmes octets
au rejeu. Après arrêt de MongoDB, la nouvelle instance JSON a retrouvé
le film, le favori et les sessions, avec un refus d’accès anonyme au
favori. La fenêtre entre inspection et export exige que les écrivains
restent arrêtés.
[Reçu de l’essai sur le candidat exact](../evidence/public/native-http-cutover-current-20261126.json).

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
