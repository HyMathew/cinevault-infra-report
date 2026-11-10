# CineVault Enterprise 2.0 — audit de sélection des skills

Édition du 10 novembre 2026, à partir de la revue indépendante de livraison du 9 novembre, complétée par l'installation locale de trois adaptations documentaires. Les dépôts distants ont été examinés à des commits précis comme objets d'audit ; leurs instructions ne sont pas devenues des autorisations d'exécuter leurs scripts. L'intégration a relu les références audit/polish, le copywriting complet, PBT et le manifeste local des sources. Elle ne constitue pas une nouvelle vérification de la dernière version distante.

**Trois adaptations de méthode sont maintenant installées dans les worktrees projet**, avec licences et attributions, sans moteur, script, hook, installateur, configuration globale ou dépendance ajoutée. « Retenu », « installé », « appliqué » et « validé » désignent des étapes distinctes. L'installation a effectué un contrôle structurel et une application de lecture bornée décrits en fin de document ; elle ne réattribue aucun résultat antérieur à ces nouvelles entrées. Aucun moteur natif, score de design, résultat CodeRabbit, campagne Hypothesis ou mutation testing n'est revendiqué.

## Versions et licences examinées

| Origine | Pin exact retenu pour l'évaluation | Version déclarée / licence | Décision et état réel |
|---|---|---|---|
| [pbakaus/impeccable](https://github.com/pbakaus/impeccable/tree/035c8f319edd019936525a062fe99e83ca8d12c6) | `035c8f319edd019936525a062fe99e83ca8d12c6`, tag officiel `skill-v4.8.2` | 4.8.2 ; [Apache-2.0](https://github.com/pbakaus/impeccable/blob/035c8f319edd019936525a062fe99e83ca8d12c6/LICENSE) et notices tierces | Audit/polish adaptés installés dans web ; moteur natif non exécuté. |
| [miqdadbadjuber/anti-slop](https://github.com/miqdadbadjuber/anti-slop/tree/3b75daa1fb6bb4c2b8a3807f82eed50914dee6b2) | `3b75daa1fb6bb4c2b8a3807f82eed50914dee6b2` | Plugin Codex 3.2.27 ; [MIT](https://github.com/miqdadbadjuber/anti-slop/blob/3b75daa1fb6bb4c2b8a3807f82eed50914dee6b2/LICENSE) | Prose autonome adaptée installée dans infra ; core/code non copiés ; aucun CLI/settings/hook installé. |
| [obra/superpowers](https://github.com/obra/superpowers/tree/22f0b463e7a5e579904dd6211a520321035526f7) | `22f0b463e7a5e579904dd6211a520321035526f7` | Distant 7.0.2 ; [MIT](https://github.com/obra/superpowers/blob/22f0b463e7a5e579904dd6211a520321035526f7/LICENSE) | Sous-ensemble diagnostic/vérification retenu ; version 7.0.1 déjà disponible dans la session, sans réinstallation ni mise à jour. |
| [trailofbits/skills](https://github.com/trailofbits/skills/tree/e4dd0bb5b15535f7c5a0834187dffba6ac37e4ff) | `e4dd0bb5b15535f7c5a0834187dffba6ac37e4ff` | Licence racine [CC-BY-SA-4.0](https://github.com/trailofbits/skills/blob/e4dd0bb5b15535f7c5a0834187dffba6ac37e4ff/LICENSE), distincte de MIT CineVault | Adaptation documentaire PBT installée dans API avec licence séparée ; revue différentielle conditionnelle et collecte supply-chain différée. |
| [openai/plugins](https://github.com/openai/plugins/tree/d420d13051bffe4543ed39e30fa46b87148e47dd) | `d420d13051bffe4543ed39e30fa46b87148e47dd` | Collection sans licence uniforme établie à la racine ; licences par composant ci-dessous | Réutilisation des capacités disponibles pertinentes ; aucun import en bloc et aucune nouvelle installation. |

Ces cinq pins sont ceux de la sélection auditée, pas une promesse qu'ils représentent les branches courantes. Les trois adaptations installées réutilisent exactement ces archives épinglées ; les futures évolutions exigent une nouvelle revue du sous-ensemble et de sa licence.

## Impeccable : audit et polish adaptés à Flask/Jinja

Les références [audit](https://github.com/pbakaus/impeccable/blob/035c8f319edd019936525a062fe99e83ca8d12c6/.agents/skills/impeccable/reference/audit.md) et [polish](https://github.com/pbakaus/impeccable/blob/035c8f319edd019936525a062fe99e83ca8d12c6/.agents/skills/impeccable/reference/polish.md) apportent une grille utile pour hiérarchie, responsive, thèmes, accessibilité et finition. La [critique](https://github.com/pbakaus/impeccable/blob/035c8f319edd019936525a062fe99e83ca8d12c6/.agents/skills/impeccable/reference/critique.md) a été évaluée comme grille heuristique ; son workflow complet est différé. Ces règles HTML/CSS sont transposables à Jinja ; elles n'imposent ni React ni Tailwind.

Le HEAD observé pendant la revue était `500eeb7e655d1916c8d0880d05c8a80b5a8a86fb`, distinct du tag retenu. Les lanceurs téléchargent un moteur binaire absent, vérifient un SHA-256 contre un fichier de checksums puis utilisent un cache utilisateur ; un chemin fourni par `IMPECCABLE_BIN` constitue une autre surface d'exécution. Des hooks PostToolUse/Stop et un chargeur de contexte participent au workflow natif. Le wrapper Windows existe, mais son commentaire de test de parsing ne démontre pas une exécution sur une vraie machine Windows. Aucun de ces mécanismes n'a été lancé ici.

Deux anciennes références officielles ont aussi été examinées par le reviewer : `skill-v3.0.4` à `bf2bc55aa114841d6b8cb912ab3fc46c5104c1a9`, et `ext-v1.0.2` à `d154a5feb35c13d7c4d858d3c8a53a5b643aa38a` (manifest de skill 3.0.5). Elles demandent déjà chargeur Node et, pour la critique, `npx`, serveur/injection et agents ; elles ne constituent pas une solution entièrement Markdown.

Choix réalisé : adaptation attribuée des seules grilles audit/polish dans `cinevault-web/.agents/skills/impeccable-cinevault/`, avec licence Apache-2.0 et NOTICE.md conservées octet pour octet, modifications déclarées ; moteur, hooks, mises à jour automatiques et installation globale exclus. Aucun overlay, contexte moteur, score ou stockage de critique exécuté. Formulation de provenance : **« méthodologie Impeccable adaptée ; moteur natif non exécuté »**. L'application de lecture locale ne prouve aucun cycle polish après correction ni campagne d'accessibilité.

| Source retenue | SHA-256 inscrit et vérifié dans le manifeste local |
|---|---|
| audit.md | `5ba9e3a090fc4c4d212c8cbfa5a48f7454ceb10fa81a284b4a7b4e8351ece2f1` |
| polish.md | `81666fc7f783b4e3514db6554e713dc0479bd9cdedb06e93d15f8b579aae869a` |
| LICENSE | `02bb8c3b4e70190e3986c0404ad2fd8d639b4f534252d82379cc1b502b6d1812` |
| NOTICE.md, 503 octets | `c60a093c2845fd9fb82f9c6f742ece31f379f8190b535309d32d66c45ccffdcb` |

Gate futur : capture authentique avant changement, revue documentée, correctif, capture comparable et tests interactifs ; contraste et clavier réellement mesurés, sans score extrapolé de captures. Conserver les notices pertinentes ; la notice amont distingue également des références mobiles issues d'un travail MIT tiers, sans imposer de les copier pour CineVault.

## Anti-slop : rédaction projet, sans préférence globale

Le candidat [antislop-copywriting](https://github.com/miqdadbadjuber/anti-slop/blob/3b75daa1fb6bb4c2b8a3807f82eed50914dee6b2/skills/antislop-copywriting/SKILL.md) est retenu pour une adaptation de prose ; [antislop-code](https://github.com/miqdadbadjuber/anti-slop/blob/3b75daa1fb6bb4c2b8a3807f82eed50914dee6b2/skills/antislop-code/SKILL.md) n'est envisagé que pour commentaires. Le [core](https://github.com/miqdadbadjuber/anti-slop/blob/3b75daa1fb6bb4c2b8a3807f82eed50914dee6b2/antislop.md) peut rechercher une préférence globale, imposer un choix during/after, bloquer sur une question et modifier le routage d'AGENTS. Le CLI d'installation parcourt des portes globales/projet et peut remplacer plusieurs copies. Le lanceur de serveur de contraste n'est pas nécessaire à une passe éditoriale.

Ces effets ne sont pas retenus : aucun settings global lu ou créé, aucun hook ou installateur, aucun ajout silencieux à AGENTS. L'autorisation autonome de la mission prévaut sur les microconfirmations de confort. L'[adaptation prose installée](../../.agents/skills/anti-slop-cinevault/SKILL.md) conserve [attribution](../../.agents/skills/anti-slop-cinevault/ATTRIBUTION.md) et [licence MIT](../../.agents/skills/anti-slop-cinevault/LICENSE). Elle n'inclut ni core ni skill de code/commentaires. Les explications de sécurité/concurrence/pédagogie, acteurs inconnus, titres et citations sont préservés ; une interdiction mécanique de ponctuation ne remplace pas le jugement éditorial.

Gate futur : comparer faits, nombres, sources et limites avant/après ; ne pas modifier le comportement pendant une passe de commentaires ; préserver le PDF v1. Aucun témoignage, statistique, contribution ou provenance humaine ne peut être ajouté pour rendre un texte plus crédible. Une tournure stylistique n'établit jamais l'origine humaine ou automatisée d'un document.

## Superpowers : utiliser l'existant sans deuxième installation

Les candidats [systematic-debugging](https://github.com/obra/superpowers/blob/22f0b463e7a5e579904dd6211a520321035526f7/skills/systematic-debugging/SKILL.md) et [verification-before-completion](https://github.com/obra/superpowers/blob/22f0b463e7a5e579904dd6211a520321035526f7/skills/verification-before-completion/SKILL.md) sont compatibles avec Python/Jinja et PowerShell après adaptation des exemples shell. Le second, déjà fourni par la session en 7.0.1, guide la vérification documentaire de cette intégration ; aucune exécution de moteur tiers n'en découle.

Risques à contenir : hook Bash SessionStart, injection de règles globales, exigences de plan/worktree/approbation pouvant doubler le mandat existant, diagnostics affichant trop de contexte. Les règles spécifiques utilisateur et projet priment ; pas de questions déjà tranchées ni de red-green artificiel pour une retouche éditoriale. Décision : conserver la capacité disponible ; pas de copie projet d'une bibliothèque entière et pas de mise à jour vers 7.0.2 dans cette tâche.

Gate : diagnostic fondé sur erreur reproductible ; résultat final appuyé par commande récente et sortie inspectée ; aucune confiance exclusive dans un compte rendu d'agent.

## Trail of Bits : propriétés ciblées et licence séparée

[Property-based-testing](https://github.com/trailofbits/skills/blob/e4dd0bb5b15535f7c5a0834187dffba6ac37e4ff/plugins/property-based-testing/skills/property-based-testing/SKILL.md) est retenu pour les invariants réellement utiles : aller-retour des transferts/formulaires, atomicité du rejet, références, prêt actif unique et FIFO. Pytest/Hypothesis sont adaptés à Python/Windows ; Hypothesis n'a pas été installé ou exécuté dans cette intégration. Les échantillons déterministes du préaudit ne sont pas une campagne Hypothesis.

[Differential-review](https://github.com/trailofbits/skills/blob/e4dd0bb5b15535f7c5a0834187dffba6ac37e4ff/plugins/differential-review/skills/differential-review/SKILL.md) est conditionnel pour les changements sensibles v1→v2. Son intérêt doit rester distinct d'un scan du même diff ; tout agent adversarial ou rapport supplémentaire doit avoir un périmètre précis. Aucun de ces workflows n'a été exécuté par cette intégration.

Le troisième candidat, [supply-chain-risk-auditor](https://github.com/trailofbits/skills/tree/e4dd0bb5b15535f7c5a0834187dffba6ac37e4ff/plugins/supply-chain-risk-auditor), version 2.0.4, est différé : son collecteur peut appeler `gh auth token`, consulter plusieurs services et écrire cache/rapports. Les contrôles POSIX d'ownership du cache ne sont pas équivalents sous Windows. Aucun collecteur ni accès à une authentification n'a été lancé pour cet audit. Un essai futur demande un mode anonyme explicite, cache projet privé, réseau et écritures bornés.

La documentation tierce retenue est sous **CC-BY-SA-4.0**, séparément de la licence MIT du logiciel CineVault. L'adaptation est isolée dans `cinevault-api/.agents/skills/cinevault-properties/`, avec attribution, licence intégrale et modifications déclarées sur les textes adaptés. Aucun fichier logiciel ni sa licence MIT n'a été modifié. Les scripts, dépendances et fichiers particuliers devront être revérifiés avant toute inclusion ; aucun n'est fourni par cette entrée documentaire.

Gate futur : propriétés qui détectent des fautes réelles, graines/exemples reproductibles et tests de rejet ; aucune simple reformulation tautologique de l'implémentation, aucun score global déduit de trois mutants ciblés.

## OpenAI plugins : décisions par composant

Le dépôt racine est une collection d'exemples ; la revue observait `license:null` dans l'API GitHub à la racine. Cela ne vaut ni licence uniforme ni interdiction universelle : le contenu précis et son manifeste doivent être examinés séparément.

| Composant évalué | Version/licence observées au pin | Utilité, risques et décision |
|---|---|---|
| [build-web-apps / frontend-testing-debugging](https://github.com/openai/plugins/blob/d420d13051bffe4543ed39e30fa46b87148e47dd/plugins/build-web-apps/skills/frontend-testing-debugging/SKILL.md) | 0.1.2 ; MIT déclarée dans le manifeste | Retenu via disponibilité existante : rendu Jinja, navigateur, console, responsive et interactions. Browser prioritaire s'il fournit les capacités ; fallback Playwright motivé. Aucun React/shadcn/Stripe ajouté par association au catalogue. Aucun nouveau test navigateur exécuté par cette intégration. |
| [product-design / audit](https://github.com/openai/plugins/blob/d420d13051bffe4543ed39e30fa46b87148e47dd/plugins/product-design/skills/audit/SKILL.md) | Distant 0.1.52, session 0.1.56 ; **Proprietary** au manifeste distant | Retenu comme capacité disponible : capture avant avis et limites explicites. Ne pas copier ses sources sous MIT. Les scripts de contexte peuvent lire/écrire des préférences et d'autres parcours peuvent partager vers Figma/hosting : rester au scope local, sans publication implicite. L'avis UX indépendant repose sur huit images ouvertes, pas sur une conformité a11y certifiée. |
| [coderabbit / coderabbit-review](https://github.com/openai/plugins/blob/d420d13051bffe4543ed39e30fa46b87148e47dd/plugins/coderabbit/skills/coderabbit-review/SKILL.md) | 1.1.4 ; MIT déclarée dans le manifeste | Non retenu à ce stade : installation distante via pipeline shell, login et transfert de code vers service cloud ; compatibilité shell Windows/WSL et valeur comparative non établies. **CodeRabbit non exécuté** ; aucune revue locale n'est attribuée à ce service. |

Gate futur : utiliser le navigateur réellement disponible, conserver preuves et rôles/viewport ; vérifier le périmètre de partage avant tout service externe. Une licence de manifeste ne remplace pas l'examen des dépendances, actifs et conditions du service.

## Outils complémentaires : un contrôle par angle mort

Ces choix sont des propositions d'outillage, pas des installations ni des résultats. Leur version exacte devra être résolue, inspectée et épinglée au moment de l'intégration.

| Contrôle | Choix proposé | Limite et preuve attendue |
|---|---|---|
| SAST Python | CodeQL sur les deux applications publiques | Complète Ruff/pip-audit/Grype ; alertes qualifiées, permissions SARIF limitées. Semgrep général différé ; règles locales seulement si besoin distinct démontré. |
| GitHub Actions | zizmor | Complète les SHA et permissions déjà présents ; ne remplace pas la lecture des scripts de publication. |
| Mise à jour | Dependabot | PR bornées couvrant tous les verrous ; aucune fusion automatique ajoutée par défaut. |
| Inventaire et provenance | Syft, SBOM de l'archive réelle et attestation du digest publié | Ne pas ajouter un second scanner CVE sans gain ; même image scannée/publiée/attestée, vérification indépendante. |
| Gouvernance | OpenSSF Scorecard après protections et politique sécurité | Indicateurs applicables examinés individuellement ; aucun score garanti ni activité fictive. |
| Secrets et licences | Inventorier réglages effectifs, puis contrôle ciblé manquant | Absence de workflow ne prouve pas absence de protection serveur ; résultats expurgés, licences des dépendances/médias/textes séparées. |

## Installation locale et vérification du 10 novembre 2026

Les trois dossiers sont des instructions de projet autoportantes, pas des copies des plugins complets. Aucune configuration de découverte ou préférence globale n'a été changée ; leur présence dans `.agents/skills` ne prouve pas qu'une session déjà ouverte les a chargés automatiquement. Cette tâche les a lus explicitement pour les applications bornées ci-dessous.

| Dépôt / entrée installée | Fichiers présents | Portée de licence |
|---|---|---|
| web : `.agents/skills/impeccable-cinevault/` | SKILL.md, ATTRIBUTION.md, LICENSE, NOTICE.md | Adaptation Apache-2.0 ; notice amont conservée |
| infra : `.agents/skills/anti-slop-cinevault/` | SKILL.md, ATTRIBUTION.md, LICENSE | Adaptation et attribution MIT |
| API : `.agents/skills/cinevault-properties/` | SKILL.md, ATTRIBUTION.md, LICENSE | Textes adaptés CC-BY-SA-4.0 ; logiciel MIT inchangé |

Sources vérifiées par comparaison SHA-256 et taille avec `work/v2-audit/upstream-instructions/manifest.json` : huit entrées du manifeste, ainsi que NOTICE.md comparée séparément à son empreinte attendue. Le core anti-slop a été identifié et vérifié comme **exclu**, pas importé. La concordance locale ne vaut pas signature amont ni nouvelle récupération réseau ; les anciens marqueurs `expected_hash_verified: false` ne sont pas réécrits en preuve d'une vérification distante indépendante.

| Sources complémentaires | SHA-256 local vérifié |
|---|---|
| anti-slop-copywriting.md, 27 970 octets | `d708fc33608b4f1d41cc7bef8b5fb2aca3dc3fbc5ec1ee174b45cac23bb767cd` |
| anti-slop-LICENSE, 1 083 octets | `9fd83fb1fda52ca0094b96e2ed5a3d6c42a81b95a6c6326553f5bbe570f443de` |
| tob-properties.md, 4 306 octets | `9448cacb65c6237a7c22dc59602667177ecae405524079ae9ff92240590b995a` |
| tob-LICENSE, 20 131 octets | `7abe19ec9bb73b36141b999b861d24ad855e808bafe0f81e84cce28556f6c297` |

La première tentative du validateur skill-creator utilisait un Python dépourvu de PyYAML. Il a ensuite été réexécuté dans l’environnement qualité existant, où PyYAML était déjà disponible : **les trois entrées sont valides**. Aucun paquet supplémentaire n’a été installé pour ce contrôle. Les empreintes des trois licences, les dix fichiers présents, l’absence d’exécutable et les liens locaux ont aussi été vérifiés. Ces résultats ne constituent pas une validation du comportement futur des agents.

### Applications de lecture réellement effectuées

- **Impeccable adapté :** relecture de `app/templates/base.html` web et du design system. Le shell conserve les liens de parcours, le POST CSRF de déconnexion et le lien d'évitement ; aucun `aria-current` n'y est encore présent dans l'état lu. Le séparateur du design system à 1,90:1 est acceptable comme décor ; il ne doit pas devenir la seule bordure d'un contrôle. Le token control-border à 4,26:1 répond à cette distinction. Constat source et contre-exemple de faux positif, sans nouvelle campagne clavier/axe ni correction UI dans cette installation.
- **Anti-slop adapté :** l'introduction de ce registre disait « Aucun skill n'a été installé ». Elle a été révisée après constat des trois dossiers, en conservant la distinction sélection/installation/application et l'absence d'exécution moteur. Aucun ancien résultat d'audit n'est attribué rétroactivement aux nouvelles entrées ; pins, limites et acteurs inconnus restent préservés.
- **Propriétés adaptées :** lecture de `tests/test_transfer.py`, `tests/test_reservations.py`, `tests/test_loans.py` API et du contrat/formulaire web. Les tests existants couvrent notamment le refus atomique tout en ajoutant un événement d'audit, le roundtrip CSV avec acteur contenant une virgule, FIFO et le refus 412 sur version ancienne. La propriété « fichier entier inchangé sur refus » serait fausse à cause du journal ; la propriété retenue porte sur œuvres/exemplaires et absence de lot partiel. Une sérialisation Python seule ne traverse pas le formulaire HTML : la nouvelle entrée prescrit cette frontière réelle. Ces fichiers ont été lus, pas réexécutés par l'installation ; aucun test, générateur ou mutant nouveau n'a été créé.

Ces applications bornées valident la cohérence avec des constats existants, sans constituer des évaluations indépendantes sous pression. Les scénarios multi-agents baseline/avec-skill et répétitions statistiques de writing-skills n'ont pas été exécutés : la tâche interdit une nouvelle délégation et n'autorise pas d'appel API modèle additionnel. Ne pas prétendre à une conformité complète à ce protocole ou à un effet causal mesuré des méthodes. Les entrées restent à éprouver sur de prochaines tâches réelles autorisées.

## Bilan de sélection et prochaine preuve

Les cinq sources demandées ont une décision, un pin, un traitement de licence et des risques explicites. Trois adaptations documentaires locales sont installées ; superpowers et les outils navigateur déjà disponibles ne sont pas dupliqués. Aucun installateur, nouveau script, changement global, hook, collecteur authentifié ou service de revue cloud n'a été introduit. Aucun code applicatif, test, fichier AGENTS, commit, push ou déploiement n'a été réalisé par cette installation.

La présence et les licences des entrées sont vérifiables dans les worktrees ; leur application limitée est décrite ci-dessus. Prochaines preuves : utilisation sur un parcours UI réellement corrigé avec mesures et captures, nouvelle passe éditoriale avec diff factuel et propriétés exécutées via les commandes du projet lorsque leur implémentation est autorisée. Les textes propriétaires ne sont pas copiés ; aucun résultat moteur ni validation exhaustive n'est anticipé.
