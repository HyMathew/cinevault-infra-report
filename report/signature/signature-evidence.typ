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

Sur MongoDB 8.0.38 et 2 501 comptes synthétiques, six plans ont utilisé l’index des identifiants pour la page. Le préfixe seul correspond à 250 comptes et son comptage lit 251 clés sans examiner leurs documents. Le comptage des gestionnaires actifs sans préfixe examine les 2 501 documents. La page à l’offset 1 800 parcourt 1 850 clés et retourne 50 profils. Ces mesures isolent le travail du moteur. La latence HTTP et la charge concurrente restent à mesurer pour ce parcours.

#heading(level: 2)[Concurrence observée dans le parcours de soutenance]
Deux membres déposent chacun une demande de prêt pour le même film. Une barrière commune déclenche deux soumissions depuis le poste de test pour le même exemplaire. Chrome et Firefox ont observé la même issue sur le couple Flask et le stockage JSON jetable. Le Web renvoie une redirection 303 après l’attribution et un conflit 409 pour l’autre demande. L’API renvoie respectivement 200 et 409. Le fichier final contient un prêt actif et une demande encore en attente. Un troisième membre prend la première place dans la file de réservation. La fiche, la réponse REST et le fichier concordent sur l’identité, le titre et l’année du film. Ce scénario démontre un cas du contrat de concurrence avec deux clients synchronisés, sur JSON local.

#heading(level: 2)[Corrélation et fraîcheur des observations]
Les réponses Web portent leur identifiant de requête. Le journal Web relie ses identifiants aux réponses de l’API par le champ `api_request_ids`. Le refus 403 d’accès à l’administration est émis par le Web après la lecture d’identité API `/api/v1/me`, qui répond 200. Le reçu montre aussi la corrélation des deux décisions d’attribution. Les contrôles enregistrent le modèle de route et le statut.

La sonde date son relevé et l’associe à un environnement. La consultation opérateur écarte les résultats anciens ou d’un autre environnement. Deux services Flask isolés ont répondu 200. Après arrêt du Web local, seule l’API a gardé sa réponse 200. Cette observation laisse ouverts l’état du réplica, l’état des tâches Swarm, les attestations et la réception d’alerte pour le staging signé.

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
  [Répétition], [5a2936b / 1693459], [signature-rehearsal-20261127.json],
)

Les reçus d’#link("https://github.com/HyMathew/cinevault-infra-report")[infrastructure] sont classés sous `evidence/public/`. Les références abrégées sont identifiées par leur empreinte complète dans ces fichiers. Les mesures Signature sont issues de bancs locaux. La qualification CI historique, le déploiement JSON du 9 novembre et les essais de composants identifient chacun leurs propres révisions.

Sur API 5a2936b et Web 1693459, les suites complètes locales ont obtenu 638 tests API réussis et 541 tests Web réussis sous Windows et Linux. La suite API conserve neuf tests ignorés et 44 sous-tests réussis. Le contrôle académique rejoue 93 échanges et valide 44 opérations OpenAPI. Le manifeste Infra permet de faire rejouer les deux révisions ensemble en CI. Le PDF Signature doit recevoir sa propre attestation après exécution du workflow officiel.

La lecture officielle du 27 novembre a retrouvé OpenSSL 3.5.9-r1 dans les huit index Alpine ciblés et a reçu HTTP 404 pour l’archive OpenSSL 3.5.10. Les scans CI du couple de qualification bloquent la publication à cause des avis classés High. L’évaluation conjointe d’images signées sur les trois VM, la migration intégrée et le retour arrière du staging restent à exécuter.
