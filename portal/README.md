# Portail documentaire CineVault

Ce site statique Astro/Starlight transforme les documents publics du dépôt en pages
navigables avec recherche locale Pagefind. Les fichiers Markdown suivis par Git
dans la racine, `docs`, `report` et `evidence` restent les sources éditoriales.
Les plans privés `docs/superpowers`, fichiers ignorés et fichiers non suivis ne
sont pas publiés. Les preuves historiques conservent leur date et leur périmètre ;
elles ne valent pas validation de la version Enterprise 2.1 en cours.

## Construire et consulter

Prérequis : Git, Node.js 24.19 ou supérieur dans la branche 24, npm 11.17 ou supérieur
dans la branche 11. Depuis `portal` :

```sh
npm ci --ignore-scripts
npm test
npm audit
npm run build
npm run preview -- --port 4321
```

Ouvrir `http://127.0.0.1:4321/cinevault-infra-report/`. Le serveur de consultation
écoute uniquement sur la machine locale. La recherche fonctionne sur le site
construit ; `file://` et le serveur de développement ne constituent pas son test.

`DOCS_SITE` configure une origine HTTPS sans chemin, identifiants ni paramètres.
`DOCS_BASE` configure le préfixe, par défaut `/cinevault-infra-report` ; `/` permet
un hébergement à la racine. La valeur canonique proposée est
`https://hymathew.github.io`, sans que la construction constitue une publication.
L'hébergement est distinct de l'application et des machines du laboratoire.

`npm run check:reproducible` construit deux fois le site et compare tous les noms
et octets produits sur cette machine. Son reçu reste dans
`.cache/reproducibility.json`. Cela ne prouve pas à lui seul une construction
identique sur une autre plateforme. `npm run sbom` produit un SBOM CycloneDX npm
dans `.cache/sbom.cdx.json`, séparé du site pour conserver les métadonnées datées
de l'outil sans modifier les fichiers statiques.

Pour les essais navigateur, créer un environnement Python 3.13 distinct, installer
`../requirements-browser.txt` avec `--require-hashes --only-binary=:all:`, puis
installer Chromium par `python -m playwright install chromium`. Sous Linux,
`--with-deps` peut installer les bibliothèques système nécessaires au navigateur.
Après construction :

```sh
python scripts/check_browser.py --report-dir .cache/browser-report
```

Le répertoire de résultats doit être neuf. `--browser-channel chrome` permet de
tester Chrome installé, dont la version est alors enregistrée. Le contrôle visite
toutes les pages, vérifie la recherche française et sa navigation, le clavier,
les menus, les thèmes et le défilement réel des tableaux et exemples de code.
Il exécute axe sur six états et conserve captures, résultats incomplets et reçu.
Le serveur temporaire écoute uniquement sur `127.0.0.1` et est arrêté après le test.
Les contrôles automatiques ne constituent pas une certification d'accessibilité.

## Garanties et limites

La construction refuse les références locales manquantes, fichiers non suivis,
sorties du dépôt, collisions de routes et liens dangereux. Elle vérifie ensuite
les liens et ancres de toutes les pages produites, ainsi que l'absence des chemins
privés de la machine de construction. Elle n'interroge pas chaque lien externe.
Les sorties `.generated`, `.astro`, `.cache` et `dist` sont ignorées par Git.
Les dossiers `.generated` et `dist` doivent être des répertoires réels du dépôt.
Une sortie préexistante sans marqueur propriétaire est refusée avant nettoyage ;
les liens symboliques et jonctions sont refusés. Pour reprendre un ancien `dist`
non reconnu, inspecter puis déplacer ce dossier avant de relancer : le produit
ne propose aucune adoption automatique. Le HTML brut n'est pas accepté dans les
documents Markdown ; les exemples de HTML peuvent rester dans des blocs de code.

`dist/source-manifest.json` relie chaque page et ressource à son empreinte.
`dist/build-receipt.json` décrit les contrôles effectués. `source_clean` concerne
les documents et ressources sélectionnés ; `tooling_clean` concerne `portal` et
`.gitignore`. Les deux doivent être vrais pour rattacher cette construction à un
commit exact. La vérification des liens ne remplace ni la revue de confidentialité
des documents publics, ni les essais de navigation, clavier et recherche.

Les dépendances sont verrouillées avec leurs intégrités npm. Les scripts
d'installation sont désactivés localement au projet ; l'audit npm est une commande
explicite. La télémétrie Astro est désactivée pour la construction sans modifier le
profil de la machine. Aucun appel à une API d'IA ou service de recherche distant
n'est nécessaire pour construire ou consulter le site.

## Licences

Le code propre au dépôt conserve sa licence. Les dépendances gardent leurs
licences respectives, qui ne sont pas toutes MIT. Le site construit distribue
`third-party/packages.json` et `third-party/licenses`, avec les textes disponibles
dans les paquets installés et la licence Pagefind d'une source amont épinglée.
Le catalogue distingue les dépendances résolues, installées et les binaires
optionnels d'autres plateformes ; il ne prétend pas identifier chaque module
effectivement inclus dans les scripts du navigateur. La provenance de la licence
Pagefind est conservée dans `licenses/provenance.json` et vérifiée à la construction.

Les versions sont fixées pour la reproductibilité, sans affirmation qu'elles
seront toujours les plus récentes ou exemptes de vulnérabilités. Les mises à jour
requièrent un nouvel audit, une construction et les essais du site rendu.
