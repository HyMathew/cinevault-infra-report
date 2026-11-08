# Contrat API cible

Statut : **proposé, à comparer aux tests et à l'implémentation définitive**. Racine JSON UTF-8 `{"films": [...]}`. `id` est un UUID produit par l'API ; il n'est pas accepté dans les propriétés à créer ou à remplacer.

| Champ métier | Règle proposée |
| --- | --- |
| `titre` | chaîne non vide après nettoyage, 1 à 200 caractères |
| `annee` | entier de 1888 à 2100, booléen exclu |
| `realisateur` | chaîne non vide, 1 à 120 caractères |
| `acteurs` | tableau de 0 à 30 chaînes non vides, jusqu'à 120 caractères chacune |
| `support` | `numerique`, `dvd`, `blu-ray`, `vhs` ou `autre` |
| `synopsis` | facultatif, chaîne vide par défaut, 4 000 caractères au maximum |

Le corps est limité à 64 Kio ; JSON malformé, champs inconnus ou répétés, type inattendu et valeurs invalides sont rejetés. `PUT` remplace les propriétés métier plutôt que d'opérer une fusion. Exemple fictif de corps de création :

```json
{"titre":"Exemple","annee":2001,"realisateur":"A. Martin","acteurs":["B. Durand"],"support":"dvd","synopsis":"Un exemple fictif."}
```

| Requête | Réponse cible |
| --- | --- |
| `GET /health` | 200 si stockage exploitable ; 503 sinon |
| `GET /api/films?q=...&support=...` | 200 `{"films": [...]}` ; filtre par titre/réalisateur sans distinction de casse et support exact |
| `GET /api/films/<id>` | 200 film ; 404 si absent ou identifiant invalide |
| `POST /api/films` | 201 film créé et en-tête `Location` ; 400/415/422 si requête invalide |
| `PUT /api/films/<id>` | 200 film remplacé ; 404 si absent ; 400/415/422 si invalide |
| `DELETE /api/films/<id>` | 204 sans corps ; 404 si absent |

En cas d'erreur, forme cible `{"error":{"code":"validation_error","message":"...","fields":{"titre":"..."}}}`, `fields` étant facultatif. Les erreurs 405, 413, 500 et 503 doivent rester cohérentes et ne divulguer ni chemins internes ni traces. Le web doit fixer des délais réseau et ne pas répéter automatiquement une mutation dont le résultat est ambigu.
