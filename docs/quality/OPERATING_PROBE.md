# Sonde d’exploitation CineVault

Lancer la sonde à la demande avec Python 3.11 ou plus récent. Elle effectue
un GET direct sur chaque URL de santé déclarée et exige un HTTP 200 de l’API
et du Web. Elle conserve la validation TLS standard et refuse les redirections.
Le délai s’applique aux opérations réseau de chaque requête. Utiliser les
URL de santé du périmètre à contrôler, sans identifiant, paramètre ni fragment.

## Relire un reçu depuis le poste opérateur

Ajouter `--environment stable`, `--environment staging` ou
`--environment synthetic` pour enregistrer le contexte et les heures
UTC de début et de fin. Conserver le reçu dans le répertoire de travail
privé de l’environnement choisi. Le libellé est fourni par l’opérateur
et doit correspondre aux URL et aux sources données à la sonde.

```sh
python3 scripts/show_operational_status.py \
  --environment staging --receipt "$STAGING_PROBE_RECEIPT" \
  --max-age-minutes "$OPERATOR_VIEW_MAX_AGE_MINUTES"
```

La vue lit un fichier, sans réseau, service Web ni identifiant. Elle
présente les états au moment de la mesure et écarte les résultats HTTP
si le reçu est trop ancien pour cette consultation. Le seuil est mesuré
depuis le début du contrôle. Un reçu sans contexte, daté dans le futur
ou provenant d’un autre environnement est indisponible. Le code de
sortie indique si le reçu est récent. L’échec éventuel d’un service
reste dans son champ et conserve le code de sortie original de la sonde.

Les erreurs HTTP, l’âge des sauvegardes, la dernière restauration
vérifiée, les mesures de capacité et les échéances TLS apparaissent
quand la sonde les a qualifiés. Pour chaque signal, le reçu séparé
de l’environnement demeure la source. La capacité ne prouve pas
l’état des tâches Swarm et le TLS MongoDB ne prouve pas une lecture
métier. Les images, les attestations et la remise d’alertes sont à
consulter dans leurs [preuves dédiées](SIGNATURE_DEFENSIVE_QUALIFICATION.md).

## Preuves à préparer

- Conserver le JSON produit par le [résumeur HTTP](../../scripts/summarize_http_logs.py)
  pour une fenêtre bornée, avec la fin UTC de cette fenêtre. Les deux services
  doivent chacun avoir au moins une requête. La sonde applique le seuil 5xx à
  chaque service et affiche le nombre de lignes ignorées.
- Conserver les sorties JSON réussies de `python -m tools.mongodb_backup backup`
  et du dernier `python -m tools.mongodb_backup restore`, avec l’heure UTC de fin
  relevée à chaque exécution. La sonde lit le statut natif, le SHA-256 déclaré
  et le nombre d’octets de l’archive dans chaque reçu.
  [Procédure MongoDB](MONGODB_PORTABLE_BACKUP.md).
- Choisir un âge maximal pour chaque preuve et un pourcentage maximal de 5xx
  selon la politique d’exploitation. Fournir les heures en ISO 8601 UTC, avec
  le suffixe `Z` ou `+00:00`. Utiliser `unknown` si l’heure est inconnue. La
  preuve concernée est alors signalée comme indisponible ou sans heure fiable.
  Les JSON UTF-8 doivent tenir chacun dans 4 Mio.

```sh
python3 scripts/check_operational_health.py \
  --api-url "$API_HEALTH_URL" --web-url "$WEB_HEALTH_URL" \
  --timeout-seconds "$HEALTH_TIMEOUT_SECONDS" \
  --http-summary "$HTTP_SUMMARY" --summary-ended-at-utc "$SUMMARY_ENDED_AT_UTC" \
  --max-summary-age-hours "$MAX_SUMMARY_AGE_HOURS" --max-5xx-percent "$MAX_5XX_PERCENT" \
  --backup-receipt "$BACKUP_RECEIPT" --backup-finished-at-utc "$BACKUP_FINISHED_AT_UTC" \
  --max-backup-age-hours "$MAX_BACKUP_AGE_HOURS" \
  --restore-receipt "$RESTORE_RECEIPT" --restore-finished-at-utc "$RESTORE_FINISHED_AT_UTC" \
  --max-restore-age-hours "$MAX_RESTORE_AGE_HOURS"
```

### Contrôler la copie hors VM

Avant chaque contrôle planifié, produire un reçu hors VM avec
`verify --expected-sha256 … --maximum-age-hours …`. Transmettre ce
reçu à la sonde avec `--backup-verification-receipt "$VERIFIED_COPY_RECEIPT"`.
Utiliser un chemin de reçu neuf par exécution et signaler tout code
non nul de `verify`. Relever le début UTC de cette tentative sur la
machine hors VM, avant d'y lancer `verify`, puis passer cette valeur
à la sonde avec `--backup-verified-since-utc "$ATTEMPT_STARTED_AT_UTC"`.
Un reçu daté avant ce début donne `verification_predates_attempt` et
un code de sortie 1, même quand la capture de sauvegarde est encore
récente. Un contrôle effectué exactement à l’heure de début est accepté.
Conserver les reçus de sauvegarde et de vérification dans des
emplacements protégés.
[Commande de vérification](../operations/MONGODB_BACKUP.md#rotation-fréquence-et-rétention).

La sonde rapproche le SHA-256 et la taille logique des deux reçus.
Elle vérifie l’ordre des horodatages et applique
`--max-backup-age-hours` à l’âge de capture au moment du contrôle.
Le résultat `backup_verification` donne l’âge de capture, l’âge du
contrôle ou l’état de l’erreur. Un fichier manquant, un SHA-256
différent ou une capture périmée fait échouer la sonde.

Un essai sous Windows a utilisé une archive MongoDB 8.0.38 issue
d’une fixture synthétique et le reçu d’une restauration antérieure.
Les endpoints HTTP synthétiques sur la boucle locale ont signalé
une panne API puis un retour à 200.
La sonde a aussi refusé le reçu manquant et le SHA-256 divergent.
[Reçu du contrôle d’exploitation](../../evidence/public/operating-probe-backup-verification-20261126.json).

Un autre essai Windows sur une archive MongoDB authentique a refusé un
reçu antérieur, accepté le reçu de la tentative et détecté le Web
indisponible. Un superviseur d’essai a interrompu la sonde à son
échéance sans sortie JSON, puis un autre appel a confirmé le
rétablissement. [Reçu des sept scénarios de tentative](../../evidence/public/operational-attempt-verification-20261126.json).

### Contrôler la capacité Swarm

Pour le lab à trois nœuds, fournir un JSON contenant `nodes` avec les rôles
`web`, `api` et `manager`. Chaque entrée contient `timestamp_utc`,
`available_ram_bytes` et `docker_available_disk_bytes`. Le
[précontrôle de staging](../staging-mongodb.md#préparer-les-entrées)
collecte ces valeurs depuis le noyau et le système de fichiers de Docker.
Le [reçu de mesure](../../evidence/public/swarm-mongodb-capacity-20261125.json)
montre le format des mesures pendant la fenêtre de lecture.

Ajouter ensemble les quatre arguments au contrôle précédent.

```sh
--swarm-capacity-snapshot "$SWARM_CAPACITY_SNAPSHOT" \
--max-capacity-age-hours "$MAX_CAPACITY_AGE_HOURS" \
--min-available-memory-mib "$MIN_AVAILABLE_MEMORY_MIB" \
--min-docker-free-mib "$MIN_DOCKER_FREE_MIB"
```

La sonde échoue si un relevé manque, est trop ancien, porte une date future
ou franchit un minimum. Le rapport désigne le nœud et le seuil concerné.
Une exécution périodique doit collecter un nouvel instantané et traiter
également une absence de résultat. La sonde fournit le résultat JSON et
le code de sortie pour l'intégration au canal d'alerte choisi.

### Qualifier la réception des alertes

Depuis le clone Infra sur l’hôte de supervision, utiliser
[`python -m scripts.supervise_operational_health`](../../scripts/supervise_operational_health.py).
Configurer deux
déclenchements indépendants pour le même créneau UTC. Le premier
prépare le tunnel et les reçus, puis lance le contrôle. Le second
lit le résultat à l’échéance, y compris quand la première tâche
n’a produit aucun JSON.

```sh
# Le lanceur reçoit les arguments de la sonde dans "$@".
python -m scripts.supervise_operational_health run --database "$SUPERVISOR_DB" \
  --slot-utc "$SLOT_UTC" --deadline-seconds "$DEADLINE_SECONDS" -- "$@"

# La tâche de surveillance utilise la même échéance et le même créneau.
python -m scripts.supervise_operational_health watch --database "$SUPERVISOR_DB" \
  --slot-utc "$SLOT_UTC" --deadline-seconds "$DEADLINE_SECONDS" --inbox "$ALERT_INBOX"

# Sur le poste destinataire, conserver le JSON de cette commande.
python -m scripts.supervise_operational_health receive --event "$EVENT_FILE"
```

Placer la base SQLite sur le disque local de l’hôte de supervision.
Donner aux deux tâches le même créneau UTC et sa durée de validité
en secondes. Traiter les créneaux par ordre chronologique.
Réserver un chemin neuf au reçu de vérification pour
chaque créneau. `run` impose comme seuil de vérification le début
de ce créneau. Utiliser une boîte de réception protégée, accessible
au destinataire. La boîte doit prendre en charge la publication
atomique sans remplacement par renommage sous Windows et par lien
physique sous Linux. Un fichier déjà présent est confirmé uniquement
si ses octets correspondent à l'événement du journal SQLite.
Conserver le message et son accusé de réception avant la rotation
des preuves d’exploitation.

`watch` renvoie 3 avant l’échéance, 0 pour un état sain et 1 pour
un incident. Le code 2 signale une erreur d’exécution ou d’accès.
Réessayer le même créneau après un échec d’écriture dans la boîte.
Le journal SQLite conserve l’événement à livrer, son identifiant,
et le dernier état de l’incident. Rejouer un créneau n’émet aucun
nouvel événement. Une nouvelle cause d’échec met à jour l’incident
ouvert et la reprise le clôt avec le même identifiant.

| Essai | Observation hors VM | Preuve côté destinataire |
| --- | --- | --- |
| Arrêt du Web | Statut Web 502, API 200, émission horodatée | Alerte reçue avec le même identifiant d’incident et une heure de réception dans le délai retenu |
| Contrôle absent | Échéance dépassée sans résultat de la tentative, signal déclenché par le superviseur | Alerte reçue avec l’identifiant de tentative et l’échéance concernés |
| Retour du Web | Statut Web 200 et retour à l’état sain de la sonde | Message de reprise reçu et rattaché à l’identifiant de l’incident |

Consigner les horodatages UTC et la référence du message reçu. Le
signal local ou l’acquittement de transport constitue une preuve
d’émission. La remise est confirmée côté destinataire.

Sur un même hôte Windows, des processus distincts ont reproduit
un Web en HTTP 502, un créneau sans lanceur et un retour à HTTP 200
avec une archive MongoDB vérifiée par age. Le destinataire a
lu trois messages rattachés au même incident et émis trois
accusés. Le superviseur a repris un envoi après indisponibilité
de la boîte et a ignoré les relectures répétées du même créneau.
[Reçu des trois messages et accusés locaux](../../evidence/public/operational-watch-delivery-20261126.json).

Quand l’observateur et le destinataire sont sur deux hôtes, déposer
le fichier `<event_id>.json` dans la boîte du destinataire via le
transport autorisé. Conserver les octets UTF-8 du fichier pendant le
transfert et vérifier son SHA-256 à l’arrivée. Exécuter `receive`
sur le fichier reçu et archiver cet accusé avec l’événement original.
Si le transport aboutit avant que l’accusé soit disponible, reprendre
avec le même `event_id` et les mêmes octets. Un accusé déjà conservé
pour cet identifiant se rapproche par son SHA-256.

Le banc inter-hôtes a déclenché trois créneaux successifs à une
minute d’intervalle depuis le Planificateur Windows. Il a contrôlé
une application de test en boucle locale et transmis les trois
événements par SSH épinglé à un destinataire Ubuntu. Le premier
transfert a été réalisé avant la lecture destinataire. Sa reprise
a produit un seul accusé conservé et le rejeu a renvoyé ce même accusé.
Les trois lectures distantes rattachent l’ouverture, l’absence de
résultat et la reprise au même incident.
[Reçu inter-hôtes et preuve de périodicité](../../evidence/public/operational-watch-cross-host-20261126.json).

### Vérifier l’échéance des certificats

Ajouter `--tls-policy "$TLS_POLICY"` pour vérifier le certificat
présenté par le proxy, MongoDB ou les deux. Exécuter la sonde depuis
le réseau autorisé du service. Le contrôle MongoDB doit joindre le
réseau de données privé. Pour un tunnel SSH vers le proxy, indiquer
`127.0.0.1` et le port local du tunnel dans les paramètres de connexion.
Conserver le nom DNS du certificat dans `server_name`.

Le fichier JSON fixe les cibles et leur durée minimale avant échéance,
en heures entières strictement positives. Chaque fichier CA est un
fichier PEM désigné par un chemin absolu du système qui exécute la
sonde. Utiliser les mêmes CA que les clients du service.

```json
{
  "proxy": {
    "connect_host": "127.0.0.1",
    "port": 8443,
    "server_name": "cinevault-stage.test",
    "ca_file": "/run/secrets/cinevault_proxy_ca.pem",
    "min_remaining_hours": 72
  }
}
```

Pour ajouter `mongodb`, utiliser le même format avec
`mongo.cv-stage.internal` comme nom et adresse DNS, le port `27017`
et le fichier CA MongoDB. Les chemins, ports et seuils doivent
correspondre au contexte de la sonde.

### Vérifier la santé Web à travers le tunnel TLS

Pour le proxy privé, ajouter `--web-via-proxy-tls` à la commande
de la sonde et fournir `--tls-policy "$TLS_POLICY"`. Indiquer en
`connect_host` l’adresse locale du tunnel, par exemple `127.0.0.1`.
Indiquer le port local dans la politique et dans `--web-url`. Par
exemple, avec un tunnel local sur le port `18443`, utiliser
`https://cinevault-stage.test:18443/health`. Conserver
`cinevault-stage.test` comme `server_name` et renseigner le PEM de
la CA privée dans `ca_file`.

Le GET Web passe sur la connexion TLS authentifiée par cette
politique. Il utilise le même nom pour la vérification du certificat
et l’en-tête HTTP Host. Le contrôle exige HTTP 200 et renvoie le
statut des redirections et des erreurs HTTP sans les suivre.
Le GET de l’API conserve l’URL `--api-url` et son accès propre.

Sur Docker Desktop, un relais local a acheminé le GET vers Caddy avec les
images candidates API et Web et MongoDB 8.0.38. La sonde a signalé le
HTTP 502 pendant l’arrêt du Web, tandis que l’API répondait HTTP 200,
puis a confirmé le rétablissement. Elle a également signalé les réponses
303 et 404 et les échecs de confiance TLS. Un test natif Windows a
vérifié le nom TLS, l’en-tête Host et le GET sur une seule connexion.
[Reçu des neuf scénarios Docker et du test Windows](../../evidence/public/operational-proxy-http-20261126.json).

### Interpréter les résultats TLS

La négociation TLS vérifie la chaîne de confiance et le nom. Le rapport
donne pour chaque service l’expiration du certificat serveur en UTC,
le nombre de secondes restantes, le seuil et la version TLS négociée.
`expires_soon` indique un certificat valide qui passe sous le seuil.
`certificate_invalid` signale un certificat rejeté, par exemple pour
une CA inconnue, un nom différent ou une expiration passée. Une CA
illisible, un échec de négociation ou un service injoignable produit
également un code de sortie 1. Le contrôle TLS utilise le délai défini
par `--timeout-seconds` pour la connexion et la négociation.

Le test sur un réseau interne Docker Desktop a interrogé Caddy et
MongoDB 8.0.38. Les deux certificats ont passé un seuil de 24 heures.
La sonde a signalé leur expiration proche au seuil de 72 heures.
Les essais ont aussi signalé une CA et un nom TLS incorrects, un
fichier CA manquant et un service injoignable. Les réponses HTTP et
les reçus de sauvegarde utilisés pendant ce test étaient synthétiques.
[Reçu du contrôle des échéances TLS](../../evidence/public/operational-tls-expiry-20261126.json).

## Résultats et limites

| Code | Interprétation |
| --- | --- |
| `0` | Les deux contrôles HTTP, les trois contrôles de preuves et les contrôles supplémentaires demandés réussissent. |
| `1` | Au moins un contrôle échoue. Le JSON identifie le service ou la preuve et son état. |
| `2` | La validation des arguments échoue avant les appels réseau. |

La sortie contient les états, codes HTTP, âges et compteurs. Les URL, chemins,
corps HTTP, empreintes et contenus de journaux restent dans les sources locales.
Une collecte absente, vide, illisible, invalide ou périmée entraîne un échec.
Une collecte partielle ou au-dessus du seuil détaille l’état de chaque service.

L’opérateur déclare les heures UTC de fin des preuves de collecte,
de sauvegarde et de restauration.
Conserver les preuves avec ces heures et leurs sources. Les reçus du contrôle
portable CI qualifient les contrats hors ligne. La sonde attend les reçus natifs
d’une sauvegarde et d’une restauration.
Le dernier exercice de restauration peut porter sur un autre chiffré que la
sauvegarde récente. Le contrôle porte sur les métadonnées des deux reçus.
L’essai a été exécuté manuellement. La validation intégrée sur le staging
reste ouverte pour la sonde périodique, les endpoints réels via SSH/TLS,
le stockage de sauvegarde hors VM et le canal d’alerte.
[État de qualification Enterprise 2.1](ENTERPRISE_21_QUALIFICATION.md).
