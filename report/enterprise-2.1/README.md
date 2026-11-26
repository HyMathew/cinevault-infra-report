# Rapport RT0705, édition Enterprise 2.1

[RT0705_CineVault_Mathieu_Kuhnapfel.pdf](RT0705_CineVault_Mathieu_Kuhnapfel.pdf)

Cette édition reprend le socle pédagogique, puis présente MongoDB, la migration,
la reprise, la vérification de TLS, les mesures et l’exploitation. Elle précise
la distinction entre qualification isolée et staging Swarm. Elle référence la
paire candidate API `4dd5cd9` et Web `2607907`, les reçus de reprise et de
circulation ainsi que les pages utilisées du sujet RT0705 et des cours C0 à C5. La v1 est
[conservée séparément](../RT0705_CineVault_Mathieu_Kuhnapfel.pdf).

Le PDF fixe ses résultats au 21 novembre. La
[qualification du candidat](../../docs/quality/ENTERPRISE_21_QUALIFICATION.md)
donne les révisions et preuves des rejeux ultérieurs.

## Reconstruire le PDF

Depuis la racine du dépôt.

```sh
python -B scripts/build_report.py --edition enterprise-2.1
```

La [source Typst](main.typ), les [chapitres](chapters.json) et la
[source DOT](figures/adaptateurs-mongodb.dot) sont modifiables. La compilation
utilise Typst 0.15.1, ses polices embarquées et une date fixe. Le script accepte
le chemin d’un compilateur déjà vérifié avec `--typst`.

Les compilations Windows et Linux ont produit 778 774 octets, SHA-256
`8c70cd4b392e9b79d70ff8a1a4b90f10cb674742faf4c11cfe94e43ea17eed5a`.
Les vingt pages ont été rendues et les six pages modifiées inspectées.
Les 45 destinations internes ont été vérifiées. Les dix-huit pages A4 portent
le corps et les preuves. Les deux planches A2 conservent la lisibilité des
diagrammes. La [preuve de vérification](verification.json) décrit les contrôles,
les rendus et les corrections de la revue universitaire.
