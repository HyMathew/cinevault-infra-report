# Évaluation du portail documentaire

Évaluation prioritaire d'Astro Starlight le12novembre2026. La documentation Markdown
versionnée reste la source ; le portail doit ajouter navigation, recherche et accès
aux preuves, sans remplacer Flask/Jinja dans l'application.

## Choix et état de qualification

Starlight a été retenu le12novembre comme **candidat au prototype isolé**, grâce à ses pages
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
de toutes leurs licences. L'étude initiale n'avait pas installé de paquet ;
le candidat public construit ensuite est décrit ci-dessous.

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
ne constituent pas un portail publié. La publication reste ouverte.

## Candidat public construit — 13 novembre 2026

Le [guide du portail](../../portal/README.md) fournit les commandes publiques de
construction, consultation, contrôle navigateur et génération de SBOM. Le
répertoire `portal` contient l'outillage, sans copie éditoriale concurrente : les
Markdown publics suivis restent les entrées. Les sorties générées sont ignorées.
Le workflow `documentation-portal.yml` prépare construction et contrôles sur
Ubuntu et Windows avec droits de lecture ; sa qualification CI est distincte des
exécutions locales ci-dessous et reste à rattacher au commit final du portail.

L'instantané de qualification locale initiale a construit 48 documents en
49 pages HTML, plus 63 ressources liées.
Les 4364 liens locaux et ancres vérifiés sont valides. Deux constructions
consécutives produisent les mêmes 340 noms de fichiers et octets sur le même
poste Windows/Node24.19.0 ; cela n'est pas une preuve entre plateformes ou entre
constructeurs indépendants. Le reçu distingue l'état des documents de celui de
l'outillage : des documents inchangés ne rendent pas un générateur modifié propre.

Les 25 tests Node initiaux passent. La correction d'un alias de chemin Windows,
reproduit en CI, ajoute ensuite deux témoins : 27 tests passent localement,
sans supprimer le refus des dépendances réellement liées. Ils couvrent aussi les sorties non possédées, parents
liés, HTML brut, ancres dupliquées, ponctuation, images dans les titres et liens
locaux avec paramètres. Les identifiants de titre sont collectés par le même
moteur Markdown verrouillé que celui du site. Le lock inclut
457 paquets résolus ; 357 étaient
installés sur ce Windows, dont axe-core4.11.0 uniquement pour les contrôles.
L'audit npm explicite du13novembre ne signale aucune vulnérabilité dans ce graphe.
Cela ne vaut pas absence générale de vulnérabilités. Le site conserve 141 textes
de licences disponibles et un catalogue qui distingue les paquets optionnels
absents ; ses dépendances n'ont pas toutes la licence MIT. Le SBOM npm contient
354 composants selon le périmètre de cet outil, distinct du graphe lock complet.

Le contrôle navigateur public a exécuté **180 vérifications**, avec Chrome
157.0.8103.51 et dix captures. Toutes les pages ont été visitées. Les essais à
320/390/768/840/1024/1280 pixels vérifient le rendu, la recherche française puis le clic
du résultat, Tab/Entrée/Échap, le menu mobile et le défilement clavier réel des
tableaux et blocs de code. Deux défauts observés ont été corrigés : le titre
tronqué sur mobile et les régions défilantes inaccessibles par Tab. Le contrôle
utilise le site statique réel, sans service applicatif ni données du laboratoire.

Les six états axe contrôlés n'ont aucune violation automatique. Deux gardent des
résultats `color-contrast` incomplets, sur la recherche et des exemples du
dictionnaire : ils demandent une appréciation humaine et ne sont pas convertis en
PASS. Les tests automatiques et captures ne certifient pas la conformité globale.
Le serveur temporaire a été arrêté ; aucune requête externe n'a été nécessaire.

Ces résultats qualifient un candidat local. Ils ne démontrent ni un portail déjà
hébergé, ni la validation finale de l'application Enterprise2.1, ni la fraîcheur
perpétuelle des dépendances. Le build CI et la publication sont encore à vérifier.
