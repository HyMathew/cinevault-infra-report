# Évaluation du portail documentaire

Évaluation prioritaire d'Astro Starlight le12novembre2026. La documentation Markdown
versionnée reste la source ; le portail doit ajouter navigation, recherche et accès
aux preuves, sans remplacer Flask/Jinja dans l'application.

## Choix et état de qualification

Starlight est retenu comme **candidat au prototype isolé**, grâce à ses pages
Markdown, navigation et recherche plein texte Pagefind intégrée. Ces capacités
proviennent des documentations officielles
[pages](https://starlight.astro.build/guides/pages/),
[configuration](https://starlight.astro.build/reference/configuration/) et
[recherche](https://starlight.astro.build/guides/site-search/).
Un site statique construit peut être servi sans processus Node sur les VM ; la
[documentation Astro de déploiement](https://docs.astro.build/en/guides/deploy/)
distingue ce mode des routes rendues à la demande.

Le registre npm officiel consulté donne
[@astrojs/starlight0.42.11](https://registry.npmjs.org/@astrojs%2fstarlight/0.42.11),
licence MIT, peer Astro^7.2.10 et markdown-remark^7.3.0 ;
[Astro7.4.11](https://registry.npmjs.org/astro/7.4.11), MIT, exige Node≥22.23.4.
Le poste possède Node24.19.0/npm11.17.0. Ces observations de métadonnées ne sont
ni un verrouillage de dépendances transitives, ni un audit de vulnérabilités ou
de toutes leurs licences. Aucun paquet de portail n'est installé par cette étude.

Conserver uniquement GitHub Markdown évite une nouvelle chaîne de build mais ne
fournit pas la même recherche documentaire structurée. Un site HTML écrit à la
main ajouterait une maintenance de navigation et recherche sans bénéfice démontré.
Le prototype Starlight doit donc prouver sa valeur avant intégration définitive.

## Contrat du prototype

Générer le contenu du portail depuis les fichiers suivis existants, avec manifeste
de sources ; ne pas maintenir deux copies éditoriales indépendantes. Les transformations
doivent ajouter le frontmatter requis, préserver le contenu et réécrire les liens
Markdown/diagrammes/preuves de façon déterministe. Refuser les collisions de routes,
liens hors dépôt, liens cassés et assets manquants. Les documents historiques doivent
garder leur date et leur statut ; une ancienne preuve v1 ne devient pas une preuve2.1.

Séparer démarrage, architecture/contrats, usage membre/gestion, administration,
sécurité/limites, qualité/preuves et parcours académique. La page d'accueil doit
indiquer l'état candidat et les exigences ouvertes. Garder accessibles les sources
brutes, licences tierces, diagrammes et PDF versionnés, sans publier d'artefact privé.

Le build exige un lock npm exact avec intégrités, revue des scripts d'installation,
licences et audit, télémétrie désactivée pour l'exécution projet, et CI avec droits
de lecture. Le rendu doit fonctionner sans données ni secrets du laboratoire.
Le déploiement documentaire ne doit donner aucun accès aux services ou bases métier.

La sélection définitive exige un build propre reproductible, contrôle des liens,
recherche sur contenu français, navigation mobile/clavier, rendu réel et zéro secret
dans le résultat. Une commande de build, un fichier de configuration ou cette étude
ne constituent pas un portail publié. Installation et publication restent ouvertes.
