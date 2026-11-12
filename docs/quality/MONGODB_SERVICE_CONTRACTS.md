# Services communs sur MongoDB réel

## Qualification C3 — collections privées et journal

Le [candidat API139a839](https://github.com/HyMathew/cinevault-api/tree/139a8391181d498144ce9c0e907734d3570b2bfb)
ajoute le service commun des collections privées et du journal. Sa
[CI43205951909](https://github.com/HyMathew/cinevault-api/actions/runs/43205951909)
complète a réussi, incluant qualité/tests Windows et Ubuntu, Mongo réel et audit
d'image. La composition HTTP reste JSON ; ce résultat n'active pas Mongo global.
Le [reçu public C3](../../evidence/public/c3-qualification-20261112.json) conserve
les résultats natifs et ceux de la paire exacte API139a839/web8256166 dans
Chromium et en HTTP sur les deux OS. Les empreintes du code chargé ont été
comparées aux archives Git sans conversion CRLF, et les cinq captures vérifiées.

Le contrat natif observe310commandes de portée privée : propriétaire appliqué
avant page ou mutation, y compris face à un administrateur, films joints bornés
à la page, unicité Unicode et conflit concurrent sans double entrée/événement.
L'audit utilise un ordinal BSON Int64 technique strict et caché, sous le verrou
transactionnel existant. La rétention garde exactement le suffixe2000 après un
jeu de2501événements et libère les UUID en plusieurs lots. Les rangs absents,
invalides ou dupliqués, leur épuisement et les parents absents sont refusés avec
annulation atomique.

Le précontrôle d'autorité effectue51lectures sans modifier session ni révision.
La commande finale relit les droits, puis réalise touch et mutation dans sa
transaction. Les refus de précontrôle ne prolongent plus la session ; les refus
métier normaux dans une commande finale gardent leur politique de commit propre.
Ce choix ne signifie pas que toute erreur de toute route ne peut jamais écrire.

L'image auditée est
`sha256:19f869849cdc923e17031c094113269b3ac3fe363371df39d1cc45f31881383e` :
UID10001, SDK4.19.0 sans extensions C, dix schémas,25index déclarés, notices
présentes et outils de build absents. Santé, scan et nettoyage réussissent ;
cinq Medium et un Low restent observés, aucun High/Critical au gate. Cette image
n'a été ni publiée ni déployée par ce run.

Une base antérieure sans ordinal exige une migration explicite, sans collMod
silencieux. Les budgets équitables, autres services, composition exclusive,
migration/rollback et exploitation finale restent ouverts. L'
[étude de sauvegarde C2c](MONGODB_BACKUP_STUDY.md) est préliminaire et doit être
requalifiée sur le schéma final. Le replica set à un membre ne fournit aucune
redondance physique.

## Qualification C2c historique

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
