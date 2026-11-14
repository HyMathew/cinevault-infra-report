# Évaluation du portail documentaire

## État publié le 14 novembre 2026

Le [portail candidat](https://hymathew.github.io/cinevault-infra-report/) est
hébergé. La [publication 43550763730](https://github.com/HyMathew/cinevault-infra-report/actions/runs/43550763730)
promue depuis main reprend exactement l'artefact Ubuntu qualifié `cf026c0`, sans
reconstruction. Les [preuves et captures](../../evidence/public/portal-hosted-20261114/README.md)
confirment les 351 fichiers servis, leurs octets, les quatre sources cachées et
187 contrôles navigateur sur le vrai site. Le marqueur de possession est la
seule omission des 352 fichiers du build. L'environnement autorise seulement main.

Recherche française, clavier, mobile et vraie réponse 404 passent. Aucun problème
de script, de console ou HTTP inattendu n'est relevé. Les six états axe gardent
deux résultats de contraste non conclusifs, soit 102 occurrences dans Chrome
Windows, contre 104 dans le navigateur Ubuntu antérieur. Ces résultats restent
ouverts. Le portail publie un instantané candidat ; la branche courante et la
release applicative ont des qualifications distinctes.

## Évaluation et preuves antérieures

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

Ces résultats locaux ne démontrent ni un portail déjà hébergé, ni la validation
finale d'Enterprise2.1, ni la fraîcheur perpétuelle des dépendances.

## Qualification CI du commit cf026c0

Le [run 43502640262](https://github.com/HyMathew/cinevault-infra-report/actions/runs/43502640262)
a réussi sur Ubuntu et Windows après correction de l'alias Windows 8.3 du projet.
Les deux logs confirment 27 tests Node réussis et aucun signal de vulnérabilité
par npm audit au moment de cette exécution. Le refus d'une vraie dépendance liée
reste testé et actif.

Le [reçu vérifié](../../evidence/public/portal-cf026c0-ci-20261114.json) rattache les
sept archives à leurs SHA-256 et aux quatre runs. Le portail utilise 49 documents
suivis, 74 ressources copiées et 50 pages HTML ; ses 4 500 liens contrôlés n'ont
aucune erreur. Sources, générateur et lock correspondent au commit exact, sans
modification de document ou d'outillage pendant le build.

Chaque runner construit deux fois les mêmes noms et octets : 352 fichiers sous
Ubuntu, 353 sous Windows, tous rehashés dans les archives. Les 50 HTML sont
identiques entre OS. Binaires et index Pagefind ainsi que notices de dépendances
natives diffèrent ; ces sorties ne sont pas annoncées reproductibles octet pour
octet entre systèmes. Le graphe résolu reste de 457 paquets, avec 358 installés
et 140 textes distincts sous Ubuntu, contre 357 et 141 sous Windows.

Le navigateur Ubuntu a réussi 183 contrôles et produit
[dix captures vérifiées](../../evidence/public/portal-cf026c0-20261114/README.md).
Recherche française, clavier, thèmes, menu et défilement utilisent le site réel.
Six états axe présentent zéro violation automatique, mais deux résultats de
contraste gardent 104 occurrences non conclusives, sans résolution manuelle
globale revendiquée. Aucun navigateur du portail Windows n'est qualifié par ce
run. Le serveur temporaire est arrêté selon le reçu.

Les autres archives conservent 45 contrôles du couple navigateur réel API7aa9b05 /
webf59c7af, six contrôles HTTP par OS et deux PDF v1 identiques au SHA
`2668ea3a3a1d73004b5ecf1310e30a07ea1cd9ba1a9c4b80c897cb5ae9525885`.
Les limites de chaque campagne sont conservées. L'hébergement de cet instantané
est qualifié ci-dessus ; la promotion des mises à jour, l'examen des résultats
axe non conclusifs et la validation finale de l'application restent à terminer.
