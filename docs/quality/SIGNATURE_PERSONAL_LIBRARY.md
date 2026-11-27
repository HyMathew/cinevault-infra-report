# Bibliothèque et historique personnels de CineVault Signature

La collection donne un accès direct aux films à voir, aux prêts en cours
et à l’ensemble des emprunts. Le tableau de bord ouvre aussi les vues
« Retournés » et « Annulés ». Ces actions transmettent toujours
`scope=mine`, y compris pour un gestionnaire. Les confirmations de
création de prêt et de réservation reviennent au suivi personnel.

Un nom de liste est utile pour les listes personnelles et pour une
recherche dans la collection entière. Lors du passage aux favoris, aux
films à voir, vus ou possédés, le Web écarte ce filtre avant l’appel API.
Un filtre de statut sans résultat donne accès aux autres statuts en
conservant le périmètre, le film et la limite de page.

## Reproduction sur les deux révisions

Le 27 novembre 2026, le même parcours a été exécuté avec l’API
`be61632b588e0ef999b07193112dd00b76d3e80a`. Les comptes, films et prêts du banc sont synthétiques.

1. Dans le Web précédent `4d630352bd1ec33a0d375c94d5f3f28277d8b723`,
   la sélection « Films à voir » dans une liste nommée envoie encore le
   nom de la liste à l’API. La vue devient vide. Ouvrir directement les
   films à voir montre que le film restait bien enregistré.
2. Dans le candidat `ec5ff842fe55b1b8dccf81e05bea2ed0f45445d9`, le même formulaire montre le film.
   Le nom de liste disparaît du formulaire et de l’appel API.
3. Avec un gestionnaire ayant un prêt retourné et un autre membre ayant
   un prêt actif, les raccourcis, le retrait du filtre et le tableau de
   bord restent dans le périmètre personnel. Le film de l’autre membre
   n’apparaît pas dans l’historique du gestionnaire.
4. Le gestionnaire demande un prêt puis réserve un autre film occupé.
   Les confirmations conduisent à « Vos emprunts » et « Vos réservations ».

La suite Web locale a réussi 533 tests. Chrome et Firefox ont activé les
contrôles par Tab et Entrée. WebKit a exercé les mêmes parcours au
pointeur sous Windows. Les trois moteurs ont utilisé JSON v2. Le même
parcours a également réussi sur Chrome avec MongoDB 8.0.38 et un réplica
local authentifié. Le reflow a été contrôlé à 320, 390, 768 et 1 280 px.
Les trois raccourcis de collection atteignent la cible de 44 px de hauteur.
Les 48 scans axe n’ont signalé aucune violation. Chaque scan a laissé
un contrôle d’attribut ARIA du bouton de recherche rapide à examiner.
Le [parcours dédié du dialogue](SIGNATURE_QUICK_SEARCH.md) vérifie son
activation et son focus.

[Collection à 390 px](../design/screens-signature-library/collection-390.png) ·
[historique à 390 px](../design/screens-signature-library/historique-390.png) ·
[filtre de prêts sans résultat](../design/screens-signature-library/pret-vide-390.png) ·
[reçu de qualification](../../evidence/public/signature-personal-library-20261127.json)

La couverture porte sur les parcours et rôles indiqués, en banc local.
Les changements Web conservent les permissions d’emprunt et les
règles d’idempotence de l’API. La qualification du staging signé
reste une étape distincte.
