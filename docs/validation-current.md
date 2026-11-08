# Synthèse des validations au 9 novembre 2026

Cette synthèse publique expurgée reprend les résultats des journaux opérationnels locaux de la mission. Ces journaux sont des **preuves locales non publiées** : leur présence et leurs résultats ont été contrôlés pendant l'exécution, mais cette synthèse ne les transforme pas en artefacts publics ni en exécution de CI distante. Aucune nouvelle campagne n'a été exécutée pour cette mise à jour documentaire.

## Révisions et validation applicative

- API : `4b15406c2a1125518fb9a52dc53e9f50545db28e` ; web : `9b1da4f85adcd20c06e6113516de566d10aa6996`.
- Windows et Linux : 156 tests API et 68 tests web réussis sur chacune des deux plateformes.
- Intégration Compose : 171 contrôles réussis sur des données et volumes jetables. Ces essais ne modifient pas le magasin distribué.
- Images exactes scannées avec Grype 0.121.2 : zéro High/Critical, cinq Medium et un Low pour chacune. Ces résultats bornés au scan ne garantissent pas l'absence de vulnérabilité.

## Mise à jour distribuée observée

La mise à jour a réussi **le 8 novembre 2026 à 23 h 14 UTC, soit le 9 novembre à 00 h 14 à Paris**, sur un cluster de trois VM. Les 31 contrôles de cette campagne portent sur les images exactes des révisions ci-dessus, la santé des services, leur exécution en UID 10001, la racine en lecture seule et le retrait de toutes les capacités (`cap_drop: ALL`). Ces résultats sont distincts des 50 contrôles de la première campagne distribuée sur les anciennes révisions.

Une sauvegarde a précédé l'opération. Les empreintes du document métier et des comptes sont identiques avant et après la mise à jour ; une session existante a été conservée et une nouvelle connexion via le web avec contexte visiteur signé fonctionne. Les comptes, le volume et les deux anciennes clés ont été préservés. La troisième clé de contexte est dédiée et distincte, partagée uniquement entre les deux services, montée comme secret Docker en mode 0400 pour UID/GID 10001. Aucune valeur de secret, adresse physique ou identité de nœud n'est publiée ici.

## Limites encore ouvertes

Les métadonnées externes sont désactivées (`METADATA_ENABLED=false`) dans cette campagne. Le préchargement vérifié des images reste un mécanisme intermédiaire ; un registre public accessible doit encore être mis en place et vérifié. Les dépôts publics ne sont pas encore créés et la CI distante est **`NOT_RUN`**. Les liens de source vers les commits locaux immuables sont préparés pour la publication ; aucune disponibilité de ces URL n'est affirmée.

La campagne ne démontre ni haute disponibilité, ni terminaison HTTPS publique, ni restauration après panne de disque ou bascule multi-hôte. Le redémarrage autonome des deux workers reste non validé. Les contrôles navigateur antérieurs ne prouvent pas un audit exhaustif d'accessibilité ou de tous les parcours. Le rapport scientifique et l'audit final restent à terminer.

Les modèles et matrices conservent leurs observations historiques datées ; leurs nombres de tests et états de jalons ne doivent pas être confondus avec les résultats ci-dessus. Les supports pédagogiques, données métier, secrets et journaux locaux ne sont pas inclus dans cette publication.
