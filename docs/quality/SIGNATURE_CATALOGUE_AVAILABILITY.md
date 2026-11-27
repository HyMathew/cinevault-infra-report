# Disponibilité au catalogue CineVault Signature

Le catalogue et l’inventaire affichent la disponibilité à côté du nombre
d’exemplaires. Un exemplaire affecté par la file de réservation ne compte
pas dans la disponibilité publique. Le membre prioritaire retrouve sa
possibilité de prêt depuis la fiche authentifiée.

## Contrat

Le Web demande `include=availability` sur la même requête que la page
de films. MongoDB groupe les lectures des exemplaires libres et des
réservations valides. JSON effectue le calcul dans son instantané de
lecture. Chaque valeur publique correspond à un identifiant de film de
la page. La projection exclut les identités et les positions de file.

Le filtre de support sélectionne les films. Le chiffre de disponibilité
couvre tous les supports du film. Un prêt en attente ne retire pas
d’exemplaire. Un prêt actif ou un exemplaire abîmé diminue la quantité
libre. Une réservation en file cesse de compter à l’instant exact de son
expiration. La fiche et la validation métier relisent l’état courant.

Le client demande une seconde fois la page sans projection si l’ancienne
API rejette le paramètre. Quand une valeur manque ou sort de la plage
attendue, la page indique « Disponibilité à vérifier sur la fiche ».
Les erreurs métier du catalogue restent visibles.

## Preuves du candidat

- API `be61632b588e0ef999b07193112dd00b76d3e80a` et Web `4d630352bd1ec33a0d375c94d5f3f28277d8b723`.
  Exécution locale le 27 novembre 2026, avec deux services issus de
  ces sources et des comptes et films synthétiques.
- Chrome, Firefox et WebKit ont exercé le catalogue et l’inventaire en
  mode JSON à 320, 390, 768 et 1 280 px. Chrome a exercé les deux vues
  aux mêmes largeurs avec MongoDB 8.0.38 en réplica local à un membre,
  authentifié par SCRAM-SHA-256.
- Le scénario HTTP a contrôlé une demande de prêt en attente, son
  approbation, le retour avec une réservation en tête, l’accès de ce
  membre et la libération après annulation. Dans le navigateur anonyme,
  chaque chargement normal de la page a produit un seul appel catalogue.
- Le test natif de l’API a observé six commandes de lecture tracées pour
  une page d’un film et six pour une page de cent films. L’égalité porte
  sur les commandes émises, indépendamment du temps de traitement du
  serveur. À l’expiration, les résultats JSON et MongoDB s’alignent sur
  l’oracle unitaire de la fiche, avec révision de persistance stable.
- L’ancienne API `f4457ac7a9f0c4d3eecfbeb74f57b5b7e21eb7f0` a été
  réellement exécutée avec le nouveau Web. Le catalogue s’affiche avec
  le libellé de repli après le refus de la projection.
- Les suites locales ont donné 635 tests API réussis et 9 ignorés, avec
  44 sous-tests réussis, ainsi que 528 tests Web réussis. Les 32 scans axe
  des deux vues ont signalé zéro violation et une vérification incomplète
  par vue sur les attributs ARIA du bouton de recherche rapide. Le
  [parcours de ce bouton](SIGNATURE_QUICK_SEARCH.md) possède sa propre
  vérification clavier, focus et dialogue.

[Catalogue à 390 px](../design/screens-signature-availability/catalogue-390.png) ·
[inventaire à 390 px](../design/screens-signature-availability/inventaire-390.png) ·
[reçu de qualification](../../evidence/public/signature-catalogue-availability-20261127.json)

Le contrat natif est exercé par `tests/test_public_catalogue_service.py` et
repris par le contrôle MongoDB du dépôt API. Ce relevé couvre la lecture
du catalogue en banc local. La qualification du couple signé sur les
trois VM et les mesures à charge de production restent ouvertes.
