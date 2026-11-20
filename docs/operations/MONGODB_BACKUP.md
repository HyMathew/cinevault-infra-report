# Sauvegarde MongoDB chiffrée et restauration isolée

L'outil public [tools/mongodb_backup](../../tools/mongodb_backup/__main__.py) s'utilise depuis un clone du dépôt d'infrastructure, sans Codex, DPAPI, helper privé ou connexion SSH imposée. Il crée une sauvegarde logique d'une seule base CineVault, chiffrée par le programme officiel age, puis restaure uniquement dans une base neuve d'un processus MongoDB distinct. Il ne modifie ni services, ni volumes, ni comptes administrateurs. Une [qualification native du backup/restore et des services restaurés](../quality/MONGODB_PORTABLE_BACKUP.md) a effectivement restauré 393 documents et 40 index sur une autre VM après suppression de la source, vérifié leur persistance après redémarrage, puis exécuté 31 appels de services métier sur une seconde restauration neuve. La requalification du schéma final reste nécessaire s'il évolue avant exploitation. L'[étude C2c antérieure](../quality/MONGODB_BACKUP_STUDY.md), privée et liée à DPAPI, est une preuve historique distincte.

## Conditions obligatoires

- Hôte opérateur autorisé : Windows x64 avec Windows PowerShell système, ou Ubuntu 24.04 x64 ; Python 3.11 à 3.14. Les versions sont verrouillées : age 1.3.2, Database Tools 100.20.0 et MongoDB Server 8.0.34. Le dump et le restore utilisent la même version Tools. Voir les [notices et limites d'audit](../../tools/mongodb_backup/THIRD_PARTY.md).
- Replica set accessible sur son primaire. Les deux identités source doivent joindre exactement le même déploiement et la même configuration de transport. URI `mongodb://` avec utilisateur, mot de passe encodé, `authSource`, `replicaSet` et `authMechanism=SCRAM-SHA-256` ; aucun nom de base dans le chemin de l'URI. Les seules autres options acceptées sont `directConnection`, `tls` et `tlsCAFile`. TLS vérifié est obligatoire hors boucle locale ; les options TLS permissives, SRV, lecture secondaire et paramètres supplémentaires sont refusés.
- Tous les writers applicatifs doivent prendre en premier, dans leur transaction, le coordinateur canonique `coordination / business`, dont `revision` est un BSON Int64. Arrêter séparément migrations, DDL, scripts administrateurs et writers directs. Les index TTL, vues, collections capped/time-series et chiffrement de champs sont refusés. Ne pas désactiver ces protections pour obtenir une sauvegarde ; choisir une maintenance et requalifier une méthode adaptée si le schéma en dépend.
- Le gel ne convient qu'à un dump assez court : 30 secondes par défaut, maximum 45, inventaires compris. La transaction reste non validée puis est annulée. Les requêtes applicatives concurrentes peuvent recevoir des conflits et épuiser leur budget de retry : prévoir une fenêtre de maintenance. Une transaction expirée, un changement de primaire, un inventaire différent ou un outil en échec invalide le résultat ; aucun fichier final n'est publié.
- La cible doit être un serveur/replica set isolé, avec nouveaux volumes provisionnés par la procédure de déploiement et sans trafic applicatif. L'outil exige un autre nom de base, une base sans collection et un autre identifiant de processus MongoDB. Ce dernier contrôle ne prouve pas à lui seul la séparation des volumes : l'opérateur doit la vérifier. Ne jamais pointer la commande vers une base de production existante.
- Stockage local fiable prenant en charge les liens physiques (NTFS/ext4), espace libre pour le fichier chiffré et une copie chiffrée temporaire pendant vérification/restauration. Aucun dump clair n'est écrit sur disque par l'outil. Les dumps mémoire, le swap/pagefile et un hôte compromis restent hors de cette garantie.

## Installation depuis un clone

Créer un environnement Python dédié hors du dépôt, l'activer puis installer uniquement les wheels verrouillées :

```text
python -m venv ../cinevault-backup-venv
```

Sous Ubuntu, `source ../cinevault-backup-venv/bin/activate` ; sous PowerShell, `../cinevault-backup-venv/Scripts/Activate.ps1`. Si la politique du poste interdit l'activation, appeler directement son interpréteur sans changer cette politique.

```text
python -m pip install --only-binary=:all: --require-hashes -r tools/mongodb_backup/requirements.lock
python -m pip check
python -m tools.mongodb_backup --help
python -m tools.mongodb_backup init-directory --directory ../cinevault-operations
```

Définir `OPS` comme chemin absolu de ce nouveau dossier : `$OPS = (Resolve-Path ../cinevault-operations).Path` en PowerShell, `OPS="$(cd ../cinevault-operations && pwd)"` sous Ubuntu. Utiliser un emplacement hors Git et hors des répertoires de données Mongo. Les commandes suivantes ont la même forme dans les deux shells :

```text
python -m tools.mongodb_backup init-directory --directory "$OPS/work"
python -m tools.mongodb_backup init-directory --directory "$OPS/keys"
python -m tools.mongodb_backup init-directory --directory "$OPS/backups"
python -m tools.mongodb_backup.install_tools --work-dir "$OPS/work" --destination "$OPS/programs"
```

L'installateur télécharge uniquement les archives HTTPS identifiées dans le verrou, vérifie leur SHA-256 avant extraction et ne lit que les binaires et notices attendus ; il n'exécute aucun script distant. Pour un hôte sans Internet, transférer les deux archives officielles correspondant à son système et ajouter `--archive-directory /chemin/du/cache`. Le dossier de destination doit être neuf. Les versions des exécutables sont revérifiées à chaque opération ; employer les fichiers installés et vérifier leurs hashes si l'on utilise un autre mode de distribution.

Sous Ubuntu, définir `AGE="$OPS/programs/age/age"`, `KEYGEN="$OPS/programs/age/age-keygen"`, `DUMP="$OPS/programs/mongodb/mongodump"`, `RESTORE="$OPS/programs/mongodb/mongorestore"`. Sous PowerShell : `$AGE="$OPS/programs/age/age.exe"`, `$KEYGEN="$OPS/programs/age/age-keygen.exe"`, `$DUMP="$OPS/programs/mongodb/mongodump.exe"`, `$RESTORE="$OPS/programs/mongodb/mongorestore.exe"`. Ces chemins doivent être absolus.

Les répertoires sont privés : mode 0700 et fichiers 0600 sous Ubuntu ; ACL inspectées sous Windows, limitées au propriétaire courant, SYSTEM, Administrateurs et OWNER RIGHTS. Les administrateurs locaux font partie de la frontière de confiance. Les liens symboliques et points de réanalyse sont refusés. Ne pas retirer un contrôle d'ACL pour contourner un échec.

Les chemins sont normalisés lexicalement, y compris les composants `..`, avant les comparaisons d'emplacement et les ouvertures. Les composants de l'orthographe originale sont contrôlés avant cette normalisation : écrire `lien/../fichier` ne masque donc pas un lien ou une jonction. Les fichiers privés d'identité et de connexion doivent rester hors du parent de l'archive, quelle que soit l'orthographe des deux chemins. Après refus des liens, les identités réelles des répertoires existants sont aussi comparées : un alias Windows étendu ou DOS 8.3 du même dossier ne contourne pas ce contrôle ; les fichiers externes légitimes gardent ces orthographes acceptées. Aucun résolveur suivant les liens n'est utilisé. Ces contrôles ne sont pas une isolation contre un processus malveillant de même privilège modifiant simultanément le système de fichiers.

## Clés indépendantes et identités MongoDB

Sur le poste de récupération, générer la clé native hybride recommandée par age : sous Ubuntu, `"$KEYGEN" -pq -o "$OPS/keys/restore-2026.txt"` ; sous PowerShell, `& $KEYGEN -pq -o "$OPS/keys/restore-2026.txt"`. Le fichier privé n'est jamais nécessaire sur le serveur de sauvegarde. Exporter uniquement les destinataires publics :

```bash
"$KEYGEN" -y "$OPS/keys/restore-2026.txt" > "$OPS/keys/recipients.txt"
chmod 600 "$OPS/keys/recipients.txt"
```

Ou sous PowerShell, conserver un encodage ASCII explicite :

```powershell
& $KEYGEN -y "$OPS/keys/restore-2026.txt" | Set-Content -Encoding ascii "$OPS/keys/recipients.txt"
```

Préserver la clé privée sur deux supports indépendants, hors du serveur source et hors des sauvegardes, sous contrôle d'accès physique et logique. Tester sa lecture depuis un autre poste autorisé. Ne pas la mettre dans Git, un ticket, un journal, une variable d'environnement ou la ligne de commande. La procédure accepte uniquement des fichiers contenant des clés natives age X25519 ou hybrides ; plugins, clés SSH et demandes interactives de phrase de passe sont refusés. Le chiffrement protège la confidentialité et l'intégrité, mais une clé publique permet à quiconque de créer une nouvelle archive : conserver aussi le reçu SHA-256 dans un canal authentifié indépendant.

Depuis une session `mongosh` d'administration autorisée, créer des identités distinctes avec `passwordPrompt()` ; aucun mot de passe littéral dans les commandes ou historiques. Exemple de rôles, en remplaçant seulement les noms de bases selon le déploiement :

```javascript
const src = db.getSiblingDB("cinevault");
src.createRole({role: "backupFreeze", privileges: [
  {resource: {db: "cinevault", collection: "coordination"}, actions: ["find", "update"]}
], roles: []});
src.createUser({user: "backupReader", pwd: passwordPrompt(), roles: [{role: "read", db: "cinevault"}]});
src.createUser({user: "backupFreeze", pwd: passwordPrompt(), roles: [{role: "backupFreeze", db: "cinevault"}]});
const auth = db.getSiblingDB("restore_auth");
auth.createRole({role: "isolatedRestore", privileges: [
  {resource: {db: "cinevault_restore_20261113", collection: ""}, actions: ["find", "insert", "createCollection", "createIndex", "listCollections", "listIndexes"]},
  {resource: {db: "cinevault_restore_20261113", collection: "_cinevault_restore_claim"}, actions: ["dropCollection"]}
], roles: []});
auth.createUser({user: "isolatedRestore", pwd: passwordPrompt(), roles: [{role: "isolatedRestore", db: "restore_auth"}]});
```

Le compte de lecture source ne peut pas écrire ; le compte de gel ne peut modifier que le coordinateur ; le compte cible ne peut ni supprimer une base, ni remplacer une collection existante, ni désactiver un validateur. La suppression autorisée porte seulement sur la collection technique de réservation d'une restauration réussie. Les comptes administrateurs ne sont jamais passés à l'outil.

Créer trois fichiers JSON privés dans `keys`, avec une seule propriété `uri`, pour la lecture source, le gel et la cible. Le JSON est aussi un fichier de configuration YAML accepté par Database Tools. Exemple de structure, à renseigner par un gestionnaire de secrets ou un éditeur autorisé, sans le coller dans un terminal :

```json
{"uri":"mongodb://IDENTITE:MOT_DE_PASSE_ENCODE@127.0.0.1:27017/?replicaSet=rs&authSource=BASE_AUTH&authMechanism=SCRAM-SHA-256&directConnection=true"}
```

Les URI source et gel doivent avoir les mêmes hôtes/options, sauf identité et base d'authentification. La cible utilise un endpoint distinct. Les fichiers sont lus sous contrôle de permissions puis copiés dans un dossier temporaire privé ; seuls leurs chemins sont passés aux outils. Sous Ubuntu appliquer `chmod 600` aux fichiers créés par l'éditeur. Sous Windows conserver l'héritage du dossier privé et vérifier l'absence d'ACE ajoutées par l'éditeur. Aucun fichier de configuration ni clé privée ne doit se trouver dans `backups`.

## Sauvegarder, sortir de la VM, vérifier

Après contrôle des writers, des index et de la fenêtre de maintenance :

```text
python -m tools.mongodb_backup --age "$AGE" backup --work-dir "$OPS/work" --mongodump "$DUMP" --database cinevault --source-config "$OPS/keys/source-reader.json" --freeze-config "$OPS/keys/source-freeze.json" --recipients-file "$OPS/keys/recipients.txt" --output "$OPS/backups/cinevault-20261113T020000Z.cvmb.age" --freeze-seconds 30 --timeout 300 --acknowledge-coordinator-writers-only
```

Un nom neuf est obligatoire ; aucun écrasement n'est possible. Le reçu JSON sur stdout comprend le hash du fichier chiffré, la durée du gel et la confirmation de son annulation. Un code de sortie non nul invalide l'opération, même si un programme a produit des octets. Le fichier final n'est publié qu'après réussite des deux programmes et des contrôles de cohérence ; les fichiers `.pending` sont nettoyés sur les erreurs traitées. Après arrêt brutal de l'hôte, un `.pending` peut rester : il n'est jamais assimilé à une sauvegarde réussie.

La transaction prend le verrou du coordinateur avant les inventaires et le dump, vérifie côté serveur qu'elle vit encore après celui-ci, compare toutes les collections/documents/indexes/options, puis annule l'incrément non validé. Les documents sont hachés en BSON, triés par `_id`, sans convertir Int64 en entier ordinaire ; l'ordre des clés d'index est conservé. Le flux `mongodump --archive --gzip` d'une seule base et son inventaire sont entièrement chiffrés dans la même enveloppe age. Ce n'est ni une copie de volume à chaud ni une sauvegarde oplog complète. La fréquence d'un point par jour ne fournit pas un RPO nul opérationnel.

Transférer uniquement le fichier `.cvmb.age` et son reçu vers un stockage hors VM autorisé, avec authentification du serveur et permissions adaptées, par exemple SFTP ou le mécanisme de sauvegarde de l'organisation. L'outil reste indépendant de ce transport. Vérifier le SHA-256 à destination et conserver le reçu dans un canal protégé distinct. Ne pas copier tout `OPS`, qui contient des fichiers sensibles. L'hôte de récupération peut vérifier l'archive sans joindre MongoDB :

```text
python -m tools.mongodb_backup --age "$AGE" verify --work-dir "$OPS/work" --input "$OPS/backups/cinevault-20261113T020000Z.cvmb.age" --identity-file "$OPS/keys/restore-2026.txt" --timeout 300
```

Ce contrôle relit tout le fichier ; une clé erronée, un octet altéré, une troncature même tardive ou des données ajoutées refusent le résultat. Comparer aussi le hash retourné au reçu de confiance : age seul ne certifie pas l'identité de l'auteur.

## Restaurer sans écraser

Préparer un replica set isolé de même version et vérifier séparément sa FCV, ses nouveaux volumes, ses identités et l'absence de trafic. Provisionner le rôle cible pour le nom neuf retenu. Récupérer le SHA-256 du reçu authentifié, pas d'un fichier de hash modifiable à côté d'une archive non fiable :

```text
python -m tools.mongodb_backup --age "$AGE" restore --work-dir "$OPS/work" --mongorestore "$RESTORE" --target-config "$OPS/keys/isolated-target.json" --database cinevault_restore_20261113 --input "$OPS/backups/cinevault-20261113T020000Z.cvmb.age" --identity-file "$OPS/keys/restore-2026.txt" --expected-sha256 HASH_SHA256_DU_RECU_FIABLE --timeout 300 --acknowledge-isolated-target
```

Avant tout contact cible, l'outil copie seulement le chiffré dans un dossier privé et le déchiffre intégralement vers un puits de validation. Ensuite il réserve atomiquement la base vide, relit le même instantané chiffré et envoie l'archive claire uniquement dans le tube de `mongorestore`. Les namespaces sont bornés à `source.* → nouvelle_base.*` ; `--drop`, `--bypassDocumentValidation`, restauration d'utilisateurs Mongo et oplog ne sont jamais demandés. Toutes les collections, documents BSON, options/validateurs et index doivent correspondre à l'inventaire avant la suppression du marqueur technique. Les UUID physiques internes des collections ne sont pas clonés ; les valeurs BSON des documents sont conservées.

Avant validation de l'inventaire complet restauré, l'outil ne demande pas la suppression de la collection de quarantaine `_cinevault_restore_claim` et ne supprime pas automatiquement une base partiellement restaurée. La finalisation est distincte : après validation, une seule demande de suppression du marqueur est envoyée. Après accusé normal, il confirme son absence et le même processus primaire, sans refaire inutilement l'inventaire complet. L'accusé ou sa confirmation peuvent toutefois être perdus alors que le serveur a déjà effectué la suppression. L'outil ne rejoue pas cette écriture, ne recrée pas le marqueur et ne recommence pas l'import. Dans cette branche incertaine, il effectue un rapprochement **en lecture seule**, borné par le budget restant et au plus cinq secondes : même processus primaire avant/après, marqueur absent, nouvel inventaire intégral exact. Ces conditions permettent un reçu de succès même après perte de l'accusé. Si elles ne peuvent être établies, le code `finalization_unknown` est retourné sans reçu de succès ; le marqueur peut alors être présent **ou absent**. Une interruption ne garantit pas non plus sa présence.

Dans tous ces cas sans reçu de succès, **garder la cible isolée, sans trafic applicatif ni bascule**. Conserver son nom et les preuves, faire vérifier en lecture seule son identité, le marqueur et les données par un opérateur autorisé ; ne pas relancer aveuglément la restauration ou supprimer la base. Si une nouvelle tentative est décidée, provisionner une autre base neuve. Après succès, tester les refus de validateurs et privilèges, la connexion applicative et les parcours métier sur cette cible ; comparer les identités Mongo autorisées dans les bases d'authentification. Le succès de copie ne remplace pas ces essais d'exploitation ni une autorisation de bascule.

## Rotation, fréquence et rétention

Politique de départ conservatrice : sauvegarde quotidienne, alerte après 24 heures sans nouveau reçu vérifié, conservation pendant 30 jours et au moins sept points ; essai de restauration isolée mensuel et à chaque changement de schéma, serveur, outils ou stratégie de clés. Adapter explicitement ces valeurs à la capacité, au RPO/RTO acceptés et aux obligations du déploiement. Planifier la commande de sauvegarde avec cron/systemd timer sur Ubuntu ou le Planificateur de tâches Windows, sous une identité dédiée ; utiliser des chemins absolus, un nom UTC neuf par exécution, les fichiers privés et le contrôle du code de sortie. Aucun service de planification n'est installé par cet outil.

```text
python -m tools.mongodb_backup retention-plan --directory "$OPS/backups" --keep-days 30 --keep-minimum 7 --maximum-age-hours 24
```

La sortie indique les candidats anciens et l'alerte de fraîcheur selon les dates de fichiers. **Elle ne supprime rien**, ne démontre pas leur restaurabilité et n'est pas une alerte de supervision installée. N'appliquer la suppression qu'après vérification du stockage hors VM, d'un point récent réellement restauré et de la disponibilité des clés ; programmer la rétention du stockage externe avec les mêmes garde-fous. Une date modifiée ou une copie ratée ne doit jamais autoriser la destruction du dernier point récupérable.

Pour la rotation, créer une nouvelle identité hors VM et exporter ses destinataires ; pendant la transition le fichier de destinataires peut contenir les deux clés publiques, une par ligne. La commande suivante authentifie d'abord l'ancienne archive puis crée une copie chiffrée neuve pour les nouveaux destinataires, sans réécriture du fichier d'origine ni archive claire sur disque :

```text
python -m tools.mongodb_backup --age "$AGE" rotate --work-dir "$OPS/work" --input "$OPS/backups/cinevault-20261113T020000Z.cvmb.age" --identity-file "$OPS/keys/restore-2026.txt" --recipients-file "$OPS/keys/new-recipients.txt" --output "$OPS/backups/cinevault-20261113T020000Z-rotated.cvmb.age" --timeout 300
```

Vérifier la nouvelle copie avec la nouvelle clé sur le poste indépendant, transférer son nouveau reçu et essayer une restauration. Garder l'ancienne clé jusqu'à expiration ou rotation vérifiée de tous ses points. Une rotation ne révoque pas les copies chiffrées déjà détenues par un tiers avec l'ancienne clé ; traiter séparément une compromission. Aucune clé n'est liée à un profil Windows : la récupération dépend de sa conservation effective, pas de la présence de l'ancien PC.

## Diagnostic et qualification

`--timeout` (1 à 3600 secondes) est un budget coopératif calculé après la préparation initiale (age et identité pour les lectures ; outils et configurations source pour backup). Pour verify/rotate/restore il est consulté pendant la copie chiffrée privée, dont le SHA-256 est calculé pendant la copie, les deux passes age et l'import. Chaque chunk de copie consulte l'échéance ; un dépassement empêche l'authentification puis tout contact avec la cible. Le même descripteur privé est conservé pour les deux passes. Le fichier source ouvert doit être régulier et conserver l'identité contrôlée avant ouverture. Pour backup, le budget de streaming est aussi limité par le gel plus court.

Ce n'est **pas un délai mural dur** : un appel OS de métadonnées, ouverture, lecture, écriture ou flush déjà bloqué n'est pas préempté par Python ; le dépassement est détecté à la consultation suivante. Les enfants ont un watchdog, les opérations Mongo des délais de connexion/socket/sélection propres, et le rapprochement final utilise en plus un bloc de [temporisation PyMongo](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/connect/connection-options/csot/) sur son budget restant de cinq secondes au plus. Les contrôles locaux entre appels restent coopératifs. Dimensionner le stockage et la fenêtre de maintenance, surveiller le processus depuis l'exploitation et requalifier les durées sur le vrai volume ; aucune garantie de terminaison universelle sur un stockage bloqué n'est annoncée.

Les erreurs contiennent un code fixe, jamais la sortie brute d'un outil, une URI, une valeur secrète ou un document Mongo. `private_acl_required` / `private_mode_required` signalent les permissions ; `uri_options_refused` le format de connexion ; `source_and_freezer_primary_mismatch` les endpoints ; `freeze_not_alive_after_dump` un gel perdu ; `source_changed_during_dump` un writer non maîtrisé ; `external_tool_failed` un programme arrêté en échec ; `target_database_not_empty` une cible existante ; `restored_inventory_mismatch_target_quarantined` une copie divergente. Vérifier les prérequis et les journaux du serveur isolé avec une identité autorisée. Ne pas activer de traces contenant URI/données, ni lever une protection pour faire passer le test.

Exécuter depuis le clone, avec `AGE_TEST_BINARY` défini sur l'exécutable age vérifié (`export AGE_TEST_BINARY="$AGE"` sous Ubuntu ; `$env:AGE_TEST_BINARY=$AGE` sous PowerShell) :

```text
python -W error -m unittest discover -s tests -p test_mongodb_backup.py -v
python -B scripts/check_docs.py
```

Sans ce paramètre, les tests age sont explicitement ignorés ; ce n'est pas un test cryptographique réussi. Les tests avec le véritable age couvrent mauvaise clé, altération/troncature tardive, rotation, clés natives hybrides, seconde lecture exacte et absence de contact cible avant authentification. Les doubles Mongo testent les contrats de gel, scope, refus et quarantaine ; ils ne prouvent pas le comportement du moteur. La qualification native à conserver pour la version déployée doit vérifier les conflits des writers canoniques, l'intégralité BSON/schémas/indexes, les refus de validateurs/privilèges, les identités source absentes de la cible, le redémarrage, les parcours métier, le nettoyage et les durées mesurées. Ne pas réutiliser les durées ou garanties de la petite fixture C2c comme SLA du schéma final.
