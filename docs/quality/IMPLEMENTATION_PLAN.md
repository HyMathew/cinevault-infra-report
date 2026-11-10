# Plan d’amélioration CineVault 2.0

Ce plan prolonge la version 1.0.0 sans modifier ses tags, son rapport original ni le déploiement stable avant validation. Les trois applications et documents restent dans des dépôts indépendants ; Flask/Jinja, REST, JSON, Compose et Swarm sont conservés.

Actualisation du 10 novembre : le mandat consolidé introduit MongoDB comme persistance principale Enterprise, avec JSON académique maintenu. L’[ADR 0001](../adr/0001-json-mongodb.md) précise la décision, les impacts et les gates. L’audit v1 et les correctifs déjà validés sont conservés. Avant une stratégie définitive de capacité, intégrer modèle documentaire, repositories, transactions, tests de contrat sur deux moteurs, migration et rollback ; un wrapper BSON du document JSON entier n’est pas l’état final attendu.

## Ordre et critères de passage

| Lot | Résultat attendu | Preuves requises avant clôture |
| --- | --- | --- |
| 0 — référence | Audit contradictoire, sauvegardes et captures actuelles | Bundles Git vérifiés, commits identifiés, tests de référence, limites explicites des audits |
| 1 — contrats web | Aucune perte de valeurs dans les formulaires ; erreurs amont et entiers invalides traités | Régressions échouant avant correction, suite complète, échanges avec une vraie API isolée |
| 2 — sécurité et ressources | Résultats des scans source validés puis corrections des contrôles défaillants | Menaces, preuves et contre-preuves ; tests de régression ; matrice ASVS 5 applicable sans certification |
| 3 — produit | Découverte et espace membre distincts de la gestion | PRODUCT, DESIGN, design system ; pages complètes avec données synthétiques cohérentes ; parcours réels |
| 4 — vérification UI | Interface utilisable sur ordinateur, mobile et au clavier | Playwright, axe, contrastes, captures avant/après comparables, erreurs et états vides |
| 5 — livraison | CI et dépôts publics utiles et traçables | Intégration des deux services, permissions minimales, analyse des workflows, SBOM/provenance, règles de branche adaptées |
| 6 — exploitation | Mode académique préservé et staging indépendant étudié | Santé vivant/prêt, corrélation, sauvegarde/restauration/rollback exécutés ; HTTPS staging si environnement disponible |
| 7 — documentation | Portail, guides, site statique et rapport 2.0 | Liens vérifiés, affirmations sourcées, PDF compilé et inspecté, original 1.0.0 inchangé |
| 8 — livraison 2.0 | Nouvelle version validée et comparaison mesurable | Tests et revues indépendantes, images exactes, déploiement contrôlé, preuves de reprise, release cohérente |

Les lots peuvent préparer des éléments indépendants en parallèle. Une dépendance non validée reste ouverte ; une revue ou une capture ne remplace pas une exécution de test.

## Premier lot : contrats web

1. Reproduire le dépassement de conversion d’un entier long et l’enveloppe d’erreur HTTP 422 mal formée. Écrire les tests de comportement avant la correction.
2. Borner et valider les nombres avant leur conversion ; préserver les bornes métier et refuser signes/Unicode non autorisés.
3. Valider l’enveloppe d’erreur du service de données. Une réponse invalide devient une indisponibilité contrôlée, sans rejouer une mutation ni perdre les valeurs saisies.
4. Remplacer le découpage ambigu des listes de noms et genres par une représentation réversible. Les virgules, guillemets et retours à la ligne déjà admis par l’API ne doivent pas être silencieusement transformés. Tester le trajet lecture, formulaire, soumission, persistance.
5. Exécuter tests ciblés, suite web complète et contrôles officiels du dépôt. Documenter séparément la validation locale et la validation intégrée.

## Décisions de périmètre

Le redesign reste rendu côté serveur. L’ajout de Tailwind, htmx ou Alpine exige un besoin concret et un bénéfice mesuré ; aucun de ces outils n’est requis pour corriger les contrats. Les méthodes Impeccable audit/polish peuvent être adaptées au projet après inspection et attribution ; le moteur natif et ses hooks ne sont pas exécutés par cette décision. Aucun audit automatique ne vaut garantie de sécurité ou de disponibilité.
