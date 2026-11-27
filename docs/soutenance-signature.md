# Soutenance RT0705 de CineVault Signature

La démonstration associe chaque manipulation à un invariant ou à une preuve.
Annoncer à chaque scène si l’observation est faite en direct, sur un banc
local, en CI ou à partir d’un relevé enregistré sur RemoteLabz.

## Préparation

- Préparer un catalogue synthétique, un membre, un gestionnaire, un
  administrateur et un film avec un exemplaire. Utiliser un projet Compose
  séparé pour les écritures de démonstration.
- Ouvrir les deux applications dans les dépôts voisins, le [contrat REST](api.md),
  les [diagrammes et flux](architecture.md) et la [traçabilité RT0705](requirements/TRACEABILITY.md).
- Vérifier le contexte Docker et le mode de persistance de chaque banc.
  Déterminer avant l’oral si les trois VM sont accessibles. Garder sous la
  main les liens des reçus ci-dessous et le [rapport historique reconstruit](../report/enterprise-2.1/README.md).
- Présenter uniquement des données synthétiques. Masquer les identités du
  laboratoire et limiter les observations du service en place à la lecture.

## Démonstration courte, 12 minutes

| Scène | Manipulation et fait à montrer | Preuve de secours |
| --- | --- | --- |
| 1. Produit, 2 min | Suivre accueil, catalogue et recherche rapide avec Ctrl+K ou ⌘K. Taper un titre, choisir une suggestion au clavier, ouvrir la fiche et créer une réservation comme membre. Montrer la collection et le catalogue à 390 px. | [Qualification recherche rapide](quality/SIGNATURE_QUICK_SEARCH.md) pour le dialogue. [Acceptation produit 2.1](../evidence/public/exact-candidate-acceptance-20261126.json) pour le catalogue et les autres parcours à leurs révisions. |
| 2. Architecture distribuée, 2 min | Présenter les rôles des trois VM et les services, réseaux et volumes observés. Suivre une requête de Web vers API puis vers la seule persistance active. Sur le banc académique, comparer fichier JSON, réponse REST et fiche rendue par Jinja. Expliquer où MongoDB intervient en mode Enterprise. | [Déploiement Swarm v1 exécuté](deploiement-swarm-enterprise.md), [exercices A/B/C](pedagogical-validation.md) et [Compose en clones neufs](../evidence/public/compose-clean-clone-20261126.json). Le reçu de [MongoDB sur overlay avec TLS](../evidence/public/swarm-mongodb-overlay-tls-20261125.json) qualifie un essai de composant. |
| 3. Concurrence, 1 min 30 | Dans le banc synthétique, présenter deux demandes concurrentes portant sur le même exemplaire. Lire les deux réponses puis l’état final, avec un seul prêt actif pour l’exemplaire. Distinguer la concurrence de deux demandes et le rejeu d’une seule demande. | [Contrats MongoDB des services](quality/MONGODB_SERVICE_CONTRACTS.md) pour l’invariant et le banc. [Élection et rejeu](../evidence/public/mongodb-election-idempotency-20261126.json) pour le cas distinct de la réponse perdue pendant une élection. |
| 4. Segmentation, 1 min 30 | Comparer les ports publiés et les réseaux effectifs. Montrer le frontal accessible, l’API et MongoDB réservés à leurs chemins autorisés, puis un échange légitime entre Web et API. Décrire le rôle de la liaison TLS entre l’API et MongoDB. | [Déploiement et réseau v1](deploiement-swarm-enterprise.md), [précontrôle des trois nœuds](../evidence/public/swarm-predeployment-readiness-20261126.json) et [essai overlay MongoDB](../evidence/public/swarm-mongodb-overlay-tls-20261125.json). Ces essais portent sur des périmètres distincts. |
| 5. Détection, 1 min 30 | Sur le banc, ouvrir l’administration en tant que membre. Montrer le refus HTTP 403 et le même identifiant de requête entre la réponse et le journal, avec le statut et la route. Montrer une réception d’alerte seulement si le destinataire est effectivement configuré et que le reçu correspond à l’événement montré. | [Journaux et corrélation](observability.md). Le [reçu de remise inter-hôtes](../evidence/public/operational-watch-cross-host-20261126.json) concerne une campagne de qualification distincte. |
| 6. Résilience, 1 min 30 | Sur un banc isolé, suivre 200 → 502 → 200 lors d’un arrêt puis redémarrage du Web derrière Caddy. Relever les heures des observations et relire le film connu. Expliquer ce qui est mesuré et pourquoi un redémarrage du Web diffère d’une restauration de données. | [Sonde TLS pendant l’arrêt Web](../evidence/public/operational-proxy-http-20261126.json), [restauration MongoDB contrôlée](../evidence/public/mongodb-backup-http-20261126.json). Présenter la durée comme mesurée sur le banc concerné. |
| 7. Chaîne de livraison, 2 min | Suivre une révision jusqu’au workflow, aux tests, à la nomenclature SBOM, au scanner, au digest, à la signature et à l’attestation. Montrer comment un avis High OpenSSL empêche la publication du couple candidat et donc la remise au staging. | [Périmètre de qualification](quality/ENTERPRISE_21_QUALIFICATION.md), [contrôle de provenance par tentative](../evidence/public/image-attestation-exact-attempt-20261126.json), [précontrôle des images](../evidence/public/staging-image-pair-preflight-20261126.json). Associer chaque digest au reçu de son propre essai. |

## Démonstration approfondie, 25 minutes

Reprendre les sept scènes. Accorder deux minutes de plus au modèle JSON et
aux exercices A/B/C, trois minutes à l’état final des prêts et réservations,
trois minutes aux flux Swarm et TLS, deux minutes à la restauration
et trois minutes au rapport CI et à la vérification de la provenance.

### Commandes repères

Depuis le dépôt infrastructure, sur le Compose de démonstration préparé selon le
[guide local](deploiement.md), inventorier les deux services et contrôler le frontal.

```sh
docker compose -p cinevault-local-v2 -f compose.yaml -f compose.enterprise.yaml config --quiet
docker compose -p cinevault-local-v2 -f compose.yaml -f compose.enterprise.yaml ps
curl -fsS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/films
```

Sur le manager du Swarm correspondant au [déploiement v1 documenté](deploiement-swarm-enterprise.md),
les commandes suivantes donnent la topologie et l’état observables durant l’oral.

```sh
docker node ls
docker stack services cinevault
docker stack ps cinevault
docker network ls --filter driver=overlay
```

Si le réseau du laboratoire est indisponible, le [gate navigateur local](quality/BROWSER_PAIR_GATE.md)
rejoue le chemin Jinja → API → JSON avec les deux applications réelles.
Le [rapport Enterprise 2.1](../report/enterprise-2.1/README.md) décrit sa
reconstruction avec les outils épinglés.

```sh
python -B scripts/build_report.py --edition enterprise-2.1
```

### Questions probables

| Question | Réponse à défendre |
| --- | --- |
| Pourquoi deux services Flask ? | Le Web traite l’interface, les formulaires et les sessions du navigateur. L’API applique les règles métier et accède au stockage. Le protocole commun est HTTP/JSON. Montrer une requête et la réponse correspondante. |
| Pourquoi garder deux modes de persistance ? | JSON rend les exercices inspectables et fournit un mode monohôte reproductible. MongoDB apporte les transactions, index et réplication à Enterprise. La sélection du backend au démarrage évite les doubles écritures. La migration vérifie le périmètre et le retour arrière. |
| Que prouvent le verrou et la transaction ? | Ils garantissent l’unicité de l’état validé lors des demandes concurrentes couvertes. Le résultat observable est un seul prêt actif pour un exemplaire. Les reçus d’idempotence traitent séparément les réessais. |
| Où les droits sont-ils vérifiés ? | Le Web filtre les destinations selon le rôle courant. Le serveur authentifie et autorise de nouveau les opérations protégées. La recherche rapide ne retourne que des données publiques de films. |
| Pourquoi un réseau interne et TLS ? | Le réseau limite les chemins accessibles. TLS authentifie le service et protège le transport, en complément des identités et privilèges MongoDB. Un test de composant overlay ne suffit pas à qualifier une bascule complète. |
| Pourquoi la signature ne suffit-elle pas ? | Elle lie une identité et un artefact précis. La décision de livraison exige en plus l’exécution attendue, le digest correspondant, le scan des octets exacts et des contrôles runtime. |
| Une seule VM suffirait-elle ? | Pour JSON et une démonstration autonome, oui. Trois VM permettent d’étudier le placement des services, les frontières réseau et les pannes de nœud. La disponibilité effective dépend du quorum et des essais réalisés. |
| Quelles alternatives ? | Une base relationnelle peut exprimer les invariants via transactions et contraintes. Un frontal monoprocédé simplifierait l’exploitation locale. Le choix présent conserve le sujet RT0705 et permet de valider le contrat réseau et les deux modes de stockage. |

En mode hors ligne, afficher les diagrammes et reçus préparés avec leurs
dates et révisions. Utiliser la courte démonstration locale si les dépendances
sont disponibles. Décrire le périmètre exercé par chaque contrôle. Pour la
synthèse, citer explicitement le
déploiement v1, le candidat applicatif et les étapes de staging en attente.
