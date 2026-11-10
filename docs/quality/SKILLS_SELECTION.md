# Sélection des compétences CineVault

État du 10 novembre 2026. Le mandat consolidé étend le catalogue initial à douze dépôts. Le [registre détaillé](SKILLS_AUDIT.md) conserve les cinq premières évaluations, pins, licences et risques. Les sept nouveaux candidats ne sont pas présentés comme audités ; leur décision finale reste à établir après lecture des instructions, scripts, licences et dépendances.

## Autorité principale par domaine

| Domaine | Méthode retenue | Limite |
| --- | --- | --- |
| Développement | Processus Superpowers déjà disponible | Pas de copie ni de hooks supplémentaires ; instructions du projet prioritaires |
| Audit UX/UI | Impeccable adapté | Conception et navigateur en complément ; moteur natif non exécuté |
| Prose | Anti-slop adapté | Faits et réserves conservés ; aucune origine humaine déduite du style |
| Sécurité | Revue source, validation indépendante et tests ciblés | Une méthode spécialisée doit répondre à une question distincte |
| Propriétés | Texte Trail of Bits adapté | Invariants et exemples déterministes ; aucune campagne Hypothesis revendiquée |
| Diagrammes et rapport | Sources versionnées et contrôle du rendu existants | Les nouveaux candidats restent à évaluer avant remplacement |

## Catalogue et décisions réelles

| Candidat | Statut | Version ou suite nécessaire |
| --- | --- | --- |
| [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | Adaptation installée | `035c8f319edd019936525a062fe99e83ca8d12c6`, Apache-2.0 ; audit/polish, licence et notice conservées |
| [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | Évaluation à réaliser | Design system, scripts, dépendances et chevauchements à examiner ; aucune installation |
| [miqdadbadjuber/anti-slop](https://github.com/miqdadbadjuber/anti-slop) | Adaptation installée | `3b75daa1fb6bb4c2b8a3807f82eed50914dee6b2`, MIT ; prose sans core, réglages globaux ni routage AGENTS |
| [obra/superpowers](https://github.com/obra/superpowers) | Existant réutilisé | Amont évalué `22f0b463e7a5e579904dd6211a520321035526f7` ; session7.0.1, MIT, pas réinstallé |
| [cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill) | Évaluation à réaliser | Portée Python/Flask, scripts et utilité distincte à vérifier ; aucune installation |
| [trailofbits/skills](https://github.com/trailofbits/skills) | Sélection partielle | `e4dd0bb5b15535f7c5a0834187dffba6ac37e4ff` ; adaptation PBT sous CC-BY-SA-4.0, collecteur différé |
| [JuliusBrussee/skills](https://github.com/JuliusBrussee/skills) | Évaluation à réaliser | Inventorier les entrées pertinentes, sans installation en bloc |
| [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) | Évaluation à réaliser | Vérifier conservation des chiffres, erreurs, preuves et limites ; aucun mode global appliqué |
| [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) | Évaluation à réaliser | Compatibilité Jinja, règles UI et conflits à vérifier ; aucune installation |
| [cathrynlavery/diagram-design](https://github.com/cathrynlavery/diagram-design) | Évaluation à réaliser | Licences, rendu et apport aux diagrammes existants à vérifier |
| [vercel-labs/agent-browser](https://github.com/vercel-labs/agent-browser) | Évaluation à réaliser | Exécutable, permissions, profils et duplication avec navigateur/Playwright à vérifier |
| [openai/plugins](https://github.com/openai/plugins) | Capacités pertinentes réutilisées | Évaluation `d420d13051bffe4543ed39e30fa46b87148e47dd` ; licences par composant, aucun import global ; CodeRabbit CLI non exécuté |

## Contrôles effectués

Trois adaptations existent dans les worktrees : web `.agents/skills/impeccable-cinevault`, infrastructure `.agents/skills/anti-slop-cinevault` et API `.agents/skills/cinevault-properties`. Les trois entrées ont passé le validateur skill-creator dans l’environnement qualité existant. Les empreintes des licences correspondent aux sources épinglées ; les liens locaux sont valides. Dix fichiers documentaires, aucun exécutable, installateur ou hook ont été constatés.

Ces vérifications établissent présence, structure et attribution. Elles ne valent ni évaluation indépendante sous pression ni résultat moteur. Aucun ancien audit n’est attribué rétroactivement à ces nouvelles entrées. L’étude des sept nouveaux candidats reste ouverte, sans empêcher les travaux indépendants sur MongoDB et le produit.
