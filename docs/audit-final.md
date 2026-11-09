# Audit technique indépendant de livraison

Arrêté du 9 novembre 2026. Cette revue confronte les 24 critères du mandat, les sources, les preuves datées et le PDF exact. Elle est indépendante de l'implémentation et de la compilation. Les corrections documentaires finales et leur publication restent à consolider par l'agent principal ; aucun tag infrastructure final n'est annoncé ici.

## Candidat et méthode

- API : `6a86f2eba9de4dd704c7d4a38d93ab75ff32adc5` ; web : `f3d10cb0d5c9233c6427bd6503f3d2b841e99548`. Les deux arbres applicatifs ont été constatés propres en lecture seule.
- Lot infrastructure examiné : `f756d512620e12cbee8a722febc10a8681366080`, puis CI réelle du commit `e0ee40767784faa7ee5a12ad4a0bc9a1fa5e97a6`. Le PDF commité est identique à celui inspecté.
- Revue de sources et reçus, comparaison d'empreintes, vérifications hors réseau, rendu dans un nouveau temporaire et inspection des **19 pages** du PDF. Aucune opération Git de mutation, VM, secret ou session brute consultée ; aucun nouveau scan de sécurité global.
- Les observations réseau et navigateur proviennent des campagnes nommées ci-dessous. La revue de leurs reçus ne prétend pas être une nouvelle exécution de ces opérations.

## Références de preuve

| Référence | Pièce et vérification | Portée |
|---|---|---|
| S | Reçu privé `swarm-frontend-contrast-deployment-v1/receipt.json`, complet, 25/25 contrôles ; fin à 15:04:36 UTC | Trois nœuds, placement, images, santé, identité non privilégiée, conservation des données/comptes/secrets et sessions. Empreintes du CSS et du validateur comparées aux sources courantes par le relecteur. |
| P | [Campagne pédagogique](pedagogical-validation.md), reçus Compose/nettoyage/SSH privés et six pièces publiques | Deux projets VSCode, SSH par clé, deux montages de code, données séparées et exercices A/B/C. API `6a86f2e` / web `4883876` ; distinct des évolutions frontend suivantes. |
| C | [Corpus et manifeste](examples/README.md) ; vérificateur et régressions exécutés indépendamment | PASS : 93 échanges, 44 opérations OpenAPI, 42 composants, 18 définitions, 51 emplacements HTTP et 5 schémas techniques ; 23 tests de corruption/compatibilité réussis. Handlers et lecteurs réels, mais données synthétiques et aucun réseau. |
| T | Suites applicatives et CI ; [synthèse des validations](validation-current.md) | Reproduction indépendante Windows : 173 tests API et 159 tests web réussis avant l'ajustement CSS. La CI du web `f3d10cb` couvre ce dernier candidat. Les suites isolées ne remplacent pas les échanges réels P/S. |
| B | [Preuves navigateur publiques](../evidence/browser-20261109/manifest.json), puis reçu privé `frontend-private-keyboard-v1/verification.json` | Catalogue : 14 positions Tab, état vide/retour, 390/820 px et contraste des placeholders corrigé. Collection : 13 positions Tab ; prêts : 11 ; filtres activés par Entrée, contrôles responsive et console vide, compte de démonstration synthétique. |
| M | [Acteurs](actors-use-cases.md), [dictionnaire](data-dictionary.md), [opérations REST](rest-operations.md), [diagrammes](diagrams/README.md), [décisions](decisions.md) et [identité visuelle](design-system.md) | Modélisation et justification confrontées au code ; les modèles statiques ne sont pas des captures réseau. |
| R | [CI documentaire 42644622299](https://github.com/HyMathew/cinevault-infra-report/actions/runs/42644622299), reçus Windows/Linux et archives téléchargées | CI réelle réussie sur Windows et Ubuntu pour `e0ee407`. Relecteur : CRC des deux ZIP et égalité des PDF vérifiés localement ; reçus Typst et empreintes lus. Les statuts distants ont été transmis par la campagne principale, sans nouvel appel réseau du relecteur. |
| Q | [PDF nommé](../report/RT0705_CineVault_Mathieu_Kuhnapfel.pdf), [source et compilation](../report/README.md), reçu privé de QA terminale | 19 pages : 17 A4 et 2 A2 ; toutes inspectées. 40 destinations internes valides ; 7 liens externes publics inspectés statiquement. |

Les campagnes historiques de 50 contrôles distribués, dont attribution concurrente et persistance après recréation API, restent datées et distinctes de S. Le [répertoire des preuves](../evidence/README.md) explique ce qui est publié et ce qui reste privé.

La capture privée `loans-focus.png` ne prouve pas le focus du bouton Filtrer : elle montre la navigation. La preuve clavier du filtrage repose sur la trace d'accessibilité et le DOM observé après les véritables Tab et l'activation Entrée. Les images de ce parcours ne sont utilisées que pour leur état visuel/responsive. Aucun focus programmatique n'est présenté comme preuve de reachabilité.

## PDF et reproductibilité vérifiés

Fichier : `RT0705_CineVault_Mathieu_Kuhnapfel.pdf`, **734 029 octets**.

```text
SHA-256 2668ea3a3a1d73004b5ecf1310e30a07ea1cd9ba1a9c4b80c897cb5ae9525885
```

Les PDF Windows et Ubuntu de R sont identiques octet pour octet à l'édition Q. Les deux archives ont un CRC valide. Le clone public neuf reproduit par l'agent principal au commit `f756d512` a également été contrôlé localement : son HEAD et son PDF donnent cette même empreinte. Cette égalité complète l'exécution réelle de la compilation ; elle ne remplace pas l'inspection visuelle.

Aucune coupe, superposition ou figure illisible bloquante n'a été relevée sur les 19 pages rendues. Les deux planches A2 sont vectorielles et zoomables. Les tableaux poursuivis sur la page suivante répètent leur en-tête ; les renvois vers les figures et les 40 destinations internes aboutissent à des pages présentes. Les liens HTTP n'ont pas été réinterrogés par cette revue hors réseau.

Le reçu détaillé privé `cinevault-terminal-pdf/verification.json` identifie l'empreinte, les 19 pages inspectées, les formats, liens, limites et comparaisons CI. Son emplacement de travail exact est transmis à l'agent principal pour conservation ; aucun chemin personnel n'est publié ici.

## Les 24 critères du mandat

`Vérifié borné` signifie acquis pour les révisions et campagnes citées, avec les limites indiquées. Ce statut ne promet ni couverture de toutes les branches ni absence générale de vulnérabilité.

| Nº | Critère du mandat §23 | État à cet audit | Preuve / portée |
|---:|---|---|---|
| 1 | Toutes les obligations du sujet traitées | Vérifié borné | 28 lignes académiques réconciliées ; P/C/M/S. Le montage et les exercices ne sont pas remplacés par Swarm. |
| 2 | Acteurs et responsabilités documentés | Vérifié | M : rôles, charges qualitatives, personas fictifs et UC01–UC14. |
| 3 | Données et formats JSON définis | Vérifié | Dictionnaire, schémas et corpus C validés ; invariants exécutables distingués de JSON Schema. |
| 4 | Modèles d'exécution et échanges décrits | Vérifié borné | Dix séquences, UML et familles de messages ; deux planches dans Q et sources vectorielles séparées. |
| 5 | Trois tiers fonctionnent | Vérifié borné | P démontre fichier/API/Jinja ; S et B documentent la stack courante. |
| 6 | Deux projets Git existent | Vérifié | Deux dépôts indépendants, HEAD et propreté constatés ; deux projets ouverts dans P. |
| 7 | VSCode/SSH démontrés | Vérifié borné | Captures distantes et preuve publickey expurgée distincte ; P. |
| 8 | Trois exercices Flask/Jinja validés séparément | Vérifié borné | P : page simple, POST réel avec résultat, égalité fichier/réponse API/rendu. |
| 9 | Volume partagé avec l'hôte démontré | Vérifié borné | Deux bind mounts inspectés, empreintes et témoins hôte/conteneur ; données dans volume distinct ; P. |
| 10 | API REST opérationnelle et testée | Vérifié borné | T et C couvrent les 44 opérations définies ; S confirme des échanges distants ciblés. |
| 11 | Frontend utilisant réellement l'API | Vérifié borné | Client natif, P/S/B ; pas un résultat déduit d'un client simulé. |
| 12 | Compose démarre les deux services | Vérifié borné | P : 16 contrôles et nettoyage ciblé, Swarm préservé. |
| 13 | Swarm sur plusieurs VM si faisable | Vérifié borné | S : trois Ready, manager Drain, workers placés, Overlay et digests. |
| 14 | Fonctions collaboratives testées | Vérifié borné | T/C, parcours distribués historiques et B privé courant ; pas de couverture de toutes les branches revendiquée. |
| 15 | Incohérences critiques empêchées | Vérifié borné | Tests de références, droits, transitions, concurrence et imports ; course historique avec une attribution acceptée et une refusée. |
| 16 | Données JSON persistantes | Vérifié borné | S conserve l'empreinte métier/comptes ; tests stockage et recréation API historique. Pas de preuve de reprise après perte de disque. |
| 17 | Contrôles de sécurité applicables fonctionnent | Vérifié dans les scénarios testés | T, S et reçus d'image : droits/sessions/CSRF, garde JSON, non-root/readonly/capacités retirées. Pas de certification globale. |
| 18 | Tests automatisés exécutés | Vérifié | T, C et R ; résultats récents distingués des campagnes historiques. |
| 19 | Preuves authentiques organisées | Vérifié, conservation finale à consolider | Index public, manifestes, reçus privés et Q. Aucun reçu privé complet ni support de cours redistribué. |
| 20 | GitHub publié après audit | Publication du candidat vérifiée ; dernier lot de clôture à publier | Sources et PDF du candidat accessibles par la campagne R ; présent audit et dernières matrices à intégrer. Aucun tag infrastructure final supposé. |
| 21 | PDF compilé et vérifié | Vérifié | Q : nom demandé, 19 pages, sources éditables, revue visuelle et liens ; R : compilation réelle Windows/Ubuntu et octets identiques. |
| 22 | Déploiement reproductible | Vérifié dans l'environnement compatible documenté | Procédures P/S, images par digest, clone neuf et compilation R/Q. Aucun build système bit-identique universel ou reprise multi-hôte promis. |
| 23 | Matrice de conformité à jour | Consolidation finale résiduelle | Les 28 exigences académiques sont réconciliées ; reporter R/Q/B privé et cet audit dans les derniers statuts d'extensions avant publication. |
| 24 | Audit indépendant final effectué | Effectué sur le candidat identifié | Présente revue, reçus et contrôles listés. La publication de ce compte rendu et la cohérence du dernier commit constituent le dernier bouclage documentaire. |

## Confidentialité du lot

Le lot `f756d512` a fait l'objet d'une revue ciblée : 92 fichiers modifiés, dont 76 textes UTF-8 ; figures, nouvelles captures publiques et PDF inspectés. Aucun en-tête de clé privée, forme usuelle de jeton d'accès recherchée, chemin personnel ou adresse RFC1918 n'a été trouvé. Le PDF commité égale celui examiné. Ce contrôle n'est pas une preuve mathématique d'absence de tout format possible de secret.

Les exemples sont explicitement fictifs ; mots de passe d'apprentissage, clés de démonstration et signatures historiques ne sont pas des accès du laboratoire. Les hashes publiés sont neutralisés, les tokens remplacés et les digests de session sans rapport avec le token publié ; les contrôles C vérifient ces propriétés. Les captures publiques ne montrent ni mot de passe ni session brute. Les données d'exploitation, clés, VPN, enveloppes et journaux VSCode bruts restent hors de la publication.

## Conclusion et réserves

Aucun défaut bloquant supplémentaire n'est établi dans le périmètre revu. Les écarts du précédent audit sur les exemples, l'inventaire, les modèles intégrés au PDF, le nom du rapport et sa reproduction ont reçu des réalisations et preuves correspondantes. Il reste à intégrer et publier ce compte rendu avec les dernières matrices, conserver les reçus de clôture et appliquer le tag infrastructure seulement lorsqu'il aura réellement été publié. Ce bouclage ne nécessite pas de relancer un cycle complet de scans ou de tests VM en l'absence de modification fonctionnelle.

Limites maintenues : boot autonome VM2/3 non démontré ; pas de terminaison HTTPS publique ; manager/API/volume uniques, sans HA ni bascule multi-hôte ; reprise après perte physique du disque non testée ; contrôles d'accessibilité ciblés, sans certification WCAG exhaustive, lecteur d'écran ou tous les états et navigateurs. Ces limites sont explicites et ne sont pas converties en réussites supposées.
