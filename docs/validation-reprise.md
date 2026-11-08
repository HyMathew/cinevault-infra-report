# Vérification, sauvegarde et reprise

La [synthèse courante du 9 novembre 2026](validation-current.md) décrit la mise à jour réellement exécutée sur trois VM. Les chiffres de reprise ci-dessous appartiennent au jalon local historique du 6 novembre 2026 ; ils ne sont pas une nouvelle campagne et ne doivent pas être présentés comme les derniers résultats applicatifs.

## État courant et campagne historique de reprise

Les deux applications ont été construites et exécutées sous Docker Compose local. Le parcours historique de reprise atteint 157 contrôles HTTP réussis (preuves locales non publiées), avec création de données synthétiques, redémarrage, panne API, instantané cohérent, reprise sur un nouveau fichier, rejet des anciens accès et retour contrôlé d'un compte. Les services tournent en UID 10001. Les suites API comportent 112 tests réussis sur Windows/Linux. Cette campagne locale historique ne démontrait pas le cluster Swarm ni une bascule distante. La mise à jour distribuée ultérieure ne démontre toujours pas une restauration après panne de disque ou une bascule multi-hôte. Le contrôle visuel navigateur des nouveaux parcours demeure distinct des tests HTTP.

## Contrôles à exécuter sur l'installation réelle

1. Confirmer versions et ressources, architecture des nœuds, disponibilité du registre, interfaces et routes ; enregistrer les mesures sans secrets.
2. Construire les images ; lancer Compose ; vérifier les états et journaux et tester les sondes. Une sonde saine ne remplace pas une mutation complète.
3. Depuis un navigateur, créer un film, le retrouver par recherche, le modifier et le supprimer ; vérifier erreurs et protection des formulaires. Tester l'indisponibilité API et les données Unicode.
4. Créer une donnée de test identifiée, recréer le conteneur API sans supprimer son volume et vérifier sa présence. Tester les écritures concurrentes dans le périmètre prévu. Nettoyer seulement les données de test identifiées.
5. Sur les VM effectivement autorisées, établir le cluster et l'Overlay, vérifier les trois nœuds, les placements, les accès réseau et les images sur les workers, puis effectuer le parcours de bout en bout. Mesurer les ports Swarm au lieu de les supposer ouverts.
6. Tester un redémarrage contrôlé, contrôler les données et journaux, puis réaliser une sauvegarde et une restauration sur une copie isolée. Associer chaque résultat à une preuve datée. Les critères non exécutés restent non validés.

## Sauvegarde et restauration

Le volume local doit être identifié précisément avant toute intervention. Pour une copie cohérente, arrêter temporairement et de manière contrôlée les écritures API, sauvegarder le contenu du volume dans un emplacement protégé, puis reprendre le service et vérifier son état. Conserver la structure et les permissions nécessaires à l'UID/GID de l'API. Ne pas publier les données personnelles dans les dépôts ou preuves.

Tester la restauration sur un volume distinct, jamais sur l'unique copie. Vérifier structure JSON, données attendues et démarrage de l'API avant toute bascule. Définir une fréquence de sauvegarde et une durée de conservation adaptées à l'usage ; aucune politique n'est prétendue en place. Les incidents de stockage, erreurs d'écriture et un échec après remplacement atomique peuvent rendre le résultat d'une mutation incertain : lire l'état réel avant de réessayer.

## Reprise Enterprise et authentification

Le dépôt API fournit `app/recovery.py` et la procédure `docs/recovery.md`. La primitive de restauration brute ne doit pas servir seule à remettre en ligne un instantané Enterprise : elle pourrait réintroduire des sessions et mots de passe anciens. La commande de reprise écrit une nouvelle cible absente, invalide tous les mots de passe restaurés, désactive les comptes, retire les sessions et crée un nouvel administrateur distinct. Les prêts sont conservés ; les attentes sont annulées ou expirées. La réactivation d'un compte vérifié exige un mot de passe frais via l'outil local ; son rôle reste inchangé.

Arrêter et vérifier les écrivains, préserver l'ancien volume, utiliser une empreinte SHA-256 provenant d'une source de confiance, contrôler les permissions et l'horloge. Configurer explicitement le nouveau chemin dans `ENTERPRISE_DATA_FILE`, renouveler les clés des services et contrôler les connexions après redémarrage. Ne jamais redémarrer simultanément l'ancien fichier comme source d'autorité. Conserver les archives et reçus de reprise dans un stockage privé ; ne pas les joindre aux dépôts publics.

L'intégration locale utilise le même volume éphémère avec deux fichiers distincts pour démontrer l'absence d'écrasement ; une restauration d'exploitation doit utiliser un volume de reprise distinct pour isoler aussi les défaillances du stockage. Aucun délai de rétablissement garanti ou perte nulle n'est revendiqué. Les changements postérieurs à l'instantané doivent être réconciliés avant réouverture.
