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

La [sonde d'exploitation à la demande](quality/OPERATING_PROBE.md) vérifie
les deux endpoints de santé, un résumé de collecte et la fraîcheur des reçus
de sauvegarde et de restauration. L'exploitant fournit les fenêtres et seuils.
Le test local a détecté une réponse 503 de l'API puis son retour à 200 avec le
Web toujours disponible. Il a aussi détecté l'absence de collecte et une
sauvegarde périmée à partir de reçus synthétiques. La sonde s'exécute manuellement.

L’option `--tls-policy` relève l’échéance du certificat servi par
le proxy ou MongoDB après une négociation TLS vérifiée. Un certificat
proche du seuil ou rejeté fait échouer la sonde avec un état par service.
[Configurer la vérification des échéances](quality/OPERATING_PROBE.md#vérifier-léchéance-des-certificats).

Pour contrôler la copie hors VM, `verify --maximum-age-hours` vérifie
le SHA-256 de confiance, authentifie l’archive et calcule son âge à
partir de la date de capture. Le planificateur peut déclencher une
alerte sur le code de sortie. La sonde d’exploitation peut rapprocher
ce reçu du reçu de sauvegarde dans le même contrôle que les services.
[Commande et procédure d’exploitation](operations/MONGODB_BACKUP.md#rotation-fréquence-et-rétention).

## Résultat mesuré

Sur le PC, un vrai appel HTTP à `/films` du Web `70fa78e` a chargé
`/api/v1/movies` de l'API `22bcecd`. Le résumeur a relié les deux événements
200 à partir de l'identifiant retourné par le Web. Le journal n'a retenu
aucune des valeurs de contrôle transmises dans la recherche, le cookie ou
l'identifiant entrant. [Reçu et révisions](../evidence/public/mongodb-performance-observability-20261121.json).

### Relevé sur les workers Swarm

Le 25 novembre 2026, un client sur VM1 a effectué 60 lectures unitaires
d'un document synthétique en TLS sur MongoDB 8.0.38, sur VM2. Après une
lecture d'échauffement, le client a attendu 250 ms entre deux lectures.
La série a duré 15,3 s et la latence observée par le client était de 7 ms
au p50, 13 ms au p95 et 46 ms au p99, à la résolution de la milliseconde.

Sur les trois relevés pris pendant la série, `docker stats` a mesuré
2,47 %, 2,42 % puis 74,65 % de CPU, et environ 109,4, 109,4 puis 274 Mio
de mémoire pour le conteneur MongoDB. Ces instantanés incluent les
processus de sonde du conteneur et ne permettent pas d'attribuer le pic
à une opération particulière. Entre les relevés encadrant la série,
les compteurs cumulés du conteneur ont augmenté d'environ 39 ko en
réception et 46 ko en émission. Le worker VM2 disposait encore d'environ
1 216 Mio de RAM et 5,86 Gio sur le disque de Docker au relevé intermédiaire.
[Définition des compteurs Docker](https://docs.docker.com/reference/cli/docker/container/stats/).

Les sondes internes du Web et de l'API stables ont répondu HTTP 200 avant,
pendant et après. Douze sondes Web depuis le PC ont répondu HTTP 200, dont
six pendant la fenêtre qui encadre la série. L'exercice a relevé la
capacité sur les trois nœuds. Avec un seuil de démonstration à 6 Gio, la
sonde a détecté le passage temporaire du disque Docker de VM2 sous le
seuil, puis le retour à l'état normal à partir des mesures réelles. Cet
essai à faible cadence calibre le diagnostic de capacité. Il ne fixe
aucun objectif de performance pour le staging applicatif.
[Reçu de capacité Swarm](../evidence/public/swarm-mongodb-capacity-20261125.json).
