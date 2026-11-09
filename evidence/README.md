# Index des preuves publiables et privées

Les pièces publiques ci-dessous ont été inspectées et associées aux révisions indiquées. Les preuves privées d'installation, réseau, données et sécurité sont conservées séparément ; leur absence dans GitHub ne devient pas une capture ou un résultat public fictif.

| Ensemble | Pièces et vérification | Portée |
|---|---|---|
| [Socle pédagogique9novembre](academic-20261109/manifest.json) | Deux captures VSCode, trois captures A/B/C, comparaison JSON ; sixSHA256 | API6a86f2e/web4883876, Compose isolé surVM1, distinct du magasin Enterprise |
| [Navigateur courant](browser-20261109/manifest.json) | Captures après correction, trace Tab et mesures ; quatreSHA256 | Webf3d10cb, catalogue public via tunnel SSH ;390/820px, recherche/état vide/retour, contrastes |
| [Parcours privés courants](browser-private-20261109/manifest.json) | Traces réelles de 13 et 11 positions Tab, activation Entrée des filtres GET, captures des états | Collection et emprunts du compte synthétique existant ; 390/820 px sans débordement, console sans avertissement ni erreur ; aucune mutation métier |
| [Reconstruction du rapport](report-20261109/verification.json) | SHA256 des artefacts CI, CRC et PDF identiques ; reçus Windows/Ubuntu et [clone public neuf](report-20261109/clean-checkout.json) | Rapport nommé de 19 pages, dont deux A2 ; même SHA256 sur les trois reconstructions et la copie inspectée |
| [Exemples synthétiques](../docs/examples/academic-json/manifest.json) |93échanges,44opérations,42composants,18définitions et5schémas techniques,23tests de validation | Vrais handlers Flask hors réseau avec stockage neuf ; jamais données ou secrets du laboratoire |
| [Diagrammes](../docs/diagrams/README.md) |10séquences D2/SVG, UML, manifestes et contrôles visuels | Revue statique des traitements et verrous ; pas une capture réseau |
| [CI API173/plateforme](https://github.com/HyMathew/cinevault-api/actions/runs/42536728355) | Jobs et journaux publics, artefacts de test/qualité/image | Source6a86f2e, Windows/Ubuntu, image contrôlée puis publiée |
| [CI web159/plateforme](https://github.com/HyMathew/cinevault-web/actions/runs/42640090796) | Jobs et journaux publics, artefacts de test/qualité/image | Sourcef3d10cb, Windows/Ubuntu, image contrôlée puis publiée |

## Preuves conservées dans l'espace privé

Les campagnes d'installation, inventaires et ports/Overlay, distribution initiale,50parcours distants historiques, mises à jour successives et reçus récents25/25 sont conservés dans l'espace de preuves du projet. Le dernier reçu contient un instantané préalable, les digests d'image, l'état des nœuds/tâches, la conservation du digest métier et des identités de secrets, les connexions et appels de métadonnées. Il n'est pas publié intégralement car il décrit l'environnement d'exploitation.

Les archives CI ont été téléchargées et contrôlées par SHA256 et CRC ; les manifestes GHCR lient les digests du registre à la configuration des images scannées. Les jetons de téléchargement temporaires ne sont pas conservés avec les pièces. Les données, clés, profils VPN, enveloppes chiffrées, journaux VSCode bruts et supports pédagogiques originaux sont exclus.

Les tests de reprise isolés ne prouvent pas une bascule après perte du disque physique ; les sondes de santé ne prouvent pas tous les parcours ; les captures d'un formulaire avant soumission ne prouvent pas son traitement. Les matrices [du sujet](../docs/requirements/TRACEABILITY.md) et [des extensions](../docs/requirements/EXTENSIONS.md) précisent les états et réserves.
