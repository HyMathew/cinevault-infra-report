# CineVault Enterprise 2.0 — conception d'expérience

Date : 10 novembre 2026. Document de conception, pas compte rendu de validation du frontend. À lire avec [PRODUCT.md](PRODUCT.md), le [design system](docs/design/DESIGN_SYSTEM.md) et le [registre des références](docs/design/concepts/README.md).

## Direction et alternatives

L'identité v1 sombre, ivoire et ambre est conservée. Les titres éditoriaux servent les œuvres ; les contrôles et les listes opérationnelles utilisent une typographie de lecture directe. Le changement porte sur la priorité des informations et les deux contextes, pas sur un décor cinématographique ajouté au-dessus des outils.

| Approche étudiée | Intérêt | Coût / décision |
|---|---|---|
| Retouche du shell v1 unique | Faible impact immédiat | Ne résout pas la découverte traitée comme inventaire ni la gestion trop longue ; insuffisant seul. |
| Deux présentations dans Flask/Jinja, composants partagés, HTML natif | Conserve routes, contrats, protections et faible coût client ; permet deux densités | **Retenue comme décision de conception dans le mandat autonome.** Exige une matrice de navigation et des tests sur les deux contextes. |
| Frontend SPA ou ajout systématique de bibliothèques | Peut convenir à des interactions client complexes | Aucun besoin établi ici ; migration hors socle imposé et nouveaux risques d'état/focus/cache ; non retenue. |

Le concept catalogue du principal est accepté comme direction de travail sous réserve des exigences d'accessibilité et de vérité ci-dessous. Ce n'est pas une validation visuelle de pages implémentées. Les vues absentes sont des exigences écrites à concevoir/inspecter, pas des maquettes déjà générées.

## Structure de présentation

Le shell contient lien d'évitement, marque, navigation contextuelle, compte, contenu principal et pied de page avec Page simple. Aucun hero géant dans la gestion. Un seul H1 décrit la tâche ; pas de surtitre décoratif systématique. L'état courant est souligné et marqué `aria-current="page"` sur le lien exact ; un parent de section peut avoir un style de section distinct sans prétendre être la page courante.

**Membre :** Catalogue, Ma collection, Mon espace ; Découvrir, Emprunts et Réservations restent visibles comme destinations secondaires explicites. Mon profil regroupe paramètres et déconnexion (POST CSRF). Un accès Gestion apparaît pour les rôles autorisés. **Gestion :** Inventaire, Emprunts, Réservations, Statistiques, Import / export et Administration seulement pour admin. Retour à l'espace membre explicite. Les groupes sont adaptés à la largeur, pas empilés en quatre rangées sur mobile.

**Petit écran :** divulgation native nommée Menu, navigation dans le flux, sans overlay ni piège de focus. Un détail natif n'impose pas artificiellement les interactions d'un menu ARIA. Le focus et Tab/Shift+Tab doivent fonctionner selon les éléments réellement ouverts ; si une amélioration JS ferme sur Échap ou transforme le composant, tester fermeture et restitution de focus. L'état sans JavaScript reste utilisable. En-tête fermé cible ≤120 px à 390.

## Catalogue membre : référence complète

Ordre : shell compact → « Le catalogue » → « Explorez les films de la vidéothèque. » → recherche/tri/filtres → total dynamique → résultats → pagination si nécessaire → pied de page. Sur desktop, recherche principale et bouton côtoient divulgation Filtres et tri ; si la largeur manque, retour à la ligne contrôlé avant chevauchement.

Résultat : emplacement affiche de proportion 2:3, ou fallback typographique ; titre lisible, réalisateur, année, quantité d'exemplaires/supports, lien « Voir le film ». Pas d'étoile, badge de disponibilité ou fausse recommandation. Le concept ne justifie pas de forcer une taille de ligne géante sur un catalogue fourni : utiliser une ligne média répétable, sans carte encadrée autour de chaque élément. Un séparateur suffit.

Le formulaire GET conserve `q`, `genre`, `year`, `support`, `sort` et la pagination existante selon contrats validés. « Rechercher », « Filtres », « Trier par » et « Effacer les filtres » sont des libellés explicites. Filtres : genre, année, support ; si un filtre secondaire est actif, le groupe reste ouvert ou son état actif reste visible avec accès d'effacement. Changer un tri exige un bouton de soumission accessible ; pas de soumission implicite qui dépend du JS. Une recherche appliquée repart au début des résultats. Ne pas inventer de facettes sans source de genres fiable.

À 1280×900, objectif : en-tête d'environ 70 px, premier résultat avant y=520 avec filtres fermés. À 390, recherche et bouton puis tri/filtres dans l'ordre de lecture ; visuel réduit à environ 96×144 ou empilé à 320 selon le texte. Le titre long revient à la ligne sans ellipsis ni défilement horizontal. Un seul résultat n'est jamais multiplié pour remplir la page.

## Fiche, collection et espace personnel

**Fiche :** retour catalogue, titre/réalisateur/année, affiche ou fallback et bloc disponibilité/action près de l'identité. Visiteur : lien « Se connecter pour agir ». Membre : demande de prêt ou réservation uniquement selon règles réelles ; actions Favoris/À voir via formulaires existants, états confirmés par serveur. Puis synopsis, genres/interprètes, exemplaires et autres métadonnées utiles. Gestion : actions modifier/ajouter exemplaire séparées de l'action personnelle. Le film n'est pas un média à lire : aucun bouton Lecture.

**Collection :** choix explicite Favoris/Possédés/Vus/À voir/Listes personnelles, critères et liste de films. Une liste personnelle garde son nom et son périmètre. Les supports personnels ne sont pas confondus avec les exemplaires de la vidéothèque. Ajouter/modifier/retirer a un résultat serveur explicite ; retrait de collection n'est pas suppression d'une œuvre.

**Mon espace :** activité à traiter en premier (demandes, prêts et échéances, réservations), liens collection et découverte ensuite. Les répartitions complètes existent dans une divulgation secondaire ; ne pas supprimer les zéros ni confondre absence de données et erreur. **Découvrir :** conserver explication du classement et exclusions. Un genre inconnu doit pouvoir être effacé. Une cause précise de vide n'est affichée que si elle est distinguable depuis le contrat : sinon « Aucune suggestion avec les critères et exclusions actuels » et lien catalogue, sans diagnostic inventé.

## Gestion : pages complètes et densité propre

**Inventaire :** titre court, action Ajouter un film, recherche/filtres, total et tableau d'œuvres (titre, réalisateur/année, quantité/supports, actions). L'édition d'œuvre et celle d'exemplaire restent des objets distincts. Formulaire desktop en groupes Identité, Classement et Premier exemplaire ; seuls les champs courts liés partagent une rangée. Synopsis et erreurs prennent la largeur utile. Mobile : colonne unique.

**Métadonnées externes :** conserver le chemin d'enrichissement depuis fiche et formulaires, recherche puis sélection de la référence, origine/révision et contrôle des champs avant sauvegarde. Une panne fournisseur n'efface pas la saisie locale ; l'affiche optionnelle demeure distincte des métadonnées et soumise à sa provenance/autorisation d'affichage. Aucun champ URL libre n'est ajouté pour contourner les protections du fournisseur.

**Circulation :** demandes/prêts/réservations avec identité film et membre, état, dates explicites et actions. Vue personnelle et globale sont nommées. Validation d'un prêt montre film/membre, exemplaire choisi, date limite et conséquences ; retour/suppression jamais représentés par une icône ambiguë. Retard est un indicateur dérivé d'un prêt actif et de son échéance, pas un statut API ajouté.

**Statistiques :** titre, portée, date/période si disponibles, chiffres et répartitions utiles. Aucun graphe décoratif n'est requis ; un tableau lisible suffit. **Administration :** résumé compte/rôle/statut, édition explicite de chaque compte par formulaire ou divulgation native ; conséquence du changement et identité près du bouton. **Transfert :** import et export en sections clairement séparées, contraintes et erreurs près du formulaire. Import réussi, refusé et résultat incertain ont des messages distincts.

Sur mobile, chaque ligne opérationnelle devient une pile de cellules étiquetées en gardant les associations de tableau ou une structure liste sémantique équivalente. Un simple `data-label` généré en CSS n'est pas une preuve d'association accessible. Les données et actions ne disparaissent pas pour tenir dans l'écran. Vérifier noms/valeurs et ordre avec technologie d'assistance ciblée.

## États et interactions transversaux

| État | Contrat de présentation |
|---|---|
| Vide réel | Titre et explication correspondant aux données, action de récupération ; aucun faux résultat. |
| Attente de réponse | Navigation HTML native reste le socle. Si indicateur local ajouté : texte de progression, état occupé et blocage du double clic sans perdre le bouton ; restaurer après échec. Pas de délai ni de skeleton artificiel. |
| Validation 422 | Résumé d'erreurs, lien au premier champ, `aria-invalid` et aide liée ; conserver valeurs non secrètes, première erreur visible. |
| Conflit 409/412/428 | Expliquer l'état changé, conserver la proposition utile, lien de relecture/comparaison ; ne pas remplacer silencieusement la version. |
| 401/403 | Reconnexion ou accès refusé avec sortie autorisée ; ne jamais suggérer d'élever ses droits. |
| 429/503 | Message récupérable, délai lorsqu'il est fiable ; action manuelle. Une erreur serveur n'est pas un catalogue vide. |
| Import ou mutation au résultat incertain | Expliquer que la réponse n'a pas confirmé l'issue ; relire l'état/historique avant tout nouvel envoi. Aucun réessai automatique d'une écriture. |
| Succès | Message associé à l'objet réellement confirmé, après réponse serveur ; redirection PRG existante conservée. |

Toutes les mutations conservent CSRF, contrôles serveur, ETag/If-Match ou champ version selon le contrat actuel. Le design ne remplace pas une autorisation ni une protection de concurrence. Les données privées restent non mises en cache selon politique existante.

L'import conserve aussi sa clé d'opération après une réponse incertaine : rappeler même fichier/mêmes options lors d'une répétition manuelle, sans promettre que le lot a échoué. Limites, politique de doublons et confidentialité de l'export restent lisibles ; le navigateur ne permet pas de préremplir un fichier après erreur, donc expliquer la nouvelle sélection nécessaire sans perdre les autres options.

## Choix frontend proportionné

Décision : Flask/Jinja + CSS local à tokens et composants, formulaires/liens HTML, divulgations natives ; pas de nouvelle dépendance UI dans la première tranche. Un petit script local n'est admis que pour un besoin concret mesuré, avec mode sans JS et tests focus/erreurs.

- [Tailwind CLI](https://tailwindcss.com/docs/installation/tailwind-cli) fournit une génération de CSS à partir des classes. Son coût de build et la migration de styles ne sont pas justifiés par les défauts constatés. À reconsidérer seulement si une mesure de maintenance/répétition montre un gain net ; aucun CDN de développement livré.
- [htmx](https://htmx.org/docs/) permet des requêtes et remplacements HTML déclaratifs. Ici les parcours GET/POST existants suffisent ; l'introduire ajouterait la gestion des fragments, de l'historique, du focus et des erreurs. À réévaluer sur une interaction documentée, jamais pour relancer automatiquement une mutation.
- [Alpine](https://alpinejs.dev/start-here) fournit état et directives client. Le menu et les filtres peuvent fonctionner nativement ; pas de second état client sans besoin établi. Toute adoption future doit être compatible CSP et auto-hébergée/versionnée.

Ces documents officiels ont été consultés le 10 novembre 2026 ; ce tableau n'est pas un benchmark de performances et ne présume aucune version installée.

## Protocole de validation du design

1. Conserver captures avant authentiques et état de données ; noter commit, route, rôle, viewport et état des filtres. Ne pas présenter le concept comme capture après.
2. Produire de vraies pages complètes et captures à 1280×900, 768, 390 et 320 ; comparer le même jeu audité, puis tester séparément les fixtures à états riches.
3. Ouvrir concept et capture rendue côte à côte avec `view_image` ; comparer texte, hiérarchie, géométrie, palette, typographie, affiches/fallback, densité et pied de page. Tenir un registre des écarts et corrections ; le concept natif est 1402×1122, pas une preuve à 1280×900.
4. Vérifier en navigateur réel les parcours produit, puis Playwright/axe-core : navigation clavier via Tab et Shift+Tab réellement exécutés, élément actif contrôlé avant activation, divulgations, focus d'erreur, zoom/reflow et reduced motion. Une injection de `focus()` ne prouve pas l'accessibilité au clavier.
5. Mesurer première ligne, bloc d'action et en-tête fermé par boîtes DOM ; confirmer zéro débordement document à 320/390/768/1280. Contrôler aussi filtres ouverts, titre long et éditions avec erreurs.
6. Exécuter les validations officielles des dépôts touchés et les tests contrats/CSRF/concurrence/legacy. Les nouvelles captures ne remplacent aucun gate existant.

Statut au moment de rédaction : concept et capture catalogue avant inspectés ; dimensions/hash du concept et ratios du design system calculés ; aucune nouvelle implémentation UI, aucune passe axe/clavier complète ni capture réelle 2.0 certifiée par ce document. Les vues gestion/mobile ont besoin d'une référence visuelle complète lorsque leur extraction ou leur rendu est incertain.
