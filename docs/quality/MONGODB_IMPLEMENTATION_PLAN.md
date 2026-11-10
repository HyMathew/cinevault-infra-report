# Persistance JSON et MongoDB : plan d’exécution

Ce plan applique l’[ADR 0001](../adr/0001-json-mongodb.md). Les branches de travail
préservent v1, son PDF et les volumes stables. Un lot terminé ne rend pas le mode
Enterprise MongoDB sélectionnable : cette activation exige tous les consommateurs
convertis et testés, sans mélange des deux sources.

## Fondation documentaire

L’API possède maintenant un codec BSON explicite, dix schémas documentaires issus
du schéma académique et des spécifications d’index. La représentation est Int64
pour les secondes UTC et autres entiers ; UUID chaîne en `_id`, casefold Python
technique exclu des vues publiques. Les tests BSON passent et un essai MongoDB
8.0.34 réel a accepté les validateurs et index, puis refusé types et doublons.
La couche de persistance applicative n’est pas encore implémentée.

## Lots et critères de passage

| Lot | Fichiers et frontière | Preuves exigées |
| --- | --- | --- |
| A — unité de travail JSON | `app/persistence/contracts.py`, `json.py`, résultats métier purs ; V2Store reste l’unique lecteur/écrivain sous verrou | Commit, abort, révision, lecture sans mutation, refus métier distinct d’une exception ; aucun verrou imbriqué |
| B — repositories MongoDB | `mongo.py`, `mongo_repositories.py`, maintenance des schémas/index ; sessions explicites | Vrai replica set, accès ciblés, commit/abort, registre UUID, aucun champ technique dans ETag ; reprises transaction/commit distinctes et bornées |
| C — identité et autorité | Services accounts ; routes auth, admission, bootstrap et recovery | Budgets avant Argon2, mêmes contrats JSON/Mongo, révocation concurrente, deux rétrogradations d’admins donnant un seul succès |
| D — catalogue et espace privé | Services catalogue/personal ; routes correspondantes | Propriété imposée dans les requêtes, 428/412 inchangés, casefold Unicode, création film+copie atomique, création de référence contre suppression |
| E — prêts et réservations | Service circulation commun ; expiration et désactivation dans le même protocole | Deux processus/même copie, cinquième place par bénéficiaire, FIFO par séquence, liens fulfilled après retour, annulation/expiration concurrentes |
| F — consommateurs et bascule | Import/reçus, statistiques/recommandations, cache/admission partagés, factory et migrations | Aucun snapshot global Mongo ; tous chemins convertis, contrats deux moteurs, panne sans repli, simulation/idempotence/comparaison, rollback avant et après nouvelles écritures |

Les tests existants restent des assertions de contrat ; les préparations de données
peuvent changer selon le moteur, pas les garanties attendues. Les essais propres
au serveur doivent utiliser un vrai MongoDB isolé. Un serveur absent n’est pas un
succès sous simulation.

## Protocole commun

Les commandes utilisent une UoW avec des repositories nommés accounts, sessions,
attempts, catalogue, personal, circulation, receipts, events et identities.
Les services ne reçoivent ni Flask, ni PyMongo, ni le document global. Les requêtes
publique et privée ont leurs filtres et projections propres ; la pagination
privée applique d’abord l’identité dans la base.

MongoDB incrémente un coordinateur scalaire avant toute lecture autorisant une
commande. Un conflit recommence depuis un snapshot frais ; les invariants dernier
admin, quotas, références et file partagent ainsi un ordre initial correct.
Ce point de contention doit être mesuré avant toute optimisation. JSON conserve
la même sémantique sous son verrou. Les commandes de maintenance utilisent ce
protocole ou une fenêtre de gel vérifiée.

Les horodatages et identifiants de commande sont préparés une fois. Les appels
externes restent hors callback rejouable. Une erreur transitoire peut refaire la
transaction ; un commit inconnu ne fait répéter que le commit de cette même
transaction, jusqu’à une borne explicite. Un résultat HTTP est construit après
issue déterminée. Une création sans reçu d’idempotence ne peut pas être déclarée
absente après une issue indéterminée.

La vérification Argon2 et le nouveau hachage du changement de mot de passe restent
après le budget et la vérification de l’identité dans la commande. Les déplacer
avant ce budget permettrait de consommer du calcul sur des tentatives refusées.
Les réservations admission/cache sont durables avant leur calcul ou appel externe,
avec état partagé sur MongoDB et implémentation fichier conservée pour JSON.

## Après activation applicative

La bascule réelle, l’image analysée, le confinement réseau Swarm, les comptes de
maintenance/application, les mesures de contention et de ressources, les sauvegardes
hors VM et restaurations isolées restent des gates distincts. Le rollback après
nouvelles écritures nécessite un export inverse validé ou un point de perte
explicitement déclaré ; changer une variable ne suffit pas.
