# Matrice ASVS 5.0.0 — état de vérification CineVault

État du 11 novembre 2026. L'applicabilité des **345 contrôles est qualifiée** par
revue documentaire et du code ; leur vérification de bout en bout reste ouverte.
Cette matrice ne constitue ni une certification ni une revendication de niveau
ASVS atteint. Elle distingue le candidat
2.0, le backend Mongo encore en intégration et le déploiement stable v1. Les
réussites locales ou CI ne sont pas une preuve de déploiement.

## Source et inventaire complet

Référence : [OWASP ASVS 5.0.0, JSON officiel au tag v5.0.0](https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.json).
Blob Git lu : `16a314527781b79f2e499ac8f1e33eaf76234d22` ; SHA-256 des octets
UTF-8 conservés : `bcdbec214d70abcfad9284a31d4f9e5134305831d628aad3aa85d7e26626cb35`.
La version du document a été vérifiée, sans substituer la branche master.

L’[inventaire CSV complet](asvs-v5.0.0-applicability.csv) conserve les **345 contrôles**
et leur texte officiel anglais : 70 de niveau 1, 183 de niveau 2 et 92 de niveau 3.
Il fournit un état, une justification, une preuve disponible et la vérification
restante par identifiant versionné. Il ne supprime pas les exigences difficiles.

Qualification actuelle : **235 contrôles applicables**, dont 175 partiels,
31 non vérifiés et 29 non satisfaits ; **110 conditionnellement non applicables**
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
les sauvegardes restaurées et le chemin Mongo déployé doivent encore être éprouvés.

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

Dans le CSV, `API@72b7624`, `Web@c3dbc9e`, `Web@7166549` et `Infra@d2a29c0`
désignent ces révisions exactes. Les chemins/fonctions sont les preuves de source inspectées ;
les chemins de test désignent un test pertinent, **pas une nouvelle exécution**
de ce test pendant cette qualification. Les constats nécessitant du réseau, de
la charge, un matériel ou un déploiement restent non vérifiés ou partiels.
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
| `v5.0.0-1.2.10` | 3 | PARTIEL | Export CSV avec protection des cellules interprétables par un tableur. Rejouer les cas formule/NUL/tabulation sur les deux moteurs et vérifier le téléchargement web. |
| `v5.0.0-2.1.1` | 1 | PARTIEL | Formes JSON et contraintes métier versionnées ; modèle BSON dérivé. Compléter dictionnaire de données, modèles auxiliaires et règles de migration. |
| `v5.0.0-2.2.1` | 1 | PARTIEL | Validation positive des types, champs, bornes, Unicode et identifiants. Conserver ces refus après extraction des services et dans tous les endpoints Mongo. |
| `v5.0.0-2.3.1` | 1 | PARTIEL | Transitions prêt/réservation, rôles et versions déjà testés sur JSON. Contrats REST et courses réelles sur Mongo ; la primitive UoW ne prouve pas tout le workflow. |
| `v5.0.0-2.3.3` | 2 | PARTIEL | Verrou et remplacement JSON ; vrai runner Mongo commit/abort éprouvé. Transactions métier complètes, import atomique et migration restent à éprouver. |
| `v5.0.0-2.4.1` | 2 | PARTIEL | Budgets login/réauth avant Argon2 et contrôle d’admission ; défauts de capacité v1 connus. Partager budgets/admission Mongo, résoudre la capacité par acteur et mesurer contention. |
| `v5.0.0-3.3.1` | 1 | NON_SATISFAIT | Secure est configurable ; noms actuels session/cinevault_auth sans préfixe requis, service stable HTTP. Déployer HTTPS et cookies préfixés adaptés avec migration/test des deux cookies. |
| `v5.0.0-3.3.2` | 2 | PARTIEL | SameSite=Lax configuré pour session et bearer cookie. Vérifier les parcours cross-origin et la configuration déployée après reverse proxy. |
| `v5.0.0-3.3.3` | 2 | NON_SATISFAIT | Les cookies actuels ne portent pas le préfixe __Host-. Définir le périmètre host-only HTTPS et vérifier migration/logout/path/domain. |
| `v5.0.0-3.3.4` | 2 | PARTIEL | HttpOnly configuré ; le bearer n’est pas retourné au JavaScript de présentation. Constater Set-Cookie sur le candidat déployé et les parcours logout/erreur. |
| `v5.0.0-3.4.1` | 1 | NON_SATISFAIT | Aucun HSTS constaté dans la configuration actuelle, HTTP laboratoire stable. Ajouter la politique seulement avec HTTPS validé et traiter le périmètre des sous-domaines. |
| `v5.0.0-3.4.3` | 2 | PARTIEL | CSP self, object-src none, base-uri none, frame-ancestors none et médias Wikimedia bornés. Vérifier toutes réponses et ressources du redesign ; justifier chaque origine permise. |
| `v5.0.0-3.4.4` | 2 | PARTIEL | X-Content-Type-Options nosniff sur les réponses Flask web. Vérifier erreurs, fichiers statiques et reverse proxy ; ne pas extrapoler au serveur externe. |
| `v5.0.0-3.4.5` | 2 | PARTIEL | Referrer-Policy same-origin. Contrôler fuite des URLs/paramètres et liens externes dans le navigateur. |
| `v5.0.0-3.4.6` | 2 | PARTIEL | frame-ancestors none remplace la confiance dans X-Frame-Options. Test des réponses HTML, erreurs et en-têtes réellement déployés. |
| `v5.0.0-3.5.1` | 1 | PARTIEL | CSRF synchronisé via cookie signé/session et champ de formulaire, contrôlé côté web. Rejouer tous POST/retours d’erreur, origine étrangère et déploiement HTTPS. |
| `v5.0.0-4.1.1` | 1 | PARTIEL | API JSON et formulaires UTF-8 ; erreurs et réponses amont mal formées contrôlées. Vérifier Content-Type sur tous exports, erreurs, statiques et proxy. |
| `v5.0.0-4.1.3` | 2 | PARTIEL | Contexte client BFF signé HMAC ; un en-tête utilisateur arbitraire n’est pas une identité. Vérifier confiance proxy, configuration clefs, usurpation et chemin Mongo après refactoring. |
| `v5.0.0-5.2.1` | 1 | PARTIEL | Import JSON/CSV borné ; limites de formulaire spécifiques et limites métier. Mesurer consommation, cas malformés et limites sur les deux moteurs sans perte partielle. |
| `v5.0.0-6.2.1` | 1 | PARTIEL | Mots de passe applicatifs de 12 à 256 caractères, borne UTF-8 ; minimum supérieur à 8. Revalider politique commune et migration des hashes ; ne pas appliquer à tort cette politique au compte Ubuntu du TP. |
| `v5.0.0-6.2.5` | 1 | PARTIEL | Aucune règle de composition par catégorie de caractère ; Unicode accepté dans les bornes. Vérifier formulaires, espaces, collage et nouvelle couche comptes ; aucune normalisation silencieuse. |
| `v5.0.0-6.3.1` | 1 | PARTIEL | Réauth 5 échecs/900s partagée entre sessions ; recul d’horloge conserve les fenêtres futures. Correctif candidat non déployé sur v1 ; mécanisme Mongo et contrôles distribués à intégrer. |
| `v5.0.0-6.3.3` | 2 | NON_SATISFAIT | Authentification applicative par mot de passe seul, pas de MFA ni combinaison de facteurs. Exigence L2 non satisfaite ; décider et documenter le profil/mesures compensatoires, sans classer simplement N/A. |
| `v5.0.0-7.2.1` | 1 | PARTIEL | L’API vérifie la session et le compte ; le frontend ne fait pas autorité sur le rôle. Relecture dans la même UoW Mongo pour chaque opération protégée et test révocation/course. |
| `v5.0.0-7.2.3` | 1 | PARTIEL | Bearer généré par secrets.token_urlsafe(32), empreinte seule persistée. Revalider durée de vie, unicité, chiffrement du transport et absence dans logs/backups publics. |
| `v5.0.0-7.4.1` | 1 | PARTIEL | Logout/changement de mot de passe/désactivation invalident les sessions côté API. Tests comparatifs deux moteurs et course révocation/action après extraction des services. |
| `v5.0.0-7.5.1` | 2 | PARTIEL | Changement de mot de passe avec mot de passe courant et budget avant Argon2. Parcours réel et service Mongo, maintien des sessions/counters en erreur et sur panne. |
| `v5.0.0-8.2.1` | 1 | PARTIEL | RBAC côté API pour opérations de gestion, rôle actuel relu. Même décision dans services communs et endpoints Mongo, pas seulement menu masqué. |
| `v5.0.0-8.2.2` | 1 | PARTIEL | Listes privées bornées par propriétaire, sans exception administrateur. Filtres propriétaire dans Mongo avant pagination et tests d’accès croisé sur le vrai backend. |
| `v5.0.0-8.3.1` | 1 | PARTIEL | Les contrôles d’accès sont côté service API ; les contrôles web sont supplémentaires. Achever extraction services/UoW sans autorisation préchargée hors transaction. |
| `v5.0.0-9.1.1` | 1 | PARTIEL | Cookie Flask signé pour CSRF/messages ; authentification API par référence opaque, sans JWT. Revue signature, paramètres et rotation de clé ; ne pas exclure le cookie signé du périmètre V9. |
| `v5.0.0-11.4.2` | 2 | PARTIEL | Argon2id actuel memory_cost65536/time_cost3/parallelism2. Mesurer coût sur VM et vérifier politique de rehash/rotation et préservation des hashes migrés. |
| `v5.0.0-11.5.1` | 2 | PARTIEL | Secrets et bearer via CSPRNG ; UUID publics ne servent pas de secrets. Web7166549 refuse désormais les clés courantes/fallback trop courtes sur toutes les sources ; 52 cas spécifiques et 428 tests réussis. La taille ne prouve pas l'entropie : provenance/génération de toutes clés et identités Mongo restent à vérifier. |
| `v5.0.0-12.2.1` | 1 | NON_SATISFAIT | Service web stable exposé en HTTP dans le laboratoire ; staging HTTPS non établi. Configurer puis éprouver HTTPS, confiance certificat et absence de repli en clair. |
| `v5.0.0-12.3.1` | 2 | NON_VERIFIE | SSH contrôlé ; essais Mongo loopback sans réseau externe, pas une preuve du transport de déploiement. Vérifier API/backend/Mongo/proxy/observabilité et documenter toute exception de frontière locale. |
| `v5.0.0-13.2.1` | 2 | PARTIEL | Identités maintenance/application séparées et privilèges Mongo réduits démontrés en étude. Identités de déploiement, rotation/expiration et éventuelles exceptions aux secrets statiques à traiter. |
| `v5.0.0-13.3.1` | 2 | PARTIEL | Secrets hors Git ; secrets Swarm/fichiers dédiés, pas de valeurs dans les preuves publiques. Tester rotation, sauvegarde, permissions, restauration ; pas de conformité key-vault/HSM déclarée. |
| `v5.0.0-15.3.1` | 1 | PARTIEL | Profil public en liste de champs autorisés, hashes/bearer hors réponses de profil. Revalider projections, exports, erreurs et jointures de la future persistance Mongo. |
| `v5.0.0-15.4.1` | 3 | PARTIEL | Verrou fichier, scopes propriétaires et transactions coordonnées ; client Mongo non partagé après fork. Courses métier et charge sur les deux backends ; primitive seule insuffisante pour FIFO complet. |
| `v5.0.0-15.4.3` | 3 | PARTIEL | Verrou possédé par le stockage, garde d’imbrication et retries bornés. Éprouver contentions réelles, erreurs réseau et durée Argon2 ; ne pas masquer les 503 sous charge. |
| `v5.0.0-16.3.1` | 2 | NON_SATISFAIT | Audit métier existant ne journalise pas toutes les opérations d’authentification. Ajouter journal de sécurité structuré/rotation/rétention, sans mots de passe, bearer ni corps bruts. |
| `v5.0.0-16.5.1` | 2 | PARTIEL | Réponses génériques côté API/web ; détails driver assainis ; pas de répétition POST automatique. Rejouer les erreurs du vrai backend/proxy et contrôler les journaux, pas seulement le corps HTTP. |

## Gates avant conclusion

Chaque contrôle retenu doit avoir une preuve liée au commit ou à l’image final,
un test adapté au risque et un constat de déploiement quand il le concerne. Les
filtres NoSQL, autorisations, prêts/FIFO, dernière identité admin, idempotence,
expiration et import seront comparés sur les deux moteurs réels. Les décisions
de profil ou exceptions seront motivées individuellement ; aucune ligne non
vérifiée ne deviendra verte par simple changement de niveau ou de libellé.
