# Observabilité et exploitation

L'API et le Web émettent un événement JSON pour chaque réponse traitée par Flask.
La durée en millisecondes s'arrête à la construction de la réponse. Le champ
`route` porte le modèle Flask, par exemple `/films/<film_id>`, ou `unmatched`.
Le serveur génère un UUIDv4 et le retourne dans `X-Request-ID`. Le Web ajoute
au plus huit identifiants retournés par l'API sur cette requête. Les journaux
d'accès Gunicorn bruts sont désactivés. L'application ne collecte aucun corps,
cookie, jeton, paramètre de recherche ou chemin concret dans ces événements.

## Résumer un intervalle

Le [résumeur Python](../scripts/summarize_http_logs.py) lit l'entrée standard.
Il calcule les comptes HTTP, le pourcentage de 5xx et les percentiles 50, 95 et
99 par service et par route. Utiliser un intervalle borné pour limiter le volume
en mémoire. Les autres lignes sont comptées parmi les lignes ignorées sans être
reproduites. Le mode `--request-id` relie un événement Web à ses réponses API.

```sh
{
  docker service logs --raw --since 5m cvstage_api 2>&1
  docker service logs --raw --since 5m cvstage_web 2>&1
} | python3 scripts/summarize_http_logs.py
```

Un rapport vide signifie qu'aucun événement au format attendu n'a été reçu.
Contrôler la fenêtre, la collecte et les révisions exécutées avant de conclure
sur le trafic. Conserver avec le rapport les heures UTC, les sources exactes
des images et le résultat de la commande.

## Diagnostiquer une indisponibilité

1. Vérifier l'état du manager et des tâches via `docker node ls`,
   `docker stack services cvstage` et `docker service ps cvstage_api`.
2. Comparer `/health` du Web, qui vérifie son processus, et `/health` de l'API,
   qui vérifie le stockage sélectionné. En cas de 503 API, relever l'heure et
   la première erreur expurgée. Vérifier les montages, les échéances du
   certificat, la résolution DNS et l'état primaire du réplica depuis les
   conteneurs autorisés.
3. Relever `docker stats --no-stream` pour les tâches concernées et l'espace
   disponible de leur volume avec `df -h`. Une saturation du disque ou un
   redémarrage OOM demande un diagnostic distinct de l'authentification.
4. Examiner l'empreinte, l'âge et le dernier résultat de restauration de la
   sauvegarde. Utiliser la [procédure de sauvegarde portable](quality/MONGODB_PORTABLE_BACKUP.md)
   et les preuves de restauration associées.
5. Garder les modifications du staging indépendantes de l'instance stable.
   Retenir une fenêtre avant/après une correction et rejouer la sonde concernée.

Aucun collecteur périodique ni destination d'alerte n'a été installé pour
cette validation. La perte de collecte, les seuils de ressources, la fréquence
des sauvegardes et le délai de reprise relèvent de la politique d'exploitation
du déploiement.

## Résultat mesuré

Sur le PC, un vrai appel HTTP à `/films` du Web `70fa78e` a chargé
`/api/v1/movies` de l'API `22bcecd`. Le résumeur a relié les deux événements
200 à partir de l'identifiant retourné par le Web. Le journal n'a retenu
aucune des valeurs de contrôle transmises dans la recherche, le cookie ou
l'identifiant entrant. [Reçu et révisions](../evidence/public/mongodb-performance-observability-20261121.json).
