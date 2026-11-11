# Services communs sur MongoDB réel

Le [candidat APIc2fe26b](https://github.com/HyMathew/cinevault-api/tree/c2fe26bf2bc5c6f75048d216eb5f104a853877a4)
extrait les services communs d’authentification, de modification de films,
d’exemplaires/reçus d’idempotence et de lecture publique du catalogue. Leur
composition HTTP reste JSON dans cette révision ; cette page ne prétend pas
qu’une API HTTP Mongo complète est déjà activée.

## CI observée

La [CI43115632833](https://github.com/HyMathew/cinevault-api/actions/runs/43115632833)
a réussi au SHA exact : qualité et tests Windows/Ubuntu, Mongo réel et image.
La publication d’image est ignorée sur cette branche. Le gate Mongo a utilisé
MongoDB8.0.34 sur noyau6.8.0-1070-azure, avec compte de maintenance séparé et
identité applicative limitée aux collections autorisées.

Le reçu téléchargé et vérifié par SHA confirme :

- Cinq tests Mongo réellement exécutés, sans skip ;
- Contrats des quatre services communs réussis avec la même logique que JSON ;
- Cinq échecs de réauthentification puis refus du budget, sans perdre la fenêtre ;
- Film et premier exemplaire atomiques, versions428/412 et références protégées ;
- Rejeu de reçu après suppression, purge501reçus expirés et deux commandes
  invalides annulées sans reliquat ;
- Recherche littérale Unicode/NUL/entre champs, page/total/résumés et plus de100
  copies sans troncature ;
- Soixante et une commandes de lecture publique limitées à
  coordination/movies/copies, sans écriture ni lecture des comptes ou sessions ;
- Refus des clés BSON calculées absentes ou altérées ;
- Refus DDL, autre base et accès anonyme ; conteneur et données temporaires nettoyés.

L’archive Mongo porte le SHA-256
`1682a56b8031aef4ccd85d0fb61b786687eadfe2c063253683051eab1bcef37a`.
Le [reçu public de qualification](../../evidence/public/c2c-qualification-20261111.json)
conserve ces résultats et ceux de la paire HTTP/navigateur exacte.

L’image API construite par ce run est
`sha256:15c9eefcdd65d66435302885910523ceee74c502abc21b0217d899959a3eab06`.
Le smoke confirme UID10001, PyMongo4.19.0 sans extensions C, dnspython2.9.2,
Int64 exact, dix schémas et25index, notices présentes et outils de build absents.
Health, scan et nettoyage réussissent ; le scanner relève cinq Medium et un Low,
aucun High/Critical au gate. Cette image n’est ni sans vulnérabilité ni publiée
ou déployée par ce run.

## Plans et limites

Les plans gagnants sur les petites fixtures sont COLLSCAN pour la sous-chaîne,
IXSCAN/movie_year_order pour année et ordre, et IXSCAN/movie_natural_key pour le
prédicat de doublon. Aucun benchmark, garantie de latence ou dimensionnement n’est
déduit de ces plans. GET copies reste non paginé par compatibilité ; toute limite
future requiert un contrat explicite.

La sonde SSH isolée du11novembre18:21–18:22UTC avait aussi réussi sur un snapshot
immuable de53fichiers, manifeste
`1a073a5b9d2c86be33b349ed34ef476151cedad3a3e4af4be436ee5945cb4c59`.
Sa trace plus simple comptait57commandes ; le listener CI compte en outre les
collections des jointures. Cette différence n’est pas un changement de contrat.
Les deux conteneurs et deux volumes possédés ont été nettoyés, et le service
stable a conservé son image et son état sain.

Le modèle candidat possède25index déclarés et des clés techniques de recherche
obligatoires. Une ancienne base Mongo exige une migration explicite ; aucun
collMod ou remplissage silencieux n’est activé au démarrage. Les premiers essais
de l’[étude moteur](MONGODB_ENGINE_STUDY.md) restent des preuves historiques d’un
modèle antérieur, distinctes de ce snapshot.

Les autres domaines, l’équité des budgets, les courses prêt/réservation, la
composition exclusive des deux backends, la migration/rollback, les sauvegardes
restaurées, TLS et le déploiement restent à qualifier dans leurs propres lots.
Un replica set à un membre ne fournit aucune redondance physique.
