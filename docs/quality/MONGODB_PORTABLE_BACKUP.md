# Qualification native du backup portable

Le 14 novembre 2026, les commandes publiques du [backup portable](../operations/MONGODB_BACKUP.md) ont sauvegardé une base MongoDB synthétique sur VM2, conservé son archive chiffrée sur un PC Windows, puis restauré cette archive sur un nouveau moteur isolé de VM3 **après suppression du conteneur et des deux volumes source**. La restauration ne reçoit aucun seed de fixture. Le [reçu public vérifiable](../../evidence/public/mongodb-portable-backup-core-20261114.json) rassemble les résultats et les empreintes des preuves privées assainies ; il ne contient ni clé, ni URI, ni valeur de document.

Cette qualification couvre le noyau de sauvegarde et de restauration du schéma API `3e15e61d0a309b12918338708e40d4f47a0ccdec`, puis ses services partagés sur une seconde cible restaurée. Elle ne clôt pas le portage Mongo de l'application, la migration bidirectionnelle ni le mandat global Enterprise 2.1. Le backend HTTP Mongo n'est pas activé par ces essais. Le reçu du noyau a été scellé avant les essais des services ; le [reçu complémentaire des services restaurés](../../evidence/public/mongodb-portable-backup-services-20261114.json) établit leur résultat ultérieur.

## Sources et environnement réellement exécutés

| Entrée | Version ou empreinte |
| --- | --- |
| Douze sources gelées du backup | Manifeste `7a827a1e1b6df3d9192c130fe654be4872ee0db51c69b25b07ad9c8be17adb8c` |
| Fixture native qualifiée | Manifeste `c1d76af16f085eda977b3f1ba00e9c14d31d0fadd0bce40aaf5a5594ba70d1b2` |
| Serveur | MongoDB 8.0.34, replica set mono-nœud authentifié |
| Dump et restore | Database Tools 100.20.0, binaires Ubuntu 24.04 vérifiés |
| Chiffrement | age 1.3.2, identité hybride native créée et conservée sur Windows |
| SDK du backup | PyMongo 4.20.0 ; distinct du SDK applicatif 4.19.0 |
| Exécution source/cible | UID applicatif 1000 sans groupes supplémentaires ; moteur UID 999, racine en lecture seule, réseau `none`, aucun port publié |

Les versions et les hashes des outils sont verrouillés dans le produit. La qualification privée automatise le provisionnement et le transport autorisés du laboratoire ; ces helpers privés ne sont pas requis pour utiliser les commandes publiques documentées. Le commentaire du verrou Python a ensuite été corrigé pour dire « binary wheel distributions » : le SDK du backup possède des extensions C et ne doit pas être décrit comme un paquet sans code natif. Aucun numéro de dépendance, hash de wheel ou module Python du produit n'a été changé par cette correction documentaire.

## Sauvegarde cohérente et récupération hors source

La source contient douze collections, **393 documents et 40 index**, dont 130 exemplaires pour dépasser un batch d'inventaire de 128. Elle comprend comptes et sessions synthétiques, reçus d'idempotence, historiques de prêts et réservations, audits ordonnés, coordinateur et registre d'identifiants. Les noms de films, profils, secrets synthétiques et hashes de mots de passe restent hors des reçus publics.

Le reader de sauvegarde n'a que les lectures nécessaires sur la base ; l'identité de gel n'a que lecture et mise à jour du coordinateur. Les refus de mutation, DDL et lecture d'une autre base ont été vérifiés. Le gel transactionnel reste non committé pendant le dump puis est annulé ; l'inventaire source avant/après reste exact.

L'archive de tube mesure 14 423 octets. Le fichier age final mesure 19 940 octets, SHA-256 `8b50eb7a4bc49aa92e40857f4ca4ec7654fd7986cb07ed444139659537421ba4`. Copié par SSH avec contrôle de clé d'hôte, il a été authentifié par la vraie commande `verify` sous Windows. La clé privée durable n'a jamais été envoyée à VM2.

Sur VM3, un nouveau replica set, deux volumes et un autre nom de base ont reçu **seulement ce chiffré conservé sur le PC**. La vraie commande `restore`, avec son SHA fiable attendu, a renvoyé `ISOLATED_RESTORE_VERIFIED`. Tous les documents BSON, options/validateurs et index correspondent à l'inventaire source ; le marqueur technique est absent. Une seconde invocation sur cette cible non vide a refusé l'opération sans changement.

Le redémarrage du même conteneur avec les mêmes volumes a donné un nouvel identifiant de processus Mongo et conservé intégralement cet inventaire. Les trois identités d'authentification Mongo de la cible ont été créées séparément ; aucun compte Mongo de sauvegarde source n'a été restauré. Les quatre comptes métier de la collection `users` font partie des données conservées.

## Privilèges, secrets temporaires et nettoyage

Avant **et** après redémarrage, les contrôles natifs ont obtenu :

- Restorer : cinq refus `13` pour mise à jour du coordinateur, suppression d'une collection métier, suppression de la base, création de compte et contournement des validateurs.
- Client anonyme : refus de lecture `13`.
- Identité applicative CRUD : document invalide refusé `121`, doublon refusé `11000`, lecture d'une autre base refusée `13`.

Le rôle de restauration peut supprimer uniquement `_cinevault_restore_claim`. L'administrateur de provisionnement n'est pas fourni à la commande publique.

La copie de K1 nécessaire à la récupération, le dossier de travail du CLI et sa configuration cible résident dans un dossier privé sur tmpfs. Cela inclut la copie d'identité créée par le produit dans son dossier de travail ; garder seulement le fichier d'origine en mémoire aurait été insuffisant. Leur suppression a été vérifiée par le système hôte, indépendamment du PID du moteur. Le conteneur cible et ses deux volumes ont ensuite été supprimés, et l'inventaire des volumes est revenu à son état initial. La clé durable et l'archive originales restent protégées sur le PC.

Tmpfs ne constitue pas une preuve d'effacement mémoire ni d'absence de swap, hibernation ou crash dumps. Les limites de confiance et de délai coopératif de la procédure d'exploitation restent applicables.

## Échecs réellement éprouvés

Sur la vraie archive conservée, mauvaise clé, bit final altéré, troncature tardive, octets ajoutés et SHA fiable incorrect ont tous été refusés avec **zéro connexion TCP à la cible**. Un contrôle positif avec l'archive intacte et les mêmes outils a déclenché onze connexions au listener local ; il a échoué comme prévu puisque ce listener n'est pas un serveur MongoDB. Ce contrôle évite d'attribuer l'absence de connexion à un chemin jamais atteint.

La rotation Windows crée une autre copie réellement chiffrée pour K2. Cette copie s'authentifie avec K2, refuse K1 et laisse l'original inchangé. La vérification croisée de la rotation Linux reste distincte.

Sur le moteur réellement restauré, le marqueur a été créé puis supprimé par un vrai appel Mongo ; une exception Python a été injectée **après** cette suppression pour représenter un accusé perdu. Un seul drop a eu lieu : rapprochement en lecture seule réussi avec inventaire exact. Dans un second cas, les confirmations ont été rendues indisponibles par injection ; le résultat attendu a été `finalization_unknown`, même avec un marqueur effectivement absent. Aucune écriture n'a été rejouée. Ce sont des injections logicielles, pas des pannes physiques du réseau.

Une deuxième session transactionnelle a tenté d'écrire le coordinateur pendant un vrai gel : conflit `112` et label `TransientTransactionError`, puis annulation. L'annulation du gel a laissé l'inventaire inchangé. Une nouvelle transaction a ensuite committé une seule avance de révision `173 → 174` ; toutes les autres collections sont restées inchangées. Ce dernier changement de sonde survient **après** les comparaisons exactes de restauration et redémarrage ; la cible est ensuite supprimée. Il ne représente pas un parcours métier HTTP complet.

## Services réellement exécutés après une seconde restauration

Une nouvelle cible isolée a reçu la même archive conservée sur le PC, avec les mêmes comparaisons BSON/options/indexes, refus et contrôles de redémarrage. Après ces vérifications, **31 appels réels aux services partagés** ont utilisé `MongoPersistence` et la seule identité applicative CRUD. Le code applicatif provient d'un snapshot immuable de 55 fichiers de `3e15e61`, distinct du candidat C5 ultérieur.

Les contrôles ont vérifié connexion et profil de trois comptes activés, refus du compte désactivé et de la session expirée, catalogue de 11 films et 130 exemplaires, séparation des collections/prêts/réservations des propriétaires et quatre refus RBAC. Deux reçus historiques ont été rejoués : exemplaire depuis supprimé et demande de prêt depuis clôturée. Leurs réponses restent exactes et aucun doublon métier n'apparaît.

Le domaine complet restauré est comparé à l'oracle synthétique avant le premier appel ; cet oracle est transmis en mémoire pour les assertions, sans insertion de seed. Les mutations d'authentification attendues sont comptées : 26 UoW/révisions committées, trois sessions ajoutées, une purgée, deux tentatives d'authentification ajoutées et aucun audit ajouté. **Les 393 documents décrivent l'état avant ces essais**, pas le cardinal final après leurs mutations.

Le runtime applicatif distinct utilise Python 3.12.3 et PyMongo 4.19.0 sans extensions C, avec les sept dépendances verrouillées et `pip check` réussi. Ce SDK a été construit deux fois depuis le sdist officiel avec `NO_EXT=1` : wheels octet-identiques, tag CP312/Linux conservé sans retag, dix contrôles BSON réussis. Il est distinct du SDK 4.20.0 du backup. Son dossier privé de dépendances peut rester pour inspection ; aucun processus serveur n'y réside. Après succès, la clé temporaire, le conteneur et les deux volumes de cette seconde cible ont été supprimés. Ces appels de services ne sont pas un parcours HTTP ni une qualification du nouveau candidat identité C5.

## Portée restante

Les durées de cette petite fixture ne sont ni un benchmark, ni un engagement RPO/RTO ou SLA. La conformité d'un déploiement final exige encore les tests sur son schéma final s'il évolue, les parcours HTTP Mongo complets, le stockage et la gestion des clés d'exploitation, ainsi que la fréquence, rétention et supervision effectivement retenues pour ce déploiement. Le [guide opérateur](../operations/MONGODB_BACKUP.md) documente la politique de départ ; son plan de rétention ne supprime rien et ne simule pas un ordonnanceur installé.
