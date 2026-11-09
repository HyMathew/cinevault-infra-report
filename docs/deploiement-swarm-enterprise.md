# Déploiement Enterprise sur trois VM

**État actuel vérifié le 9 novembre 2026 à 10 h 40 Paris :** images des CI API `6a86f2e` et web `4883876` téléchargées anonymement sur les trois nœuds et déployées par digests GHCR. Vingt-deux contrôles réussis, sauvegarde et données/comptes/secrets/sessions préservés. Les métadonnées externes sont activées et une recherche/aperçu réelle a réussi via la stack. Voir la [synthèse des CI, digests et limites](validation-current.md).

**Jalon historique : mise à jour effectivement vérifiée le 8 novembre 2026 à 23 h 14 UTC, soit le 9 novembre à 00 h 14 à Paris.** API `4b15406` et web `9b1da4f` ont passé 31 contrôles sur trois VM, avec images exactes, santé, UID 10001, racine en lecture seule et `cap_drop: ALL`. Sauvegarde effectuée ; empreintes du document métier et des comptes identiques avant/après, session existante préservée et nouvelle connexion web avec contexte signé fonctionnelle. La troisième clé dédiée est montée comme secret Docker en mode 0400 pour UID/GID 10001 ; les deux anciennes clés, les comptes et le volume ont été préservés. Voir la [synthèse complète et ses limites](validation-current.md). Les paragraphes ci-dessous distinguent cette mise à jour de la première campagne historique.

Lors de la première campagne distribuée du 8 novembre 2026, la stack Enterprise a été exécutée avec un manager dédié et deux workers distincts. Les deux images étaient celles des révisions API `e7ff089` et web `4303ef3`, validées localement au jalon qualité. Cinquante contrôles fonctionnels distribués ont réussi, dont une course d'attribution d'exemplaire et la persistance après recréation du service API. La preuve couvre ce laboratoire et ces images ; elle ne démontre ni haute disponibilité, ni certification de sécurité, ni CI GitHub.

## Préconditions et placement

Relever OS, ressources, routes et adresses de chaque VM. Docker29.9.3, Compose5.7.0 et Git2.43.0 ont été constatés sur les trois nœuds utilisés. Vérifier TCP2377, TCP/UDP7946 et UDP4789 dans les deux sens, puis tester réellement l'Overlay chiffré : des probes UDP seules ne prouvent pas l'encapsulation ni la communication d'un service. L'option encrypted utilise IPsec ; les règles réseau doivent permettre ce trafic.

Le manager est en disponibilité Drain. Les workers portent respectivement `cinevault=web` et `cinevault=api`. Le pool Overlay doit être déterminé localement après inventaire des routes et vérification de l'absence de chevauchement sur tous les nœuds ; aucune plage propre au laboratoire n'est publiée ici. Les adresses physiques proviennent de l'inventaire, jamais d'un exemple recopié.

La stack [stack.enterprise.yaml](../stack.enterprise.yaml) est distincte de la stack pédagogique historique. Une seule réplique API monte le volume local `cinevault-enterprise-data` sur le worker API. La présentation utilise le nom DNS du service API sur le réseau chiffré. Aucun port API n'est publié. Le web publie8080 en mode host sur son worker ; ce port n'est pas automatiquement limité à localhost.

## Distribution courante par registre

Utiliser les deux références `ghcr.io/hymathew/cinevault-api@sha256:…` et `ghcr.io/hymathew/cinevault-web@sha256:…` complètes dans la [synthèse courante](validation-current.md). Ne pas déployer un tag mutable en supposant son contenu. Le digest du manifeste et son `config.digest` lient le registre au reçu d'image scannée de la CI. Contrôler ensuite le téléchargement sur chaque worker, les `RepoDigests`, la spécification de service et les conteneurs effectifs. Un téléchargement anonyme a été testé avec un dossier de configuration Docker temporaire vide ; aucune connexion au registre n'est nécessaire pour ces images publiques.

La CI ne publie que sur la branche par défaut après tests, qualité, construction, santé et scan. Les exécutions de contribution construisent/scannent sans droit de publication. Les permissions d'écriture de paquet et le jeton sont limités au job et à l'étape de publication.

## Distribution historique par préchargement

Pour ce petit cluster fixe, les images ont été exportées depuis le poste, transférées par SFTP sur les trois nœuds, puis chargées par Docker. Le SHA256 de l'archive était identique sur le poste et les trois VM ; les IDs chargés ont ensuite été comparés au manifeste du jalon qualité :

| Image locale | ID de l'image vérifié |
|---|---|
| cinevault-api:rt0705-e7ff08980a1f | sha256:c28c0d9a112d016a53397e1ee6a7306ad4b2965f8be99cd8903208ab8ff68ff9 |
| cinevault-web:rt0705-4303ef317a45 | sha256:4a8dbd9207e1ccb3a877c6ae925e014a2151cc250391613f877e6647ab8762fb |

Un tag seul est mutable. Ici, le contrôle des IDs avant déploiement et des conteneurs réellement exécutés complète le nom local. La commande de déploiement emploie `--resolve-image never` : ce mécanisme repose sur les caches préchargés et vérifiés, sans registre publié. Un nœud ajouté ou vidé doit recevoir les images avant de pouvoir exécuter les tâches. Cette phrase décrit le jalon historique : le déploiement courant utilise désormais le registre et les images issues de la CI vérifiée.

## Données et secrets

Le fichier de stack courant ajoute le contexte visiteur signé, postérieur à la première preuve distribuée ci-dessus. Il exige trois secrets : `cinevault_auth_throttle_v1`, `cinevault_web_session_v1` et `cinevault_client_context_v1`. Le troisième est une clé dédiée, partagée uniquement par web/API ; `CLIENT_CONTEXT_KEY_FILE` la désigne et l'API exige `CLIENT_CONTEXT_REQUIRED=true`. Il ne faut ni réutiliser une clé existante d'une autre fonction, ni remplacer les deux anciennes clés lors de cette mise à jour. La mise à jour a été vérifiée séparément sur les workers le 9 novembre à 00 h 14, heure de Paris ; ses 31 contrôles restent distincts des 50 contrôles du premier déploiement.

Avant le premier lancement, créer uniquement un volume identifié comme neuf, puis initialiser explicitement `V2Store("/data/enterprise.json").initialize()` dans l'image API en UID10001. Un volume, fichier ou secret préexistant doit être inspecté ; cette procédure ne doit pas l'écraser. La fonction d'initialisation refuse une cible déjà présente. Les données restent sur le worker API ; un changement de label ou de machine ne déplace pas ce volume.

Pour une installation neuve, créer les trois secrets Docker aléatoires et stables ci-dessus, à partir de 64 octets chacun. Les données des secrets sont transmises sur l'entrée standard, jamais dans le YAML, les arguments ou les journaux. La stack les monte en lecture seule pour UID/GID 10001, mode 0400. L'API lit `AUTH_THROTTLE_KEY_FILE`, le web `SECRET_KEY_FILE`, et les deux lisent `CLIENT_CONTEXT_KEY_FILE`. Le premier administrateur doit être créé explicitement dans le magasin initialisé ; aucun mot de passe par défaut n'est fourni. Les secrets et accès du laboratoire exécuté ont une copie de reprise chiffrée sur le poste, hors dépôts publics.

## Déploiement et contrôle effectif

Après vérification des images, volume et secrets, fournir les références par digest dans `CINEVAULT_API_IMAGE` et `CINEVAULT_WEB_IMAGE` de l'environnement du processus. Pour activer les métadonnées, définir `METADATA_ENABLED=true` et un `WIKIMEDIA_USER_AGENT` identifiant le projet et son URL publique. La valeur par défaut reste false ; l'application fonctionne aussi sans fournisseur externe. Contrôler d'abord la configuration puis déployer :

```sh
docker stack config -c stack.enterprise.yaml >/dev/null
docker stack deploy --resolve-image always -c stack.enterprise.yaml cinevault
docker stack services cinevault
docker stack ps --no-trunc cinevault
```

Ces commandes constituent une procédure ; leur simple présence n'atteste pas leur exécution dans un nouvel environnement. Contrôler les tâches sur les workers attendus, les IDs réels des images, UID10001, racine en lecture seule, capacités retirées et healthchecks. Les deux services disposent d'un montage tmpfs explicite sur `/tmp` de64Mio. **La forme courte `tmpfs:` avait été acceptée par `docker stack config` mais ignorée dans la spécification de service de ce laboratoire** ; Gunicorn échouait alors faute de dossier temporaire inscriptible. Le montage long `volumes: type: tmpfs` a été vérifié après conversion dans les `Mounts` effectifs, puis par le démarrage des deux services.

La sonde web vérifie son processus ; celle de l'API valide l'accès au magasin. Leur succès ne remplace pas les parcours HTTP. La campagne distribuée a notamment exercé inscription, connexion, CSRF, autorisations, CRUD versionné, recherche, collections privées y compris refus admin404, demandes de prêts, double attribution concurrente (un200 et un409), retour, statistiques et recommandations. Une mise à jour forcée du service API a recréé sa tâche ; film, collection, session et historique du prêt restaient accessibles ensuite. Cette opération teste une recréation de conteneur, pas une panne de disque ni une reprise multi-hôte.

## Accès depuis le poste et limites

L'accès utilisé depuis le PC passe par un tunnel SSH lié à127.0.0.1:8080, avec vérification stricte de la clé hôte du worker web. Le navigateur utilise HTTP loopback et le trajet distant est chiffré par SSH. Ce mécanisme n'est pas une terminaison HTTPS publique ; `COOKIE_SECURE=false` correspond à ce contexte. Le port8080 reste également publié sur les interfaces du worker : réserver le laboratoire à ses données synthétiques et à son réseau prévu, sans annoncer une exposition sûre de vrais comptes sur Internet.

Le test Chrome local a exercé recherche anonyme, connexion administrateur et filtre d'historique. Les largeurs desktop et390px ne présentaient pas de débordement horizontal sur l'écran testé ; cela ne constitue pas une validation exhaustive de l'accessibilité. Les captures et reçus sont conservés dans l'espace de preuves privé avant audit de publication.

La limite ISO/ordre de boot des VM2/3 reste ouverte : le choix du disque dans GRUB a été nécessaire malgré l'éjection demandée. Le cluster actuel fonctionne, mais le redémarrage autonome de ces VM ne doit pas être déclaré validé. Le manager unique, la réplique API unique et le volume local constituent des points de défaillance explicites. Garder les sauvegardes et les étapes de reprise séparées des essais jetables.
