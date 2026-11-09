# Exemples JSON entièrement fictifs

Le dossier `academic-json/` illustre les formes réellement présentes dans le candidat API adjacent. Son contrat comporte **42 composants OpenAPI**, comptés depuis `components.schemas`, ainsi que 18 définitions du schéma de stockage. Aucun 43e composant n'a été inventé. `manifest.json` donne les composants, emplacements de schéma HTTP, versions d'outils, empreintes des sources et artefacts, contrôles exécutés et limites.

Le générateur utilise les vrais handlers Flask avec `test_client`, un stockage neuf dans `TemporaryDirectory`, une horloge historique, des UUID maîtrisés et un fournisseur explicitement synthétique. Aucun réseau, serveur, compte réel ou machine distante n'intervient. Le cache local et les validations métier sont ceux de l'API. Les exemples comprennent 93 échanges HTTP couvrant les **44 couples méthode + chemin paramétré déclarés dans OpenAPI**, tous les états des prêts et réservations, des imports JSON/CSV, les politiques de doublon et reçus, les projections publiques/privées, les états techniques et une reprise hors ligne jetable. Les suppressions utilisent des objets jetables dédiés pour préserver le snapshot et les liens des cycles métier. Cette couverture de routes ne signifie pas que toutes leurs branches ou tous leurs cas d'erreur ont été exercés.

Les mots de passe sont des textes d'apprentissage fictifs. Les mécanismes Argon2 réels sont exercés uniquement dans le temporaire ; **les hachages publiés sont volontairement invalides et les tokens remplacés**. Les digests de session ne correspondent pas au token publié. Leur rejet a été vérifié à l'horloge fictive. Les signatures de contexte sont calculées avec une clé publique d'exemple et des dates historiques, puis vérifiées acceptées à cette horloge et refusées après 31 secondes. Ces fichiers ne doivent jamais être importés dans un service réel.

Les identifiants Wikidata, URLs d'images, artistes et licences sont illustratifs : aucun fournisseur ni média n'a été consulté, et aucune attribution réelle ou autorisation de réutilisation n'est affirmée. Les exports contiennent uniquement le catalogue fictif. Le snapshot complet comporte également les comptes et états techniques synthétiques ; ce n'est pas un export catalogue.

Depuis la racine du workspace, avec l'environnement de développement existant de l'API :

```powershell
& cinevault-api/.venv/Scripts/python.exe -B cinevault-infra-report/scripts/academic_json_examples.py --write
& cinevault-api/.venv/Scripts/python.exe -B cinevault-infra-report/scripts/academic_json_examples.py
& cinevault-api/.venv/Scripts/python.exe -B cinevault-infra-report/scripts/test_academic_json_examples.py -v
```

Le premier appel régénère seulement les fichiers possédés par le générateur, après validation complète. Il refuse d'écraser une fixture dont l'empreinte a été changée. Le second vérifie les empreintes, la correspondance des sources, JSON Schema 2020-12 et les formats, les ETags, les états et les lecteurs exécutables. Le dernier introduit des corruptions dans des copies en mémoire pour vérifier que les contrôles les détectent. L'environnement qualité du projet fournit Ruff ; aucune dépendance n'est installée ou téléchargée par ces scripts.

Les empreintes de sources suivent le mode explicite `sha256:utf8-lf:v1` du manifeste : décodage UTF-8 strict, conversion CRLF et CR en LF, puis SHA-256 du texte réencodé UTF-8. Cette règle couvre les sources API, le générateur et ses tests ; elle ne retire ni espaces, ni caractères, ni marqueur BOM. Un checkout Windows CRLF et Linux LF donnent ainsi la même empreinte, mais une altération du texte reste rejetée. Les empreintes des artefacts de données et des snapshots restent calculées sur leurs **octets exacts**, sans normalisation.

Pour une installation sans les environnements locaux nommés ci-dessus, employer un Python où `cinevault-api/requirements-dev.txt` a été installé. L'option `--api-root CHEMIN` du générateur/validateur désigne explicitement le checkout API ; par défaut, les checkouts `cinevault-api` et `cinevault-infra-report` sont frères. Les tests utilisent également ce défaut de checkouts frères.

JSON Schema seul ne prouve ni les droits, ni les références, ni la chronologie. Les assertions du scénario et `validate_document` complètent ce contrôle. `format:password` reste une annotation OpenAPI ; les règles de mot de passe sont exercées par les handlers. Le rapport de reprise décrit les fichiers **neutralisés publiés** ; son empreinte cible a été recalculée après neutralisation des hachages, et ne doit pas être présenté comme un reçu de restauration réelle.

`academic-json/technical-schemas.json` ajoute cinq schémas JSON Schema 2020-12, accessibles par `#/$defs/<nom>`. Ils décrivent les formes générales et contraintes des implémentations ci-dessous, avec champs obligatoires et objets stricts lorsque le lecteur l'exige. Le validateur applique réellement chacun des cinq schémas à son exemple et vérifie aussi les formats. Ils constituent une documentation académique complémentaire, sans modification des contrats ni du code de l'API.

| Schéma | Source exécutée / représentation | Limites complétées par le code |
|---|---|---|
| `LegacyCatalogue` | `Repository._read`, `validation.validate` ; catalogue legacy persistant | Unicité des IDs, lecture du fichier et remplacement transactionnel |
| `Health` | Réponse réussie `/health` de `create_app` | Disponibilité réelle du stockage, qu'un objet `status:ok` isolé ne peut prouver |
| `RecoveryReport` | Rapport produit par `recovery.recover` | Correspondance des empreintes avec les fichiers, compteurs source, révocation et quarantaine |
| `MetadataCache` | `MetadataCache.read/check_value` | Horloge relative, calcul exact TTL/grâce, bornes de taille en octets et cache sans constantes JSON non finies |
| `ClientContext` | Porteur JSON synthétique de ce générateur ; contraintes natives des en-têtes de `client_context.client_address` | HMAC, liaison au corps exact, message, IP canonique et fenêtre de fraîcheur |

Le porteur de contexte n'est pas un nouvel objet JSON reçu par l'API : les trois valeurs natives sont des en-têtes HTTP. Son enveloppe documentaire est stricte ; d'autres en-têtes HTTP textuels restent autorisés, comme dans l'implémentation. Le cache autorise volontairement des valeurs objets JSON génériques sans clé `cache`, conformément au vrai lecteur ; il n'est pas restreint à la forme d'une seule fixture de film. L'admission conserve le schéma existant `cinevault-api/schemas/registration-admission.schema.json`, avec vérification complémentaire de la somme et de l'horloge ; aucun doublon de ce schéma n'est ajouté.

Les formats UUID, IPv4 et IPv6 sont vérifiés par `FormatChecker`. Le validateur URI optionnel de jsonschema est absent de cet environnement ; le script lui enregistre donc un contrôle syntaxique RFC 3986 local, testé aussi avec des URI invalides, sans résolution DNS. Les empreintes des douze artefacts sont identiques entre deux générations neuves ; seul l'horodatage réel de génération du manifeste est destiné à varier.

Ces résultats sont des preuves locales de fixtures synthétiques. Ils n'attestent ni une nouvelle CI, ni un déploiement, ni un audit de sécurité exhaustif.
