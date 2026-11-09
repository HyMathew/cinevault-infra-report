#set document(title: "CineVault Enterprise - RT0705", author: "Mathieu Kuhnapfel")
#set page(paper: "a4", margin: (x: 22mm, y: 20mm), footer: context align(right, text(size: 9pt, fill: rgb("526071"))[CineVault · RT0705 #h(8pt) #counter(page).display("1")]))
#set text(font: "Libertinus Serif", size: 10.5pt, lang: "fr", fill: rgb("172330"))
#set par(justify: true, leading: 0.6em, spacing: 0.8em)
#set heading(numbering: "1.")
#set figure(gap: 7pt)
#show heading.where(level: 1): it => block(above: 15pt, below: 10pt, text(size: 17pt, weight: "bold", fill: rgb("163b5c"), it))
#show heading.where(level: 2): it => block(above: 9pt, below: 5pt, text(size: 12pt, weight: "bold", it))
#show raw.where(block: true): set text(font: "DejaVu Sans Mono", size: 8pt)
#let status = sys.inputs.at("status", default: "Version de travail - audit final en cours")

#v(25mm)
#text(size: 13pt, tracking: 1.3pt)[UNIVERSITÉ DE REIMS CHAMPAGNE-ARDENNE]
#v(4mm)
Master 1 Réseaux et Télécommunications · 2026-2027
#v(25mm)
#text(size: 40pt, weight: "bold", fill: rgb("163b5c"))[CineVault]
#v(2mm)
#text(size: 21pt)[Enterprise]
#v(13mm)
#text(size: 17pt)[Conception, réalisation et validation\ d'une vidéothèque répartie]
#v(7mm)
RT0705 · Python, Flask, Jinja et stockage JSON\
Docker Compose puis Docker Swarm sur trois VM
#v(20mm)
#text(size: 13pt, weight: "bold")[Mathieu Kuhnapfel]
#v(3mm)
État technique du 9 novembre 2026, 16 h 04, heure de Paris
#v(13mm)
#block(fill: rgb("f1f4f6"), inset: 10pt, radius: 3pt)[#text(size: 10pt, weight: "bold")[#status]\
Ce document distingue exigences académiques, extensions, observations et limites. Les preuves d'administration privées et les secrets sont exclus de la publication.]
#pagebreak()

#heading(numbering: none, outlined: false)[Résumé]
CineVault est une application collaborative de gestion de vidéothèque. Le navigateur utilise un serveur Flask/Jinja, lequel appelle une API Flask distincte par HTTP/JSON. L'API est seule propriétaire du document JSON métier. Les films, exemplaires, collections privées, prêts et réservations sont reliés par des identifiants stables ; les transactions sont protégées entre processus et les écritures remplacent atomiquement le fichier validé.

Le socle pédagogique a été exécuté sous Docker Compose avec code hôte monté et données séparées, puis étendu à trois VM Ubuntu 24 : présentation, API et manager Docker Swarm dédié. Les images de registre public sont reliées à des CI Windows/Ubuntu réussies et déployées par digest. Au jalon décrit, les suites comportent173 tests API et159 tests web sur chacune de ces plateformes ; la dernière mise à jour distribuée a passé25 contrôles avec conservation des données et sessions. Ces nombres décrivent des campagnes précises, et non un taux universel de conformité ou de sécurité.

Le rapport explique les choix, les traitements à réception des messages, les contrôles réellement exécutés et leurs limites. Le laboratoire demeure sans haute disponibilité ni terminaison HTTPS publique. Le boot autonome de deux VM et la reprise après perte de disque ne sont pas démontrés. Le corpus des exemples, les contrôles et leurs limites accompagnent les sources ; les matrices et les pièces de clôture précisent leur portée.

#v(4mm)
*Mots-clés :* application répartie, REST, Flask, Jinja, JSON, verrou interprocessus, Swarm, provenance d'image.
#pagebreak()
#outline(title: [Sommaire], indent: auto, depth: 2)
#pagebreak()

#let chapters = json("chapters.json")
#for chapter in chapters {
  heading(level: 1, chapter.title)
  for paragraph in chapter.paragraphs { text(paragraph); parbreak() }
  if chapter.id == "usecases" { [Le modèle UML complet est reproduit dans la planche @uml-complet. Les préconditions et exceptions détaillées restent dans le document de modélisation associé.] }
  if chapter.id == "execution" { [La planche @sequence-pret explicite une attribution de prêt et le conflit concurrent, avec traitements à réception. Les neuf autres séquences vectorielles sont fournies dans le dépôt.] }
  if chapter.id == "frontend" {
    raw(read("excerpts/api-response-boundary.txt"), lang: "python", block: true)
    [Extrait de #link("https://github.com/HyMathew/cinevault-web/blob/10612c999cef4a82b268b8d8f900222d713b4e2b/app/api_client.py")[la frontière HTTP native au commit 10612c9]. Le contrôle précède tout accès aux champs et toute adaptation destinée à Jinja.]
  }
  if chapter.id == "logical" {
    [La figure @architecture-logique précise la responsabilité exclusive de l'API sur le fichier métier.
    #figure(image("../docs/architecture-diagrams/logical.svg", height: 134mm, fit: "contain"), caption: [Trois tiers logiques. Le manager assure l'orchestration, hors du chemin métier.]) <architecture-logique>]
  }
  if chapter.id == "physical" {
    [La figure @architecture-physique distingue le trafic métier du contrôle d'orchestration.
    #figure(image("../docs/architecture-diagrams/physical.svg", height: 142mm, fit: "contain"), caption: [Placement effectif sur trois VM. Les adresses du laboratoire restent dans les preuves privées.]) <architecture-physique>]
  }
  if chapter.id == "actors" {
    table(columns: (1fr, 2fr), inset: 5pt, stroke: 0.4pt + rgb("b8c4ce"),
      table.header([*Acteur*], [*Responsabilité et limite*]),
      [Visiteur], [Lecture du catalogue public ; aucune mutation métier.],
      [Membre], [Ressources privées, demandes, favoris et listes.],
      [Gestionnaire], [Catalogue partagé, exemplaires, attribution et retours.],
      [Administrateur], [Comptes et rôles applicatifs ; pas d'accès automatique aux collections privées d'autrui.],
      [Exploitant], [Linux, Docker, déploiement et reprise ; rôle distinct des autorisations HTTP.])
  }
  if chapter.id == "rest" {
    table(columns: (1.2fr, 1fr, 1.8fr), inset: 5pt, stroke: 0.4pt + rgb("b8c4ce"),
      table.header([*Famille /api/v1*], [*Méthodes*], [*Réception et réponse*]),
      [movies / copies], [GET, POST, PUT, DELETE], [Lecture publique ; mutations manager/admin, validation et If-Match.],
      [auth / me / users], [POST, GET, PATCH, PUT], [Session, profil et contrôle des rôles ; secrets jamais renvoyés.],
      [collections], [GET, POST, PUT, DELETE], [Propriété de la ressource vérifiée côté API.],
      [loans / reservations], [GET, POST], [Transitions métier, conflits, priorité et version.],
      [catalogue/import, export], [POST, GET], [Porteur JSON, validation du lot et idempotence.],
      [metadata / posters], [GET], [Cache, fournisseur et affiches sous conditions.],
      [statistics / recommendations], [GET], [Calculs bornés aux données et autorisations présentes.])
  }
  if chapter.id == "tests" {
    table(columns: (1.5fr, 1fr, 1fr), inset: 5pt, stroke: 0.4pt + rgb("b8c4ce"),
      table.header([*Campagne*], [*Résultat*], [*Périmètre*]),
      [API 6a86f2e], [173 / 173], [Windows / Ubuntu],
      [Web f3d10cb], [159 / 159], [Windows / Ubuntu],
      [Compose auth historique], [171 contrôles], [API 4b15406 / web 9b1da4f],
      [Compose pédagogique neuf], [16 contrôles], [API 6a86f2e / web 4883876],
      [Mise à jour Swarm courante], [25 contrôles], [API 6a86f2e / web f3d10cb])
  }
}

#pagebreak()
#heading(level: 1)[Annexes de preuve et références]
#heading(level: 2)[Socle pédagogique : HTML, formulaire et JSON]
Les trois captures suivantes proviennent du parcours Chrome du 9 novembre dans la pile Compose isolée. Le film et ses personnes sont fictifs. La comparaison fichier JSON, réponse API et valeurs Jinja est conservée séparément ; une capture de formulaire seule ne démontrerait pas le traitement.
#figure(image("../evidence/academic-20261109/exercice-a.jpg", width: 100%), caption: [Exercice A : page HTML réellement servie par Flask.])
#pagebreak()
#figure(image("../evidence/academic-20261109/exercice-b-formulaire.jpg", width: 100%, fit: "contain"), caption: [Exercice B : saisie du formulaire avant soumission.])
#figure(image("../evidence/academic-20261109/exercice-c-fiche.jpg", width: 100%, fit: "contain"), caption: [Exercice C : confirmation et fiche Jinja après le POST réel.])
#pagebreak()
#heading(level: 2)[Deux projets dans VS Code Remote SSH]
La connexion et l'ouverture effective des deux projets sont visibles. L'authentification par clé est attestée par un diagnostic OpenSSH expurgé séparé ; aucune clé privée ni journal brut n'est publié.
#figure(image("../evidence/academic-20261109/vscode-api.jpg", width: 100%), caption: [Projet API ouvert sur le worker web dans l'espace de développement séparé.])
#figure(image("../evidence/academic-20261109/vscode-web.jpg", width: 100%), caption: [Projet de présentation et client HTTP ouverts dans le second dépôt Git.])
#pagebreak(weak: true)
#heading(level: 2)[Sources et reproductibilité]
Les sources publiques et leurs historiques sont disponibles dans les trois dépôts suivants. Les fichiers README, les matrices d'exigences et les manifestes précisent les limites temporelles et la portée des preuves.

- #link("https://github.com/HyMathew/cinevault-api")[API et stockage JSON].
- #link("https://github.com/HyMathew/cinevault-web")[Présentation Flask/Jinja].
- #link("https://github.com/HyMathew/cinevault-infra-report")[Infrastructure, modèles, preuves et rapport].
- #link("https://github.com/HyMathew/cinevault-api/actions/runs/42536728355")[CI API 173 tests par plateforme].
- #link("https://github.com/HyMathew/cinevault-web/actions/runs/42640090796")[CI web 159 tests par plateforme].

Les supports C0 à C6 et le sujet RT0705TP constituent les sources pédagogiques remises pour la mission ; ils ne sont pas redistribués. Les choix de formatage du présent document utilisent #link("https://typst.app/docs/")[la documentation officielle Typst] et le compilateur portable 0.15.1, dont l'archive a été vérifiée contre le digest officiel.

#pagebreak()
#set page(paper: "a2", margin: 20mm)
#heading(level: 2)[Planche vectorielle : cas d'utilisation]
Cette planche A2 conserve les quatorze cas, les acteurs et les notes du modèle complet, à une taille lisible dans son format original. Elle peut être agrandie sans pixellisation. Les liens représentent des capacités fonctionnelles, pas une trace réseau.
#figure(image("../docs/diagrams/use-cases.svg", height: 495mm, width: 100%, fit: "contain"), caption: [Diagramme UML UC01 à UC14, rendu depuis le PlantUML versionné et vérifié statiquement.]) <uml-complet>
#pagebreak()
#heading(level: 2)[Planche vectorielle : attribution d'un prêt]
La consultation des options ne réserve pas une copie. L'attribution, la priorité et la satisfaction de réservation sont recontrôlées dans une seule transaction. Le bloc alternatif décrit un second message concurrent ; il ne simule pas une capture d'exécution.
#figure(image("../docs/diagrams/05-loan-approval.svg", height: 480mm, width: 100%, fit: "contain"), caption: [Séquence UC06 et UC07 : demande, options, attribution et conflit, avec validation et remplacement du document JSON.]) <sequence-pret>
