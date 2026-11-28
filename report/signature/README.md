# Rapport RT0705 — CineVault Signature Edition

[Lire le rapport scientifique](RT0705_CineVault_Mathieu_Kuhnapfel.pdf).

Cette édition datée du 28 novembre 2026 conserve le corps scientifique
et les planches vectorielles de l’édition Enterprise 2.1. Elle ajoute les
protocoles, résultats et limites de la recherche rapide, de la disponibilité,
de la bibliothèque, de la fiche film, de l’annuaire et de la répétition de
soutenance. La page de mesures HTTP s’appuie sur les
[projections du catalogue](../../evidence/public/signature-http-projections-20261128.json)
et les [renouvellements de session de l’annuaire](../../evidence/public/signature-directory-activity-20261128.json).
Le rapport décrit aussi le [relevé local d’exploitation](../../evidence/public/signature-operations-readout-20261127.json).
Les résultats propres au candidat
Signature proviennent de bancs locaux. Les dates et révisions historiques
restent indiquées dans le corps. La qualification du staging signé reste
ouverte.

## Reproduire

Depuis la racine du dépôt, avec Python 3.13.

```sh
python -B scripts/build_report.py --edition signature
```

Le script vérifie l’archive de Typst 0.15.1 et fixe l’horodatage du PDF.
Le PDF est composé avec les polices embarquées de Typst. Employer
`--typst` pour un binaire de la même version déjà vérifié.

Les builds locaux Windows et Linux WSL donnent le même SHA-256.
Les 23 pages A4 et les deux planches A2 ont été rendues et les
59 liens internes ont été vérifiés.

[Source Typst](main.typ) · [chapitres communs](../enterprise-2.1/chapters.json) ·
[complément Signature](signature-evidence.typ) · [configuration](build-config.json) ·
[reçu de vérification](verification.json)

Le [workflow de documentation](../../.github/workflows/docs.yml)
recompile le PDF Signature sous Ubuntu et Windows. Sur le chemin de
qualification, il compare le PDF Ubuntu aux octets du commit et au
reçu de compilation avant de demander l’attestation. Le contrôle de
provenance vérifie ensuite la signature et le commit source. Il publie
un résultat propre à cette édition sous `signature-report-verified-provenance`.

Les [sources et le PDF Enterprise 2.1](../enterprise-2.1/README.md) et
le [rapport original v1](../README.md) sont conservés dans leurs éditions.
