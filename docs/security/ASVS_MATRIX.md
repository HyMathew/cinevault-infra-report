# Matrice ASVS 5.0.0 — état de vérification CineVault

État au 26 novembre 2026. L'applicabilité des **345 contrôles** a été examinée
par revue documentaire et du code. Les contrôles de bout en bout du candidat
Enterprise 2.1 restent en cours. Les preuves locales, natives et CI sont datées
et rattachées au code mesuré. Le déploiement stable v1 possède ses propres preuves.

## Source et inventaire complet

Référence : [OWASP ASVS 5.0.0, JSON officiel au tag v5.0.0](https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.json).
Blob Git lu : `16a314527781b79f2e499ac8f1e33eaf76234d22` ; SHA-256 des octets
UTF-8 conservés : `bcdbec214d70abcfad9284a31d4f9e5134305831d628aad3aa85d7e26626cb35`.
La version du document a été vérifiée, sans substituer la branche master.

L’[inventaire CSV complet](asvs-v5.0.0-applicability.csv) conserve les **345 contrôles**
et leur texte officiel anglais : 70 de niveau 1, 183 de niveau 2 et 92 de niveau 3.
Il fournit un état, une justification, une preuve disponible et la vérification
restante par identifiant versionné. Il ne supprime pas les exigences difficiles.

La grille contient **236 contrôles applicables**, dont 179 partiels,
30 non vérifiés et 27 non satisfaits, et **109 conditionnellement non applicables**
à l'architecture actuelle. Chaque ligne comporte une justification et une
vérification restante. Aucun contrôle n'est déclaré pleinement satisfait et aucun
pourcentage de conformité n'est calculé. La qualification d'applicabilité n'est
pas une preuve d'exécution de 345 tests.

Les descriptions officielles proviennent d’OWASP et des contributeurs ASVS, sous
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Le CSV reprend ces
descriptions sans modification et ajoute les colonnes de qualification CineVault ;
cette grille dérivée est diffusée sous la même licence. La licence MIT du logiciel
CineVault reste distincte. Aucun aval ou certification OWASP n’est suggéré.

## Profil et frontières

Le socle à vérifier est L1. Les exigences L2 et L3 sont évaluées comme compléments,
avec leur niveau d'origine conservé dans chaque ligne : `SOCLE_L1`,
`COMPLEMENT_L2_EVALUE` ou `COMPLEMENT_L3_EVALUE`. Ces libellés ne font pas de toutes
les fonctions L3 un engagement produit : une absence de HSM, de notification
indépendante ou d'analyse de posture device reste un écart visible de ce niveau,
sans prétendre que ces fonctions ont été demandées. Les décisions de profil et
risques acceptés doivent être motivés avant la livraison ; aucun écart n'est clos
par le seul changement de profil.

Périmètre applicatif : Flask/Jinja web, REST API, deux profils exclusifs JSON et
MongoDB, imports/exports, métadonnées externes et exploitation des trois VM. URCA,
RemoteLabz, leur SSO et leurs consoles ne sont pas des composants d’authentification
CineVault. OAuth/OIDC, GraphQL, WebSocket, WebRTC et certains facteurs inexistants
sont donc conditionnellement N/A, avec réouverture obligatoire si la fonction est
ajoutée. **L’absence de MFA n’exempte pas V6.3.3**, qui est explicitement non
satisfait. Le cookie Flask signé pour CSRF/messages reste à examiner sous V9 même
si le bearer API est opaque et qu’aucun JWT n’est utilisé.

Une limite d’environnement ne suffit pas à marquer un contrôle satisfait. En
particulier, HTTP du laboratoire, cookie non préfixé et absence de journal
d’authentification restent des écarts, pas des N/A. Le staging HTTPS, la rotation,
les contrôles de reprise en staging et le chemin Mongo déployé doivent encore être éprouvés.

## Repères de preuve

- API candidat [72b7624](https://github.com/HyMathew/cinevault-api/tree/72b7624101eb25bda4387726b9825c3bc596205c) :
  fichiers suivis de `app/`, contrats, schémas et tests lus dans cette révision,
  y compris UoW, repositories et maintenance Mongo. Les routes HTTP métier restent
  JSON ; le refactoring d'authentification en cours n'est pas utilisé comme preuve.
- Web : [c3dbc9e](https://github.com/HyMathew/cinevault-web/tree/c3dbc9e2b4db1e494c2f3317be43e074a5d1b22b),
  contrôles CSRF, cookies, client HTTP, formulaires, templates et navigation.
- Complément ciblé web [7166549](https://github.com/HyMathew/cinevault-web/tree/7166549f932ea608a8b1a272931d504ad209cc05) :
  validation commune de la clé de session courante et de chaque ancienne clé
  `SECRET_KEY_FALLBACKS`, au moins 32 octets UTF-8/bruts, sans transformation des
  clés valides. Reçu local isolé relu : 428 tests réussis dont 52 spécifiques ;
  [CI43071643085 réussie](https://github.com/HyMathew/cinevault-web/actions/runs/43071643085)
  au SHA exact. Les trois lignes `11.2.3`, `11.5.1` et `13.3.1` intègrent cette
  preuve et restent PARTIEL ; aucune conclusion sur v1 déployée n'en découle.
- Infra : [d2a29c0](https://github.com/HyMathew/cinevault-infra-report/tree/d2a29c083affffffb2e3f33a06205b85f1314240),
  stack, Compose, contrats d'exploitation et études. Les mentions datées de v1
  ne sont pas présentées comme une observation de v2 déployée.
- [Étude Mongo exécutée](../quality/MONGODB_ENGINE_STUDY.md) et
  [plan de persistance](../quality/MONGODB_IMPLEMENTATION_PLAN.md) :
  vrai moteur/driver et transactions élémentaires éprouvés ; ne pas les assimiler
  aux endpoints REST, à la migration ou au déploiement.
- Scan source v1 scellé : quatre constats de sévérité moyenne, dont le budget de
  réauthentification corrigé sur la branche candidate. Les constats de capacité
  restent une référence de travail ; l’introduction de MongoDB n’est pas leur
  résolution automatique.
- Services stables : v1 préservée. Un contrôle marqué partiel dans le candidat
  n’est pas déclaré corrigé sur le service actuellement exposé.

### Campagnes du 20 et 21 novembre 2026

- La migration `a500e24` a exercé 39 échanges HTTP et neuf étapes, dont le retour
  à JSON après de nouvelles écritures sur Mongo. Ce même code a été testé en
  transfert de catalogue lors de 21 échanges HTTP. La campagne de lecture
  `c270d94` a travaillé sur 393 documents restaurés avec un fournisseur de
  métadonnées simulé. [Migration et opérations sur les comptes](https://github.com/HyMathew/cinevault-api/blob/c1e150927b24fb9e0f22441272f5a701e81eda04/docs/evidence/mongodb-p5-operator-native-20261120.json) ·
  [Transfert de catalogue](https://github.com/HyMathew/cinevault-api/blob/1ac6adeb638a260783ba78fcacbdb46db11ee471/docs/evidence/catalogue-transfer-native-20261121.json) ·
  [Services de lecture](https://github.com/HyMathew/cinevault-api/blob/c1e150927b24fb9e0f22441272f5a701e81eda04/docs/evidence/read-services-native-20261120.json).
- `12.3.1` et `12.3.4` passent à `PARTIEL`. L'API `a500e24` a négocié TLS 1.3
  avec MongoDB en isolation. La readiness HTTP a renvoyé 200 avec CA, SAN et
  authentification valides, et 503 si l'un de ces paramètres était invalide.
  La validation des certificats sur Swarm et du HTTPS navigateur reste ouverte.
  [Reçu TLS natif](https://github.com/HyMathew/cinevault-api/blob/1ac6adeb638a260783ba78fcacbdb46db11ee471/docs/evidence/mongodb-tls-native-20261121.json).
- La rotation et la vérification de l'archive chiffrée ont été éprouvées sur
  Linux et Windows. Le lot opérationnel reste ouvert pour les identités et les
  secrets applicatifs du déploiement final.
  [Reçu de sauvegarde et rotation](../../evidence/public/mongodb-portable-backup-ci-rotation-20261120.json).
- Le renouvellement du certificat et de la clé HTTPS sous une CA
  constante, puis leur retour arrière, ont été observés depuis Windows
  via SSH sur un proxy Swarm temporaire. Le contrôle `13.3.4` reste
  partiel pour le cycle de vie des autres secrets et du déploiement
  final.
  [Reçu de rotation TLS](../../evidence/public/swarm-https-certificate-rotation-20261126.json).
- La reprise `f1515dd` a publié la quarantaine dans une nouvelle base à partir
  d'une archive chiffrée restaurée. Elle a désactivé quatre comptes et révoqué
  six sessions. Le nouveau compte a obtenu 200 en HTTP. Un ancien mot de passe
  et un jeton restauré ont obtenu 401.
  [Reçu de reprise MongoDB](https://github.com/HyMathew/cinevault-api/blob/4dd5cd99287fafdc647dead5ce32dbd42a5c457c/docs/evidence/mongodb-quarantine-native-20261121.json).
- Les journaux structurés de l'API `22bcecd` et du Web `70fa78e` ont corrélé un
  échange HTTP réel en loopback avec un identifiant généré par chaque service.
  La campagne de performance distincte a mesuré 736 réponses HTTP sur les deux
  moteurs. La collecte durable, les événements exhaustifs et les mesures sur le
  réseau de déploiement restent à vérifier.
  [Reçu de performance et observabilité](../../evidence/public/mongodb-performance-observability-20261121.json).

Dans le CSV, `API@72b7624`, `Web@c3dbc9e`, `Web@7166549` et `Infra@d2a29c0`
désignent ces révisions exactes. Les chemins/fonctions sont les preuves de source inspectées ;
les chemins de test désignent un test pertinent, **pas une nouvelle exécution**
de ce test pendant cette qualification. Les références SHA-1 des campagnes
indiquent le code testé, et les liens ci-dessus identifient les reçus publiés
après exécution. Les constats nécessitant d'autres preuves restent non vérifiés
ou partiels.
Les [écarts et prochaines preuves](ASVS_FINDINGS.md) regroupent le travail concret.

## Premier ensemble de contrôles et écarts actuels

`PARTIEL` : élément vérifié ou testé, mais preuve encore insuffisante pour
l’ensemble du contrôle et du candidat final. `NON_SATISFAIT` : contradiction
concrète constatée. `NON_VERIFIE` : preuve absente ou trop faible. Les détails
de source et la prochaine vérification figurent dans le CSV.

Le tableau ci-dessous conserve les 44 contrôles commentés initialement. Les
301 autres lignes qualifiées et leurs justifications sont dans le CSV complet ;
ce tableau n'est pas la totalité du périmètre.

| Identifiant ASVS | Niveau source | État | Qualification et travail restant |
| --- | --- | --- | --- |
| `v5.0.0-1.2.1` | 1 | PARTIEL | Échappement contextuel Jinja, jamais de HTML utilisateur de confiance. Revalider les rendus après redesign, y compris attributs, URLs et erreurs. |
| `v5.0.0-1.2.4` | 1 | PARTIEL | Sélecteurs UUID typés et requêtes Mongo fixes ; opérateurs reçus comme objets refusés. Tester les vrais endpoints Mongo et le futur filtre de recherche ; aucun filtre arbitraire fourni par HTTP. |
| `v5.0.0-1.2.10` | 3 | PARTIEL | Export CSV éprouvé par HTTP dans la campagne native de transfert. Les protections de cellules existent dans le sérialiseur. Rejouer les cas formule/NUL/tabulation sur les deux moteurs et vérifier le téléchargement web. |
| `v5.0.0-2.1.1` | 1 | PARTIEL | Le modèle BSON et les formes JSON ont été comparés lors d’une migration aller-retour avec nouvelles écritures. Les vues de lecture ont été comparées sur un instantané restauré. Vérifier tous les modèles auxiliaires, les bornes et la correspondance aux contrats de la révision finale. |
| `v5.0.0-2.2.1` | 1 | PARTIEL | Le transfert Mongo natif a vérifié le refus atomique d’un conflit de métadonnées. Les services de lecture ont vérifié quatre refus de validation. Rejouer les refus aux frontières de tous les endpoints et des formulaires sur le couple final avec les deux moteurs. |
| `v5.0.0-2.3.1` | 1 | PARTIEL | P5 a validé des parcours HTTP avec prêt approuvé et réservation après migration vers Mongo, puis leur export et relecture dans JSON. Tester la course HTTP sur la dernière copie, les étapes FIFO et toutes les transitions au candidat final. |
| `v5.0.0-2.3.3` | 2 | PARTIEL | Le transfert Mongo a préservé la révision après refus d'un lot conflictuel. P5 a vérifié transaction de migration, rejeu, nouvelles écritures et retour JSON. Vérifier les défaillances réseau et la reprise opérationnelle du couple final déployable, ainsi que les autres flux transactionnels. |
| `v5.0.0-2.4.1` | 2 | PARTIEL | Budgets login/réauth avant Argon2 et contrôle d’admission ; défauts de capacité v1 connus. Partager budgets/admission Mongo, résoudre la capacité par acteur et mesurer contention. |
| `v5.0.0-3.3.1` | 1 | NON_SATISFAIT | Secure est configurable ; noms actuels session/cinevault_auth sans préfixe requis, service stable HTTP. Déployer HTTPS et cookies préfixés adaptés avec migration/test des deux cookies. |
| `v5.0.0-3.3.2` | 2 | PARTIEL | SameSite=Lax configuré pour session et bearer cookie. Vérifier les parcours cross-origin et la configuration déployée après reverse proxy. |
| `v5.0.0-3.3.3` | 2 | NON_SATISFAIT | Les cookies actuels ne portent pas le préfixe __Host-. Définir le périmètre host-only HTTPS et vérifier migration/logout/path/domain. |
| `v5.0.0-3.3.4` | 2 | PARTIEL | HttpOnly configuré ; le bearer n’est pas retourné au JavaScript de présentation. Constater Set-Cookie sur le candidat déployé et les parcours logout/erreur. |
| `v5.0.0-3.4.1` | 1 | PARTIEL | Le HTTPS privé émet HSTS avec une durée d’essai de 300 s. Chromium applique la règle. La durée minimale d’un an et la couverture du déploiement final restent à vérifier. |
| `v5.0.0-3.4.3` | 2 | PARTIEL | CSP self, object-src none, base-uri none, frame-ancestors none et médias Wikimedia bornés. Vérifier toutes réponses et ressources du redesign ; justifier chaque origine permise. |
| `v5.0.0-3.4.4` | 2 | PARTIEL | X-Content-Type-Options nosniff sur les réponses Flask web. Vérifier erreurs, fichiers statiques et reverse proxy ; ne pas extrapoler au serveur externe. |
| `v5.0.0-3.4.5` | 2 | PARTIEL | Referrer-Policy same-origin. Contrôler fuite des URLs/paramètres et liens externes dans le navigateur. |
| `v5.0.0-3.4.6` | 2 | PARTIEL | frame-ancestors none remplace la confiance dans X-Frame-Options. Test des réponses HTML, erreurs et en-têtes réellement déployés. |
| `v5.0.0-3.5.1` | 1 | PARTIEL | CSRF synchronisé via cookie signé/session et champ de formulaire, contrôlé côté web. Rejouer tous POST/retours d’erreur, origine étrangère et déploiement HTTPS. |
| `v5.0.0-4.1.1` | 1 | PARTIEL | API JSON et formulaires UTF-8 ; erreurs et réponses amont mal formées contrôlées. Vérifier Content-Type sur tous exports, erreurs, statiques et proxy. |
| `v5.0.0-4.1.3` | 2 | PARTIEL | Contexte client BFF signé HMAC ; un en-tête utilisateur arbitraire n’est pas une identité. Vérifier confiance proxy, configuration clefs, usurpation et chemin Mongo après refactoring. |
| `v5.0.0-5.2.1` | 1 | PARTIEL | L’import JSON/CSV applique des bornes de formulaire et de traitement. La campagne native confirme le refus d’un lot conflictuel sans mutation partielle. Mesurer consommation, cas malformés et limites sur les deux moteurs sans perte partielle. |
| `v5.0.0-6.2.1` | 1 | PARTIEL | Mots de passe applicatifs de 12 à 256 caractères, borne UTF-8 ; minimum supérieur à 8. Revalider politique commune et migration des hashes ; ne pas appliquer à tort cette politique au compte Ubuntu du TP. |
| `v5.0.0-6.2.5` | 1 | PARTIEL | Aucune règle de composition par catégorie de caractère ; Unicode accepté dans les bornes. Vérifier formulaires, espaces, collage et nouvelle couche comptes ; aucune normalisation silencieuse. |
| `v5.0.0-6.3.1` | 1 | PARTIEL | Réauth 5 échecs/900s partagée entre sessions ; recul d’horloge conserve les fenêtres futures. Correctif candidat non déployé sur v1 ; mécanisme Mongo et contrôles distribués à intégrer. |
| `v5.0.0-6.3.3` | 2 | NON_SATISFAIT | Authentification applicative par mot de passe seul, pas de MFA ni combinaison de facteurs. Exigence L2 non satisfaite ; décider et documenter le profil/mesures compensatoires, sans classer simplement N/A. |
| `v5.0.0-7.2.1` | 1 | PARTIEL | L’API vérifie la session et le compte ; le frontend ne fait pas autorité sur le rôle. Relecture dans la même UoW Mongo pour chaque opération protégée et test révocation/course. |
| `v5.0.0-7.2.3` | 1 | PARTIEL | Bearer généré par secrets.token_urlsafe(32), empreinte seule persistée. Revalider durée de vie, unicité, chiffrement du transport et absence dans logs/backups publics. |
| `v5.0.0-7.4.1` | 1 | PARTIEL | Le reset natif Mongo révoque les sessions du compte ciblé dans la transaction et préserve celles d'un autre compte. Logout et désactivation restent couverts par les tests applicatifs. La reprise native a vidé six sessions restaurées et refusé un ancien jeton sur le candidat HTTP. Comparer tous les chemins de terminaison et les courses révocation/action sur le couple final. |
| `v5.0.0-7.5.1` | 2 | PARTIEL | Changement de mot de passe avec mot de passe courant et budget avant Argon2. Parcours réel et service Mongo, maintien des sessions/counters en erreur et sur panne. |
| `v5.0.0-8.2.1` | 1 | PARTIEL | Les opérations de transfert satisfont le rôle de gestion vérifié et refusent le membre dans le vrai backend HTTP Mongo. Les services de lecture ont testé d'autres portées. Rejouer les autorisations directes et la révocation en cours de requête sur chaque route du candidat. |
| `v5.0.0-8.2.2` | 1 | PARTIEL | La campagne de lecture sur l'instantané Mongo restauré a vérifié cinq refus de portée, des filtres propriétaire et des projections. Rejouer les portées via HTTP et navigateur, avant et après changement de rôle, sur le couple final. |
| `v5.0.0-8.3.1` | 1 | PARTIEL | Les décisions sont prises par les services communs. Les refus de portée et de rôle ont été observés dans les services natifs et le transfert HTTP. Vérifier la totalité des routes d'écriture, y compris la révocation et les appels directs sans interface web. |
| `v5.0.0-9.1.1` | 1 | PARTIEL | Cookie Flask signé pour CSRF/messages ; authentification API par référence opaque, sans JWT. Revue signature, paramètres et rotation de clé ; ne pas exclure le cookie signé du périmètre V9. |
| `v5.0.0-11.4.2` | 2 | PARTIEL | Argon2id actuel memory_cost65536/time_cost3/parallelism2. Mesurer coût sur VM et vérifier politique de rehash/rotation et préservation des hashes migrés. |
| `v5.0.0-11.5.1` | 2 | PARTIEL | Secrets et bearer via CSPRNG ; UUID publics ne servent pas de secrets. Web7166549 refuse désormais les clés courantes/fallback trop courtes sur toutes les sources ; 52 cas spécifiques et 428 tests réussis. La taille ne prouve pas l'entropie : provenance/génération de toutes clés et identités Mongo restent à vérifier. |
| `v5.0.0-12.2.1` | 1 | NON_SATISFAIT | Service web stable exposé en HTTP dans le laboratoire ; staging HTTPS non établi. Configurer puis éprouver HTTPS, confiance certificat et absence de repli en clair. |
| `v5.0.0-12.3.1` | 2 | PARTIEL | TLS 1.3, CA et SAN éprouvés pour API → Mongo en isolation. Vérifier le transport et les frontières effectives en staging. |
| `v5.0.0-13.2.1` | 2 | PARTIEL | Identités de maintenance, de restauration et d'application séparées avec droits testés. Le lien API → Mongo isolé a vérifié SCRAM sur TLS. Vérifier l'identité de chaque service réel, la rotation/expiration et les secrets statiques résiduels. |
| `v5.0.0-13.3.1` | 2 | PARTIEL | Secrets montés ou lus dans des fichiers dédiés. Clés de session Web courante et de secours validées. L'archive chiffrée a été restaurée et sa clé renouvelée sous Linux puis vérifiée sous Windows. Tester accès minimaux, génération, rotation, sauvegarde, restauration et destruction des secrets dans le déploiement final ; pas de conformité globale key-vault/HSM ni de validation de v1 annoncée. |
| `v5.0.0-15.3.1` | 1 | PARTIEL | Les vues publiques sont des projections de champs autorisés. C5 a vérifié des projections de lecture sur Mongo restauré et P5 a réellement exercé les profils HTTP. Vérifier les projections, erreurs et pièces de téléchargement par rôle et sur le couple final. |
| `v5.0.0-15.4.1` | 3 | PARTIEL | Transactions contrôlées et sept courses processus dans C4/P4. Mesures HTTP sur les deux moteurs à 120 et 600 films, sur hôte isolé. Vérifier la course HTTP sur la dernière copie, la FIFO sous charge et le service final sur plusieurs hôtes. |
| `v5.0.0-15.4.3` | 3 | PARTIEL | Les courses processus C4/P4 et mesures comparatives de 736 réponses HTTP complètent le runner transactionnel avec réessais bornés. Vérifier contentions et erreurs réseau à charge soutenue, latence Argon2, admission et 503 sans masquer les refus. |
| `v5.0.0-16.3.1` | 2 | NON_SATISFAIT | Audit métier existant ne journalise pas toutes les opérations d’authentification. Ajouter journal de sécurité structuré/rotation/rétention, sans mots de passe, bearer ni corps bruts. |
| `v5.0.0-16.5.1` | 2 | PARTIEL | Réponses 500 génériques et journaux expurgés dans les tests Flask. Les champs expurgés et la corrélation ont été vérifiés sur un vrai GET Web/API en loopback. Rejouer les erreurs du vrai backend/proxy et contrôler les journaux, pas seulement le corps HTTP. |

## Gates avant conclusion

Chaque contrôle retenu doit avoir une preuve liée au commit ou à l’image final,
un test adapté au risque et un constat de déploiement quand il le concerne. Les
filtres NoSQL, autorisations, prêts/FIFO, dernière identité admin, idempotence,
expiration et import seront comparés sur les deux moteurs réels. Les décisions
de profil ou exceptions seront motivées individuellement ; aucune ligne non
vérifiée ne deviendra verte par simple changement de niveau ou de libellé.
