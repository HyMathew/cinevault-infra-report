# Synthèse des validations au 9 novembre 2026, 10 h 40 Paris

Les liens GitHub ci-dessous donnent accès aux exécutions publiques. Les reçus d'administration, instantanés et données du laboratoire restent privés ; ils ont été contrôlés pendant l'exécution et ne sont pas reproduits dans ce dépôt. Cette synthèse documentaire ne constitue pas une nouvelle campagne.

## Révisions et CI réellement exécutées

| Projet | Source immuable | Exécution GitHub Actions | Tests Windows / Ubuntu |
|---|---|---|---|
| API | `6a86f2eba9de4dd704c7d4a38d93ab75ff32adc5` | [42536728355 — succès](https://github.com/HyMathew/cinevault-api/actions/runs/42536728355) | 173 / 173 |
| Web | `4883876f596e1e44218de762cad9a6ea6d1148c1` | [42536731570 — succès](https://github.com/HyMathew/cinevault-web/actions/runs/42536731570) | 85 / 85 |

Les journaux des quatre jobs de tests ont été lus. Les jobs qualité Windows/Ubuntu et les jobs construction, santé, scan et publication ont réussi. Dans ces exécutions de branche par défaut, le job d'image sans publication est intentionnellement ignoré : il est mutuellement exclusif du job qui publie après contrôle. Il ne manque donc pas un contrôle obligatoire. Ces résultats sont distincts des campagnes locales antérieures : 156/68 tests sur chaque plateforme et 171 contrôles HTTP Compose aux révisions API `4b15406` / web `9b1da4f`.

## Registre et provenance des images déployées

| Service | Référence utilisée par la stack |
|---|---|
| API | `ghcr.io/hymathew/cinevault-api@sha256:ca3effbd243062120078029f6ebcb9e5be1d142760913f52bb4187e3df355783` |
| Web | `ghcr.io/hymathew/cinevault-web@sha256:c258bd7aef02f0fb214f0e42f1ba440fea0c01490f7bc1a0694834aa3b556747` |

Les six téléchargements anonymes ont réussi : deux images sur chacun des trois nœuds, avec configuration Docker temporaire vide. Le SHA256 des corps bruts des manifestes publics égale leur digest annoncé. Leur `config.digest` correspond à l'ID d'image scanné dans la CI : API `sha256:a3a0fc3911ddff9f7ab631b921ee840ea658a652154c23582092320dea2b231d`, web `sha256:fcbf8d4f9102bb701d78c79c0e308482675caa11d8a719b4b91eacda14674be0`. Le moteur du laboratoire et celui de la CI affichent des identités de niveaux différents ; la comparaison passe par le manifeste et ses références, puis par les `RepoDigests` et les conteneurs effectifs.

Grype 0.121.2 : zéro High/Critical, cinq Medium et un Low par image. Les archives d'artefacts GitHub ont été téléchargées et leur SHA256 comparé aux métadonnées du service. Ce scan borné ne garantit pas l'absence de vulnérabilité. Une première CI avait échoué : l'archive Docker en mode 0600 n'était pas lisible par le scanner non privilégié sous Linux. La correction ne rend lisible que ce fichier temporaire, garde son dossier privé et le montage en lecture seule ; le scanner et son seuil ne sont pas affaiblis. La régression a été reproduite puis corrigée, avec succès des CI suivantes.

## Mise à jour distribuée observée

La campagne s'est terminée le **9 novembre 2026 à 09 h 40 UTC, soit 10 h 40 à Paris**, avec 22 contrôles réussis : trois nœuds Ready, manager dédié en Drain, tâches placées sur les deux workers prévus, images exactes, santé, UID 10001, racine en lecture seule et retrait des capacités. Une API unique conserve son volume local ; l'Overlay chiffré est maintenu.

Un instantané privé a précédé l'opération. Le digest métier et comptes est identique avant/après ; les champs opérationnels de sessions, compteurs d'authentification et révision sont exclus de cette comparaison. Les trois secrets Docker et le volume sont inchangés. Une session préexistante fonctionne après la mise à jour ; une nouvelle connexion signée et les pages publiques/privées ont également été contrôlées.

Les métadonnées externes sont désormais **activées**. Une recherche réelle « Metropolis » et l'aperçu Wikidata `Q151599` ont réussi via le web et l'API distante ; « Fritz Lang » et les conditions du média sont présents. Aucun film n'a été ajouté par cet aperçu. Ces essais sont distincts des tests de fournisseur simulé, et ne garantissent pas la disponibilité future de Wikimedia ni les droits de tout futur média.

## Limites encore ouvertes

Le redémarrage autonome depuis le disque des VM2/3 reste non validé. Un manager unique, une réplique API et un volume local ne constituent pas une haute disponibilité. La campagne ne démontre pas une restauration après panne de disque ou une bascule multi-hôte.

Le navigateur accède au laboratoire par HTTP loopback et tunnel SSH ; aucune terminaison HTTPS publique n'est annoncée. Les contrôles navigateur ciblés ne remplacent pas un audit exhaustif d'accessibilité ou de tous les parcours. La robustesse face à des réponses API structurellement invalides, les dernières preuves académiques, le rapport scientifique et l'audit final restent en cours.

Les modèles et matrices conservent leurs observations historiques datées. Les supports pédagogiques, données métier, secrets et journaux d'administration privés sont exclus des dépôts publics.
