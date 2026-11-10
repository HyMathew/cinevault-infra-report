# CineVault Enterprise 2.0 — spécification produit

Date : 10 novembre 2026. Statut : conception pour implémentation et validation progressives, pas annonce de livraison 2.0. Les parcours v1 existent ; leur nouvelle présentation reste à vérifier en navigateur. [Design](DESIGN.md), [système de présentation](docs/design/DESIGN_SYSTEM.md), [registre du concept](docs/design/concepts/README.md).

## Intention

CineVault aide les membres à choisir un film et à suivre leur vidéothèque personnelle ; il aide l'équipe à tenir un inventaire et à faire circuler des exemplaires. Ce sont deux rythmes de travail : découverte lisible pour les membres, opérations compactes pour les gestionnaires. La séparation concerne présentation et navigation, jamais une nouvelle source d'autorisations.

La 2.0 doit réduire le temps passé à chercher une action ou à distinguer stock, disponibilité et activité personnelle. Elle conserve Flask/Jinja, HTTP/JSON, Compose/Swarm, les routes existantes et les exercices académiques. Le mode académique conserve son fichier JSON ; MongoDB devient la persistance principale Enterprise, selon l’[ADR 0001](docs/adr/0001-json-mongodb.md). Cette évolution n’est pas encore implémentée ou déployée. Aucun streaming, bande-annonce, notation sociale, recommandation générée ou service commercial nouveau n'est inclus.

## Base factuelle et portée

La revue v1 du 10 novembre porte sur le web `f3d10cb0d5c9233c6427bd6503f3d2b841e99548`. Le dossier de travail `work/v2-audit/ux-review.md` et `work/v2-audit/screens-v1/` conserve ses observations et captures authentiques ; il n'est pas une ressource publiée dans ce dépôt. L'audit relève un premier résultat vers y=700, un bloc d'emprunt vers y=825, une navigation mobile sur plusieurs rangées et une arrivée après connexion sur les réglages du profil. Ces positions sont des lectures approximatives de captures, pas des mesures DOM.

Les modules web lus pour cette spécification sont `accounts.py`, `routes.py`, `personal.py`, `lending.py`, `insights.py`, `api_client.py` et les gabarits catalogue, découverte et navigation. Cette lecture établit les mécanismes actuels ; elle ne vaut pas exécution des mutations.

Le concept membre représente le film synthétique **Échos du laboratoire — édition Swarm**, **Créateur fictif**, **2026**, **1 exemplaire**, **DVD**, déjà présent dans l'environnement audité. Il n'a pas d'affiche autorisée. Le catalogue à un résultat et les recommandations réellement vides doivent être beaux et compréhensibles sans enrichissement artificiel.

## Publics, contextes et navigation

| Contexte | Navigation et destination | Règles |
|---|---|---|
| Visiteur | Accueil, Catalogue, Connexion ; inscription depuis Connexion | Consultation publique existante ; se connecter pour les fonctions personnelles. |
| Membre | Catalogue, Ma collection, Mon espace ; Mon profil dans les accès de compte | Découvrir, Emprunts et Réservations restent des liens explicites dans Mon espace et la navigation secondaire membre. |
| Gestionnaire | Accès explicite Gestion ; Inventaire, Emprunts, Réservations, Statistiques, Import / export | Les fonctions personnelles restent accessibles dans le contexte membre. Les contrôles suivent `can_manage` et les refus API existants. |
| Administrateur | Contexte gestion + Administration | Rôle/status et conséquences des modifications restent clairement attribués au bon compte. |
| Mode académique/legacy | Routes et Page simple conservées | Enterprise désactivé continue de fonctionner ; aucun prérequis pédagogique supprimé ou masqué. |

Un contexte est déduit de la page et, si nécessaire pour une vue partagée, d'un choix explicite de présentation validé ; il ne transforme ni rôle ni permission. Conserver les URL actuelles. Toute variante de catalogue par contexte doit être autorisée côté serveur et testée avec ses filtres et sa pagination. Un gestionnaire ne doit pas perdre son catalogue membre à cause de son rôle.

**Mon profil** désigne exclusivement `/profil` et ses paramètres. **Mon espace** désigne `/mon-espace`, la synthèse personnelle. Décision de conception : connexion directe réussie → Mon espace, y compris pour un gestionnaire ; celui-ci accède ensuite explicitement à Gestion. Ce changement exige un test de redirection 303 et des cookies/session existants. Le retour automatique à une tâche n'est pas livré par cette spécification : s'il est ajouté, destination locale contrôlée et tests contre les redirections externes sont obligatoires.

## Parcours et critères d'acceptation

| Parcours | Page complète attendue et comportement | Preuve à obtenir |
|---|---|---|
| Rechercher un film | `/films` : titre court, recherche, tri, filtres secondaires, résultats, pagination. GET partageable ; critères conservés, effacement explicite. | Même film/données qu'en v1 ; premier résultat avant y=520 à 1280×900, filtres fermés ; filtre actif reste identifiable. |
| Choisir puis agir | `/films/{id}` : identité, statut réel et prochaine action, puis synopsis, métadonnées et exemplaires. | Statut et action dans les 700 premiers pixels à 1280×900, titre long et sans affiche. |
| Constituer sa collection | `/ma-collection`, ajout, modification, retrait : favoris, possédés, vus, à voir, listes personnelles et supports pertinents. | Récupération du vide vers catalogue ; état confirmé après relecture ; isolation entre deux membres. |
| Découvrir | `/decouvrir` : suggestions calculées, critères lisibles, explication du classement et des exclusions. | Aucun candidat inventé ; vide exact lorsque la cause est connue, sinon formulation prudente et retour catalogue. |
| Suivre son activité | `/mon-espace` : demandes en attente, prêts/échéances, réservations, accès collection et découverte ; répartitions secondaires repliables. | Priorités personnelles visibles dans le premier viewport avec mêmes données ; compte vide et activité non vide vérifiés. |
| Demander un prêt | Fiche → demande → `/emprunts` : demande en attente clairement distincte du prêt validé. | CSRF, droits, conflit de stock et absence de double confirmation ; gestionnaire valide exemplaire et échéance. |
| Réserver | Fiche → réservation → `/reservations` : statut attente/attribuée/annulée/expirée selon API. | Ne pas inventer de rang ou date d'attribution ; conflit et annulation versionnée testés. |
| Gérer l'inventaire | Inventaire compact, création/modification œuvre, ajout/modification exemplaire, suppression explicite. | Champs œuvre et exemplaire distincts ; versions transmises ; erreurs et saisie conservées. |
| Enrichir les métadonnées | Recherche externe et sélection depuis création/édition/fiche, selon routes existantes ; provenance et révision conservées. | Champs proposés vérifiables avant enregistrement, corrections locales préservées ; panne fournisseur récupérable et aucune URL externe libre ajoutée. |
| Faire circuler | Emprunts/réservations gestion : critères, identité membre/film, état, date et actions attribuables. | Valider, retour et annuler selon droits/transitions réels ; risque de retour sur mauvais prêt vérifié. |
| Comprendre les statistiques | `/mon-espace?scope=all` pour la gestion ; vue personnelle `scope=mine`. | Portée/période/unités affichées ; tous les chiffres dérivés des données ; scope global refusé au membre. |
| Administrer | `/administration` : liste synthétique comptes/rôles/statuts puis édition explicite du compte choisi. | Trois comptes audités lisibles sans éditeurs tous ouverts ; risque de mauvais compte et conséquences de révocation testés. |
| Importer/exporter | `/transfert` : format, contraintes, fichier, validation et résultat ; export téléchargeable réel. | Erreur d'import explicite, atomicité inchangée ; résultat réseau incertain sans réessai automatique. |
| Gérer son compte | Connexion/inscription, `/profil`, changement de mot de passe, déconnexion POST. | Libellés concordants ; erreurs liées aux champs ; mots de passe jamais réaffichés ; conséquences de session préservées. |

## Données et véracité

- `copy_count` représente le **nombre total d'exemplaires**, pas le nombre disponible. Afficher « 1 exemplaire · DVD » est légitime ; « Disponible » exige un contrat de disponibilité fiable.
- Le détail peut utiliser sa disponibilité réelle existante. Ajouter cette information dans une liste exige un contrat agrégé/batch testé ; aucun appel de détail supplémentaire par ligne et aucune inférence depuis le stock total.
- Les affiches passent par le mécanisme batch existant. Source, licence/conditions d'affichage, attribution éventuelle et provenance doivent être documentées avant ajout. Aucun poster récupéré au hasard pour embellir les captures.
- Les favoris/listes/collections et prêts sont propres à l'utilisateur. Les recommandations n'exposent aucune collection d'autrui et conservent l'explication métier existante.
- Zéro, absence, inconnu et indisponibilité de service sont quatre états distincts. Aucun chiffre d'exemple n'est codé dans une page applicative.

## Jeu de validation reproductible

Préserver le jeu audité pour la comparaison avant/après. Dans un environnement de test isolé, définir un second jeu déterministe : membres A/B, gestionnaire, administrateur ; film sans affiche et titre long ; film avec affiche seulement si droits établis ; exemplaire disponible, prêt en attente, prêt actif avec retard calculé à partir d'une horloge figée, réservation et historique retourné. Les états incompatibles utilisent des scénarios séparés, jamais un même exemplaire simultanément libre et prêté.

Créer ces fixtures via les mécanismes officiels de test/seed et les transitions métier, pas dans les VM stables pour des captures. Horodater le relevé, enregistrer identifiants non secrets, état de données, horloge, rôle, route, filtre, viewport et version applicative. Les conflits 412, refus 403, données invalides 422 et service 503 peuvent être simulés dans des tests clairement étiquetés ; ils ne deviennent pas des incidents ou des résultats réels inventés.

## Ordre de réalisation et conditions de sortie

1. Installer le vocabulaire, le shell compact et les deux contextes sans modifier les autorisations.
2. Catalogue/fiche, puis collection/découverte/espace personnel et compte.
3. Inventaire, circulation, statistiques, administration et transfert avec composants de gestion.
4. Valider chaque tranche puis comparer réellement avant/après ; conserver les preuves et limitations.

Les gates sont cumulatifs : routes et tests existants, contrats API, clavier réel, axe-core, contrastes, reflow 320/390/768/1280, captures représentatives et fidélité au concept. Les cibles ne sont pas des résultats acquis. Une maquette ImageGen, un build réussi ou une capture isolée ne valide ni un parcours ni l'accessibilité. Les commandes exactes viennent des dépôts applicatifs et de leur CI ; ce document ne les remplace pas.

Pour l'import incertain, conserver la clé d'opération existante et rappeler qu'une répétition manuelle exige le même fichier et les mêmes options. Une nouvelle clé ne doit pas transformer un réessai en double import. Les limites et protections existantes (UTF-8, 1 Mio, lot validé avant ajout, politiques de doublons, CSV protégé pour tableur, aucun compte ou historique privé exporté) restent visibles et inchangées.

Risques ouverts : maquettes spécifiques gestion/mobile non produites ; disponibilité batch de catalogue non spécifiée ; droits de nouvelles affiches non établis ; résultats Playwright/axe et mesures avant/après à produire. Les fonctions v1 et la stabilité académique priment sur une livraison visuelle partielle.
