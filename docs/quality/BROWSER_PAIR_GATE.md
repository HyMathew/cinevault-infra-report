# Gate navigateur avec les deux services réels

`scripts/check_browser_pair.py` pilote un navigateur local, le frontend Flask,
l’API HTTP et un magasin JSON temporaire. Aucun client API n’est simulé. Ce gate
complète le [contrat de paire JSON](REAL_BROWSER_PAIR.md) et les tests de
présentation qui utilisent des réponses synthétiques simulées.

## Parcours vérifiés

Le scénario crée uniquement des données fictives dans un magasin neuf : connexion
administrateur avec contexte client signé, création d’un film et de son premier
exemplaire, inscription et connexion d’un membre, modification de son profil,
refus CSRF, refus d’une route de gestion, collection privée et séparation des
acteurs, demande de prêt, attribution par le gestionnaire, réservation puis
retour et priorité de réservation. Des assertions relisent enfin le JSON pour
vérifier le propriétaire, l’emprunteur, les états et le nom d’acteur avec virgule.

Le navigateur ne peut charger que l’origine HTTP locale du frontend pendant le
scénario. Une tentative contrôlée vers un domaine réservé `.invalid` vérifie le
refus avant envoi par Playwright. Les service workers sont bloqués. Cette règle
de routage ne constitue pas un pare-feu ni un confinement réseau du système
d’exploitation. Le frontend joint l’API sur son propre port loopback ; les
métadonnées externes sont désactivées pour ce scénario reproductible.

Les cinq captures portent sur des états après soumission : fiche, profil,
collection, prêt retourné et réservation prioritaire. Aucun écran contenant un
mot de passe saisi n’est capturé. Les comptes et films restent fictifs.

## Exécution portable

Créer deux environnements Python distincts et installer les dépendances
verrouillées de chaque service. Installer ensuite les outils navigateur dans
l’environnement web :

```sh
python -m venv .venv-api
python -m venv .venv-web
.venv-api/bin/python -m pip install -r cinevault-api/requirements.txt
.venv-web/bin/python -m pip install -r cinevault-web/requirements.txt
.venv-web/bin/python -m pip install --only-binary=:all: --require-hashes \
  -r cinevault-infra-report/requirements-browser.txt
.venv-web/bin/python -m pip check
.venv-api/bin/python -m pip check
.venv-web/bin/python -m playwright install --with-deps chromium
.venv-web/bin/python cinevault-infra-report/scripts/check_browser_pair.py \
  --api-root cinevault-api --web-root cinevault-web \
  --api-python .venv-api/bin/python \
  --report reports/browser-pair.json --screens-dir reports/browser-pair-screens
```

Sur Windows, employer `Scripts/python.exe` à la place de `bin/python`. Un Chrome
déjà installé peut être utilisé avec `--browser-channel chrome` ; ce choix
n’installe aucun navigateur. Par défaut, le runner utilise le Chromium fourni
par la version Playwright verrouillée. Ne pas résoudre le lien symbolique
`bin/python` vers son interpréteur de base : le runner conserve le chemin du
venv pour le processus API.

Les chemins de sources, d’interpréteur et de sortie sont des arguments ; aucun
répertoire personnel n’est codé dans le script. Les sources API/web doivent être
distinctes. Le rapport et le répertoire de captures doivent être nouveaux afin
de préserver les preuves précédentes. Les sorties à l’intérieur des sources API ou web sont refusées pour ne pas
modifier le code testé. Les erreurs d’arguments échouent avant démarrage d’un
service.

## Dépendances et provenance

Le lock navigateur cible CPython 3.13, Ubuntu x86_64 et Windows AMD64. Ses quatre
distributions et leurs dépendances transitives sont épinglées : Playwright
1.64.1, pyee 14.0.0, greenlet 3.5.6 et typing-extensions 4.16.0. Les hashes ont été
comparés aux octets téléchargés et aux métadonnées des versions officielles
[Playwright](https://pypi.org/pypi/playwright/1.64.1/json),
[pyee](https://pypi.org/pypi/pyee/14.0.0/json),
[greenlet](https://pypi.org/pypi/greenlet/3.5.6/json) et
[typing-extensions](https://pypi.org/pypi/typing-extensions/4.16.0/json).

Licences déclarées : Apache-2.0 pour Playwright, MIT pour pyee, MIT et PSF-2.0 pour
greenlet, PSF-2.0 pour typing-extensions. Chromium et le driver distribuent aussi
leurs composants tiers ; aucune licence MIT globale n’est attribuée à cet
ensemble. Le projet ne vendore pas les exécutables.

Le [workflow navigateur](../../.github/workflows/browser-pair.yml) épingle les
actions GitHub et les deux commits applicatifs. Les environnements sont séparés,
les wheels d’outillage sont installées avec `--require-hashes`, puis le navigateur
officiel correspondant à la version Playwright est installé selon les
[instructions CI officielles](https://playwright.dev/python/docs/ci). Playwright
associe chaque version à des révisions de navigateur précises ;
[leur installation est documentée par l’éditeur](https://playwright.dev/python/docs/browsers).
Ce pin de package n’est pas présenté comme un hash de l’archive Chromium.

## Preuves, secrets et nettoyage

Le rapport contient les versions, le canal navigateur, les contrôles passés, les
empreintes des captures, les empreintes applicatives et les résultats de
nettoyage. Pour un vrai checkout Git, le commit et la propreté de la source sont
enregistrés. Pour une archive sans métadonnées Git, le rapport indique
`kind=archive`, sans inventer de commit ; sa provenance doit être liée séparément
au hash de l’archive et au commit exporté. L’empreinte applicative porte sur
`app/` et `requirements.txt`, comme le helper de paire existant.

Le mot de passe et les clés sont générés pour la campagne. La configuration API
est transmise par stdin ; la clé de session est créée dans le dossier privé
temporaire. Les journaux bruts restent dans ce dossier et ne sont pas publiés.
Le rapport d’échec ne garde que la classe d’erreur et l’étape nommée, sans
message brut, commandes, token, mot de passe ou corps de réponse.

Le navigateur et ses contextes sont fermés, le serveur web arrêté, puis stdin
API fermé pour arrêter aussi le descendant d’interpréteur Windows. Les données
ne sont supprimées qu’après confirmation de l’arrêt des écrivains possédés.
Une absence de confirmation ou un échec de suppression refuse le gate ; seul
le dossier privé possédé est alors conservé pour diagnostic. Les captures et
le rapport demandés sont des livrables, pas des données temporaires à effacer.

## Première CI réellement exécutée

La [CI43115608968](https://github.com/HyMathew/cinevault-infra-report/actions/runs/43115608968)
a réussi sur infra2ae586e, avec API4c062f9 et web8256166 propres, sous Ubuntu24.04.
Chromium156.0.8078.4, fourni par Playwright1.64.1, a réussi18contrôles et produit
cinq captures. Le reçu confirme APIexit0, arrêt web, fermeture du navigateur et
suppression des données temporaires. Les empreintes des cinq images et le SHA
de l’archive ont été contrôlés après téléchargement :
`3f6d554f0afa0cf6d438cbd045f15d46260a3739a7f9534700d62854b19bbc05`.
La fiche desktop et le profil mobile ont aussi été examinés visuellement.

Cette réussite concerne exactement cette paire. Les workflows ont ensuite été
épinglés sur APIc2fe26b/web8256166 pour qualifier les nouvelles lectures communes
du catalogue. Cette paire a ensuite réussi la
[CI43116366688](https://github.com/HyMathew/cinevault-infra-report/actions/runs/43116366688),
avec18contrôles et cinq captures vérifiées. Les contrats HTTP réels ont aussi
réussi sur Windows et Ubuntu dans le
[run43116366696](https://github.com/HyMathew/cinevault-infra-report/actions/runs/43116366696).
Le [reçu public de qualification](../../evidence/public/c2c-qualification-20261111.json)
lie les commits, versions, contrôles et empreintes des archives. La comparaison
des octets Linux a utilisé des archives Git sans conversion locale CRLF ; les
paramètres n’ont été appliqués qu’à cette commande, sans changer Git globalement.

Les workflows ont ensuite ciblé API139a839/web8256166 pour qualifier les
collections privées et le précontrôle sans écriture. La CI complète de cet API
a réussi dans le [run43205951909](https://github.com/HyMathew/cinevault-api/actions/runs/43205951909).
Ce couple a ensuite réussi le
[run navigateur43251502747](https://github.com/HyMathew/cinevault-infra-report/actions/runs/43251502747),
avec18contrôles et cinq captures, ainsi que le
[run HTTP43251503081](https://github.com/HyMathew/cinevault-infra-report/actions/runs/43251503081)
sur Windows et Ubuntu. Le [reçu C3](../../evidence/public/c3-qualification-20261112.json)
lie les archives vérifiées, empreintes du code chargé et résultats natifs Mongo.
La version web de cette preuve reste8256166 ; elle ne qualifie pas un changement
web postérieur.

Les pins courants visent API139a839/webf59c7af, après réussite de la
[CI web43254511589](https://github.com/HyMathew/cinevault-web/actions/runs/43254511589).
Ce changement raccorde les formulaires à clé d'opération et la référence DESIGN.md.
La nouvelle exécution de paire doit encore être inspectée ; les reçus C3 ci-dessus
conservent la version8256166 exacte. L'API139a839 n'implémente pas encore les reçus
de création C4 : ce couple peut vérifier les parcours compatibles, pas leur rejeu
backend après réponse perdue.

## Limites de portée

Ce scénario couvre une paire HTTP locale et le backend JSON. Il ne démontre pas
MongoDB, TLS, Docker/Swarm, un déploiement, une charge représentative, la
concurrence générale ou l’équité FIFO globale. Il n’est pas une campagne complète
de clavier, d’accessibilité ou de compatibilité entre moteurs de navigateur.
Une exécution locale réussie ne vaut pas validation GitHub Actions ; le reçu CI
doit être relié à son commit et à son run après intégration du workflow.
