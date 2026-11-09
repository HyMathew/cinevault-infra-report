# Inventaire des opérations REST Enterprise

Relevé depuis OpenAPI au commit API `6a86f2eba9de4dd704c7d4a38d93ab75ff32adc5` :44 couples méthode/chemin. Les réponses listées sont celles du contrat, pas la déclaration que chaque code a été observé en réseau. Les droits de rôle/propriété et traitements sont détaillés dans les sources et [les modèles d’exécution](execution-model.md). Le manifeste des [exemples synthétiques](examples/README.md) précise les échanges réellement exécutés hors réseau.

| Méthode | Chemin | Opération du contrat | Authentification déclarée | Codes du contrat |
|---|---|---|---|---|
| POST | `/api/v1/auth/register` | `register` | Public | 201, 401, 409, 422, 429, 503 |
| POST | `/api/v1/auth/login` | `login` | Public | 200, 401, 429 |
| POST | `/api/v1/auth/logout` | `logout` | Bearer requis | 204, 401 |
| GET | `/api/v1/me` | `getMe` | Bearer requis | 200, 401 |
| PATCH | `/api/v1/me` | `updateMe` | Bearer requis | 200, 401, 422 |
| PUT | `/api/v1/me/password` | `changePassword` | Bearer requis | 204, 401, 422 |
| GET | `/api/v1/users` | `listUsers` | Bearer requis | 200, 401, 403, 422 |
| GET | `/api/v1/users/{id}` | `getUser` | Bearer requis | 200, 401, 403, 404 |
| PATCH | `/api/v1/users/{id}` | `adminUpdateUser` | Bearer requis | 200, 401, 403, 404, 409, 422 |
| GET | `/api/v1/movies` | `listMovies` | Public | 400, 413, 415, 422, 503, 404, 409, 200 |
| POST | `/api/v1/movies` | `createMovie` | Bearer requis | 401, 403, 400, 413, 415, 422, 503, 404, 409, 201, 429 |
| GET | `/api/v1/movies/{id}` | `getMovie` | Public | 400, 413, 415, 422, 503, 404, 409, 200 |
| PUT | `/api/v1/movies/{id}` | `replaceMovie` | Bearer requis | 401, 403, 400, 413, 415, 422, 503, 412, 428, 404, 409, 200 |
| DELETE | `/api/v1/movies/{id}` | `deleteMovie` | Bearer requis | 401, 403, 400, 413, 415, 422, 503, 412, 428, 404, 409, 204 |
| GET | `/api/v1/copies` | `listCopies` | Public | 400, 413, 415, 422, 503, 404, 409, 200 |
| POST | `/api/v1/copies` | `createCopy` | Bearer requis | 401, 403, 400, 413, 415, 422, 503, 404, 409, 201 |
| GET | `/api/v1/copies/{id}` | `getCopy` | Public | 400, 413, 415, 422, 503, 404, 409, 200 |
| PUT | `/api/v1/copies/{id}` | `replaceCopy` | Bearer requis | 401, 403, 400, 413, 415, 422, 503, 412, 428, 404, 409, 200 |
| DELETE | `/api/v1/copies/{id}` | `deleteCopy` | Bearer requis | 401, 403, 400, 413, 415, 422, 503, 412, 428, 404, 409, 204 |
| GET | `/api/v1/collections` | `listCollections` | Bearer requis | 400, 401, 403, 404, 409, 413, 415, 422, 503, 200 |
| POST | `/api/v1/collections` | `createCollectionEntry` | Bearer requis | 400, 401, 403, 404, 409, 413, 415, 422, 503, 201 |
| GET | `/api/v1/collections/{id}` | `getCollectionEntry` | Bearer requis | 400, 401, 403, 404, 409, 413, 415, 422, 503, 200 |
| PUT | `/api/v1/collections/{id}` | `replaceCollectionEntry` | Bearer requis | 400, 401, 403, 404, 409, 413, 415, 422, 503, 412, 428, 200 |
| DELETE | `/api/v1/collections/{id}` | `deleteCollectionEntry` | Bearer requis | 400, 401, 403, 404, 409, 413, 415, 422, 503, 412, 428, 204 |
| GET | `/api/v1/audit-events` | `listAuditEvents` | Bearer requis | 400, 401, 403, 404, 409, 413, 415, 422, 503, 200 |
| POST | `/api/v1/loans` | `requestLoan` | Bearer requis | 400, 401, 403, 404, 409, 413, 415, 422, 503, 201 |
| GET | `/api/v1/loans` | `listLoans` | Bearer requis | 400, 401, 403, 404, 409, 413, 415, 422, 503, 200 |
| GET | `/api/v1/loans/{id}` | `getLoan` | Bearer requis | 400, 401, 403, 404, 409, 413, 415, 422, 503, 200 |
| POST | `/api/v1/loans/{id}/approve` | `approveLoan` | Bearer requis | 400, 401, 403, 404, 409, 413, 415, 422, 503, 412, 428, 200 |
| POST | `/api/v1/loans/{id}/return` | `returnLoan` | Bearer requis | 400, 401, 403, 404, 409, 413, 415, 422, 503, 412, 428, 200 |
| POST | `/api/v1/loans/{id}/cancel` | `cancelLoan` | Bearer requis | 400, 401, 403, 404, 409, 413, 415, 422, 503, 412, 428, 200 |
| GET | `/api/v1/availability` | `getAvailability` | Public | 400, 401, 403, 404, 409, 413, 415, 422, 503, 200 |
| GET | `/api/v1/loans/{id}/options` | `getLoanOptions` | Bearer requis | 400, 401, 403, 404, 409, 413, 415, 422, 503, 200 |
| POST | `/api/v1/reservations` | `createReservation` | Bearer requis | 400, 401, 403, 404, 409, 413, 415, 422, 503, 201 |
| GET | `/api/v1/reservations` | `listReservations` | Bearer requis | 400, 401, 403, 404, 409, 413, 415, 422, 503, 200 |
| GET | `/api/v1/reservations/{id}` | `getReservation` | Bearer requis | 400, 401, 403, 404, 409, 413, 415, 422, 503, 200 |
| POST | `/api/v1/reservations/{id}/cancel` | `cancelReservation` | Bearer requis | 400, 401, 403, 404, 409, 413, 415, 422, 503, 412, 428, 200 |
| POST | `/api/v1/catalogue/import` | `importCatalogue` | Bearer requis | 400, 401, 403, 409, 413, 415, 422, 428, 503, 200 |
| GET | `/api/v1/catalogue/export` | `exportCatalogue` | Bearer requis | 401, 403, 422, 503, 200 |
| GET | `/api/v1/statistics` | `getStatistics` | Bearer requis | 401, 403, 422, 503, 200 |
| GET | `/api/v1/recommendations` | `getRecommendations` | Bearer requis | 401, 403, 422, 503, 200 |
| GET | `/api/v1/metadata/search` | `searchExternalFilms` | Bearer requis | 401, 403, 422, 429, 503, 200 |
| GET | `/api/v1/metadata/{identity}` | `getExternalFilm` | Bearer requis | 401, 403, 422, 429, 503, 200 |
| GET | `/api/v1/posters` | `getCachedPosters` | Public | 422, 503, 200 |

Les cinq opérations legacy `/api/films` et `/api/films/{id}` et le contrôle `/health` appartiennent au mode pédagogique/système et sont documentés séparément. HEAD et OPTIONS automatiques ne sont pas comptés comme fonctions métier supplémentaires. Le contrat JSON décrit les représentations ; les validateurs Python assurent aussi références, chronologie, droits et transitions.
