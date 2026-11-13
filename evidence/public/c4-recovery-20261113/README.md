# Couple C4 — captures synthétiques du 13 novembre 2026

Ces sept captures proviennent du même parcours réel : API7aa9b05 et webf59c7af,
Chrome157.0.8103.51, deux services Flask et JSON temporaire. Les empreintes
figurent dans le [reçu original](../c4-browser-7aa-f59-20261113.json).
Une [réexécution indépendante](../c4-browser-independent-20261113.json) vérifie
les mêmes45contrôles dans de nouvelles sorties. Aucun compte réel, mot de passe
saisi ou clé d'opération brute n'est affiché.

- [Fiche du film après création](actual-film-desktop.png).
- [Profil modifié sur mobile](actual-profile-mobile.png).
- [Collection privée sur mobile](actual-collection-mobile.png).
- [Création de prêt incertaine après réponse perdue](actual-uncertain-loan.png).
- [Création de réservation incertaine après réponse perdue](actual-uncertain-reservation.png).
- [Prêt rendu sur mobile](actual-returned-loan-mobile.png).
- [Réservation prioritaire après retour](actual-ready-reservation-desktop.png).

Le proxy local coupe sa connexion au Web après réception du201 de l'API. Une
reprise manuelle de la même demande retrouve le même identifiant, avec une seule
entité, un seul événement de création et un reçu inchangé. Cela qualifie la
reprise HTTP/JSON de cette paire ; ce n'est ni une preuve MongoDB, ni une panne
physique du réseau, ni un benchmark ou une qualification globale d'accessibilité.
