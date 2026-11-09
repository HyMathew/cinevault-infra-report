# Dictionnaire des données CineVault

**Références de source :** les liens ciblent des commits immuables désormais accessibles dans les dépôts publics audités. Les documents pédagogiques, secrets et journaux privés restent exclus. Voir la [synthèse courante des validations](validation-current.md) pour les révisions déployées et les CI réellement exécutées. Les analyses statiques historiques ci-dessous restent datées.

État documentaire : **9 novembre 2026**, confrontation statique au candidat API présent dans le workspace, y compris `client_context.py` et `registration_admission.py`. Ce document décrit les formes implémentées ; il ne prouve ni le déploiement du candidat, ni l'exécution de ses tests. Aucune validation d'exemple, aucun service et aucun appel réseau n'ont été exécutés pour rédiger ce dictionnaire. Les exemples ci-dessous sont fictifs, proposés à la validation, sauf mention de leur simple présence dans les sources. Ils ne contiennent aucun compte réel, secret utilisable ou attribution de média réelle.

Le périmètre répond aux exigences S04 et S10 de la matrice du sujet (preuves locales non publiées). La synthèse des cours (preuves locales non publiées) éclaire la distinction entre représentation, stockage et messages ; elle ne définit pas les objets effectifs de CineVault. Les acteurs et droits sont détaillés dans [les cas d'utilisation](actors-use-cases.md), les échanges dans [le modèle d'exécution](execution-model.md).

## 1. Autorité, conventions et niveaux de représentation

| Niveau | Finalité et source de vérité | Ce qu'il ne faut pas confondre |
|---|---|---|
| Document legacy | Catalogue pédagogique `{"films":[...]}` ; `Repository._read`, `validation.validate` | Ce n'est pas le document Enterprise et il ne contient pas de comptes |
| Document Enterprise v2 | Un fichier JSON transactionnel ; `storage_v2.validate_document`, puis validateurs auth/métier/reçus | `schema_version:2` ne signifie pas version 2 de l'API HTTP |
| Projection HTTP Enterprise v1 | Objets publics/privés autorisés, jointures et valeurs calculées ; routes et OpenAPI | `_etag`, disponibilité, retards et positions ne sont pas des colonnes métier persistées |
| Transfert catalogue v1 | Export/import JSON ou CSV limité aux films et exemplaires | Ce n'est pas une sauvegarde du document complet |
| États techniques dérivés v1 | Cache de métadonnées et admission d'inscription dans des fichiers séparés | Leurs `version:1`, compteurs et verrous sont indépendants de `revision` métier |
| Contexte de client signé | En-têtes éphémères présentation → API, pour la source des opérations d'authentification | Ce n'est ni une session utilisateur ni une entité du catalogue |

Sources exécutables : [storage_v2.py](https://github.com/HyMathew/cinevault-api/blob/4b15406c2a1125518fb9a52dc53e9f50545db28e/app/storage_v2.py), [auth_storage.py](https://github.com/HyMathew/cinevault-api/blob/4b15406c2a1125518fb9a52dc53e9f50545db28e/app/auth_storage.py), [business_storage.py](https://github.com/HyMathew/cinevault-api/blob/4b15406c2a1125518fb9a52dc53e9f50545db28e/app/business_storage.py), [receipt_storage.py](https://github.com/HyMathew/cinevault-api/blob/4b15406c2a1125518fb9a52dc53e9f50545db28e/app/receipt_storage.py), [validation.py](https://github.com/HyMathew/cinevault-api/blob/4b15406c2a1125518fb9a52dc53e9f50545db28e/app/validation.py). Schémas déclaratifs : [catalogue-v2.schema.json](https://github.com/HyMathew/cinevault-api/blob/4b15406c2a1125518fb9a52dc53e9f50545db28e/schemas/catalogue-v2.schema.json), [catalogue-transfer-v1.schema.json](https://github.com/HyMathew/cinevault-api/blob/4b15406c2a1125518fb9a52dc53e9f50545db28e/schemas/catalogue-transfer-v1.schema.json), [registration-admission.schema.json](https://github.com/HyMathew/cinevault-api/blob/4b15406c2a1125518fb9a52dc53e9f50545db28e/schemas/registration-admission.schema.json), et [openapi-v1.json](https://github.com/HyMathew/cinevault-api/blob/4b15406c2a1125518fb9a52dc53e9f50545db28e/docs/openapi-v1.json), OpenAPI 3.1, `components.schemas` et schémas de corps inline dans `paths`.

La notation `UUID` désigne une chaîne canonique minuscule acceptée par `str(uuid.UUID(value)) == value`, pas un entier. Les identifiants créés par l'application sont des UUID aléatoires. `T` désigne un entier JSON positif ou nul, en **secondes UTC depuis l'époque Unix** ; il ne s'agit ni de millisecondes, ni d'une chaîne ISO 8601. `null` est une valeur explicite et ne signifie pas champ absent. Les booléens sont contrôlés séparément des entiers par les validateurs Python (`type(value) is int/bool`). Les chaînes doivent être encodables en UTF-8 lorsque le validateur l'exige. Les longueurs métier sont des nombres de caractères ; certaines limites réseau/fichier sont des nombres d'octets.

Les objets stricts refusent les champs supplémentaires. Les décodeurs métier et HTTP refusent les clés JSON dupliquées ; les entrées JSON HTTP/Enterprise refusent également les constantes non JSON comme NaN. Les schémas contrôlent une forme ; ils ne remplacent pas les contrôles de référence, de droits, de chronologie et de concurrence décrits ci-dessous. Le schéma v2 est en JSON Schema 2020-12. Ses sous-types sont accessibles par `#/$defs/<nom>` ; leurs copies OpenAPI se nomment notamment `Stored_movie`, `Stored_copy`, `Stored_collection`, `Stored_loan`, `Stored_reservation`, `Stored_audit_event`.

**Person et Genre :** il n'existe pas d'entité persistée `Person`, de table de réalisateurs/acteurs ou d'entité `Genre`. `director` est une chaîne, `actors` une liste de chaînes, `genres` une liste de chaînes. Le fait que le support de cours propose une autre structure ne change pas l'implémentation. Il n'existe pas ici d'objet `Review`, de note utilisateur ou d'endpoint de critique.

## 2. Document Enterprise persistant

### 2.1 Racine et intégrité transversale

`storage_v2.COLLECTIONS` définit exactement dix tableaux. La racine possède exactement `schema_version`, `revision` et ces dix noms :

```json
{"schema_version":2,"revision":0,"users":[],"sessions":[],"auth_attempts":[],"idempotency_records":[],"movies":[],"copies":[],"collections":[],"loans":[],"reservations":[],"audit_events":[]}
```

`schema_version` est l'entier constant 2 ; `revision` est un entier ≥ 0 géré par `V2Store.transact`, augmenté de 1 après chaque transaction réussie, avant validation et remplacement atomique du fichier. Une transaction d'identité peut actualiser une session et augmenter cette révision sans changer un film. Le code mutant n'a pas le droit d'imposer lui-même une autre révision.

Les IDs des films, exemplaires, comptes, sessions, collections, prêts, réservations, événements et reçus sont uniques à travers leurs collections respectives dans le même document. Les champs de référence ne sont pas de nouveaux IDs d'entité. Les compteurs d'authentification ont une clé de digest, pas d'UUID. Limites de stockage contrôlées : 10 000 comptes, sessions et compteurs d'authentification chacun ; 10 000 entrées personnelles, prêts, réservations et reçus chacun ; 2 000 événements d'audit. Le validateur v2 n'impose pas ici de plafond global explicite aux tableaux `movies` et `copies` ; les plafonds de transfert ne sont pas des plafonds de toute la vidéothèque.

L'écriture s'effectue sous verrou de fichier, sur un temporaire synchronisé puis remplacé. Une sauvegarde complète conserve la même forme v2 et contient des données privées : ce n'est pas un export publiable. La validation d'un objet isolé ne prouve pas la cohérence de ses références dans un document entier.

### 2.2 Film (`movies[]`)

Finalité : métadonnées d'une œuvre, indépendantes du nombre d'exemplaires. Source : `validate_document`, `enterprise_catalogue.movie_data`, `duplicate`. Schéma : v2 `#/$defs/movie`, OpenAPI `Stored_movie` ; projection `Movie`.

| Attribut | Type et contraintes effectives |
|---|---|
| `id` | UUID unique |
| `title` | Chaîne 1–200, sans espace de bord après normalisation HTTP |
| `year` | Entier 1888–2100 |
| `director` | Chaîne 1–120, sans espace de bord |
| `actors` | Tableau de 0–30 chaînes 1–120 sans espace de bord ; aucun ID de personne ; unicité des noms non imposée |
| `synopsis` | Chaîne 0–4 000 |
| `genres` | Tableau obligatoire au stockage, 0–30 chaînes de 1–80 sans espace de bord ; unicité exacte au stockage et unicité après `casefold()` à l'entrée catalogue/transfert |
| `external_source` | Facultatif, objet de provenance défini en §2.10 ou `null` |

À l'entrée HTTP, `genres` omis devient `[]` et titre/réalisation/noms d'acteurs sont épurés avec `strip()`. Le stockage exige déjà cette forme canonique. Le doublon de film est contrôlé par la logique HTTP/import sur `(title.casefold(), year, director.casefold())` après normalisation ; le validateur du document n'impose pas cette clé naturelle. Cette différence importe lors d'une fabrication manuelle du fichier.

Exemple de film stocké, acteur fictif :

```json
{"id":"11111111-1111-4111-8111-111111111111","title":"Le Voyage de papier","year":2001,"director":"A. Martin","actors":["B. Durand"],"synopsis":"Une exploratrice découvre une ville de papier.","genres":["Aventure"]}
```

Un film peut avoir zéro à plusieurs exemplaires et zéro à plusieurs références de collection/prêt/réservation. Toute référence de ces types, même historique, empêche sa suppression HTTP. Aucun effacement en cascade n'est effectué.

### 2.3 Exemplaire (`copies[]`)

Finalité : unité du stock partagé, physique ou numérique. Source : `validate_document`, `enterprise_catalogue.copy_data` et routes de copie. Schéma : v2 `copy`, OpenAPI `Stored_copy`, projection `Copy`.

| Attribut | Type et contrainte |
|---|---|
| `id` | UUID unique |
| `movie_id` | UUID d'un film existant ; immuable par PUT de l'exemplaire |
| `support` | `numerique`, `dvd`, `blu-ray`, `vhs`, `autre` |
| `location` | Chaîne UTF-8 0–200, pas une URL nécessairement |
| `condition` | `unknown`, `good`, `damaged` |

```json
{"id":"22222222-2222-4222-8222-222222222222","movie_id":"11111111-1111-4111-8111-111111111111","support":"dvd","location":"Rayon A","condition":"good"}
```

Le support personnel d'une collection ne crée pas un exemplaire partagé. `condition:damaged` exclut l'exemplaire des attributions ; `unknown` reste prêtable selon le code. L'absence de prêt actif et la priorité des réservations sont revérifiées au moment de l'attribution. Une référence de prêt, y compris retourné, empêche la suppression de la copie. Un reçu historique n'empêche pas cette suppression.

### 2.4 Compte (`users[]`) et session (`sessions[]`)

Finalité du compte : identité locale, rôle et activation ; finalité de la session : authentification révocable. Source : `auth_storage.validate_auth`, `enterprise_auth` ; schéma v2 `user`, `session`, `digest`, `timestamp`. **Aucun de ces deux objets stockés n'est renvoyé intégralement par HTTP.**

| Objet | Attributs et contraintes |
|---|---|
| Compte | `id:UUID` ; `username:string` unique, regex `^[a-z0-9][a-z0-9._-]{2,31}$` ; `display_name:string` 1–120, épuré ; `password_hash:string` commençant par `$argon2id$`, longueur ≤512 ; `role:member\|manager\|admin` ; `enabled:boolean` ; `created_at:T` |
| Session | `id:UUID` unique ; `user_id:UUID` vers un compte existant ; `token_hash:string` hexadécimale minuscule de 64 caractères, unique parmi les sessions ; `created_at:T`, `last_seen:T`, `expires_at:T` avec `created_at ≤ last_seen ≤ expires_at` |

Le schéma de stockage ne prouve pas qu'un texte commençant par `$argon2id$` est un hachage cryptographique utilisable. Les comptes créés par l'application utilisent réellement `PasswordHasher` Argon2id, paramètres `time_cost=3`, `memory_cost=65536`, `parallelism=2`. Un faux préfixe ne doit pas être présenté comme un exemple de compte authentifiable. Aucun exemple de hachage de compte n'est ajouté à ce document.

Un `username` entrant est normalisé par `strip().lower()` avant contrôle. L'inscription impose `member` et `enabled:true` ; elle ne permet pas au client de choisir un rôle. Le mot de passe entrant comporte 12–256 caractères et au plus 1 024 octets UTF-8 ; il n'est jamais une propriété persistée en clair. Les changements de rôle/activation et de mot de passe révoquent les sessions concernées. La route administrative protège le dernier administrateur actif ; ce n'est pas une contrainte structurelle globale du JSON.

Le jeton est créé avec `secrets.token_urlsafe(32)` puis seulement son SHA-256 est stocké. L'expiration de session est fixée à création +28 800 s ; la vérification rejette aussi une inactivité ≥1 800 s et une horloge antérieure au dernier accès. La durée maximale et l'inactivité sont des règles d'authentification au-delà de la seule chronologie du schéma. Une session peut référencer un compte désactivé dans le fichier, mais elle ne permet alors pas de s'authentifier.

Exemple structurel de session, digest synthétique non relié à un jeton distribué ; il exige le compte fictif `3333…` dans le document de validation :

```json
{"id":"44444444-4444-4444-8444-444444444444","user_id":"33333333-3333-4333-8333-333333333333","token_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","created_at":1700000000,"last_seen":1700000000,"expires_at":1700028800}
```

### 2.5 Compteurs de connexion (`auth_attempts[]`)

Finalité : limiter les échecs de connexion par identifiant normalisé et source. Source : `auth_storage.validate_auth`, `enterprise_auth.login`, `limit_key`. Schéma : v2 `attempt`.

`key` est une chaîne de 64 caractères hexadécimaux, unique dans le tableau ; `window_start:T` ; `count` entier 1–5. La clé est un HMAC-SHA-256 avec secret anti-abus distinct, sur un préfixe de domaine (`user:` ou `ip:`) et la valeur concernée. Ce n'est ni l'identifiant en clair ni un hash de mot de passe. Les compteurs de connexion sont dans le document v2 ; la fenêtre métier est de 900 s. Leur purge dépend des opérations de connexion, sans démon permanent.

```json
{"key":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","window_start":1700000000,"count":1}
```

### 2.6 Entrée personnelle (`collections[]`)

Finalité : classer un film pour un propriétaire, sans modifier le stock partagé. Source : `business_storage.valid_collection_attributes`, `validate_business`, `enterprise_collections`. Schéma v2 `collection`, OpenAPI `Stored_collection`, `CollectionEntry`.

| Attribut | Type et contrainte |
|---|---|
| `id` | UUID unique |
| `owner_id` | Compte existant ; identité imposée par l'API, jamais un choix du corps POST |
| `movie_id` | Film existant |
| `kind` | `owned`, `favorite`, `watched`, `watchlist`, `custom` |
| `list_name` | Chaîne obligatoire au stockage ; vide sauf pour `custom` ; pour custom 1–80, épurée et sans caractère de code <32 |
| `supports` | Tableau obligatoire, ≤5 supports distincts de l'énumération §2.3 ; autorisé seulement pour `owned`, sinon `[]` |
| `created_at` | T |

Unicité de `(owner_id,movie_id,kind,list_name.casefold())` dans le document. Le propriétaire reste seul autorisé, même face à un admin ; une entrée étrangère est masquée par 404. Le PUT remplace seulement `list_name` et `supports`, en tenant compte du type existant.

```json
{"id":"55555555-5555-4555-8555-555555555555","owner_id":"33333333-3333-4333-8333-333333333333","movie_id":"11111111-1111-4111-8111-111111111111","kind":"owned","list_name":"","supports":["dvd"],"created_at":1700000000}
```

### 2.7 Prêt (`loans[]`)

Finalité : conserver demande, attribution et historique de restitution. Source : `business_storage.validate_business`, `enterprise_lending`. Schéma v2 `loan`, OpenAPI `Stored_loan`, projection `Loan`.

`id:UUID`, `movie_id` vers film existant, `borrower_id` vers compte existant, `copy_id:UUID|null`, `status:pending|active|returned|cancelled`, `requested_at:T` ; `approved_at`, `due_at`, `returned_at`, `cancelled_at` sont `T|null`. Tous ces champs sont présents au stockage, même nulls.

| État | Champs et relations obligatoires |
|---|---|
| `pending` | Aucun exemplaire ; les quatre autres dates sont nulles |
| `cancelled` | Aucun exemplaire/approbation/échéance/retour ; `cancelled_at ≥ requested_at` |
| `active` | Exemplaire existant du même film ; `requested_at ≤ approved_at < due_at ≤ approved_at + 90×86400` ; retour/annulation nulls |
| `returned` | Même attribution/chronologie que active ; `returned_at ≥ approved_at`, annulation nulle |

Un seul prêt `pending` ou `active` par couple bénéficiaire/film ; un seul prêt actif par copie ; au plus 10 demandes pending et 5 prêts actifs par bénéficiaire. L'approbation exige en plus un bénéficiaire actif, une copie non abîmée libre et une priorité de réservation compatible. Le bénéficiaire d'une demande vient de la session. Une demande pending peut coexister avec sa réservation ; l'annulation d'une réservation ne supprime pas automatiquement le prêt demandé.

Transitions HTTP : `pending → active` par manager/admin ; `active → returned` par manager/admin ; `pending → cancelled` par propriétaire ou manager/admin. Pas de DELETE d'historique ni d'annulation d'un prêt actif. Le retard est une projection `status == active && due_at < now`, jamais un cinquième statut stocké.

```json
{"id":"66666666-6666-4666-8666-666666666666","movie_id":"11111111-1111-4111-8111-111111111111","borrower_id":"33333333-3333-4333-8333-333333333333","copy_id":null,"status":"pending","requested_at":1700000000,"approved_at":null,"due_at":null,"returned_at":null,"cancelled_at":null}
```

### 2.8 Réservation (`reservations[]`)

Finalité : file de priorité FIFO pour un film sans exemplaire disponible hors file. Source : `business_storage.validate_reservations`, `enterprise_reservations`, `reservation_service`. Schéma v2 `reservation`, OpenAPI `Stored_reservation`, projection `Reservation`.

`id:UUID`, `movie_id` vers film existant, `user_id` vers compte existant ; `status:waiting|fulfilled|cancelled|expired` ; `sequence` entier unique avec `1 ≤ sequence ≤ document.revision` ; `created_at:T`, `expires_at:T` avec `created_at < expires_at ≤ created_at +14×86400` ; `closed_at:T|null`, `loan_id:UUID|null`.

À la création, `sequence = revision + 1` sous verrou, puis la transaction augmente `revision`. C'est un ordre transactionnel global utilisé pour la FIFO, pas une date ni un rang permanent. `waiting` exige compte actif, aucune clôture, aucun prêt lié et un couple compte/film unique parmi les attentes ; maximum 10 attentes par compte. La route refuse une réservation si l'acteur possède déjà un prêt actif du film ou s'il existe un exemplaire disponible hors file.

`cancelled`/`expired` ont `closed_at ≥ created_at` et `loan_id:null` ; pour expired, `closed_at ≥ expires_at`. `fulfilled` exige un prêt actif ou retourné du même film et bénéficiaire, `closed_at == loan.approved_at < expires_at`, et un prêt ne peut satisfaire deux réservations. Ces trois états sont terminaux. Les attentes sont expirées à l'occasion de traitements API ; les projections de disponibilité les excluent dès l'échéance, même avant la clôture persistée. La désactivation d'un compte annule ses attentes non expirées.

Exemple isolé d'attente ; exige `revision ≥ 1`, le film et un compte actif dans le document complet :

```json
{"id":"77777777-7777-4777-8777-777777777777","movie_id":"11111111-1111-4111-8111-111111111111","user_id":"33333333-3333-4333-8333-333333333333","status":"waiting","sequence":1,"created_at":1700000000,"expires_at":1701209600,"closed_at":null,"loan_id":null}
```

### 2.9 Événement d'audit (`audit_events[]`)

Finalité : trace métier minimale à rétention bornée, distincte d'un journal d'accès HTTP. Source : `audit.record_event`, `business_storage.validate_business`. Schéma v2 `audit_event`, OpenAPI `Stored_audit_event`, enveloppe `AuditList`.

`id:UUID` unique ; `actor_id:UUID|null` ; `entity_id:UUID` ; `entity_type` parmi `movie`, `copy`, `collection`, `loan`, `reservation`, `import`, `export`, `recovery` ; `timestamp:T` ; `action` doit appartenir à la liste autorisée et commencer par `entity_type + "."`.

Actions autorisées : `movie|copy|collection` avec `created|updated|deleted` ; `loan` avec `requested|approved|returned|cancelled` ; `reservation` avec `created|fulfilled|cancelled|expired` ; `import.completed|failed` ; `export.completed` ; `recovery.completed|password_reset`. Le schéma exige acteur null pour `reservation.expired` ; le code accepte null seulement pour cette action, mais accepte aussi structurellement un acteur existant pour cette même action. L'émetteur normal d'expiration utilise bien null. Cette légère différence de validation est à conserver visible.

Hors événement système, l'acteur doit être un compte existant. `entity_id` est historique et peut correspondre à une ressource supprimée ou à un identifiant d'opération sans collection persistée : ce n'est pas une clé étrangère imposant l'existence courante de l'entité. Aucun titre, liste privée, IP, mot de passe ou token n'est enregistré. Rétention : les 2 000 événements les plus récents. Une action autorisée par schéma ne prouve pas son émission par chaque route : le candidat catalogue inspecté ne contient pas d'appel direct à `record_event` dans ses CRUD film/copie, contrairement aux collections, prêts, réservations et transferts. Ne pas présenter l'audit comme exhaustif.

```json
{"id":"88888888-8888-4888-8888-888888888888","actor_id":"33333333-3333-4333-8333-333333333333","action":"loan.requested","entity_type":"loan","entity_id":"66666666-6666-4666-8666-666666666666","timestamp":1700000000}
```

### 2.10 Provenance externe et reçu d'idempotence

`external_source` est une **valeur imbriquée**, pas une collection. Finalité : conserver l'entité Wikidata choisie et la révision relue. Source : `metadata_model.valid_source`, `enterprise_catalogue.prepare_movie`. Schéma v2 `external_source`, transfert `external_source`, OpenAPI `ExternalSource`. Forme : `null` ou exactement `qid` correspondant à `Q[1-9][0-9]{0,11}`, `revision` entier 1–10^15 et `retrieved_at` entier 0–2^53.

```json
{"qid":"Q151599","revision":123,"retrieved_at":1700000000}
```

Le QID ci-dessus est seulement une illustration de syntaxe ; la révision et la date sont fictives. La route CRUD reçoit `external_id`, pas cet objet : elle relit la proposition côté serveur. Omettre external_id en PUT conserve la provenance, null la retire. L'import conserve une annotation fournie par le gestionnaire sans consultation réseau. La présence d'une provenance ne prouve ni l'égalité des champs saisis avec Wikidata, ni les droits sur une affiche ; ceux-ci relèvent de l'objet média.

`idempotency_records[]` mémorise des résultats autorisés, pas des requêtes d'authentification. Source : `idempotency.run_once`, `receipt_storage.validate_receipts`. Schéma v2 `receipt`, `cached_copy`, `import_summary`.

| Attribut | Contrainte |
|---|---|
| `id`, `actor_id` | UUID unique du reçu ; compte existant pour l'acteur |
| `key_hash`, `request_hash` | Chaînes hexadécimales minuscules de 64 caractères |
| `operation` | `copy.create` ou `catalog.import` seulement |
| `created_at`, `expires_at` | T, `created_at < expires_at ≤ created_at+86400` |
| `response` | Pour copy.create : copie publique avec `_etag` ; pour catalog.import : résumé d'import §4 |

Unicité `(actor_id,key_hash)` commune aux opérations. Le hash de clé correspond au SHA-256 de l'en-tête reçu, le hash de requête à sa représentation JSON canonique. Pour un reçu de copie, le validateur recalcule `_etag` depuis la copie et `request_hash` depuis ses attributs sans ID/ETag. Un simple exemple rempli de digests arbitraires serait donc trompeur : aucun reçu complet n'est fourni comme « valide » ici. Le reçu d'import contient seulement `operation_id` et quatre compteurs ; il ne conserve pas le fichier importé. Les références de résultat restent historiques et peuvent être absentes du stock courant.

## 3. Projections et corps JSON HTTP

### 3.1 Identité, erreurs et contrôle de santé

| Objet / finalité | Forme et contraintes | Référence de validation |
|---|---|---|
| `Profile` public autorisé | Exactement `id`, `username`, `display_name`, `role`, `enabled` ; aucun hash ni date de création | `enterprise_auth.public_profile`, OpenAPI `Profile` |
| `Token` de connexion | `token:string`, `token_type:"Bearer"`, `expires_in:28800` ; token opaque émis une fois | `enterprise_auth.login`, OpenAPI `Token` |
| Erreur commune | `{"error":{"code":string,"message":string,"fields":object?}}` ; fields décrit éventuellement des saisies invalides | `enterprise_auth.error`, `create_app` error handlers, OpenAPI `Error` |
| Santé | `{"status":"ok"}` seulement après accès au stockage sélectionné | `create_app.health` ; pas de composant OpenAPI v1 nommé |

Exemples de projection de compte fictif et d'erreur :

```json
{"id":"33333333-3333-4333-8333-333333333333","username":"membre.demo","display_name":"Camille Démo","role":"member","enabled":true}
```

```json
{"error":{"code":"validation_error","message":"Données invalides.","fields":{"year":"Valeur invalide."}}}
```

Le compte d'exemple est un **membre**, pas un admin ni un opérateur système. Les projections de profils sont contrôlées par la route (propriétaire/admin ou gestion autorisée des prêts/réservations), elles ne rendent pas tout le tableau users public. Les réponses Enterprise portent `Cache-Control:no-store`. Un exemple de token réel n'est pas requis pour documenter sa forme ; un jeton de démonstration doit être généré en test et ne pas devenir un secret de livraison.

### 3.2 Entrées d'opération

Les schémas d'authentification et de transition de prêt sont inline dans `paths`, sans composant nommé autonome. Leur validation effective repose sur `payload` et les fonctions métier indiquées. Les contrôles de propriété/rôle sont exécutés côté API indépendamment de la conformité du JSON.

| Opération / objet | Corps JSON attendu | Validation et décisions |
|---|---|---|
| Inscription | `username`, `display_name`, `password` | `enterprise_auth.register`, règles §2.4 ; rôle/propriétaire interdits |
| Connexion | `username`, `password` | `login` ; identité invalide et mauvais secret : erreur uniforme |
| Profil propre | `{"display_name":"Camille Démo"}` | PATCH `/me`, `valid_display` |
| Changement de secret | `current_password`, `new_password` | PUT `/me/password`, valid_password sur nouveau ; révocation de toutes les sessions |
| Administration | `{"role":"manager"}` et/ou `{"enabled":false}` ; au moins un | PATCH `/users/{user_id}`, rôle admin, protection du dernier admin |
| `MovieCreate` | Champs film sans ID ; genres/external_id facultatifs ; initial_copy facultatif = CopyInput | POST films, `prepare_movie`, `movie_data`, création film+copie atomique |
| `MovieInput` | Champs film sans ID ni initial_copy ; genres/external_id facultatifs | PUT film, remplacement des métadonnées, version exigée |
| `CopyCreate` | `movie_id`, `support`, `location`, `condition` | `copy_data`, référence film existante |
| `CopyInput` | `support`, `location`, `condition` | PUT copie, pas de changement movie_id |
| `CollectionCreate` | `movie_id`, `kind` ; list_name/supports facultatifs suivant kind | `attributes`, compte courant comme owner_id |
| `CollectionUpdate` | `list_name`, `supports` obligatoires | PUT collection, conserve propriétaire/film/type |
| Demande prêt/réservation | `{"movie_id":"11111111-1111-4111-8111-111111111111"}` | POST loans/reservations ; auteur imposé par session |
| Approbation prêt | `{"copy_id":"22222222-2222-4222-8222-222222222222","due_at":1700604800}` | `approve_loan` ; échéance future à l'heure réelle du traitement, ≤90 jours |
| Retour/annulation | **Aucun corps**, pas un objet vide obligatoire | POST loan return/cancel et reservation cancel ; If-Match requis |
| `ImportRequest` | `format`, `content`, duplicate_policy facultatif | Voir §4 ; manager/admin et clé d'idempotence obligatoire |

Exemples d'entrées sans secret :

```json
{"title":"Le Voyage de papier","year":2001,"director":"A. Martin","actors":["B. Durand"],"synopsis":"Une ville de papier.","genres":["Aventure"],"initial_copy":{"support":"dvd","location":"Rayon A","condition":"good"}}
```

```json
{"movie_id":"11111111-1111-4111-8111-111111111111","kind":"watchlist"}
```

L'exemple d'approbation ci-dessus n'est utilisable qu'avec une horloge synthétique cohérente ; le reprendre aujourd'hui avec une échéance passée ne démontre pas une approbation valide. Les mots de passe fictifs et hachages nécessaires aux tests doivent être produits dans les jeux de test dédiés, pas confondus avec des comptes existants.

### 3.3 Ressources versionnées et enveloppes de lecture

`Movie`, `Copy`, `CollectionEntry`, `Loan`, `Reservation` = entité stockée correspondante **plus `_etag`**. Les attributs métier et leurs contraintes sont ceux de §2. Le code `resource(entity)` calcule la projection ; `respond` place la même version dans l'en-tête `ETag` lors des réponses individuelles. Un ETag complet n'est pas inventé dans les exemples de ce document : sa validité demande le calcul sur les octets canoniques exacts, voir §6.

| Composant OpenAPI | Attributs de l'enveloppe / type et relation |
|---|---|
| `MovieList` | `movies:Movie[]`, `total:int≥0`, `limit:int`, `offset:int`, `copy_summaries:{movie_id:{count:int≥0,supports:Support[] distincts}}` ; résumés du stock de la page, pas de disponibilité |
| `CopyList` | `copies:Copy[]`, éventuellement filtré par film |
| `CollectionList` | `entries:CollectionEntry[]`, `movies:{id:Movie}`, `total,limit,offset` ; jointure limitée aux films des entrées propres de la page |
| `AuditList` | `events:Stored_audit_event[]`, `total,limit,offset` ; admin seulement ; événements sans `_etag` |
| `LoanList` | `loans:Loan[]`, `movies:{id:Movie}`, `borrowers:{id:Profile}`, `overdue_ids:UUID[] distincts`, `total,limit,offset` ; retards dérivés sur la page |
| `LoanOptions` | `loan_id:UUID`, `copies:Copy[]` ; choix libres/prêtables et priorité à l'instant lu, revérifiés à l'approbation |
| `ReservationList` | `reservations:Reservation[]`, `movies:{id:Movie}`, `users:{id:Profile}`, `positions:{reservation_id:int≥1}`, `ready_ids:UUID[] distincts`, `open_loan_ids:{reservation_id:loan_id}`, `total,limit,offset` |
| Liste comptes | `users:Profile[]`, `total,limit,offset` ; schéma inline GET `/users`, admin seulement |
| `Availability` | `movie_id:UUID`, `total,loaned,free,reserved,available:int≥0` ; lecture publique sans identité |

Pagination usuelle à l'entrée : limit 1–100, défaut 24, offset 0–10 000 ; comptes/audit défaut 50. Les composants de réponse acceptent parfois un minimum plus faible que l'entrée ; la route est l'autorité pour les paramètres. `positions` ne contient que les réservations waiting visibles dans la page, mais leur position est calculée par rapport à toute la file du film. `ready_ids` identifie les têtes visibles avec une copie libre ; `open_loan_ids` relie chaque réservation de la page à une demande/prêt actif du même compte et film. Ces cartes ne sont pas des champs persistés de Reservation.

Les membres lisent leurs seuls prêts/réservations ; `scope=all` est réservé manager/admin, `mine` est disponible aux trois rôles. Les profils joints sont limités aux entités autorisées de la page. Les collections restent strictement propres à l'acteur, y compris pour admin. La disponibilité publique calcule `free` sur les copies non abîmées sans prêt actif, `reserved` sur les attentes non expirées, `available=max(0,free-reserved)`. `reserved` peut dépasser `total`, `loaned` ne signifie pas « tous les exemplaires non disponibles ».

Exemples d'enveloppes vides, sans hypothèse de hachage :

```json
{"movies":[],"total":0,"limit":24,"offset":0,"copy_summaries":{}}
```

```json
{"reservations":[],"total":0,"limit":24,"offset":0,"movies":{},"users":{},"positions":{},"ready_ids":[],"open_loan_ids":{}}
```

```json
{"movie_id":"11111111-1111-4111-8111-111111111111","total":1,"loaned":0,"free":1,"reserved":0,"available":1}
```

## 4. Formats d'échange catalogue et reprise

### 4.1 CatalogueTransfer, CSV et enveloppes HTTP

Source : [catalogue_transfer.py](https://github.com/HyMathew/cinevault-api/blob/4b15406c2a1125518fb9a52dc53e9f50545db28e/app/catalogue_transfer.py), [enterprise_transfer.py](https://github.com/HyMathew/cinevault-api/blob/4b15406c2a1125518fb9a52dc53e9f50545db28e/app/enterprise_transfer.py), [contrat import/export](https://github.com/HyMathew/cinevault-api/blob/4b15406c2a1125518fb9a52dc53e9f50545db28e/docs/import-export-contract.md). Schéma autonome `catalogue-transfer-v1.schema.json`, composant OpenAPI `CatalogueTransfer`.

La racine stricte contient `format_version:1` et `movies:TransferMovie[]` (≤1 000). Chaque film contient `title,year,director,actors,synopsis,copies`, avec `genres`, `id` et `external_source` facultatifs. Leurs contraintes textuelles sont celles du catalogue. Chaque copie imbriquée contient `support,location,condition`, plus `id` facultatif ; elle n'a pas `movie_id`, car le parent le détermine. Au plus 5 000 copies **dans tout le lot**, règle imposée par `normalize`, au-delà du plafond local par tableau du schéma. Les IDs fournis doivent être canoniques et uniques à travers films et copies du lot. Sans ID, l'import en génère. Les doublons de clé naturelle dans un même lot sont refusés.

```json
{"format_version":1,"movies":[{"id":"11111111-1111-4111-8111-111111111111","title":"Le Voyage de papier","year":2001,"director":"A. Martin","actors":["B. Durand"],"synopsis":"Une ville de papier.","genres":["Aventure"],"copies":[{"id":"22222222-2222-4222-8222-222222222222","support":"dvd","location":"Rayon A","condition":"good"}]}]}
```

Le CSV n'est pas un nouvel objet métier. Ordre exact des 11 colonnes historiques : `movie_id,copy_id,title,year,director,actors,genres,synopsis,support,location,condition`. Variante admise : colonne finale `external_source`. `actors` et `genres` sont des tableaux JSON encodés dans une cellule ; external_source est un objet JSON/null. Les guillemets suivent les règles CSV, pas une découpe naïve sur virgule. Une ligne par copie, ou une ligne aux attributs de copie vides pour un film sans exemplaire. Les métadonnées répétées doivent rester identiques dans le groupe. BOM UTF-8 accepté à l'entrée ; export avec BOM, cellules toutes citées et protection des débuts interprétables comme formule (`csv_safe`). Cette protection peut préfixer une apostrophe et n'est pas une promesse d'identité textuelle parfaite après aller-retour de données commençant par un opérateur.

`ImportRequest` : `{"format":"json|csv","content":objet-ou-texte,"duplicate_policy":"reject|skip|append_copies"}`. Le défaut est reject. Pour CSV, content doit réellement être une chaîne ; JSON admet objet ou texte JSON strict. Le schéma général content n'exprime pas toute cette dépendance de format. Taille UTF-8 du contenu : ≤1 Mio ; enveloppe HTTP import API : ≤8 Mio (pour l'expansion des échappements), distincte de la limite ordinaire API de 65 536 octets et de celle du formulaire web. `prepare_import` prépare une copie du document avant commit : refus de lot sans import partiel, avec audit possible du refus.

Politique reject : refuse tout film déjà présent ; skip : ignore son film et ses copies ; append_copies : exige métadonnées compatibles avec l'œuvre existante puis ajoute ses copies, ou ignore une copie de même ID déjà strictement identique. Les collisions d'identifiant restent refusées. Aucun compte, session, collection privée, prêt, réservation, audit ou reçu ne voyage dans ce format.

`ImportSummary` est exactement `operation_id:UUID` et quatre entiers non négatifs : `created_movies`, `skipped_movies` ≤1 000 ; `created_copies`, `skipped_copies` ≤5 000. `operation_id` est une opération, pas l'ID d'un film. Même forme dans un reçu d'import (`#/$defs/import_summary`).

```json
{"operation_id":"99999999-9999-4999-8999-999999999999","created_movies":1,"created_copies":1,"skipped_movies":0,"skipped_copies":0}
```

`CatalogueExport` = `format:json|csv`, `content:CatalogueTransfer|string`, `filename:cinevault-catalogue.json|cinevault-catalogue.csv`. L'API renvoie **toujours JSON**, même pour transporter une chaîne CSV ; le téléchargement de fichier est réalisé par la présentation. `{"format":"json","content":{"format_version":1,"movies":[]},"filename":"cinevault-catalogue.json"}` est un exemple vide proposé.

### 4.2 Sauvegarde et rapport de reprise

La sauvegarde de `V2Store.snapshot` est un document v2 complet validé, dont l'empreinte SHA-256 des octets est renvoyée ; la primitive ne produit pas une enveloppe JSON de transfert. `V2Store.restore` restaure exactement vers une cible absente. La reprise opérationnelle `recovery.recover` vérifie empreinte/schéma/horloge, révoque les sessions, enlève les compteurs de connexion, met les comptes anciens en quarantaine avec nouveaux hachages aléatoires jetés et ajoute un nouvel admin. Les prêts historiques restent cohérents ; les attentes sont clôturées. Voir [le contrat de reprise](https://github.com/HyMathew/cinevault-api/blob/4b15406c2a1125518fb9a52dc53e9f50545db28e/docs/recovery.md).

Le rapport JSON CLI de reprise contient exactement `operation_id:UUID`, `source_sha256:string`, `target_sha256:string` (64 hexadécimaux), `disabled_users:int≥0`, `revoked_sessions:int≥0`, `closed_reservations:int≥0`. Source : `recovery.recover`. Aucun schéma JSON autonome/OpenAPI ne décrit actuellement ce rapport ; le corpus de la section8.3 fournit désormais un rapport qualifié et des empreintes calculées sur les fichiers synthétiques neutralisés publiés. Il n'y a pas de route HTTP de restauration. Les empreintes garantissent une comparaison d'octets avec une référence fiable, pas l'actualité de la sauvegarde ou un RPO nul.

## 5. Données dérivées et enrichissement

### 5.1 Statistics et Recommendations

Sources : [insights.py](https://github.com/HyMathew/cinevault-api/blob/4b15406c2a1125518fb9a52dc53e9f50545db28e/app/insights.py), [enterprise_insights.py](https://github.com/HyMathew/cinevault-api/blob/4b15406c2a1125518fb9a52dc53e9f50545db28e/app/enterprise_insights.py) et [contrat](https://github.com/HyMathew/cinevault-api/blob/4b15406c2a1125518fb9a52dc53e9f50545db28e/docs/insights-contract.md). Schémas : OpenAPI `Statistics`, `Recommendations`, y compris leurs objets imbriqués inline. Aucun tableau persistant de statistiques, de préférences de genre ou de recommandations.

`Statistics` contient :

| Bloc | Attributs et signification |
|---|---|
| `as_of` | T de l'instantané de calcul |
| `catalogue` | `movies,copies,damaged,free,held_for_queue,available` : compteurs ≥0 ; `by_support` : compteur pour chacun des cinq supports ; `by_genre` : carte libellé→compteur, genres regroupés sans casse |
| `personal` | `collection_entries`, `collection_movies` (films distincts), `by_kind` (les cinq types), `by_owned_support` (les cinq supports personnels), `loans` (pending/active/returned/cancelled), `overdue`, `waiting_reservations`, `activity_retained`, `activity_last_7_days`, `recent_activity` |
| `recent_activity[]` | Au plus dix objets `{action,timestamp}` de l'acteur ; ordre décroissant date puis ID, pas un journal complet |
| `operations` facultatif | Pour scope all réservé manager/admin : `loans`, `overdue`, `waiting_reservations`, `activity_last_7_days` (carte action→compteur) ; pas d'identités ni de collections privées tierces |

Tous les compteurs sont des entiers ≥0. `held_for_queue` additionne `min(free,waiting)` par film ; available additionne le restant. Un film multigenre contribue à plusieurs compteurs : leur somme n'est pas le nombre de films. `by_owned_support` compte les entrées personnelles possédées sur un support, pas le stock partagé. La fenêtre d'activité vaut sept jours et porte seulement sur l'audit conservé ; connexions/consultations ne sont pas un historique d'activité métier. Aucun nombre de visiteurs ou mesure de pertinence n'en est déduit.

`Recommendations` = `recommendations:Recommendation[]` (≤24), `total:int≥0`, `limit:int 1–24`, `personalized:boolean`, `method:"content-rules-v1"`. Chaque élément contient `movie:Movie`, `score:int 0–306`, `reasons:Reason[]` (1–63), `available_copies:int≥0`. Chaque raison contient `code` parmi `preferred_genre,similar_genre,similar_director,similar_actors,watchlist,catalogue`, `label:string≤240`, `points:int 0–5`. Le score est la somme des points, vérification sémantique au-delà du schéma ; ce n'est pas une probabilité.

Signaux propres : favoris poids 3, vus et prêts retournés poids 1, maximum par film de référence ; genre commun somme plafonnée à 5 par genre, réalisateur +2, acteurs communs +1 chacun plafonné à 2 ; genre explicitement choisi +5 ; watchlist +2. Les films déjà favoris/vus/possédés et les prêts pending/active/returned sont exclus. Tri par score décroissant, titre normalisé puis ID ; pas de préférences des tiers. Une proposition sans signal reçoit une raison catalogue à 0 point. Disponibilité exposée sans bonus de score caché. Les paramètres genre sont temporaires (≤10 valeurs, ≤80 caractères), limit 1–24, défaut 12.

```json
{"recommendations":[],"total":0,"limit":12,"personalized":false,"method":"content-rules-v1"}
```

Le corpus de la section8.3 fournit désormais Statistics complet et une recommandation non vide avec ETag calculé ; une carte partielle ne serait pas une ressource Statistics valide.

### 5.2 Recherche, proposition de métadonnées et affiche

Sources : [metadata.py](https://github.com/HyMathew/cinevault-api/blob/4b15406c2a1125518fb9a52dc53e9f50545db28e/app/metadata.py), [wikimedia.py](https://github.com/HyMathew/cinevault-api/blob/4b15406c2a1125518fb9a52dc53e9f50545db28e/app/wikimedia.py), [enterprise_metadata.py](https://github.com/HyMathew/cinevault-api/blob/4b15406c2a1125518fb9a52dc53e9f50545db28e/app/enterprise_metadata.py), [contrat](https://github.com/HyMathew/cinevault-api/blob/4b15406c2a1125518fb9a52dc53e9f50545db28e/docs/metadata-contract.md). Le fournisseur externe est facultatif ; son absence ne rend pas le catalogue invalide.

| Objet OpenAPI | Constitution et validation |
|---|---|
| `MetadataSearch` | `items` ≤5 objets `{id:QID,title:string≤200,description:string≤4000,source_url:URI}` ; `cache:{status:fresh|stale,stored_at:T,hit:boolean}` |
| `MetadataDetail` | `film` objet proposé ci-dessous et même cache ; seul manager/admin accède recherche/détail |
| Proposition `film` | `id:QID`, `title` ≤200, `year:int1888–2100|null`, `director` ≤120, `actors:string[]` ≤30×120, `genres:string[]` ≤30×80, `description` ≤4000, `poster_filename:string≤240|null`, `poster:Poster|null`, `revision:int1–10^15`, `retrieved_at:T≤2^53`, `source_url` Wikidata HTTPS, `warnings:string[]` ≤20×240 selon OpenAPI |
| `Poster` | Exactement `image_url`, `source_url`, `artist`, `license`, `license_url` : chaînes ; `attribution_required:boolean` |
| `Posters` | `posters:{movie_id:Poster}` ; absence d'une clé = pas d'affiche autorisée disponible, pas un film absent |

Une proposition externe est distincte d'un Movie stocké : elle peut manquer d'année/réalisation, utilise `description` et avertissements, et ne doit pas être enregistrée sans validation du formulaire. `normalize_film` exige une entité déclarée film (`Q11424`), construit les libellés disponibles et peut tronquer des champs. Le client sélectionne cette proposition puis les champs du film passent la validation catalogue ; la provenance reflète l'entité choisie et non une identité parfaite de tous les champs. La révision de l'entité principale n'est pas celle de chaque libellé lié ou page Commons.

Pour Poster, `normalize_poster`/`validated_poster` imposent HTTPS, hôtes image exacts `upload.wikimedia.org` ou `thumb.wikimedia.org`, chemin `/wikipedia/commons/`, suffixe JPEG/PNG/WebP et MIME cohérent ; source HTTPS `commons.wikimedia.org/wiki/File:...`, aucune query/fragment sur la source. Les paramètres d'image admis sont nettoyés ; auteur obligatoire en texte nettoyé ≤240, restrictions refusées. Licences reconnues : CC0, CC BY 4.0, CC BY-SA 4.0, CC BY 3.0, CC BY-SA 3.0, Public domain, avec URL de licence attendue. Une forme JSON correcte ne prouve ni existence de l'image ni droits ; aucune URL fictive d'image n'est fournie comme média exploitable.

Les affiches publiques proviennent uniquement d'un cache frais dont QID **et révision** correspondent à la provenance du film. La lecture publique `/posters` n'effectue pas de recherche réseau, ne divulgue pas d'identité et reçoit 1–100 UUID de film. Le cache périmé peut dépanner recherche/détail, mais ne justifie pas une affiche publique périmée.

Exemples proposés sans données de fournisseur ni droit de média supposés :

```json
{"items":[],"cache":{"status":"fresh","stored_at":1700000000,"hit":false}}
```

```json
{"posters":{}}
```

### 5.3 Cache technique des métadonnées

Source de validation : `MetadataCache.read`, `check_value`, `reserve`, `fetch`, `peek_many`. **Pas de schéma JSON autonome actuellement.** Le schéma des réponses HTTP ci-dessus n'est pas un schéma du fichier de cache.

Racine stricte : `version:1`, `window_start:T`, `count:int0–20`, `blocked_until:T`, `entries:object≤100 clés`. Une clé est le SHA-256 hexadécimal de `search:<recherche normalisée>` ou `detail:<QID>`. Chaque valeur est exactement `{stored_at:T,expires_at:T,stale_until:T,value:object}`. Chronologie : stored_at ≤ maintenant, expires_at = stored_at +86 400, stale_until = expires_at +7×86 400. `value` n'a pas de clé cache et sa sérialisation fait au plus 32 768 octets ; sa validation générique n'est pas une validation exhaustive de MetadataDetail. Les liens d'affiche sont contrôlés de nouveau avant exposition.

Le fichier lu fait au plus 8 Mio ; l'horloge ne doit pas précéder window_start. Le quota partagé est 20 requêtes fournisseur par 60 s ; un créneau est persisté avant réseau, même si un worker échoue. `blocked_until` indique une retenue technique liée au fournisseur. Un verrou de cache séparé protège ce fichier ; aucun objet cache n'entre dans le document métier.

```json
{"version":1,"window_start":1700000000,"count":0,"blocked_until":0,"entries":{}}
```

### 5.4 Admission d'inscription et contexte du client

Source : [registration_admission.py](https://github.com/HyMathew/cinevault-api/blob/4b15406c2a1125518fb9a52dc53e9f50545db28e/app/registration_admission.py), [client_context.py](https://github.com/HyMathew/cinevault-api/blob/4b15406c2a1125518fb9a52dc53e9f50545db28e/app/client_context.py), [auth-admission.md](https://github.com/HyMathew/cinevault-api/blob/4b15406c2a1125518fb9a52dc53e9f50545db28e/docs/auth-admission.md). Schéma autonome : `registration-admission.schema.json` ; aucun composant OpenAPI de ce fichier privé.

L'état dérivé d'admission est écrit dans `<document-v2>.registration.json`, avec son verrou propre. Il ne contient ni mot de passe, ni utilisateur, ni adresse IP en clair. Racine stricte :

| Champ | Type, relation et finalité |
|---|---|
| `version` | Entier constant 1, version du format technique |
| `window_start` | T, ≤heure fournie au contrôle ; début de fenêtre de 60 s |
| `total` | Entier 0–60 ; budget global de travail d'inscription réservé |
| `sources` | Carte de ≤60 clés HMAC-SHA-256 hexadécimales vers un entier 1–20 ; chaque clé dérive de `register-ip:` + adresse observée |

`sum(sources.values()) == total` est une règle du code, absente du JSON Schema. Le fichier fait au plus 65 536 octets ; la fenêtre échue réinitialise l'état logique. La réservation est écrite avant hachage de mot de passe et reste consommée en cas d'échec du worker. Le verrou non bloquant est maintenu pendant ce calcul et un autre appel peut recevoir 429 avec délai borné ; ce verrou n'est pas celui des transactions catalogue/session. La capacité métier de 10 000 comptes est vérifiée avant le travail puis de nouveau au commit. Le compteur global 60 n'est ni un total d'utilisateurs créés ni un compteur de connexions.

```json
{"version":1,"window_start":1700000000,"total":1,"sources":{"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc":1}}
```

Ce fichier est dérivé ; le perdre/réinitialiser n'est pas une restauration métier et remettrait à zéro la protection de sa fenêtre. Sa forme n'est pas incluse dans l'archive snapshot du document v2. Sa gestion opérationnelle reste distincte.

Le contexte client est transporté dans trois **en-têtes**, donc sans objet JSON HTTP dédié :

| En-tête | Représentation et validation |
|---|---|
| `X-CineVault-Client-IP` | Texte IP canonique IPv4/IPv6, ≤45 caractères, sans zone `%` ; assertion du service de présentation |
| `X-CineVault-Client-Time` | Texte décimal canonique de 1–10 chiffres, pas une valeur JSON numérique ; écart absolu à l'horloge API ≤30 s |
| `X-CineVault-Client-Signature` | 64 caractères hexadécimaux minuscules ; HMAC-SHA-256 avec clé distincte d'au moins 32 octets |

Message signé exact, lignes séparées par LF : `cinevault-client-v1`, heure, adresse, méthode, chemin HTTP, SHA-256 des octets du corps. La signature lie l'adresse au corps et à la route de la requête. Le code ne fait pas confiance à un simple X-Forwarded-For. Les trois champs doivent être présents ensemble ; contexte fourni mais invalide = refus ; si la politique l'exige, absence = refus avant hachage. Sans politique obligatoire et sans contexte fourni, la source est `request.remote_addr` (ou unknown). Ce contexte n'est pas une preuve d'identité utilisateur, et la fenêtre de fraîcheur n'est pas une déduplication anti-rejeu permanente. Aucun exemple de signature non calculée n'est présenté comme valide. Les paramètres sont également décrits dans OpenAPI, en dehors de `components.schemas`.

## 6. Temps, versions, idempotence et cache : mécanismes distincts

| Mécanisme | Calcul / portée / durée | Vérification nécessaire |
|---|---|---|
| Temps Unix T | Horodatage métier ou technique en secondes UTC | Inégalités, durée limite, horloge de référence et nullabilité selon objet |
| `revision` v2 | Compteur global d'écritures ; origine des séquences de réservation | Géré uniquement par store ; aucune équivalence avec dernière modification du film |
| `sequence` réservation | Numéro unique attribué sous verrou | FIFO par ordre croissant ; position dérivée variable |
| `_etag` / `ETag` / `If-Match` | SHA-256 de JSON entité persistée `sort_keys=True,ensure_ascii=False,separators=(",",":")`, encodé UTF-8 ; digest entouré de guillemets, inclus comme texte JSON dans `_etag` | PUT/DELETE et transitions protégées comparent exactement la version ; 428 absente, 412 périmée ; le digest n'est ni un horodatage ni un secret |
| `Idempotency-Key` | En-tête ASCII `[A-Za-z0-9_-]{16,128}` ; hash mémorisé par acteur pour copy.create et catalog.import, conservation ≤24 h | Requête canonique et opération identiques ; conflit 409 sinon ; clé optionnelle pour copie, obligatoire pour import |
| Rejeu de création | Même résultat initial, 201 copie ou 200 import, en-tête `Idempotency-Replayed:true` | Droits courants revérifiés ; ne recrée pas une ressource retirée depuis ; après expiration, nouvelle création possible |
| Cache fournisseur | 24 h frais +7 jours de grâce pour certains appels, quotas et verrou propres | Cache HTTP no-store distinct ; cohérence de révision exigée pour affiche publique |
| HMAC contexte / compteurs | Secrets de service distincts, domaines et durées définis en §2.5/§5.4 | Pas de mot de passe ni bearer dans ces champs ; une signature correcte ne confère pas un rôle |

Il n'existe pas de retry automatique universel : répéter une création non couverte par idempotence peut créer un doublon. Un ETag protège une mutation de ressource contre une version périmée ; il ne déduplique pas une création. Un digest SHA-256 de sauvegarde vérifie des octets ; il ne remplace ni l'autorisation, ni la validation du document, ni un historique d'opérations.

## 7. Modèle legacy conservé

Source : [repository.py](https://github.com/HyMathew/cinevault-api/blob/4b15406c2a1125518fb9a52dc53e9f50545db28e/app/repository.py), `validation.validate`, routes de `create_app`. Racine `{"films":[LegacyFilm...]}` ; film = exactement `id:UUID,titre:string1–200,annee:int1888–2100,realisateur:string1–120,acteurs:string[]0–30×1–120,support:Support,synopsis:string0–4000`. Les mêmes épurations textuelles de base s'appliquent. Le champ support est ici **dans le film**, alors qu'Enterprise le sépare en exemplaires. Pas de genres, comptes, ETag ni prêts dans ce format.

```json
{"films":[{"id":"11111111-1111-4111-8111-111111111111","titre":"Le Voyage de papier","annee":2001,"realisateur":"A. Martin","acteurs":["B. Durand"],"support":"dvd","synopsis":"Une ville de papier."}]}
```

GET liste et ressource utilisent cette forme ; POST/PUT attendent les attributs sans id (synopsis facultatif à l'entrée, défaut chaîne vide). En mode Enterprise, les mutations legacy sont refusées ; leur lecture de transition reste disponible depuis le fichier legacy distinct. L'OpenAPI v1 ne sert pas de schéma des routes `/api/films`. Il n'existe pas actuellement de schéma JSON autonome legacy ; la validation est exécutable par Repository/validate.

## 8. Inventaire historique des exemples et couverture actualisée

### 8.1 Exemples présents dans le dépôt au moment de lecture

| Fichier API | Type illustré | Limite de preuve dans ce travail |
|---|---|---|
| `schemas/catalogue-v2.example.json` | Document complet avec un film/une copie, autres tableaux vides | Pas d'exemple non vide compte/session/prêt/réservation/audit/reçu ; `test_v2_schema.py` prévoit schéma + validate_document, mais n'a pas été exécuté pour ce dictionnaire |
| `schemas/collection.example.json` | Sous-objet collection owned | IDs propres à cet exemple, à ne pas fusionner tels quels avec ceux du document catalogue ; validation référentielle exige un document enveloppant cohérent |
| `schemas/external-source.example.json` | Annotation de provenance | Ne prouve aucune consultation de fournisseur ou droit de média |
| `schemas/catalogue-transfer-v1.example.json` et `.example.csv` | Transfert catalogue | Leur présence et les tests de transfert ne constituent pas ici un résultat frais d'exécution |
| `schemas/registration-admission.example.json` | État dérivé version 1, une source | Vérifier schéma et somme/horloge via le code ; aucun test exécuté par ce travail |

Les exemples inline de ce document donnent des représentations proposées, parfois dépendantes d'un document environnant ou d'une horloge contrôlée. Ils ne portent pas l'étiquette « validés par exécution ». Ils ne remplacent pas des fixtures versionnées et des résultats datés. Les UUID 1111… (film), 2222… (copie), 3333… (compte), 4444… (session), 5555… (collection), 6666… (prêt), 7777… (réservation), 8888… (audit), 9999… (opération) sont cohérents **dans les exemples de ce document**, sans relation avec un utilisateur réel.

### 8.2 Couverture des composants OpenAPI

Tous les composants lus sont classés ci-dessous ; une famille n'implique pas que chaque branche possède déjà sa fixture validée.

| Famille / section | Composants exacts couverts |
|---|---|
| Types scalaires §1–2 | `Stored_id`, `Stored_shortText`, `Stored_timestamp` |
| Identité/erreur §3.1 | `Profile`, `Token`, `Error` |
| Film/copie §2.2–2.3 et §3 | `Stored_movie`, `Stored_copy`, `Movie`, `Copy`, `MovieInput`, `MovieCreate`, `CopyInput`, `CopyCreate`, `MovieList`, `CopyList` |
| Collections/audit §2.6/2.9 et §3 | `Stored_collection`, `Stored_audit_event`, `CollectionEntry`, `CollectionCreate`, `CollectionUpdate`, `CollectionList`, `AuditList` |
| Prêts/disponibilité §2.7 et §3 | `Stored_loan`, `Loan`, `LoanList`, `LoanOptions`, `Availability` |
| Réservations §2.8 et §3 | `Stored_reservation`, `Reservation`, `ReservationList` |
| Transfert §4 | `CatalogueTransfer`, `ImportSummary`, `ImportRequest`, `CatalogueExport` |
| Calcul §5.1 | `Statistics`, `Recommendations`, blocs et éléments imbriqués |
| Métadonnées §2.10/5.2 | `ExternalSource`, `Poster`, `MetadataDetail`, `MetadataSearch`, `Posters`, champs cache/proposition imbriqués |

S'ajoutent les types v2 non exposés comme composants nommés OpenAPI (`user`, `session`, `attempt`, `receipt`, `cached_copy`, `import_summary`), les schémas HTTP inline d'authentification/admin/demande/approbation, le modèle legacy, la santé, le rapport de reprise, le cache technique et le contexte signé. Le `$defs/reserved` du schéma v2 décrit un tableau nécessairement vide ; c'est un auxiliaire de schéma, pas une onzième collection effective ni une entité métier.

### 8.3 Corpus exécutable de complément — 9 novembre 2026

Le [corpus synthétique](examples/README.md) et son [manifeste](examples/academic-json/manifest.json) complètent les exemples inline proposés plus haut. Le générateur offline utilise les vrais handlers Flask, un magasin temporaire neuf, une horloge/UUID contrôlés et un fournisseur explicitement fictif. Aucun réseau ni magasin du laboratoire. Le contrôle exécuté vérifie **42 composants OpenAPI, 18 définitions de stockage, 93 échanges HTTP et 51 emplacements de schéma HTTP uniques résolubles**, avec formats UUID/URI. Les exemples inline historiques de ce dictionnaire ne sont pas pour autant déclarés exécutés.

Le snapshot est non vide dans les dix tableaux et présente ensemble les quatre états de prêt et quatre états de réservation. Les ETags sont calculés ; les cartes et références, branches de schéma, imports/exports JSON et CSV, reçus et rejeux, statistiques, recommandations, cache, admission et contexte signé sont vérifiés. Les hachages Argon2 réellement générés restent dans le temporaire : les fichiers publiés neutralisent hachages et tokens, dont le rejet est testé. Une reprise est exécutée dans ce temporaire ; le rapport public est explicitement adapté aux fichiers neutralisés et ne prétend pas être un reçu de restauration du laboratoire.

Les sources et scripts sont empreintés selon UTF-8/LF normalisé ; les données gardent des empreintes d'octets exacts. Le contrôle distingue une variation de fin de ligne d'une altération réelle. Cinq schémas autonomes complémentaires sont désormais fournis dans technical-schemas.json (LegacyCatalogue, Health, RecoveryReport, MetadataCache, ClientContext), validés avec leurs exemples ; l'admission conserve le schéma API existant. HMAC, fraîcheur, IP canonique, digests, sommes et contraintes en octets restent aussi contrôlés par le code. Vingt-trois tests négatifs/positifs passent. Le tableau historique ci-dessous ne décrit plus une absence de ces cinq schémas. Les exemples de fournisseur, URLs, artistes et licences sont entièrement fictifs, sans autorisation de média réel déduite de leur seule forme.

### 8.4 Historique des manques initiaux et limites sémantiques

Le tableau suivant conserve les besoins identifiés avant le corpus. Les lignes d'exemples et de couverture sont traitées dans le corpus ci-dessus ; la ligne des divergences de modèle reste une réserve documentaire à lire avec le code, sans prétendre qu'un JSON Schema exprime toutes les règles métier.

| Manque | Livrable ou validation encore nécessaire |
|---|---|
| Exemples v2 non vides | Document synthétique complet avec compte au hachage Argon2id réellement généré, session, tentatives, collections, états des prêts/réservations, audit et deux variantes de reçu ; IDs uniques et références/chronologie cohérentes |
| Branches d'état | Fixtures pending/active/returned/cancelled et waiting/fulfilled/cancelled/expired ; vérifier liens prêt-réservation, séquence/révision, quotas et acteur système |
| Ressources HTTP versionnées | `Movie`, `Copy`, `CollectionEntry`, `Loan`, `Reservation` avec ETag **recalculé**, et branches MovieCreate/MovieInput, CopyCreate/CopyInput, CollectionCreate/CollectionUpdate ; les exemples persistés sans ETag n'en sont pas des exemples complets |
| Enveloppes HTTP | Fixtures complètes non vides `MovieList`, `CopyList`, `CollectionList`, `AuditList`, `LoanList`, `LoanOptions`, `ReservationList`, liste comptes ; valider cartes/jointures et portée d'accès, pas seulement les tableaux vides |
| Authentification | Exemples contrôlés register/login/password/admin + Profile/Token/Error issus de clients de test ; pas de secrets réels ; corps inline à contrôler contre chemins OpenAPI |
| Transfert | Exécuter validation JSON Schema et normalisation/import CSV, enveloppes `ImportRequest`, `CatalogueExport`, résultat `ImportSummary`, reçus et politiques de doublon ; vérifier les exemples existants avec le candidat exact |
| Statistiques/recommandations | Fixture Statistics intégrale pour mine et all, Recommendation non vide + Reason, vérifier somme des points/ordre/exclusions/confidentialité et compteurs d'inventaire |
| Métadonnées/affiches | Fixture MetadataDetail complète (avec et sans Poster), MetadataSearch non vide, Poster et carte Posters non vide issus de données synthétiques/fournisseur contrôlé ; validation des URLs/licences séparée de la simple forme ; aucune image réelle requise dans le dépôt |
| États techniques | Valider l'exemple admission contre schéma **et** lecture avec horloge contrôlée ; fixture de cache avec entrée et durée calculée ; contexte client avec signature calculée sur le corps exact |
| Schémas autonomes absents | Legacy, santé, rapport CLI de reprise, fichier cache, message de contexte client : validateurs exécutables identifiés, mais pas de schéma JSON autonome dédié ; ne pas présenter le schéma HTTP MetadataDetail comme schéma de cache |
| Divergences connues | Unicité sans casse des genres plus stricte à l'entrée que dans le fichier ; règles d'acteur d'expiration légèrement différentes entre schéma et code ; actions d'audit catalogue autorisées sans émission démontrée par CRUD ; propriétés de référence/chronologie et digests non exprimées par JSON Schema |

Les suites existantes pertinentes sont notamment `test_v2_schema.py`, `test_storage_v2.py`, `test_enterprise_auth.py`, `test_auth_admission.py`, `test_collections.py`, `test_loans.py`, `test_reservations.py`, `test_idempotency.py`, `test_transfer.py`, `test_metadata.py`, `test_metadata_routes.py`, `test_insights.py`, `test_recovery.py` et les contrôles documentaires de `scripts/check_docs.py`. Elles sont citées comme mécanismes de preuve à rattacher au candidat, **pas comme validations exécutées dans cette rédaction**. Un succès antérieur ou une lecture de code n'est pas un nouveau résultat de test. Les validations locales ne démontrent pas à elles seules le fonctionnement du déploiement distant.
