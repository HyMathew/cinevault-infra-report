# CineVault Enterprise 2.0 — priorités et critères de sortie

Plan issu de l'[audit initial](INITIAL_AUDIT.md), établi le 10 novembre 2026. **Statut : plan de réalisation ; aucun lot ci-dessous n'est déclaré livré par ce document.** Les IDs restent ceux de l'audit. La priorité de correction est distincte de la gravité d'une vulnérabilité ; une amélioration UX ou un manque de preuve n'est pas automatiquement une faille.

## Contraintes conservées

Préserver les tags, bundles de sauvegarde, PDF original, données et preuves v1. Travailler sur branches isolées, sans reset ni écrasement des changements existants. Conserver Flask/Jinja, deux dépôts applicatifs indépendants, REST, JSON, Compose, Git et Swarm ; une seule réplique API tant que le stockage impose un écrivain unique. Aucun déploiement stable avant validation de la paire de versions ; aucune exposition publique des VM pédagogiques.

Chaque lot doit produire : changement borné → test du comportement → gate pertinent → preuve datée avec commit/digest → décision sur les limites restantes. Les résultats locaux, CI, navigateur, staging et laboratoire sont séparés. Un rapport n'est pas une preuve d'exécution de son plan.

## Ordre de réalisation

| Lot / ordre | IDs et objectif | Travail attendu | Condition de sortie mesurable |
|---|---|---|---|
| 0 — Base et traçabilité | Préservation, six dimensions, skills | Conserver baseline API 173/web 159, références immuables et PDF ; enregistrer chaque nouvelle preuve ; sélectionner les méthodes compatibles dans [SKILLS_AUDIT.md](SKILLS_AUDIT.md). | Bundles et empreinte vérifiables, trois versions connues, état utilisateur préservé ; statut sélectionné/installé exact. L'audit initial seul ne clôt pas la mission. |
| 1 — Protection de livraison, P1 | DEL-01, DEL-02 | Actualiser les protections observées, instaurer checks requis adaptés au projet ; créer intégration Enterprise de la paire exacte en Compose isolé. | PR contrôlée démontrant les règles effectives ; login, propriétaire, CRUD/ETag, prêts/réservations et erreurs de contrat réels entre services ; nettoyage et données stables préservés. |
| 2 — Fidélité et robustesse, P2/P3 | A1, A5, A6 | Liste réversible du formulaire ; conversion numérique bornée ; validation complète des enveloppes d'erreur. | Régression reproduisant chaque défaut puis réussite du correctif, aucune mutation intempestive, saisie préservée ; tests web et intégration touchés réussis. Les défauts A5/A6 restent P3 dans l'audit mais sont regroupés avec la frontière formulaire. |
| 3 — Capacité et reprise, P2 | A2, A3, PRE-03 | Définir reprise à capacité maximale, budgets de création et archivage réversible ; conserver comptes/références/historiques nécessaires. | 9 999/10 000/10 001 traités explicitement ; second membre servi après rafale bornée ; archives restaurables ; sauvegardes inchangées en cas d'échec. Prêts, réservations et collections vérifiés séparément. |
| 4 — Authentification et écritures, P2 | A4, PRE-01, PRE-02, PRE-05 | Admission hors verrou avec revalidation atomique, politique de sessions, lecture sans commit inutile, arbitrage anti-verrouillage ciblé et corpus de secrets courants licencié. | Accès métier pendant calcul contrôlé ; désactivation/changement de secret concurrent sans session indue ; limites par compte/globales ; défense distribuée conservée ; chemins création/changement/bootstrap/reprise cohérents. Mesures de charge distinctes des tests déterministes. |
| 5 — Sécurité de référence, P2 | PRE-04 et revue de tous PRE | Matrice ASVS 5.0.0 applicable, scans formels distincts du préaudit, qualification des alertes ; événements d'identité/autorisation corrélés et expurgés. | Chaque exigence a statut applicable/preuve/écart/limite ; nouveaux scans et versions traçables ; régressions des vulnérabilités démontrées ; journaux sans secret ni contenu privé. Aucun niveau ASVS ni certification déduit d'une sélection de contrôles. |
| 6 — Produit complet, P2 | UX-01 à UX-07 | PRODUCT.md, DESIGN.md, design system maintenu, parcours et maquettes ; identité commune et deux densités membre/gestionnaire ; catalogue, détail, favoris/listes/collections, découverte, circulation, statistiques, import/export et administration. | Pages complètes avec données synthétiques cohérentes, états vides/erreur/chargement, titres longs et sans affiche ; captures avant/après mêmes rôles/données/viewport ; flux existants conservés. Pas de simples composants de démonstration. |
| 7 — Accessibilité et frontend | UX-02, UX-04 et tous parcours critiques | Navigation courante/compacte, formulaires et focus ; Playwright/axe-core et régression visuelle ; mesures de performance avant optimisation. | Desktop/mobile/intermédiaire, reflow 320/390, zoom, Tab/Shift+Tab réels, focus visible/restitué, reduced-motion, contrastes mesurés et alertes axe triées ; budgets proposés mesurés et justifiés. Aucun score inventé ni bibliothèque ajoutée sans gain prouvé. |
| 8 — Architecture progressive | Dette Python, A4/A6 | Types de frontière, fonctions pures partagées, contrats cohérents et erreurs explicites ; propriétés métier et mutations sentinelles sur invariants critiques. | Typage sur périmètre choisi réellement exécuté ; propriétés non tautologiques, séquences/concurrence, mutant détecté ; aucune refonte sans bénéfice mesuré, aucun score global extrapolé d'un échantillon. |
| 9 — Supply chain, P2 | DEL-03 à DEL-06 | CodeQL, audit Actions, secrets effectifs, Dependabot, hashes, SBOM/licences et attestations ; conserver pip-audit/Grype et SHA complets. | CI Windows/Linux de chaque candidat, alertes triées, permissions minimales, dépendances fermées ; même image construite/scannée/publiée/attestée ; assets durables téléchargés et hashes vérifiés. Scorecard indicatif, Semgrep seulement pour besoin distinct. |
| 10 — Exploitation et staging, P2 | PRE-06, OPS-01/02/03 | Audit système/réseau Docker et permissions effectives ; sauvegarde/rollback avant changement ; staging HTTPS indépendant si faisable, logs corrélés, santé vivant/prêt et surveillance proportionnée. | Accès conservé après chaque modification, flux testés depuis hôtes autorisés, cookies/TLS réels, sauvegarde/restauration et rollback exécutés ; ressources vérifiées avant outils. Faisabilité impossible documentée avec preuve et limite, sans fausse haute disponibilité. |
| 11 — Portail et documentation, P2/P3 | DOC-01/02/03 | Trois README exacts, guides utilisateur/admin/exploitation, API, sécurité, contribution, templates, changelog/roadmap ; site statique réutilisant sources ; captures authentiques expurgées et licences médias. | Clone neuf utilisable, liens locaux/ancres/distants contrôlés avec limites datées ; signalement sécurité réaliste ; aucune coordonnée privée ; GitHub Pages présenté comme documentation, pas serveur Flask. |
| 12 — Édition académique et livraison stable | Conformité et mission complète | Maintenir matrice des 28 exigences et 61 extensions, édition améliorée du rapport distincte, comparaison v1/v2 ; nouvelle version, changelog et release. | Trois commits candidats et paire interservices validés ; rapport compilé/inspecté, preuves navigateur et sécurité récentes, digests et assets rapprochés ; installation/redéploiement/rollback vérifiés ; publication et déploiement explicitement constatés, réserves restantes publiées. |

Les lots de code et design peuvent avancer en parallèle sur des périmètres d'écriture distincts ; leur intégration reste séquentielle aux frontières API/web. La sélection des outils et les preuves avant modification précèdent leur installation. Les politiques de capacité, d'anti-abus et de reprise doivent être décidées ensemble avant de changer les seuils ; relever un plafond seul n'est pas un correctif d'archivage.

## Critères de produit à mesurer

Les cibles suivantes viennent de la revue UX ; elles sont proposées et restent à tester, pas acquises : premier résultat avant y=520 et statut/action de détail dans les 700 premiers pixels à 1280 × 900 ; en-tête fermé ≤120 px à 390 ; activité personnelle visible dans le premier viewport ; administration synthétique moins haute avec les mêmes comptes. Les positions initiales proviennent de lectures d'images et devront être remplacées par des mesures DOM reproductibles.

Une amélioration visuelle est acceptée seulement avec disponibilité réelle distincte du stock, navigation accessible, contenu long, absence d'affiche autorisée, erreurs et conservation de saisie. Les parcours doivent inclure catalogue/détail, connexion/profil, favoris/listes, dashboard/découverte, emprunts/réservations, gestion de film, administration et transfert. Les captures brutes privées ne sont pas des assets publics prêts à publier.

## Couverture du mandat complet

| Sections du mandat | Lots et livrables attendus |
|---|---|
| 1–3 : préservation, audit, skills | 0–1 ; références v1, audit six dimensions, sélection attribuée et installation bornée à venir |
| 4–5 : redesign et qualité UX/UI | 6–7 ; produit, design system, deux expériences, navigateur et accessibilité mesurés |
| 6 : revue approfondie du code | 2–4, 8 ; intégrité, capacité, concurrence, contrats, typage et invariants |
| 7–8 : ASVS et système/réseau | 5, 10 ; scans distincts, matrice applicable, état effectif et retour arrière |
| 9 : supply chain | 1, 9 ; gates interservices, dépendances, inventaire/licences et provenance |
| 10–11 : GitHub et site documentaire | 1, 11 ; gouvernance, portail et sources réutilisées |
| 12–13 : démonstration et observabilité | 10 ; staging proportionné, TLS, logs, disponibilité, restauration/rollback |
| 14 : documentation et rapport | 11–12 ; relecture factuelle, attributions, PDF v1 intact et édition améliorée |
| 15–17 : validation, livraison, reprise | Tous ; preuves à chaque lot, release finale et état durable de reprise |

## Règle de clôture

Un ID est clos seulement si sa preuve initiale est conservée, son correctif est identifié, son scénario risqué est retesté et les régressions pertinentes passent. Les équivalences A3/PRE-03 et A4/PRE-02 partagent les travaux mais exigent toutes leurs assertions : capacité normale et abus pour le premier groupe, latence/écritures et sessions/autorisation pour le second.

Les protections GitHub devront être relues au moment du changement ; le profil HTTPS dépend d'une origine et d'un environnement réellement disponibles. Ces points ne justifient pas l'arrêt des travaux locaux indépendants. Une limitation irréductible est consignée avec ce qui a été exécuté et le risque restant ; elle ne devient pas une réussite par reformulation.

L'audit documentaire n'est pas la condition de sortie finale. La mission reste ouverte jusqu'à la nouvelle livraison stable et sa comparaison vérifiable avec v1, ou jusqu'à des blocages externes explicitement documentés après épuisement des actions réalisables.
