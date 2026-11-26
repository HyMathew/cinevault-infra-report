# Sonde d’exploitation CineVault

Lancer la sonde à la demande avec Python 3.11 ou plus récent. Elle effectue
un GET direct sur chaque URL de santé déclarée et exige un HTTP 200 de l’API
et du Web. Elle conserve la validation TLS standard et refuse les redirections.
Le délai s’applique aux opérations réseau de chaque requête. Utiliser les
URL de santé du périmètre à contrôler, sans identifiant, paramètre ni fragment.

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
non nul de `verify`. La sonde doit lire le chemin de cette tentative.
Conserver les reçus de sauvegarde et de vérification dans des
emplacements protégés.
[Commande de vérification](../operations/MONGODB_BACKUP.md#rotation-fréquence-et-rétention).

La sonde rapproche le SHA-256 et la taille logique des deux reçus.
Elle vérifie l’ordre des horodatages et applique
`--max-backup-age-hours` à l’âge de capture au moment du contrôle.
Le résultat `backup_verification` donne l’âge de capture, l’âge du
contrôle ou l’état de l’erreur. Un fichier manquant, un SHA-256
différent ou une capture périmée fait échouer la sonde.

Un essai sous Windows a utilisé un reçu issu d’une nouvelle archive
MongoDB 8.0.38 et le reçu d’une restauration antérieure. Les endpoints
HTTP locaux de test ont signalé une panne API puis un retour à 200.
La sonde a aussi refusé le reçu manquant et le SHA-256 divergent.
[Reçu du contrôle d’exploitation](../../evidence/public/operating-probe-backup-verification-20261126.json).

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
MongoDB 8.0.38. Les deux certificats ont passé un seuil de 24 heures,
puis déclenché une alerte au seuil de 72 heures. Les essais ont aussi
signalé une CA et un nom TLS incorrects, un fichier CA manquant et
un service injoignable. Les réponses HTTP et les reçus de sauvegarde
utilisés pendant ce test étaient synthétiques.
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
L’exécution reste manuelle.
