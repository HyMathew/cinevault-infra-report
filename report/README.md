# Rapport éditable et compilation

`main.typ`, `chapters.json`, `excerpts/` et `build-config.json` composent le rapport français ; images et diagrammes sont versionnés dans ce dépôt. Le PDF porte le nom demandé `RT0705_CineVault_Mathieu_Kuhnapfel.pdf`. Ses deux planches finales sont au format A2 pour conserver la lisibilité des modèles vectoriels détaillés ; les pages principales sont A4.

Depuis la racine de ce dépôt, avec Python3.13 :

```sh
python -B scripts/build_report.py
```

Ce script télécharge uniquement l'archive officielle Typst0.15.1 correspondant à Windowsx64 ou Linuxx64, vérifie son SHA256 fixé avant extraction et exécution, puis compile avec les polices embarquées. Il n'installe rien globalement et ne télécharge aucun paquet Typst. Un compilateur local déjà vérifié peut être fourni par `--typst /chemin/typst`.

La date de création PDF est fixée à l'instant de référence technique dans `build-config.json` ; le reçu distingue la date réelle de compilation. Les polices système sont ignorées pour éviter une substitution entre plateformes. Les empreintes des archives officielles Windows/Linux et les contrôles d'extraction sont dans le script. La [release officielle](https://github.com/typst/typst/releases/tag/v0.15.1) permet de les vérifier.

La CI documentaire Windows/Ubuntu vérifie les liens, les SVG et les chapitres, valide le corpus JSON et ses régressions puis compile le PDF. Chaque plateforme conserve son PDF et un reçu d'empreinte. La compilation n'est pas une inspection visuelle : celle-ci et l'audit terminal sont consignés séparément. La présence du fichier nommé ne constitue pas à elle seule la clôture de la livraison.

Les outils binaires portables et aperçus de travail ne sont pas requis dans le dépôt pour compiler le rapport ; seuls les SVG et captures versionnés sont lus. La reproduction des schémas eux-mêmes est décrite dans [la documentation des rendus](../docs/diagrams/README.md).
