# CineVault — infrastructure et documentation

Ce dossier regroupe l'architecture et les configurations de développement et de déploiement. La mise à jour Enterprise du 9 novembre 2026 à 00 h 14, heure de Paris, a été vérifiée sur trois VM avec les révisions API `4b15406` et web `9b1da4f` : 31 contrôles de mise à jour distribuée, après validation Windows/Linux et 171 contrôles Compose sur données jetables. Voir la [synthèse datée des validations et de leurs limites](docs/validation-current.md). Les services web et API vivent dans des dépôts Git distincts. Les dépôts publics ne sont pas encore créés et la CI distante est `NOT_RUN` ; publication, registre public, audit final et rapport scientifique restent ouverts.

- [Architecture, flux et modèle de données](docs/architecture.md)
- [Dictionnaire des données, messages JSON et limites de validation](docs/data-dictionary.md)
- [Inventaire des pages, traitements et scripts frontend](docs/frontend-inventory.md)
- [Contrat HTTP proposé](docs/api.md)
- [Développement local et déploiement](docs/deploiement.md)
- [Swarm Enterprise réellement exécuté et limites](docs/deploiement-swarm-enterprise.md)
- [Vérification et reprise](docs/validation-reprise.md)

`compose.yaml` et `stack.yaml` conservent le socle pédagogique ; `compose.enterprise.yaml` complète le développement local et `stack.enterprise.yaml` décrit le déploiement collaboratif. Ils ne contiennent aucun secret ni adresse physique supposée. Le dossier des preuves privées distingue opérations réellement exécutées et procédures. Le redémarrage autonome VM2/3, une terminaison HTTPS publique et la haute disponibilité ne sont pas validés.
