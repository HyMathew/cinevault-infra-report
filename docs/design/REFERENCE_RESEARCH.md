# Références de design de CineVault Signature

Consultation du 27 novembre 2026. La [direction existante](DESIGN_SYSTEM.md)
fournit le noir chaud, l’ivoire, l’accent ambre et les titres éditoriaux.
La première étude porte sur la recherche rapide et l’accès aux parcours
depuis chaque écran. Le catalogue garde ses affiches, filtres et résultats.

## Comparaison des composants

| Source consultée | Décision pour CineVault |
| --- | --- |
| [21st.dev, catalogue](https://21st.dev/) et [aperçu public de Command Palette](https://cdn.21st.dev/sarmaasis/command-palette/default/bundle.1795585795455-3a52c060-3bf1-480c-ab55-3d3265be5b4f.html) | Retenir un point d’entrée global, la saisie en tête et une distinction entre films et destinations. Utiliser les noms du catalogue et les droits déjà établis par CineVault. Les commandes et le code React de la démo restent propres à sa source. |
| [shadcn/ui, Command](https://ui.shadcn.com/docs/components/base/command) | Retenir le regroupement et la présence d’un raccourci repérable. Utiliser en Jinja un formulaire, une liste de liens et des boutons natifs. Le composant React et son comportement de sélection restent hors du projet. |
| [Aceternity UI, Animated Modal](https://ui.aceternity.com/components/animated-modal) | Retenir la séparation du premier et de l’arrière-plan par le voile. L’effet d’échelle et le mouvement d’entrée introduiraient une attente dans un contrôle utilisé souvent. |
| [Magic UI, Animated List](https://magicui.design/docs/components/animated-list) | Retenir l’idée de rendre visible l’arrivée d’un résultat. Utiliser un statut textuel et un affichage immédiat, en gardant la position de saisie. Écarter l’apparition progressive des lignes. |
| [Uiverse, bibliothèque Galaxy](https://github.com/uiverse-io/galaxy) | Comparer la lisibilité des boutons au repos et au survol. Garder le trait et l’accent du système CineVault. Les loaders et effets survolés du catalogue apportent peu à une recherche qui annonce déjà son état. |
| [WAI-ARIA APG, dialogue modal](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/) et [MDN, élément dialogue](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/dialog) | Ouvrir sur le champ, confiner les interactions au dialogue, fermer par Échap ou par un contrôle visible et rendre le focus. Tester le comportement effectif sur les différents moteurs. |

Les aperçus servent à examiner l’ergonomie. Aucun composant, média, logo,
capture de référence ou code de ces sites n’entre dans l’application.
Toute incorporation ultérieure devra vérifier la licence de l’élément précis,
son auteur et les obligations d’attribution.

## Outils officiels de 21st.dev

Le [dépôt officiel épinglé](https://github.com/21st-dev/codex-plugin/tree/c0505c7f1c2d9cea6db05e44892b61cb7ce35334)
fournit le plugin `21st` 0.5.0. Les entrées inspectées incluent
`21st-ui-explore` pour comparer des directions, `21st-ui-build` pour la
construction, `21st-ui-review` pour la critique, `21st-cli-use` pour le
catalogue, `21st-ai` pour les variantes et `21st-design-sync` pour la
publication de thèmes. Les entrées registre et vidéo figurent également
dans l’arbre. Le manifeste portable déclare un MCP distant et le dépôt
documente une connexion de compte à l’installation. Le [paquet CLI officiel](https://www.npmjs.com/package/@21st-dev/cli)
est publié en 1.18.1 au relevé, sous MIT d’après les métadonnées npm.

Le [manifeste du plugin](https://github.com/21st-dev/codex-plugin/blob/c0505c7f1c2d9cea6db05e44892b61cb7ce35334/plugin.json)
déclare MIT alors que le [fichier LICENSE](https://github.com/21st-dev/codex-plugin/blob/c0505c7f1c2d9cea6db05e44892b61cb7ce35334/LICENSE)
contient le texte Apache 2.0. Cet écart reste à éclaircir avant toute reprise
de code. Le CLI `21st` et le MCP n’étaient pas exposés au banc de travail.
Les aperçus publics ont suffi à cette comparaison. Installation,
authentification, achat, génération et publication de thèmes n’ont pas
été exécutés. Le [tarif officiel](https://21st.dev/plans) distingue
consultation et services comptabilisés. Le quota du compte n’a pas été observé.

## Galeries secondaires

| Galerie | Observation et décision |
| --- | --- |
| [Curated Design](https://curated.design/) | Sélection publique de compositions Web. La hiérarchie éditoriale soutient l’usage de titres courts et d’une densité maîtrisée. Les sections marketing restent hors du parcours de recherche. |
| [Layers](https://layers.to/) | Vitrine publique de travaux de designers. Les compositions sont des références de densité et de rythme, sans valeur de validation pour une interface en service. |
| [60fps](https://60fps.design/) | Galerie publique de micro-interactions iOS. Les transitions servent à expliquer une continuité spatiale dans certains parcours. La recherche modale CineVault reste fixe et immédiate. |
| [Saaspo](https://saaspo.com/) | Inventaire public de présentations SaaS. La clarté des intitulés d’action est transposable. Les zones promotionnelles et les annonces d’usage ne répondent pas à une tâche du catalogue. |
| [Screenlane](https://screenlane.com/) | Galerie indisponible au relevé avec le lecteur de recherche. Aucun écran attribué à cette source. |
| [Mobbin](https://mobbin.com/) | Accueil public consulté pour son organisation par parcours et composants. La comparaison porte sur la succession ouverture, recherche, résultat, retour. Les captures soumises à compte n’ont pas été reprises. |
| [Insposite](https://www.insposite.com/) | Accueil public et index consultés. Les compositions exploratoires restent une référence d’ambiance pour l’accueil. Une recherche se prête à une surface plus sobre. |

## Direction retenue

Un accès « Rechercher » dans l’en-tête, une surface ambre et ivoire sur fond
sombre, un seul champ et deux zones distinctes. Les films sont présentés par
titre, réalisation et année. Les destinations sont imprimées par le serveur
selon les droits courants. Les résultats se lisent dès leur arrivée,
conservent les titres complets et restent accessibles sans animation.
Sans JavaScript, le lien mène au champ natif du catalogue. Les captures
de validation montrent CineVault avec les données synthétiques du banc.
