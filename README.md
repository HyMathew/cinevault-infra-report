# CineVault — infrastructure et documentation

Ce dépôt regroupe l'architecture, les configurations et la documentation de CineVault Enterprise. Le 9 novembre 2026 à 16 h 04, heure de Paris, les images issues des CI GitHub réussies ont été déployées par digest sur trois VM : API `6a86f2e`, web `f3d10cb`. Vingt-cinq contrôles de mise à jour ont réussi, avec préservation des données, comptes, secrets et sessions. Voir la [synthèse datée des validations et de leurs limites](docs/validation-current.md). Le rapport scientifique et l'audit final restent en cours.

Les deux projets applicatifs sont publics : [API Flask/JSON](https://github.com/HyMathew/cinevault-api) et [présentation Flask/Jinja](https://github.com/HyMathew/cinevault-web). Leurs CI exécutent les tests sur Windows et Ubuntu, les contrôles qualité, la construction et le scan des images avant publication dans GHCR. Les images ont été téléchargées sans identifiant sur les trois VM ; la stack utilise leurs références immuables.

- [Preuves VS Code, volume partagé et exercices A/B/C](docs/pedagogical-validation.md)
- [Architecture, flux et modèle de données](docs/architecture.md)
- [Dictionnaire des données, messages JSON et limites de validation](docs/data-dictionary.md)
- [Inventaire des pages, traitements et scripts frontend](docs/frontend-inventory.md)
- [Contrat HTTP proposé](docs/api.md)
- [Développement local et déploiement](docs/deploiement.md)
- [Swarm Enterprise réellement exécuté et limites](docs/deploiement-swarm-enterprise.md)
- [Vérification et reprise](docs/validation-reprise.md)

`compose.yaml` et `stack.yaml` conservent le socle pédagogique ; `compose.enterprise.yaml` complète le développement local et `stack.enterprise.yaml` décrit le déploiement collaboratif. Ils ne contiennent aucun secret ni adresse physique supposée. Le dossier des preuves privées distingue opérations réellement exécutées et procédures. Le redémarrage autonome VM2/3, une terminaison HTTPS publique et la haute disponibilité ne sont pas validés.
