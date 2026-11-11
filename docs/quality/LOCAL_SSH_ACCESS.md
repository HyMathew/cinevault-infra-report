# Administration locale par SSH

Le 11 novembre 2026 à18:17UTC, les trois VM du laboratoire ont été vérifiées
depuis le PC Windows avec leurs clés d’hôte épinglées. L’administration utilise
SSH local et ne dépend plus de la console du navigateur RemoteLabz.

## Politique constatée

Les connexions au compte de projet proposent uniquement `publickey` sur les trois
VM. Cette observation provient d’une nouvelle négociation SSH par machine, après
vérification de sa clé d’hôte et sans envoyer de mot de passe. Une connexion
anonyme n’a pas été acceptée.

VM2 et VM3 refusaient déjà l’authentification SSH par mot de passe. VM1 a été
alignée avec le fichier `/etc/ssh/sshd_config.d/10-cinevault-key-auth.conf`, propriété
root, mode0600 :

```text
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
```

Empreinte du fichier complet, commentaire inclus :
`08e6a8442e2300792cb06559ffac57c77b6ffe100013081ab49a668786d3b938`.
La syntaxe a été validée avant le rechargement du service. Une connexion par clé
existante a été conservée pendant l’opération ; une nouvelle connexion par clé a
ensuite réussi. Le service SSH est actif. La politique root existante reste
`without-password`, c’est-à-dire sans authentification root par mot de passe.

## Préservation et retour arrière

Le contrôle de18:18UTC retrouve les trois nœuds Swarm Ready, le manager Leader
Drain et les deux conteneurs stables sains. Les deux digests de la v1 sont
inchangés. Aucun service applicatif, volume, pare-feu Windows ou VPN n’a été
modifié par cette opération.

Le retour arrière consiste, depuis une session d’administration conservée, à
vérifier l’empreinte du seul fichier ajouté, le retirer, valider `sshd -t`, puis
recharger SSH. Ne pas remplacer ni supprimer le fichier cloud-init existant.
Ne pas désactiver l’authentification par clé sans un autre accès éprouvé.

Le [reçu public](../../evidence/public/local-ssh-access-20261111.json) conserve les
résultats et empreintes des preuves privées, sans clés ni mots de passe. Cela ne
constitue pas une rotation des clés, un déploiement de v2 ni une vérification
complète de durcissement système.
