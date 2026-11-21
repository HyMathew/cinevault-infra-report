#set document(title: "CineVault Enterprise 2.1 - RT0705", author: "Mathieu Kuhnapfel")
#set page(paper: "a4", margin: (x: 22mm, y: 20mm), footer: context align(right, text(size: 9pt, fill: rgb("526071"))[CineVault Enterprise 2.1 · RT0705 #h(8pt) #counter(page).display("1")]))
#set text(font: "Libertinus Serif", size: 10.5pt, lang: "fr", fill: rgb("172330"))
#set par(justify: true, leading: 0.6em, spacing: 0.8em)
#set heading(numbering: "1.")
#set figure(gap: 7pt)
#show heading.where(level: 1): it => block(above: 15pt, below: 10pt, text(size: 17pt, weight: "bold", fill: rgb("163b5c"), it))
#show heading.where(level: 2): it => block(above: 9pt, below: 5pt, text(size: 12pt, weight: "bold", it))
#show table: set par(justify: false)
#show raw.where(block: true): set text(font: "DejaVu Sans Mono", size: 8pt)
#let status = sys.inputs.at("status", default: "Version de travail - audit final en cours")

#v(25mm)
#text(size: 13pt, tracking: 1.3pt)[UNIVERSITÉ DE REIMS CHAMPAGNE-ARDENNE]
#v(4mm)
Master 1 Réseaux et Télécommunications · 2026-2027
#v(25mm)
#text(size: 40pt, weight: "bold", fill: rgb("163b5c"))[CineVault]
#v(2mm)
#text(size: 21pt)[Enterprise 2.1]
#v(13mm)
#text(size: 17pt)[Conception, réalisation et validation\ d'une vidéothèque répartie]
#v(7mm)
RT0705 · Python, Flask, Jinja et HTTP/JSON\
Document académique et persistance MongoDB
#v(20mm)
#text(size: 13pt, weight: "bold")[Mathieu Kuhnapfel]
#v(3mm)
État technique vérifié le 21 novembre 2026
#v(13mm)
#block(fill: rgb("f1f4f6"), inset: 10pt, radius: 3pt)[#text(size: 10pt, weight: "bold")[#status]\
Édition scientifique de la vidéothèque répartie. Les campagnes indiquent leur environnement, leur révision et les limites de la vérification.]
#pagebreak()

#heading(numbering: none, outlined: false)[Résumé]
CineVault répartit la présentation Flask/Jinja et l’API Flask sur trois tiers. Leur échange reste HTTP/JSON. L’API sélectionne son adaptateur au démarrage. Le document JSON demeure le support des exercices RT0705. MongoDB stocke l’état Enterprise sous forme BSON avec des collections validées, des index et des transactions.

La preuve académique du 9 novembre porte sur les exercices Compose et la stack JSON exploitée sur trois VM. L’édition 2.1 ajoute les résultats d’un laboratoire MongoDB isolé. La migration a importé un instantané JSON synthétique dans une base provisionnée. Le scénario a contrôlé 39 échanges HTTP. Après l’import, les nouvelles sessions, le prêt, la réservation et les reçus de rejeu ont été conservés dans l’export JSON. Les originaux ont conservé leur empreinte.

Des campagnes séparées ont testé le transfert de catalogue, les commandes de comptes, la sauvegarde chiffrée et une connexion TLS 1.3 avec refus de certificats erronés. Une comparaison de 736 requêtes sur deux volumes de données mesure les latences JSON et MongoDB. Le staging Swarm a une configuration contrôlée par le manager. Le scan du 21 novembre a bloqué les images de staging à cause de cinq avis OpenSSL encore détectés dans les paquets utilisés.

#v(4mm)
*Mots-clés.* Cinémathèque, application répartie, REST, JSON, BSON, Flask, Jinja, MongoDB, TLS, Docker Swarm.
#pagebreak()
#outline(title: [Sommaire], indent: auto, depth: 2)
#pagebreak()

#let chapters = json("chapters.json")
#for chapter in chapters {
  heading(level: 1, chapter.title)
  for paragraph in chapter.paragraphs { text(paragraph); parbreak() }
  if chapter.id == "usecases" { [Le modèle UML complet figure dans @uml-complet. Les préconditions et exceptions détaillées restent dans le document de modélisation associé.] }
  if chapter.id == "execution" { [@sequence-pret explicite une attribution de prêt et le conflit concurrent, avec traitements à réception. Les neuf autres séquences vectorielles sont fournies dans le dépôt.] }
  if chapter.id == "frontend" {
    raw(read("../excerpts/api-response-boundary.txt"), lang: "python", block: true)
    [Extrait de #link("https://github.com/HyMathew/cinevault-web/blob/10612c999cef4a82b268b8d8f900222d713b4e2b/app/api_client.py")[la frontière HTTP native au commit 10612c9]. Le contrôle précède tout accès aux champs et toute adaptation destinée à Jinja.]
  }
  if chapter.id == "logical" {
    [@architecture-logique rappelle l’organisation du socle JSON. @adaptateurs-mongodb précise le choix exclusif de l’adaptateur Enterprise.
    #figure(image("../../docs/architecture-diagrams/logical.svg", height: 134mm, fit: "contain"), caption: [Socle académique à trois tiers. Le manager assure l’orchestration hors du chemin métier.]) <architecture-logique>]
  }
  if chapter.id == "physical" {
    [@architecture-physique distingue le trafic métier du contrôle d'orchestration.
    #figure(image("../../docs/architecture-diagrams/physical.svg", height: 123mm, fit: "contain"), caption: [Placement effectif de la stack JSON du 9 novembre. Cette figure fournit le point de comparaison du staging MongoDB.]) <architecture-physique>]
  }
  if chapter.id == "actors" {
    block(breakable: false, table(columns: (1fr, 2fr), inset: 5pt, stroke: 0.4pt + rgb("b8c4ce"),
      table.header([*Acteur*], [*Responsabilité et limite*]),
      [Visiteur], [Consultation du catalogue public.],
      [Membre], [Ressources privées, demandes, favoris et listes.],
      [Gestionnaire], [Catalogue partagé, exemplaires, attribution et retours.],
      [Administrateur], [Administration des comptes et des rôles. Les collections restent réservées à leur propriétaire.],
      [Exploitant], [Linux, Docker, déploiement et reprise. Ce rôle relève de l’infrastructure.]))
  }
  if chapter.id == "rest" {
    table(columns: (1.2fr, 1fr, 1.8fr), inset: 5pt, stroke: 0.4pt + rgb("b8c4ce"),
      table.header([*Famille /api/v1*], [*Méthodes*], [*Réception et réponse*]),
      [movies / copies], text(hyphenate: false)[GET, POST, PUT, DELETE], [Lecture publique. Mutations manager/admin, validation et If-Match.],
      [auth / me / users], [POST, GET, PATCH, PUT], [Session, profil et contrôle des rôles. Réponses sans secrets.],
      [collections], text(hyphenate: false)[GET, POST, PUT, DELETE], [Propriété de la ressource vérifiée côté API.],
      [loans / reservations], [GET, POST], [Transitions métier, conflits, priorité et version.],
      [catalogue/import, export], [POST, GET], [Porteur JSON, validation du lot et idempotence.],
      [metadata / posters], [GET], [Cache, fournisseur et affiches sous conditions.],
      [statistics / recommendations], [GET], [Calculs bornés aux données et autorisations présentes.])
  }
  if chapter.id == "mongo" {
    [#figure(
      image("figures/adaptateurs-mongodb.svg", width: 100%, fit: "contain"),
      caption: [Un seul adaptateur métier par démarrage. Les preuves de laboratoire et le staging prévu correspondent à des campagnes distinctes.],
    ) <adaptateurs-mongodb>]
  }
  if chapter.id == "tests" {
    table(columns: (1.4fr, 1fr, 1.4fr), inset: 5pt, stroke: 0.4pt + rgb("b8c4ce"),
      table.header([*Campagne*], [*Résultat*], [*Périmètre*]),
      [Socle pédagogique], [16 contrôles], [Compose neuf 6a86f2e / 4883876],
      [Swarm JSON historique], [25 contrôles], [API 6a86f2e / Web f3d10cb],
      [API 22bcecd], [567 tests et 35 sous-tests], [Windows, 5 MongoDB ignorés faute d’URI],
      [Web 70fa78e], [470 tests], [Windows],
      [CI moteur], [5 / 5], [MongoDB natif, API a500e245],
      [Migration P5], [39 requêtes HTTP], [Aller MongoDB puis retour JSON],
      [Transfert de catalogue], [21 requêtes HTTP], [MongoDB isolé])
  }
  if chapter.id == "performance" {
    table(columns: (1.75fr, 0.8fr, 0.8fr, 0.8fr, 0.8fr), inset: 4pt, stroke: 0.4pt + rgb("b8c4ce"),
      table.header([*p95 en ms*], [*JSON 120*], [*Mongo 120*], [*JSON 600*], [*Mongo 600*]),
      [Page, 1 client], [10,8], [13,2], [39,8], [12,6],
      [Page, 4 clients], [267,9], [42,1], [819,0], [47,1],
      [Recherche, 4 clients], [284,1], [40,6], [829,5], [43,7],
      [Fiche, 4 clients], [272,2], [19,6], [810,1], [20,2],
      [Favori, 4 clients], [1 038,9], [574,2], [2 141,3], [708,9])
  }
}

#pagebreak()
#heading(level: 1)[Annexes de preuve et références]
#heading(level: 2)[Socle pédagogique : HTML, formulaire et JSON]
Les trois captures suivantes proviennent du parcours Chrome du 9 novembre dans la pile Compose isolée. Le film et ses personnes sont fictifs. La comparaison du fichier JSON, de la réponse API et du rendu Jinja est consignée dans la preuve du socle pédagogique.
#figure(image("../../evidence/academic-20261109/exercice-a.jpg", width: 100%), caption: [Exercice A : page HTML réellement servie par Flask.])
#pagebreak()
#figure(image("../../evidence/academic-20261109/exercice-b-formulaire.jpg", width: 100%, fit: "contain"), caption: [Exercice B : saisie du formulaire avant soumission.])
#figure(image("../../evidence/academic-20261109/exercice-c-fiche.jpg", width: 100%, fit: "contain"), caption: [Exercice C : confirmation et fiche Jinja après le POST réel.])
#pagebreak()
#heading(level: 2)[Deux projets dans VS Code Remote SSH]
La connexion et l'ouverture effective des deux projets sont visibles. Un diagnostic OpenSSH expurgé atteste l’authentification par clé.
#figure(image("../../evidence/academic-20261109/vscode-api.jpg", width: 100%), caption: [Projet API ouvert sur le worker web dans l'espace de développement séparé.])
#figure(image("../../evidence/academic-20261109/vscode-web.jpg", width: 100%), caption: [Projet de présentation et client HTTP ouverts dans le second dépôt Git.])
#pagebreak(weak: true)
#heading(level: 2)[Sources et reproductibilité]
Les sources publiques et leurs historiques sont disponibles dans les trois dépôts suivants. Les fichiers README, les matrices d'exigences et les manifestes précisent les limites temporelles et la portée des preuves.

- #link("https://github.com/HyMathew/cinevault-api")[API, services et adaptateurs JSON et MongoDB].
- #link("https://github.com/HyMathew/cinevault-web")[Présentation Flask/Jinja].
- #link("https://github.com/HyMathew/cinevault-infra-report")[Infrastructure, modèles, preuves et rapport].
- #link("https://github.com/HyMathew/cinevault-api/actions/runs/42536728355")[CI API 173 tests par plateforme].
- #link("https://github.com/HyMathew/cinevault-web/actions/runs/42640090796")[CI historique du Web].
- #link("https://github.com/HyMathew/cinevault-api/actions/runs/44831153091")[CI API a500e245 et job MongoDB natif].
- #link("https://github.com/HyMathew/cinevault-api/blob/22bcecdadee4512ddc5eb6db5759834c27b1ad48/docs/evidence/mongodb-p5-operator-native-20261120.json")[Reçu de migration et commandes de comptes].
- #link("https://github.com/HyMathew/cinevault-api/blob/22bcecdadee4512ddc5eb6db5759834c27b1ad48/docs/evidence/mongodb-tls-native-20261121.json")[Vérification TLS et disponibilité].
- #link("https://github.com/HyMathew/cinevault-infra-report/blob/d3108dea6e50c2a251e1335db301b673312e6183/evidence/public/mongodb-performance-observability-20261121.json")[Mesures natives et corrélation HTTP].
- #link("https://www.openssl-library.org/source/")[Versions OpenSSL publiées].

Les supports C0 à C5 et le sujet RT0705TP constituent les sources pédagogiques de cette étude. Les choix de formatage du présent document utilisent #link("https://typst.app/docs/")[la documentation officielle Typst] et le compilateur portable 0.15.1, dont l'archive a été vérifiée contre le digest officiel.

#pagebreak()
#set page(paper: "a2", margin: 20mm)
#heading(level: 2)[Planche vectorielle : cas d'utilisation]
Cette planche A2 conserve les quatorze cas, les acteurs et les notes du modèle complet, à une taille lisible dans son format original. Elle peut être agrandie sans pixellisation. Les liens représentent des capacités fonctionnelles, pas une trace réseau.
#figure(image("../../docs/diagrams/use-cases.svg", height: 495mm, width: 100%, fit: "contain"), caption: [Diagramme UML UC01 à UC14, rendu depuis le PlantUML versionné et vérifié statiquement.]) <uml-complet>
#pagebreak()
#heading(level: 2)[Planche vectorielle : attribution d'un prêt]
La consultation des options ne réserve pas une copie. L'attribution, la priorité et la satisfaction de réservation sont recontrôlées dans une seule transaction. Le bloc alternatif du diagramme représente un second message concurrent.
#figure(image("../../docs/diagrams/05-loan-approval.svg", height: 480mm, width: 100%, fit: "contain"), caption: [Séquence historique UC06 et UC07 pour le stockage JSON. Le service partagé porte les mêmes décisions au sein de l’unité de travail du moteur sélectionné.]) <sequence-pret>
