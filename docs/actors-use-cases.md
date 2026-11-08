# Acteurs et cas d'utilisation

Modèle historique confronté au code Enterprise au 7 novembre 2026. Il décrivait alors l'application locale et traitait le cluster distant comme une cible. Les campagnes distribuées ultérieures sont distinguées dans la [synthèse courante datée](validation-current.md) ; elles ne constituent pas un audit exhaustif de tous les cas d'utilisation. Les personas ci-dessous sont fictifs et servent à justifier des choix d'interface. Ils ne constituent pas des résultats d'entretiens utilisateurs.

| Acteur | Objectifs et contraintes | Responsabilités et droits |
|---|---|---|
| Visiteur | Découvrir le catalogue avant inscription, sur téléphone ou ordinateur | Recherche, filtres, fiches, disponibilité publique et inscription ; aucune identité d'emprunteur visible |
| Membre | Organiser ses films, préparer ses emprunts, retrouver leur état | Profil, collections privées, demandes et annulations propres, réservations, statistiques personnelles et recommandations |
| Gestionnaire (`manager`) | Tenir l'inventaire et éviter une double attribution | Droits membre, CRUD films/exemplaires, import/export, attribution/retour, suivi opérationnel agrégé, enrichissement externe facultatif |
| Administrateur applicatif (`admin`) | Gérer les accès sans effacer le dernier accès d'administration | Droits gestionnaire et gestion des rôles/activations ; aucun droit de consulter les collections privées d'autrui |
| Exploitant système | Déployer, diagnostiquer et restaurer les services | SSH, images, secrets de déploiement, volumes, sauvegardes et reprise ; distinct d'un rôle HTTP de l'application |
| Fournisseur Wikimedia | Répondre aux demandes d'enrichissement autorisées | Service externe optionnel, accès réseau borné et provenance conservée ; ne reçoit ni session membre ni catalogue privé |

## Personas de conception

**Léa, membre sur mobile.** Elle prépare une sélection dans les transports. Elle doit comprendre immédiatement ce qui est disponible, conserver une liste privée et retrouver sa demande après retour à la fiche. D'où les filtres conservés, les libellés d'état, l'accès « mes emprunts » et la mise en page à une colonne. Critère : demander un film et retrouver la demande ouverte sans exposer celles des autres membres.

**Samir, gestionnaire de la vidéothèque.** Il traite plusieurs demandes et attribue un exemplaire physique précis. Une carte ne suffit pas à connaître l'inventaire ; il lui faut support, état et échéance. D'où les exemplaires séparés du film, le choix d'attribution, la priorité FIFO et les conflits explicites. Critère : deux validations concurrentes d'un même exemplaire produisent un seul prêt actif.

**Camille, administratrice applicative.** Elle ajuste les droits d'une équipe réduite. D'où une page de comptes paginée, le contrôle API des rôles, la révocation des sessions après changement de droits et la protection du dernier admin. Critère : un membre ne peut pas s'accorder des droits et un admin ne lit pas la collection privée d'un tiers.

**Alex, exploitant.** Il reprend un service après incident sans écraser la seule copie des données. D'où une API unique sur volume local, les instantanés, la restauration vers une nouvelle cible, les clés séparées et le refus des données corrompues. Critère : restauration vérifiée, anciennes sessions invalidées, archive source préservée. Ce parcours CLI ne constitue pas une fonction du navigateur.

## Scénarios et contrats de réussite

Les opérations métier du navigateur passent par la présentation Flask/Jinja. Les images facultatives sont chargées directement depuis Wikimedia HTTPS, sans cookie CineVault et sans en-tête Referer. Toute mutation web exige un CSRF valide ; toute autorisation métier est revérifiée par l'API. Les droits ci-dessus s'appliquent à chaque scénario, indépendamment de la visibilité des boutons.

| Cas | Préconditions et acteur | Messages et traitement principal | Postcondition / exceptions |
|---|---|---|---|
| UC01 Rechercher et consulter | Visiteur ou compte connecté ; API disponible | GET web → GET API catalogue, fiche, copies et disponibilité ; rendu HTML | Aucun prêt privé dévoilé ; filtre invalide 422, film absent 404, panne 503 |
| UC02 Créer un compte et se connecter | Visiteur, champs valides ; nom libre | POST formulaire → inscription puis connexion distincte ; cookie HttpOnly | Nouveau compte member ; doublon 409, saisie 422, identité invalide 401, abus 429 |
| UC03 Gérer son profil et son secret | Identité active | PATCH profil ou PUT mot de passe avec secret actuel | Profil modifié ; changement de secret révoque les sessions, retour connexion ; refus sans modification métier demandée, mais actualisation technique de session possible |
| UC04 Tenir films et exemplaires | Manager/admin ; versions courantes pour édition | POST/PUT/DELETE JSON ; validation et transaction du document | Création 201, modification 200, suppression 204 ; doublon/référence 409, If-Match absent 428 ou périmé 412 |
| UC05 Organiser sa collection | Membre actif ; film existant | Créer/modifier/retirer un type owned/favorite/watched/watchlist/custom | Propriété imposée par identité ; entrée étrangère 404 même pour admin ; doublon 409 |
| UC06 Demander un prêt | Membre actif ; film existant ; limites respectées | POST demande propre | Demande pending ; pas d'attribution implicite ; doublon/limite/conflit 409 |
| UC07 Attribuer un prêt | Manager/admin ; demande pending ; bénéficiaire actif ; copie libre non abîmée ; priorité compatible | Lire options puis POST approve avec version et échéance ; contrôle atomique | Un prêt active, copie indisponible ; course ou transition invalide 409, version 412 |
| UC08 Annuler ou enregistrer le retour | Annulation d'attente par son auteur ou gestionnaire ; retour par gestionnaire | POST cancel/return avec If-Match | Historique conservé, état cancelled/returned ; retour rend la copie disponible sous réserve de priorité |
| UC09 Réserver | Membre actif ; film indisponible ; aucune attente propre incompatible ; limites respectées | POST réservation, numéro séquentiel FIFO ; annulation explicite | waiting puis fulfilled/cancelled/expired ; expiration évaluée lors d'opérations API, aucun démon de planification |
| UC10 Importer/exporter | Manager/admin ; format/stratégie autorisés | Fichier contrôlé web → import JSON API ; lot validé sur copie sous transaction avant écriture ; clé d'opération obligatoire | Lot atomique, reçu minimal, aucun compte exporté ; fichier supérieur à 1 Mio : 422 ; enveloppe web supérieure à 2 Mio/API 8 Mio : 413 à cette couche ; conflit 409 |
| UC11 Enrichir une fiche | Manager/admin ; option fournisseur et User-Agent configurés | Recherche, aperçu, relecture puis enregistrement ; HTTP fournisseur hors verrou métier | Provenance serveur et affiche facultative licenciée ; dégradation contrôlée, quotas/cache ; saisie manuelle préservée |
| UC12 Lire statistiques et recommandations | Membre actif ; portée all réservée manager/admin | GET calcul déterministe à partir du document | Données propres ou agrégats autorisés ; explication du score ; aucune recommandation par IA ni preuve de pertinence mesurée |
| UC13 Administrer les comptes | Admin actif ; conserver au moins un admin actif | Liste paginée et PATCH rôle/activation sous transaction | Révocation des sessions concernées ; refus 403, dernier admin 409 |
| UC14 Sauvegarder et reprendre | Exploitant autorisé ; arrêt/coordination des écritures selon procédure | Primitive Python `V2Store.snapshot(destination)`, vérification SHA/schéma, CLI `app.recovery restore` vers cible absente et quarantaine comptes | Nouvelle cible valide et archive intacte ; refus si intégrité invalide ; anciennes sessions invalidées ; la CLI n'a pas de sous-commande snapshot et `V2Store.restore` est une primitive de restauration exacte distincte |

## Relations et limites

Manager hérite des capacités membre ; admin hérite des capacités manager. L'exploitant n'hérite pas d'un accès web aux données privées : son accès système constitue un périmètre de confiance différent. L'enrichissement étend la saisie manuelle sans être une précondition du CRUD. L'authentification est une précondition des cas privés, pas un appel réseau magique inclus à chaque clic : l'identité et le rôle sont relus aux points de contrôle.

Les cas d'utilisation sont reliés aux routes dans [l'inventaire frontend](frontend-inventory.md), au protocole dans [le modèle d'exécution](execution-model.md) et aux exigences dans [TRACEABILITY](requirements/TRACEABILITY.md) et [EXTENSIONS](requirements/EXTENSIONS.md). Les preuves locales datées (preuves locales non publiées) et résultats HTTP Compose (preuves locales non publiées) portent sur les cas exécutés ; le modèle seul ne prouve pas le déploiement distant, la conformité WCAG ou la sécurité globale. La revue indépendante (preuves locales non publiées) demande encore une couverture fonction → cas → routes/tests/preuves, des séquences supplémentaires et un rendu du [diagramme UML](diagrams/use-cases.puml).

## Charge et ressources par acteur

Ces charges sont qualitatives ; aucune mesure de débit utilisateur n'est revendiquée. Le visiteur effectue des recherches interactives et charge des fiches : rendu web, lecture JSON et, facultativement, réseau Wikimedia pour les images. Le membre ajoute les écritures de session et ses opérations privées : verrou et validation du document API. Le gestionnaire mobilise également la normalisation des imports sous verrou, les transitions d'attribution et le réseau externe facultatif hors verrou principal. L'administrateur utilise les mêmes ressources avec des transactions de comptes et révocations. L'exploitant mobilise CPU/RAM, disque, réseau SSH et copies de sauvegarde hors parcours HTTP. Le fournisseur est un acteur externe soumis aux délais, quotas et cache décrits dans le modèle d'exécution.

**Nora, collectionneuse passionnée, persona fictif complémentaire.** Elle distingue films possédés, vus, favoris et envies sur plusieurs supports. Son besoin est de retrouver une collection privée organisée sans la confondre avec le stock prêté par la vidéothèque. Les types de collections, supports possédés et filtres existants répondent à ce scénario. Critère : filtrer ses propres entrées et modifier leur classement tout en conservant le refus 404 sur celles d'un tiers. Il s'agit d'une justification de conception a posteriori, sans entretien utilisateur ni influence historique démontrée.
