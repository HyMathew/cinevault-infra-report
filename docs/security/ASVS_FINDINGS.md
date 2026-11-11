# ASVS 5.0.0 — écarts de qualification et preuves restantes

Revue source du 11 novembre 2026, associée à la [matrice](ASVS_MATRIX.md) et à son
[inventaire de 345 contrôles](asvs-v5.0.0-applicability.csv). Révisions : API
`72b7624101eb25bda4387726b9825c3bc596205c`, web
`c3dbc9e2b4db1e494c2f3317be43e074a5d1b22b`, infra
`d2a29c083affffffb2e3f33a06205b85f1314240`. Complément ciblé : correctif de
configuration web `7166549f932ea608a8b1a272931d504ad209cc05`, décrit ci-dessous.
Les autres modifications après les révisions initiales ne sont pas couvertes par
cette qualification.

La grille contient 235 contrôles applicables : 175 partiels, 31 non vérifiés,
29 non satisfaits. Les 110 N/A sont conditionnels à l'absence d'une fonctionnalité
précise. Aucun statut ne vaut certification ou validation du déploiement v2.
Les niveaux ASVS sont des niveaux d'exigence, pas une échelle de sévérité de
vulnérabilité. Les écarts ci-dessous ne sont donc pas des constats CVSS et ne
remplacent pas les résultats du scan source scellé v1.

## Écarts à traiter dans le candidat et son exploitation

### Configuration de la clé de session web : correction candidate vérifiée

Le [chargement de clé web](https://github.com/HyMathew/cinevault-web/blob/c3dbc9e2b4db1e494c2f3317be43e074a5d1b22b/app/__init__.py)
refuse un fichier de moins de 32 octets, mais ne vérifie que la présence d'une
valeur lorsqu'elle vient directement de `SECRET_KEY`/configuration. Une valeur
non vide de longueur 1 est donc acceptée par la fabrique.

Une reproduction locale sur cette révision, avec une valeur synthétique de test,
a créé l'application et reçu 200 sur `/health`. Aucun compte, donnée du laboratoire
ou secret réel n'a été utilisé. Cela démontre une configuration faible admissible,
**pas** l'utilisation d'une clé faible sur la stack existante : cette dernière
est documentée avec une clé aléatoire séparée de 64 octets montée comme secret.

Le [correctif web7166549](https://github.com/HyMathew/cinevault-web/commit/7166549f932ea608a8b1a272931d504ad209cc05)
applique désormais une validation unique après sélection de la clé courante :
configuration Python, environnement ou fichier. Chaque clé doit être une chaîne
encodable en UTF-8 d'au moins 32 octets, ou des `bytes` d'au moins 32 octets.
Clés absentes, vides, trop courtes, textes non encodables et types non admis
refusent le démarrage sans afficher la valeur, y compris avec `TESTING=true`.
La voie sœur `SECRET_KEY_FALLBACKS`, qui permettait également d'accepter un cookie
signé avec une ancienne clé courte, est incluse : liste/tuple explicite et même
contrôle pour chaque clé, sans désactiver la rotation Flask.

Le fichier conserve ses octets bruts, espaces et fins de ligne compris, sans
`strip` ni décodage. Clés valides, priorité fichier, ordre des anciennes clés et
signatures existantes restent inchangés. Les nouveaux cookies utilisent toujours
la clé courante. Ni le digest ni l'algorithme de signature n'ont été modifiés.

Les [52 cas spécifiques](https://github.com/HyMathew/cinevault-web/blob/7166549f932ea608a8b1a272931d504ad209cc05/tests/test_session_key_config.py)
couvrent les frontières de taille/types/UTF-8, les trois sources, la priorité,
l'absence de fuite dans l'erreur et les cookies avant/après rotation. Le reçu
JUnit local relu contient **428 tests, dont ces 52, sans échec, erreur ni skip**.
Son manifeste source lie un checkout isolé basé sur web57aa187 aux 12 fichiers du
correctif ; les 12 empreintes et leur égalité avec le commit7166549 ont été
contrôlées, en tenant compte uniquement des fins de ligne Git. Cette campagne
exclut les modifications d'interface de gestion encore en cours. La
[CI43071643085](https://github.com/HyMathew/cinevault-web/actions/runs/43071643085)
a été constatée terminée avec succès pour le SHA7166549 exact.

Ce défaut de validation n'est plus reproduit dans le candidat vérifié. Cela ne
modifie pas le constat historique ci-dessus et ne prouve aucun déploiement de ce
correctif sur v1. Les contrôles `v5.0.0-11.2.3`, `11.5.1` et `13.3.1` restent
**PARTIEL** : la longueur seule ne mesure pas l'entropie, et génération/provenance
de toutes les clés, inventaire cryptographique, rotation opérationnelle,
permissions, sauvegarde et restauration demandent encore leurs preuves.

La signature du cookie utilise le digest délégué par Flask/itsdangerous ; la
reproduction a observé `sha1`. Il faut qualifier cet usage HMAC et son algorithme
dans l'inventaire cryptographique ; ce nom seul ne démontre pas une falsification
ni une vulnérabilité exploitable.

### HTTPS, cookies et en-têtes

La [stack actuelle](../../stack.enterprise.yaml) configure `COOKIE_SECURE=false`
et publie le web HTTP de laboratoire ; le tunnel SSH protège un trajet local mais
n'est pas une terminaison HTTPS du navigateur. Le nom des cookies n'est pas
préfixé `__Host-`/`__Secure-`. Le
[middleware web](https://github.com/HyMathew/cinevault-web/blob/c3dbc9e2b4db1e494c2f3317be43e074a5d1b22b/app/__init__.py)
émet CSP/nosniff/Referrer-Policy, sans HSTS ni COOP. Leur absence a aussi été
observée dans la réponse locale `/health` ; aucune nouvelle mesure distante
n'est revendiquée ici.

Action : préparer le staging HTTPS, qualifier certificat/protocoles/suites et
migration des cookies, puis tester les réponses et parcours réels. Activer HSTS
seulement sur un hôte HTTPS maîtrisé ; ne pas précharger un domaine universitaire
non possédé. Contrôles : `v5.0.0-3.3.1`, `3.3.3`, `3.4.1`, `3.4.8`, `12.1.1`,
`12.2.1`. Le reporting CSP `3.4.7` est un complément L3 distinct nécessitant un
collecteur et une politique de minimisation.

### Politique de mots de passe

[`valid_password`](https://github.com/HyMathew/cinevault-api/blob/72b7624101eb25bda4387726b9825c3bc596205c/app/enterprise_auth.py)
contrôle Unicode, longueur de 12–256 caractères et taille UTF-8. Il ne consulte
ni liste de mots de passe courants/compromis ni liste contextuelle. Les contrôles
`v5.0.0-6.2.4` (L1), `6.1.2`, `6.2.11` et `6.2.12` ne sont donc pas satisfaits.

Action : définir un corpus fiable et sa mise à jour, privilégier la confidentialité
du secret, appliquer la même politique aux voies HTTP/bootstrap/recovery et tester
les frontières. Ne pas durcir arbitrairement la composition ni transformer le
refus en troncature/normalisation silencieuse. L'authentification à facteur unique
reste un écart L2 visible sous `6.3.3` ; cette qualification n'impose pas à elle
seule une nouvelle fonctionnalité MFA au périmètre produit.

### Admission, sessions et capacité

Le budget de réauthentification candidat est présent, mais les capacités globales
du fichier JSON, dont 10000 sessions, ne constituent pas une admission équitable
par acteur. La politique de sessions simultanées par compte et son comportement
à saturation restent à définir (`v5.0.0-7.1.2`). Il n'existe pas d'interface
utilisateur de visualisation/révocation des sessions après réauthentification
(`7.5.2`). Login crée un bearer neuf tout en laissant les autres sessions valides ;
la rotation d'une éventuelle session courante de réauthentification mérite un
contrat explicite (`7.2.4`, partiel).

Action : compléter les politiques et tests communs JSON/Mongo ; conserver les
budgets anti-bruteforce avant Argon2, la révocation atomique et les refus lors d'un
recul d'horloge. Les essais UoW et index Mongo ne prouvent pas encore toutes les
routes de prêts, réservations, import et administration. Les constats de capacité
du scan v1 restent ouverts tant que leurs scénarios métier ne sont pas traités et
retestés ; changer de moteur ne les clôt pas automatiquement.

### Journal de sécurité et conservation

[`record_event`](https://github.com/HyMathew/cinevault-api/blob/72b7624101eb25bda4387726b9825c3bc596205c/app/audit.py)
écrit un journal métier JSON borné à 2000 événements. Il ne couvre pas toutes les
authentifications, refus d'autorisation ou tentatives de contournement, et demeure
modifiable avec le magasin applicatif. Les logs locaux Docker possèdent une
rotation, sans collecte séparée ni inventaire complet de sécurité.

Actions : définir format, événements, données exclues, corrélation, destinations,
contrôle d'accès et rétention ; ajouter des tests de fuite/injection et vérifier
la réception séparée. Prévenir une amplification de logs par tentative répétée.
Contrôles non satisfaits : `v5.0.0-16.1.1`, `16.3.1`, `16.3.2`, `16.3.3`,
`16.4.2`, `16.4.3`. La classification/rétention des données privées et sauvegardes
reste également incomplète (`14.2.7`) : une troncature arbitraire de l'historique
ne constitue pas une politique de rétention justifiée.

### Rotation des secrets et maintenance des dépendances

Les secrets sont séparés et montés avec des droits restreints, mais leur cycle de
rotation/expiration 2.0 n'est pas éprouvé (`v5.0.0-13.3.4`). Les audits de dépendances
produisent des résultats datés et bloquent High/Critical ; aucun calendrier de
remédiation par risque n'est défini (`15.1.1`). La provenance/SBOM de la livraison
2.0, le build PyMongo, les sauvegardes Mongo restaurées et le transport Mongo
déployé demandent leurs preuves propres.

Actions : définir procédures/fréquences et cas de retour arrière, puis tester
rotation, continuité des budgets, lecture/restauration des backups, avis Medium/Low
et délais. Ni Docker Secrets ni un checksum SHA d'archive ne sont à présenter comme
un HSM ou un mécanisme complet d'authentification de sauvegarde.

### Extension des fichiers importés

Le [transfert web](https://github.com/HyMathew/cinevault-web/blob/c3dbc9e2b4db1e494c2f3317be43e074a5d1b22b/app/transfer.py)
ignore le nom du fichier et vérifie le format choisi par parsing strict JSON/CSV.
Cela évite de faire confiance à une extension et les octets ne sont pas stockés,
mais la comparaison extension/contenu exigée par `v5.0.0-5.2.2` n'est pas réalisée.
Cette divergence est déclarée, sans la transformer en exécution arbitraire de
fichier ni prétendre que le parsing prouve l'intégralité du contrôle.

Action : décider/documenter la politique d'extension et tester contenu/format
contradictoires, corps surdimensionné, BOM et fichier malformé. L'absence de
décompression et de stockage d'originaux justifie les N/A propres aux archives,
symlinks et antivirus de binaires redistribués ; ces décisions sont à rouvrir si
une fonction d'upload média est ajoutée.

## Compléments L3 à décider explicitement

| Contrôle | Écart visible | Décision ou preuve attendue |
| --- | --- | --- |
| `v5.0.0-6.3.5` et `6.3.7` | Pas de notification indépendante de connexion suspecte ou de changement de secret. | Évaluer besoin/canal/confidentialité avant d'introduire un système de notification. |
| `v5.0.0-6.3.8` | Login générique, mais inscription409 révèle un username déjà utilisé. | Décider du risque d'énumération et éprouver codes/messages/temps ; ne pas annoncer une uniformité globale. |
| `v5.0.0-6.4.6` | Le reset offline permet à l'opérateur système de choisir le nouveau secret. | Documenter l'autorité et la trace ; si retenu, préférer une activation choisie par l'utilisateur et inconnue de l'opérateur. |
| `v5.0.0-13.3.3` | Pas de module isolant toutes les opérations cryptographiques. | Déclarer la limite du laboratoire et analyser le besoin ; ne pas nommer les secrets Docker un HSM. |
| `v5.0.0-11.7.1`, `12.1.5`, `8.4.2` | Chiffrement mémoire, ECH et posture device non prouvés. | Ces lignes restent non vérifiées ; une revue source ne démontre pas une propriété matérielle ou réseau. |

Les détails de chaque autre contrôle, y compris les N/A OAuth/OIDC, WebRTC, LDAP,
XML, SVG upload et multi-tenant, figurent dans le CSV. L'absence de JWT ne rend pas
V9 entièrement N/A : le cookie Flask signé reste qualifié. L'authentification
URCA/RemoteLabz est hors du produit, sans être utilisée pour satisfaire ses propres
contrôles de MFA, session ou récupération.

## Preuves encore nécessaires avant conclusion

- Relier les contrôles applicatifs au candidat final : contrats REST des deux
  moteurs réels, accès croisés, champs techniques, import et parcours web.
- Éprouver les défaillances réseau, commit inconnu, révocation concurrente,
  contentions et limites de ressources au périmètre revendiqué.
- Constater la configuration effective du staging et des images livrées : réseau,
  certificats, cookies, headers, permissions, secrets et fichiers exposés.
- Restaurer les backups isolément, vérifier leur confidentialité/intégrité et
  tester migration/rollback après de nouvelles écritures Mongo.
- Actualiser chaque statut avec preuve et limite ; la qualification documentaire
  ne ferme ni le mandat global ni la revue indépendante finale.

Descriptions des exigences : OWASP et contributeurs ASVS, [ASVS5.0.0 officiel](https://github.com/OWASP/ASVS/tree/v5.0.0),
[CC BY-SA4.0](https://creativecommons.org/licenses/by-sa/4.0/). Cette qualification
de la grille dérivée suit la même licence ; le logiciel CineVault reste sous sa
licence propre et aucun aval OWASP n'est suggéré.
