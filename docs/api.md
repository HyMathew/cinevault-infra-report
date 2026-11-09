# API REST réellement implémentée

La référence courante est [OpenAPI3.1 au commit6a86f2e](https://github.com/HyMathew/cinevault-api/blob/6a86f2eba9de4dd704c7d4a38d93ab75ff32adc5/docs/openapi-v1.json), avec42 composants et44 couples méthode/chemin Enterprise. Le [tableau exhaustif des opérations](rest-operations.md) donne méthodes, ressources, identifiants d'opération, authentification et codes. Le [dictionnaire](data-dictionary.md) distingue données stockées, projections HTTP, transferts et états techniques ; le [corpus exécutable](examples/README.md) fournit exemples, requêtes/réponses synthétiques et validations réellement exécutées.

## Ressources et traitements

Les familles `/api/v1/movies`, `/copies`, `/collections`, `/loans`, `/reservations`, `/users`, `/me`, `/catalogue`, `/metadata`, `/posters`, `/statistics`, `/recommendations` et `/audit-events` exposent les opérations du contrat. À réception : décodage JSON, validation de forme/paramètres, authentification si requise, rôle/propriété et état métier, transaction ou lecture, puis projection et code HTTP. Les [séquences](diagrams/README.md) détaillent les traitements et les nuances de verrouillage ; elles ne sont pas des traces réseau.

La lecture du catalogue, des copies et de la disponibilité est publique ; les données privées exigent un bearer et un contrôle côté API. Les mutations de catalogue et d'exemplaires sont réservées à la gestion, les entrées de collection à leur propriétaire, les transitions de prêts/réservations aux acteurs autorisés. Le rôle est relu côté API ; une décision dans le frontend seul ne fait pas autorité.

## Versions, conflits et erreurs

Les mutations protégées comparent `If-Match` à l'ETag dérivé de l'entité persistée :428 si absent,412 si périmé.409 décrit notamment doublon, état incompatible, copie indisponible ou priorité de réservation ;422 concerne validation.401/403/404 expriment session, permission et ressource, avec404 pour certaines ressources privées d'autrui.429 limite une opération ;503 garde l'erreur de service contrôlée. Les succès incluent200,201 et204 selon l'opération. Les corps d'erreur possèdent leur schéma, avec champs de formulaire lorsqu'applicable.

Une création enrichie contrôle les droits avant le réseau puis les recontrôle au commit ; les appels fournisseur n'ont pas lieu sous le verrou métier. Un import utilise un porteur JSON même pour le contenu CSV ; la clé d'idempotence et son reçu évitent une réapplication du même lot. Une erreur de transport après écriture peut rendre le résultat incertain : lire l'état avant de répéter une mutation. Le frontend n'effectue aucune relance automatique de mutation.

## Authentification et mode pédagogique

Inscription et connexion utilisent un contexte visiteur signé lorsque la politique le requiert. La clé de contexte est distincte des clés de session et d'admission. Les tokens et mots de passe réels ne sont jamais des exemples publics ; le corpus publie des valeurs neutralisées et historiques, avec limites explicites.

Le mode historique expose `/api/films` (GET,POST), `/api/films/{id}` (GET,PUT,DELETE), avec fichier `{"films":[…]}`. Lorsque Enterprise est activé, ses mutations sont bloquées ; ce mode n'est pas un chemin d'administration parallèle. `/health` vérifie la santé du service et du magasin approprié, sans remplacer un parcours métier.

## Vérifications et limites

La suite API courante compte173 tests réussis sur Windows et Ubuntu dans la [CI publique](https://github.com/HyMathew/cinevault-api/actions/runs/42536728355). Les requêtes/réponses du corpus utilisent les vrais handlers Flask mais restent in-process et hors réseau. Les essais Compose, Swarm et Chrome sont documentés séparément dans [la synthèse des validations](validation-current.md) et [le socle pédagogique](pedagogical-validation.md). Ces preuves ne sont pas fusionnées en une campagne fictive ni en une garantie de couverture de chaque branche possible.
