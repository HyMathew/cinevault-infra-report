# Preuves défensives avant mise en service Signature

Cette grille traduit la revue du 27 novembre en critères observables
pour la segmentation, la journalisation et l’alerte. Elle complète la
[matrice ASVS](../security/ASVS_MATRIX.md) et le
[guide de staging](../staging-mongodb.md). Les résultats restent rattachés
à leur environnement et à leurs révisions.

| Garantie à vérifier sur le staging signé | Relevés de préparation et de composants | Critère d’acceptation |
| --- | --- | --- |
| Accès privé au frontal et segmentation des services | [Réseau et TLS du composant MongoDB](../../evidence/public/swarm-mongodb-overlay-tls-20261125.json) et [précontrôle des trois nœuds](../../evidence/public/swarm-predeployment-readiness-20261126.json). | Relever depuis le manager les services, digests, tâches et ports publiés. Pour la variante HTTPS privée, les quatre services publient zéro port Swarm. Le tunnel opérateur donne accès à Caddy sur `edge`. Vérifier aussi Web sur `edge` et `front`, API sur `front` et `data`, MongoDB sur `data`. |
| Identité et échéance TLS | [Sonde TLS et expiration en banc isolé](../../evidence/public/operational-tls-expiry-20261126.json). | Les noms, autorités attendues et dates du frontal et de MongoDB concordent avec la politique. Conserver les empreintes publiques et les heures UTC de la sonde déjà prévue. |
| Corrélation et traitement des journaux | [Corrélation HTTP sur banc local](../../evidence/public/mongodb-performance-observability-20261121.json) et [procédure d’exploitation](../observability.md). | Sur une navigation de démonstration, relier l’identifiant de réponse aux lignes Web et API. Relever la décision d’accès, le statut et le modèle de route. Documenter aussi rétention, droits de lecture et destination réellement configurée. |
| Alerte et confirmation de réception | [Remise inter-hôtes du banc](../../evidence/public/operational-watch-cross-host-20261126.json) et [cycle d’indisponibilité du Web](../../evidence/public/operational-proxy-http-20261126.json). | Rapprocher le créneau de supervision, l’événement émis, la réception séparée et la récupération au moyen des identifiants existants. Joindre le reçu de la vérification hors VM de l’archive. |
| Capacité Docker avant création des ressources | [Précontrôle Signature sur les trois nœuds](../../evidence/public/signature-staging-readiness-20261127.json). | Mesurer les trois nœuds après chargement des images qualifiées. Le budget doit couvrir journaux, volumes, retour arrière et marge d’exploitation. Le reçu du contrôleur indique le seuil de campagne et la mesure de chaque nœud. |

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

## Rattacher les résultats à la promotion

- Associer les commits API, Web et Infra, l’empreinte de la sélection
  OpenSSL et le résultat des tests de la paire exacte. Dans le reçu
  d’images, conserver le run, sa tentative, les empreintes des pièces
  contrôlées, le sujet signé et les digests de plateforme et de configuration.
  Le [vérificateur de paire](../../scripts/check_staging_image_pair.py)
  contrôle les images applicatives. Les tests croisés et la vérification
  des images de support sont des preuves complémentaires.
- Dater les bases de scan et consigner le mode d’identification de chaque
  archive. En mode archive Docker, le digest de configuration identifie
  l’image examinée. L’égalité avec un manifeste OCI d’archive est vérifiée
  quand ce manifeste existe. Pour les images MongoDB et Caddy chargées
  localement, rapprocher l’image exécutée de l’identifiant du scan de
  l’archive et du rendu Swarm.
- Conserver le rendu du couple précédemment réussi et les références
  versionnées de ses secrets et configurations, ainsi que le reçu et
  l’empreinte de sauvegarde nécessaires si les données sont concernées.
  Après un retour arrière, revoir l’accès, la santé, la paire et les
  montages avant de rouvrir les écritures. Le retour de la paire et la
  restauration des données produisent des preuves distinctes.

Au 27 novembre 2026, ces contrôles sur le staging intégré restent ouverts.
Les relevés partiels servent de preuve de composant et de préparation.
La [soutenance](../soutenance-signature.md) peut les présenter avec leur
périmètre lorsque le laboratoire est indisponible.
