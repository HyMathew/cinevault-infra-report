# Synthèse des validations au 9 novembre 2026, 16 h 04 Paris

Les liens GitHub ci-dessous donnent accès aux exécutions publiques. Les reçus d'administration, instantanés et données du laboratoire restent privés ; ils ont été contrôlés pendant l'exécution et ne sont pas reproduits dans ce dépôt. Cette synthèse documentaire ne constitue pas une nouvelle campagne.

## Révisions et CI réellement exécutées

| Projet | Source immuable | Exécution GitHub Actions | Tests Windows / Ubuntu |
|---|---|---|---|
| API | `6a86f2eba9de4dd704c7d4a38d93ab75ff32adc5` | [42536728355 — succès](https://github.com/HyMathew/cinevault-api/actions/runs/42536728355) | 173 / 173 |
| Web | `f3d10cb0d5c9233c6427bd6503f3d2b841e99548` | [42640090796 — succès](https://github.com/HyMathew/cinevault-web/actions/runs/42640090796) | 159 / 159 |

Les journaux des quatre jobs de tests ont été lus. Les jobs qualité Windows/Ubuntu et les jobs construction, santé, scan et publication ont réussi. Dans ces exécutions de branche par défaut, le job d'image sans publication est intentionnellement ignoré : il est mutuellement exclusif du job qui publie après contrôle. Il ne manque donc pas un contrôle obligatoire. Ces résultats sont distincts des campagnes locales antérieures : 156/68 tests sur chaque plateforme et 171 contrôles HTTP Compose aux révisions API `4b15406` / web `9b1da4f`.

## Registre et provenance des images déployées

| Service | Référence utilisée par la stack |
|---|---|
| API | `ghcr.io/hymathew/cinevault-api@sha256:ca3effbd243062120078029f6ebcb9e5be1d142760913f52bb4187e3df355783` |
| Web | `ghcr.io/hymathew/cinevault-web@sha256:4d715bc72b7b18faff2ba9e5a7b8386adf99e96f5d2baea4b6cfe2a4d9a85bcf` |

Les six téléchargements anonymes ont réussi : deux images sur chacun des trois nœuds, avec configuration Docker temporaire vide. Le SHA256 des corps bruts des manifestes publics égale leur digest annoncé. Leur `config.digest` correspond à l'ID d'image scanné dans la CI : API `sha256:a3a0fc3911ddff9f7ab631b921ee840ea658a652154c23582092320dea2b231d`, web `sha256:403f2ad04c0227cfaf4fa1ca83b0f43e9ee2703a9ea53b29e4563319546ffaea`. Le moteur du laboratoire et celui de la CI affichent des identités de niveaux différents ; la comparaison passe par le manifeste et ses références, puis par les `RepoDigests` et les conteneurs effectifs.

Grype 0.121.2 : zéro High/Critical, cinq Medium et un Low par image. Les archives d'artefacts GitHub ont été téléchargées et leur SHA256 comparé aux métadonnées du service. Ce scan borné ne garantit pas l'absence de vulnérabilité. Une première CI avait échoué : l'archive Docker en mode 0600 n'était pas lisible par le scanner non privilégié sous Linux. La correction ne rend lisible que ce fichier temporaire, garde son dossier privé et le montage en lecture seule ; le scanner et son seuil ne sont pas affaiblis. La régression a été reproduite puis corrigée, avec succès des CI suivantes.

## Mise à jour distribuée observée

La campagne s'est terminée le **9 novembre 2026 à 15 h 04 UTC, soit 16 h 04 à Paris**, avec 25 contrôles réussis : trois nœuds Ready, manager dédié en Drain, tâches placées sur les deux workers prévus, images exactes, santé, UID 10001, racine en lecture seule et retrait des capacités. Le conteneur API est resté identique pendant la mise à jour du frontend ; son code de validation des réponses correspond par SHA256 au commit publié. Une API unique conserve son volume local ; l'Overlay chiffré est maintenu.

Un instantané privé a précédé l'opération. Le digest métier et comptes est identique avant/après ; les champs opérationnels de sessions, compteurs d'authentification et révision sont exclus de cette comparaison. Les trois secrets Docker et le volume sont inchangés. Une session préexistante fonctionne après la mise à jour ; une nouvelle connexion signée et les pages publiques/privées ont également été contrôlées.

Les métadonnées externes sont désormais **activées**. Une recherche réelle « Metropolis » et l'aperçu Wikidata `Q151599` ont réussi via le web et l'API distante ; « Fritz Lang » et les conditions du média sont présents. Aucun film n'a été ajouté par cet aperçu. Ces essais sont distincts des tests de fournisseur simulé, et ne garantissent pas la disponibilité future de Wikimedia ni les droits de tout futur média.

## Limites encore ouvertes

Le redémarrage autonome depuis le disque des VM2/3 reste non validé. Un manager unique, une réplique API et un volume local ne constituent pas une haute disponibilité. La campagne ne démontre pas une restauration après panne de disque ou une bascule multi-hôte.

Le navigateur accède au laboratoire par HTTP loopback et tunnel SSH ; aucune terminaison HTTPS publique n'est annoncée. Les contrôles navigateur ciblés ne remplacent pas un audit exhaustif d'accessibilité ou de tous les parcours. La frontière native JSON du frontend rejette désormais les formes consommées invalides, les chaînes non encodables en UTF-8 et les réponses204 inattendues en503 contrôlé. Les74 nouveaux cas de régression/compatibilité ont été reproduits avant et après correction ; les clients API injectés restent inchangés. Le contraste des placeholders est corrigé :3,56:1 avant,8,99:1 observé après rechargement du service courant. Le parcours Tab réel compte14positions ; recherche/état vide/retour ont été vérifiés à390/820px sans débordement, console sans erreur. Les [pièces navigateur](../evidence/browser-20261109/verification.json) précisent la portée ciblée. Les dernières étapes de publication et de clôture documentaire restent en cours.

Les modèles et matrices conservent leurs observations historiques datées. Les supports pédagogiques, données métier, secrets et journaux d'administration privés sont exclus des dépôts publics.
