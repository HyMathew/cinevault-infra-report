# Étude préliminaire de sauvegarde MongoDB

Le 12 novembre 2026, une sauvegarde chiffrée hors VM et sa restauration isolée ont
réussi sur des données synthétiques du commit API
`c2fe26bf2bc5c6f75048d216eb5f104a853877a4`. Le
[reçu public](../../evidence/public/mongodb-backup-study-20261112.json) conserve une
liste explicite de résultats, sans clés, chemins privés ni identifiants serveur.
Cette étude ne livre pas encore la procédure portable finale Enterprise 2.1.

## Capture cohérente et restauration

MongoDB 8.0.34, FCV 8.0 et Database Tools 100.20.0 sont identiques sur source et
cible. Les douze collections contiennent 244 documents et 37 index, dont 25 index
déclarés. La comparaison après restauration vérifie les documents BSON typés,
options et index de chaque collection avant toute écriture de test. Elle ne
prétend pas comparer les pages physiques du stockage.

Une transaction conserve le verrou du coordinateur applicatif pendant le dump
d'une seule base, en archive gzip. Un writer canonique concurrent rencontre trois
WriteConflict 112 et ne committe pas. La présence de la transaction est vérifiée
côté serveur avant et après le dump ; toutes les empreintes restent identiques.
La garde est ensuite annulée sans changer la révision. Cette méthode dépend du
respect de ce coordinateur par tous les writers et d'une fenêtre sans DDL. Elle
n'est pas présentée comme une sauvegarde en ligne de toute une instance avec oplog.

Le serveur source est arrêté et son arrêt confirmé avant de lancer le serveur
cible, sur un volume neuf et une autre base. Les validateurs restent actifs.
L'authentification applicative, la lecture du catalogue, les refus natifs de type
invalide et de permissions, puis la persistance après redémarrage sont contrôlés.
Les anciennes informations de connexion du compte de sauvegarde sont refusées
avec les deux authSources, originale et renommée. usersInfo confirme les ensembles
exacts d'identités attendus dans les deux bases d'authentification.

## Chiffrement et protection des clés

L'archive claire transite en mémoire sur le poste, sans fichier clair persistant.
AES-256-GCM utilise une clé de 32 octets et un nonce aléatoire neuf de 12 octets.
L'enveloppe et son contexte sont authentifiés ; aucun clair n'est transmis à la
restauration avant vérification complète. Mauvaise clé, altération et troncature
sont refusées. La rotation utilise une autre clé et un autre nonce ; les deux
archives persistées sont relues et déchiffrées par un processus indépendant.

Les clés de l'étude sont protégées par Windows DPAPI CurrentUser, hors dépôt et
hors dossier de sauvegarde. Le contrôle des ACL effectives confirme une DACL
protégée limitée à l'utilisateur courant et SYSTEM. Un contre-exemple avec une
permission Everyone explicite est refusé par ce contrôle. Sept tests locaux
passent avec les avertissements traités comme erreurs ; ils complètent les essais
natifs sans les remplacer.

DPAPI dépend du profil Windows : ce mécanisme n'est **pas un escrow portable**.
L'implémentation d'étude utilise aussi un helper SSH privé et une limite de
64 Mio en mémoire. Les programmes privés, clés et archives chiffrées ne sont pas
publiés comme un outil d'exploitation réutilisable.

## Mesures et limites

Sur cette petite fixture et une seule exécution, le gel dure 1,134 s, le dump et
transfert mémoire 0,886 s, mongorestore 2,386 s. De l'arrêt source confirmé à la
cible vérifiée, le temps observé est de 36,514 s. Ce temps exclut notamment la
détection d'incident, la récupération d'une clé perdue, le téléchargement d'images,
un volume de production et la réouverture de l'API finale. Aucun SLA n'en découle.
L'absence de mutation perdue pendant un gel imposé n'établit pas le RPO d'un
système en activité.

Quatre conteneurs et quatre volumes appartenant à l'étude ont été supprimés, sans
erreur. Le service applicatif stable conserve son conteneur, son image et son état
healthy. Aucun service ou document stable n'a été modifié. Un replica set à un
membre ne fournit aucune redondance physique.

La première étude conservée ne testait le refus de l'ancien compte qu'avec son
authSource originale ; cette preuve était insuffisante après renommage. La seconde
ajoute le refus avec la nouvelle authSource et les inventaires exacts des comptes.
Le reçu initial reste inchangé et sa portée est explicitement rectifiée.

Restent obligatoires : requalification du schéma final C3+, outillage public
paramétrable, récupération des clés indépendante du poste, fréquence, rétention,
rotation opérationnelle et restauration par un opérateur extérieur. Cette preuve
préliminaire ne ferme pas ces critères de l'objectif Enterprise 2.1.
