# Rapport RT0705, édition Enterprise 2.1

[RT0705_CineVault_Mathieu_Kuhnapfel.pdf](RT0705_CineVault_Mathieu_Kuhnapfel.pdf)

Cette édition reprend le socle pédagogique, puis présente MongoDB, la migration,
la reprise, la vérification de TLS, les mesures et l’exploitation. Elle précise
la distinction entre qualification isolée et staging Swarm. La v1 est
[conservée séparément](../RT0705_CineVault_Mathieu_Kuhnapfel.pdf).

## Reconstruire le PDF

Depuis la racine du dépôt.

```sh
python -B scripts/build_report.py --edition enterprise-2.1
```

La [source Typst](main.typ), les [chapitres](chapters.json) et la
[source DOT](figures/adaptateurs-mongodb.dot) sont modifiables. La compilation
utilise Typst 0.15.1, ses polices embarquées et une date fixe. Le script accepte
le chemin d’un compilateur déjà vérifié avec `--typst`.

Les compilations Windows et Linux ont produit 764 117 octets, SHA-256
`9c891e534242b48170b0ca3d11bcab9b29b19bbea2bc83867ae2b51d534b2992`.
Les vingt pages ont été rendues et inspectées. Les dix-huit pages A4 portent
le corps et les preuves. Les deux planches A2 conservent la lisibilité des
diagrammes. La [preuve de vérification](verification.json) décrit les contrôles,
les rendus et les corrections de la relecture indépendante.
