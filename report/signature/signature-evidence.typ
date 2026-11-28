#heading(level: 1)[Évaluation de la Signature Edition]

#heading(level: 2)[Recherche depuis chaque écran]
Le catalogue disposait déjà de filtres. Le nouveau contrôle devait permettre de retrouver un film sans interrompre le parcours en cours. Une nouvelle page de recherche aurait réutilisé les contrôles existants, au prix d’une navigation supplémentaire. Le dialogue natif conserve l’écran et son focus. Un lien équivalent vers le catalogue assure le parcours sans JavaScript. Le serveur construit les raccourcis selon le rôle de la session.

Sur un catalogue JSON de neuf films, la saisie groupée ne produit qu’une requête de suggestion. Chaque mesure part de l’événement de saisie et se termine à l’apparition du résultat dans le DOM. Les 250 ms de temporisation sont incluses. Le banc a relevé huit durées par moteur. La navigation a aussi été vérifiée après une réponse tardive, un refus après retrait de rôle et un HTTP 503 contrôlé.

#table(
  columns: (1.1fr, 1fr, 1fr, 1fr), inset: 5pt, stroke: 0.4pt + rgb("b8c4ce"),
  table.header([*Mesure*], [*Chrome*], [*Firefox*], [*WebKit*]),
  [Médiane locale], [291,4 ms], [296,5 ms], [298,5 ms],
  [Mesures], [8], [8], [8],
)
Ces durées décrivent le banc local. Un lecteur d’écran en conditions réelles, le clavier virtuel iOS et un grand catalogue n’ont pas été testés dans cette campagne.

#heading(level: 2)[Disponibilité et priorité de réservation]
Le nombre d’exemplaires du catalogue inclut des exemplaires déjà prêtés ou abîmés. Un appel de détail par film aurait multiplié les échanges. Une route groupée distincte aurait lu le stock dans un autre instantané. L’option de projection du catalogue rassemble les films et leur disponibilité dans la même lecture. La fiche et l’attribution recalculent l’état au moment de leur requête.

Sur MongoDB 8.0.38 authentifié, le banc a observé six commandes de lecture pour une page d’un film et six pour une page de cent films. JSON et MongoDB ont été comparés à la réponse de disponibilité unitaire. Le test isole l’instant exact d’expiration d’une réservation. Dans le scénario HTTP, le retour d’un exemplaire conserve sa priorité au membre en tête de file. L’égalité du nombre de commandes ne borne pas le temps du moteur sous charge.

#heading(level: 2)[Bibliothèque personnelle]
Lors du changement de catégorie, un nom de liste resté dans le formulaire pouvait masquer un film à voir présent dans la collection. Le banc a reproduit le défaut sur le parent du correctif. L’application écarte désormais ce filtre pour les catégories qui ne portent pas de nom de liste. Un gestionnaire disposant d’un prêt retourné retrouve son historique, sans voir le prêt actif d’un autre membre. Les confirmations de création restent dans son espace personnel. Chrome et Firefox ont exercé la navigation par Tab et Entrée. WebKit sous Windows a exercé le même parcours au pointeur.

#pagebreak()
#heading(level: 1)[Lecture de la fiche film]
Le choix d’un film devait rendre visibles ses supports et la prochaine action avant les crédits de l’affiche. L’état de prêt est regroupé en tête. Le synopsis suit l’action, dans la même colonne sur grand écran. Sans exemplaire enregistré, la possibilité de réserver est conservée et la mise en file est annoncée.

Pour prolonger la découverte, la fiche peut demander jusqu’à quatre films apparentés dans sa lecture existante. Le rapprochement se fonde sur des genres communs et, en départage, sur le réalisateur. Il écarte le film courant et tout résultat sans relation. Il utilise uniquement les métadonnées publiques. Le navigateur reçoit les raisons à afficher. La version If-Match du film reste stable lorsque les suggestions changent, tandis que l’ETag de la représentation suit la projection.

JSON et MongoDB ont produit le même résultat sur le jeu de test, qui distingue les départages par réalisateur, titre replié, année et identifiant. Le banc MongoDB a tracé trois commandes de lecture pour cette représentation. Les navigateurs ont vérifié quatre largeurs de 320 à 1 280 px. Le rejeu académique de cette API conserve les 93 échanges et les 44 opérations REST du corpus, dans un stockage temporaire hors réseau.

#figure(
  image("../../docs/design/screens-signature-detail/fiche-1280.png", width: 100%, height: 120mm, fit: "contain"),
  caption: [Fiche d’un film fictif sur le banc local. Le contrôle de disponibilité précède le synopsis.],
)

#pagebreak()
#heading(level: 1)[Administration, concurrence et exploitation]

#heading(level: 2)[Annuaire et coût du filtrage]
L’ancienne vue proposait uniquement de parcourir les pages. Les filtres par préfixe littéral, rôle et statut sont maintenant appliqués à l’annuaire avant pagination. Les formulaires de mise à jour conservent la sélection et la page. Sur les deux persistances, un changement de rôle en deuxième page a ramené le total filtré de 55 à 54. Le refus de désactiver le dernier administrateur a conservé les filtres sur le banc JSON.

Sur MongoDB 8.0.38 et 2 501 comptes synthétiques, six plans ont utilisé l’index des identifiants pour la page. Le préfixe seul correspond à 250 comptes et son comptage lit 251 clés sans examiner leurs documents. Le comptage des gestionnaires actifs sans préfixe examine les 2 501 documents. La page à l’offset 1 800 parcourt 1 850 clés et retourne 50 profils. Ces mesures isolent le moteur. La campagne HTTP sur un jeu distinct figure dans @http-signature.

#heading(level: 2)[Concurrence observée dans le parcours de soutenance]
Deux membres déposent chacun une demande de prêt pour le même film. Une barrière commune déclenche deux soumissions pour un exemplaire. Chrome et Firefox ont observé sur JSON puis sur un réplica MongoDB jetable d’un membre les décisions Web 303 et 409 et les décisions API 200 et 409. Les lectures directes confirment le prêt actif et la demande restée en attente. Un troisième membre prend la première place dans la file. Sur MongoDB, les fenêtres clientes se chevauchent et un seul événement d’attribution a été observé. La fiche, la réponse REST et le stockage concordent sur le film.

#heading(level: 2)[Corrélation et fraîcheur des observations]
Les réponses Web portent leur identifiant de requête. Le journal Web relie ses identifiants aux réponses de l’API par le champ `api_request_ids`. Le refus 403 d’accès à l’administration est émis par le Web après la lecture d’identité API `/api/v1/me`, qui répond 200. Le reçu montre aussi la corrélation des deux décisions d’attribution. Les contrôles enregistrent le modèle de route et le statut.

La sonde date son relevé et l’associe à un environnement. La consultation opérateur écarte les résultats anciens ou d’un autre environnement. Deux services Flask isolés ont répondu 200. Après arrêt du Web local, seule l’API a gardé sa réponse 200. Cette observation laisse ouverts l’état du réplica, l’état des tâches Swarm, les attestations et la réception d’alerte pour le staging signé.

#pagebreak()
#heading(level: 1)[Mesures HTTP du candidat] <http-signature>
#let activity = json("../../evidence/public/signature-directory-activity-20261128.json")
#let projections = json("../../evidence/public/signature-http-projections-20261128.json")
#let window(variant, backend, mode) = activity.at(variant).observations.find(row => row.backend == backend).windows.find(row => row.mode == mode)
#let ms(value) = str(calc.round(value))
#let sample-count = projections.observations.map(pass => pass.scenarios.values().map(
  scenario => scenario.values().map(batch => batch.measurements_ms.len()).sum()
).sum()).sum()

#heading(level: 2)[Projections et parité de réponse]
Sur l’API #text([#projections.api_commit.slice(0, 7)]), quatre passes alternent les deux moteurs. Elles utilisent le même document de 600 films, 1 798 exemplaires et 500 comptes. Par scénario et concurrence, cinq requêtes d’échauffement précèdent 50 GET mesurés. Le temps client inclut la lecture et le décodage JSON. Les #text([#sample-count]) réponses mesurées ont le statut 200 et les corps JSON canonisés concordent. Une première comparaison avait isolé un écart dans l’ordre des supports. Le tri par identifiant a aligné leur ordre entre les deux moteurs.

Pour une page avec disponibilité, le p95 allait de 47 à 49 ms avec JSON et de 52 à 56 ms avec MongoDB à un client. Avec quatre clients, il allait de 303 à 329 ms avec JSON et de 82 à 93 ms avec MongoDB. Le résultat dépend de la concurrence et de la projection.

#heading(level: 2)[Renouvellement des sessions de l’annuaire]
Une lecture autorisée réécrivait l’activité même lorsque l’horloge donnait la même seconde. Espacer les renouvellements aurait changé la politique d’inactivité. L’API #text([#activity.candidate.api_commit.slice(0, 7)]) utilise un instantané commun pour l’identité, le rôle et la page si l’activité est déjà à jour. Quand elle doit avancer, l’API revalide la session dans la transaction de renouvellement.

#let burst(mode) = (
  [#ms(window("previous", "json", mode).p95_ms) → #ms(window("candidate", "json", mode).p95_ms)],
  [#ms(window("previous", "mongodb", mode).p95_ms) → #ms(window("candidate", "mongodb", mode).p95_ms)],
)
#table(
  columns: (1.7fr, 1fr, 1fr), inset: 6pt, stroke: 0.4pt + rgb("b8c4ce"),
  table.header([*Rafale à quatre clients*], [*JSON, p95 en ms*], [*MongoDB, p95 en ms*]),
  [Une session], ..burst("shared_session_concurrent"),
  [Quatre sessions], ..burst("distinct_session_concurrent"),
)

Les #text([#activity.total_measurements]) observations comprennent des lots de 32 GET à horloge fixe. Les deux moteurs passent de 32 révisions à zéro par rafale. Un lot de six appels espacés par moteur et révision utilise l’horloge réelle. Chaque appel renouvelle l’activité.

#let pace(backend, field) = [
  #ms(window("previous", backend, "wall_clock_paced").at(field)) → #ms(window("candidate", backend, "wall_clock_paced").at(field))
]
#table(
  columns: (1.7fr, 1fr, 1fr), inset: 5pt, stroke: 0.4pt + rgb("b8c4ce"),
  table.header([*Appels espacés*], [*JSON, ms*], [*MongoDB, ms*]),
  [Médiane], pace("json", "p50_ms"), pace("mongodb", "p50_ms"),
  [Maximum observé], pace("json", "max_ms"), pace("mongodb", "max_ms"),
)

La première lecture ajoute un coût lorsqu’il faut avancer l’activité. Le contrat natif vérifie l’expiration et la révocation entre lecture et renouvellement.

Les mesures proviennent du poste local. Elles couvrent HTTP sur boucle locale et un réplica MongoDB 8.0.38 jetable d’un membre. Les lots sont trop petits pour publier un p99. Le réseau Swarm, le TLS et les images signées feront l’objet de la qualification intégrée.

#pagebreak()
#heading(level: 1)[Provenance et limites du candidat]

#table(
  columns: (1.05fr, 1.35fr, 1.65fr), inset: 5pt, stroke: 0.4pt + rgb("b8c4ce"),
  table.header([*Campagne*], [*API / Web*], [*Reçu vérifiable dans le dépôt Infra*]),
  [Recherche], [f4457ac / 51b6962], [signature-quick-search-20261127.json],
  [Disponibilité], [be61632 / 4d63035], [signature-catalogue-availability-20261127.json],
  [Bibliothèque], [be61632 / ec5ff84], [signature-personal-library-20261127.json],
  [Fiche film], [3adf53b / 7203e25], [signature-film-detail-20261127.json],
  [Annuaire], [5a2936b / 1693459], [signature-account-directory-20261127.json],
  [Plans de l’annuaire], [API 5a2936b], [signature-account-directory-plans-20261127.json],
  [Répétition JSON], [5a2936b / 1693459], [signature-rehearsal-20261127.json],
  [Répétition MongoDB], [5a2936b / 1693459], [signature-mongo-rehearsal-20261127.json],
  [Projections HTTP], [API 244cd01], [signature-http-projections-20261128.json],
  [Activité de session], [fdc6162 puis 9243cbb], [signature-directory-activity-20261128.json],
)

Les reçus d’#link("https://github.com/HyMathew/cinevault-infra-report")[infrastructure] sont classés sous `evidence/public/`. Les références abrégées sont identifiées par leur empreinte complète dans ces fichiers. Les mesures Signature sont issues de bancs locaux. La qualification CI historique, le déploiement JSON du 9 novembre et les essais de composants identifient chacun leurs propres révisions.

L’API 9243cbb a réussi 640 tests locaux sous Windows, dont le contrôle de renouvellement de session, avec neuf tests ignorés et 44 sous-tests réussis. Le Web 1693459 avait réussi 541 tests locaux. Chrome a exercé l’annuaire de cette paire sur JSON et MongoDB. Le contrôle académique rejoue 93 échanges et valide 44 opérations OpenAPI. Le manifeste Infra retient la paire pour le rejeu en CI. Le PDF Signature doit recevoir sa propre attestation du workflow officiel.

Le relevé du 28 novembre a trouvé OpenSSL 3.5.9-r1 dans les huit index Alpine ciblés et reçu HTTP 404 pour l’archive 3.5.10. Les scans CI antérieurs signalent des avis classés High sur les images de qualification alors construites. Les vérifications des images corrigées et signées, la migration intégrée et le retour arrière du staging sur les trois VM restent à exécuter.
