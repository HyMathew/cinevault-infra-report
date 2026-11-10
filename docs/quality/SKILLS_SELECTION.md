# Sélection des compétences CineVault

État du 10 novembre 2026. Les douze dépôts du mandat consolidé ont une décision de sélection. Le [registre initial](SKILLS_AUDIT.md) conserve sans remplacement les cinq premières évaluations. L'[audit complémentaire](SKILLS_ADDITIONAL_AUDIT.md) documente les sept autres sources à des commits précis, leurs licences, les fichiers réellement examinés et les limites de la lecture statique. Aucun nouveau skill ni moteur n'a été installé ou exécuté dans cette seconde évaluation.

## Autorité principale par domaine

| Domaine | Méthode retenue | Limite |
| --- | --- | --- |
| Développement | Processus Superpowers déjà disponible | Pas de copie ni de hooks supplémentaires ; instructions du projet prioritaires |
| Audit UX/UI | Impeccable adapté | Conception et navigateur en complément ; moteur natif non exécuté |
| Prose | Anti-slop adapté | Faits et réserves conservés ; aucune origine humaine déduite du style |
| Sécurité | Revue source, validation indépendante et tests ciblés | Une méthode spécialisée doit répondre à une question distincte |
| Propriétés | Texte Trail of Bits adapté | Invariants et exemples déterministes ; aucune campagne Hypothesis revendiquée |
| Diagrammes et rapport | Sources versionnées et contrôle du rendu existants ; grille sémantique diagram-design en référence secondaire | Aucun remplacement de D2/PlantUML, profil global ou moteur supplémentaire |
| Finition produit | Parcours utilisateur réel et critères observables ; questions last-20-percent en complément | Pas de deuxième orchestrateur ni de nouvelle fonctionnalité par effet de méthode |

## Catalogue et décisions réelles

| Candidat | Statut | Version ou suite nécessaire |
| --- | --- | --- |
| [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | Adaptation installée | `035c8f319edd019936525a062fe99e83ca8d12c6`, Apache-2.0 ; audit/polish, licence et notice conservées |
| [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | Référence secondaire conditionnelle | `6ae86f61f520d6ca229d2f40e070410638c908c5`, MIT ; catalogue de pistes seulement, sans régénérer le design system ni installer le CLI |
| [miqdadbadjuber/anti-slop](https://github.com/miqdadbadjuber/anti-slop) | Adaptation installée | `3b75daa1fb6bb4c2b8a3807f82eed50914dee6b2`, MIT ; prose sans core, réglages globaux ni routage AGENTS |
| [obra/superpowers](https://github.com/obra/superpowers) | Existant réutilisé | Amont évalué `22f0b463e7a5e579904dd6211a520321035526f7` ; session7.0.1, MIT, pas réinstallé |
| [cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill) | Méthode ciblée, harness non retenu | `c1c8a8c1471069fb0e188eeaff69b8e8db6564a8`, MIT ; ressources/cycle de vie en contre-grille ; pas de deuxième scan ni de garantie de cloisonnement OS inventée |
| [trailofbits/skills](https://github.com/trailofbits/skills) | Sélection partielle | `e4dd0bb5b15535f7c5a0834187dffba6ac37e4ff` ; adaptation PBT sous CC-BY-SA-4.0, collecteur différé |
| [JuliusBrussee/skills](https://github.com/JuliusBrussee/skills) | Sélection de méthode, pas de paquet installé | `8470b263d82579bd5b563b1e4e494472d3f0457f`, MIT ; last-20-percent pour parcours/états vides, sept autres entrées non activées |
| [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) | Non retenu | `3dc497a7f858c774d6e15b25e8c6120ef3a0eda8`, Apache-2.0 avec héritage MIT et notices tierces ; style persistant et suite runtime redondants |
| [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) | Pipeline natif non retenu | `f6b76575f949707b4e3c37cd86cb44b0b98643e8`, MIT ; contraintes de landing page et hooks incompatibles avec la direction de l'application |
| [cathrynlavery/diagram-design](https://github.com/cathrynlavery/diagram-design) | Méthode sémantique/offline retenue | `f2496acbde9f45ccb55c24d4f75210c8a1355df8`, MIT et actifs tiers distincts ; pas de copie, installation, export ou rendu nouveau |
| [vercel-labs/agent-browser](https://github.com/vercel-labs/agent-browser) | Installation non retenue | `e7519957b9067c541825afa21a792fbe1f483047`, Apache-2.0 et axe-core MPL-2.0 ; privilégier navigateur fourni et tests existants, sans nouvelle session persistante |
| [openai/plugins](https://github.com/openai/plugins) | Capacités pertinentes réutilisées | Évaluation `d420d13051bffe4543ed39e30fa46b87148e47dd` ; licences par composant, aucun import global ; CodeRabbit CLI non exécuté |

## Contrôles effectués

Trois adaptations existent dans les worktrees : web `.agents/skills/impeccable-cinevault`, infrastructure `.agents/skills/anti-slop-cinevault` et API `.agents/skills/cinevault-properties`. Les trois entrées ont passé le validateur skill-creator dans l’environnement qualité existant. Les empreintes des licences correspondent aux sources épinglées ; les liens locaux sont valides. Dix fichiers documentaires, aucun exécutable, installateur ou hook ont été constatés.

Ces vérifications établissent présence, structure et attribution des trois adaptations initiales. Elles ne valent ni évaluation indépendante sous pression ni résultat moteur. Aucun ancien audit n’est attribué rétroactivement à ces entrées. La seconde évaluation clôt la sélection documentaire des sept candidats : elle compare leurs instructions, scripts et effets d'installation au projet réel, sans benchmark, preuve de fonctionnement Windows ni mesure causale de qualité. Les décisions de méthode ne sont pas des installations. Aucun AGENTS, réglage global, hook ou code applicatif n'a été modifié.
