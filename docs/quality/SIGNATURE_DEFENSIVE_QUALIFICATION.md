# Preuves défensives avant mise en service Signature

Cette grille traduit la revue du 27 novembre en critères observables
pour la segmentation, la journalisation et l’alerte. Elle complète la
[matrice ASVS](../security/ASVS_MATRIX.md) et le
[guide de staging](../staging-mongodb.md). Les résultats restent rattachés
à leur environnement et à leurs révisions.

| Garantie à vérifier sur le staging signé | Preuve acquise | Critère d’acceptation |
| --- | --- | --- |
| Publication du frontal et segmentation des services | [Réseau et TLS du composant MongoDB](../../evidence/public/swarm-mongodb-overlay-tls-20261125.json) et [précontrôle des trois nœuds](../../evidence/public/swarm-predeployment-readiness-20261126.json). | Relever depuis le manager les services, digests, tâches et ports publiés. Associer chaque service à ses réseaux effectifs. La configuration et le relevé doivent montrer que seul le frontal publie un port prévu. Les services internes portent uniquement les réseaux attendus. |
| Identité et échéance TLS | [Sonde TLS et expiration en banc isolé](../../evidence/public/operational-tls-expiry-20261126.json). | Les noms, autorités attendues et dates du frontal et de MongoDB concordent avec la politique. Conserver les empreintes publiques et les heures UTC de la sonde déjà prévue. |
| Corrélation et traitement des journaux | [Corrélation HTTP sur banc local](../../evidence/public/mongodb-performance-observability-20261121.json) et [procédure d’exploitation](../observability.md). | Sur une navigation de démonstration, relier l’identifiant de réponse aux lignes Web et API. Relever la décision d’accès, le statut et le modèle de route. Documenter aussi rétention, droits de lecture et destination réellement configurée. |
| Alerte et confirmation de réception | [Remise inter-hôtes du banc](../../evidence/public/operational-watch-cross-host-20261126.json) et [cycle d’indisponibilité du Web](../../evidence/public/operational-proxy-http-20261126.json). | Rapprocher le créneau de supervision, l’événement émis, la réception séparée et la récupération au moyen des identifiants existants. Joindre le reçu de la vérification hors VM de l’archive. |

## Préparer la preuve

1. Partir des digests validés par le [contrôle de paire](../staging-mongodb.md)
   et relever la fenêtre UTC. Un résultat antérieur à la mise en service
   ne suffit pas pour attribuer la topologie au candidat.
2. Comparer les **faits du relevé** aux valeurs attendues dans la
   configuration. Retenir les associations entre composants, noms
   fonctionnels et versions. Conserver les adresses, chemins privés et
   comptes d’administration dans le dossier opérationnel privé.
3. Pour la collecte des journaux, consigner origine, rétention, contrôle
   d’accès et copie distincte lorsqu’elle existe. Le journal métier et le
   résumé HTTP ont des périmètres différents.
4. Pour l’alerte, conserver ensemble l’identifiant du créneau, celui de
   l’événement, l’heure d’observation, l’heure de réception et la preuve
   de reprise. La sortie positive d’une sonde ne prouve pas la remise.
   Le [guide de la sonde](OPERATING_PROBE.md) décrit le lanceur, le
   superviseur et le reçu du destinataire.

Au 27 novembre 2026, ces contrôles sur le staging intégré restent ouverts.
Les relevés partiels servent de preuve de composant et de préparation.
La [soutenance](../soutenance-signature.md) peut les présenter avec leur
périmètre lorsque le laboratoire est indisponible.
