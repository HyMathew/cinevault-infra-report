# Staging indépendant et exploitation proportionnée

Étude du12novembre2026, distincte d'un déploiement. RemoteLabz conserve son rôle
pédagogique ; aucun port Internet, hébergement payant ou service de staging n'a
été créé par cette étude. Les rôles web/API/manager du laboratoire sont préservés.

## Ressources réellement observées

À16:02:26UTC, une observation en SSH depuis le PC confirme trois nœuds Ready,
manager Drain, services API et web chacun1/1 et healthy depuis trois jours.
Le [reçu de ressources](../../evidence/public/lab-resource-snapshot-20261112.json)
contient les valeurs collectées, sans adresses ni identités personnelles :

| Rôle | CPU logiques | RAM totale | RAM disponible | Disque racine disponible |
|---|---:|---:|---:|---:|
| Web | 2 | 1966 Mio | 1446 Mio | 8,68 Gio |
| API | 2 | 1966 Mio | 1480 Mio | 8,06 Gio |
| Manager | 2 | 1966 Mio | 1507 Mio | 30,48 Gio |

Ce sont des instantanés de disponibilité, pas des besoins sous charge. Les sondes
Mongo précédentes bornent un serveur à768Mio et ses clients séparément ; elles
ne justifient pas d'ajouter automatiquement une pile Prometheus/Grafana/Loki sur
le worker API. Le manager drainé ne devient pas un worker applicatif pour gagner
de la place.

## Choix du reverse proxy pour le prochain environnement

Pour ce nombre limité de services, **Caddy est le choix retenu pour le prototype
de staging**, avec routes explicites. Son HTTPS automatique et sa CA locale
permettent de séparer test privé et domaine public ; une CA locale exige une
distribution volontaire de sa racine de confiance et ne vaut pas un certificat
public. Voir la [documentation HTTPS officielle](https://caddyserver.com/docs/automatic-https).

Traefik est une alternative cohérente lorsque la découverte dynamique des services
Swarm devient nécessaire. Son
[provider Swarm](https://doc.traefik.io/traefik/reference/install-configuration/providers/swarm/)
ajouterait ici une dépendance à l'API du manager et sa frontière d'accès. Les routes
actuelles ne justifient pas cette découverte ni deux reverse proxies simultanés.
Ce choix ne fixe encore aucune image Caddy : version, digest, licence, scan et
configuration seront qualifiés lors du prototype.

Le staging doit posséder son propre hôte ou contexte de déploiement, volumes,
secrets, réseau Mongo privé et données synthétiques. Un autre nom de stack partageant
les mêmes disques et secrets n'est pas une isolation suffisante. Une démo locale
peut utiliser la CA interne et le loopback ; l'ouverture sur un domaine externe
requiert une cible explicite et des contrôles de DNS, certificats et exposition.
Les VM universitaires ne sont pas exposées publiquement par ce choix.

## Exploitation à livrer avec le backend final

Les healthchecks et la rotation Docker json-file10m×3 existent dans la stack
historique. Le web vérifie son processus ; ce n'est pas une preuve de disponibilité
de l'API. La future readiness API doit vérifier le backend **sélectionné** et
refuser une panne Mongo sans basculer silencieusement sur JSON.

L'observabilité retenue commence par des logs structurés assainis, identifiants de
corrélation, durée/statut des requêtes, disponibilité/readiness, CPU/RAM/disque et
âge/résultat des sauvegardes. Aucun corps, jeton, mot de passe ou chaîne de
connexion ne doit devenir une dimension ou un message. Le journal métier circulaire
n'est ni un journal de sécurité immuable ni une alerte.

Un contrôle périodique léger doit produire un code d'échec et un reçu borné,
collecté hors VM ; sa panne ou l'absence de reçu est elle-même un signal. Les seuils,
durées de conservation et destination d'alerte seront configurés, puis testés avec
panne API/Mongo, disque sous seuil, sauvegarde ancienne et collecteur indisponible.
Ces éléments ne sont pas annoncés comme déjà installés par l'instantané SSH.

Le staging sera qualifié seulement après installation depuis clone propre, HTTPS,
refus externe27017, parcours authentifié synthétique, arrêt/redémarrage,
sauvegarde/restauration, mise à jour/rollback, diagnostic et vérification de
disponibilité. Son indépendance et sa reprise devront être démontrées par un
opérateur extérieur. Même réussi, il ne sera pas décrit comme une production
certifiée ou un replica set physiquement redondant.
