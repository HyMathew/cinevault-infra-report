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

### Contrôler la capacité Swarm

Pour le lab à trois nœuds, fournir un JSON contenant `nodes` avec les rôles
`web`, `api` et `manager`. Chaque entrée contient `timestamp_utc`,
`available_ram_bytes` et `docker_available_disk_bytes`. Relever
`MemAvailable` dans `/proc/meminfo` sur le nœud et convertir ses Kio en
octets. Relever l'espace disponible en octets sur le système de fichiers qui
contient le répertoire Docker. Le [reçu de mesure](../../evidence/public/swarm-mongodb-capacity-20261125.json)
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

## Résultats et limites

| Code | Interprétation |
| --- | --- |
| `0` | Les deux contrôles HTTP, les trois contrôles de preuves et le contrôle de capacité s’il est demandé réussissent. |
| `1` | Au moins un contrôle échoue. Le JSON identifie le service ou la preuve et son état. |
| `2` | La validation des arguments échoue avant les appels réseau. |

La sortie contient les états, codes HTTP, âges et compteurs. Les URL, chemins,
corps HTTP, empreintes et contenus de journaux restent dans les sources locales.
Une collecte absente, vide, illisible, invalide ou périmée entraîne un échec.
Une collecte partielle ou au-dessus du seuil détaille l’état de chaque service.

L’opérateur déclare les heures UTC de fin qui servent au calcul de fraîcheur.
Conserver les preuves avec ces heures et leurs sources. Les reçus du contrôle
portable CI qualifient les contrats hors ligne. La sonde attend les reçus natifs
d’une sauvegarde et d’une restauration.
Le dernier exercice de restauration peut porter sur un autre chiffré que la
sauvegarde récente. Le contrôle porte sur les métadonnées des deux reçus.
L’exécution reste manuelle.
