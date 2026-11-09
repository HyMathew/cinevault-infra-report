# Diagrammes CineVault — modèles statiques vérifiés

Reprise du 9 novembre 2026 : dix séquences D2 préexistantes conservées, recompilées en SVG et confrontées au code ; cas d'utilisation PlantUML rendu en SVG sans modifier sa source. Les schémas décrivent l'ordre des messages, les traitements et les verrous. Ils ne constituent ni des captures réseau, ni une preuve de concurrence réelle, ni une validation du déploiement Swarm.

Références de code communiquées pour cette revue : API `6a86f2e`, web `4883876`. Le client web comporte en outre un correctif local de contrôle des réponses HTTP/JSON, encore non commité pendant la revue. Aucun Git n'a été exécuté : ces identifiants ne constituent pas une attestation indépendante de HEAD. Les empreintes des fichiers réellement lus sont conservées dans `source-manifest.json` ; elles identifient l'instantané statique plus précisément que ces seuls identifiants.

La seule erreur de route relevée dans les séquences a été corrigée : figure 01, `GET /catalogue` est devenu `GET /films`, conformément au blueprint web. Les autres parcours et les nuances de verrouillage existantes ont été préservés. Aucun changement à `use-cases.puml` n'a été nécessaire.

## Figures et sources de vérification

Chemins API relatifs à `cinevault-api/app/` ; chemins web relatifs à `cinevault-web/app/`. Les numéros de ligne correspondent à l'instantané lu, et peuvent évoluer après une modification de code.

| Figure / rendu | Traitement confronté au code | Sources principales |
|---|---|---|
| [01 Catalogue](01-catalogue.svg) | Lecture publique sans écriture ; copies et disponibilité lues séparément ; conversion puis Jinja | API `enterprise_catalogue.py:175,226`, `storage_v2.py:209` ; web `routes.py`, `api_client.py` (`search`, `get`, `movie_view`) |
| [02 Inscription](02-registration.svg) | HMAC de contexte, contrôle initial, admission persistée avant Argon2, recontrôle final sous verrou métier | API `client_context.py`, `enterprise_auth.py:206`, `registration_admission.py:61` ; web `accounts.py:71`, `api_client.py` (`anonymous_auth`) |
| [03 Connexion](03-login.svg) | Vérification Argon2 sous transaction métier, limitations utilisateur/source, session opaque et cookie | API `enterprise_auth.py:251`, `client_context.py` ; web `accounts.py:110` |
| [04 Mutation versionnée](04-versioned-mutation.svg) | Deux transactions : précontrôle puis écriture ; réseau externe éventuel entre les deux ; nouvel If-Match vérifié | API `enterprise_catalogue.py:106,254` ; web `routes.py:86` |
| [05 Attribution de prêt](05-loan-approval.svg) | Demande sans copie ; options non réservantes ; attribution, priorité FIFO et satisfaction de réservation dans le même commit | API `enterprise_lending.py:165`, `reservation_service.py` ; web `lending.py` |
| [06 Réservation et retour](06-reservation-return.svg) | Attente de 14 jours, expiration opportuniste, retour sans attribution automatique, recalcul de priorité | API `enterprise_reservations.py:22,73`, `enterprise_lending.py:242`, `reservation_service.py` ; web `lending.py` |
| [07 Import atomique](07-atomic-import.svg) | Copie candidate du lot, reçu idempotent et catalogue dans le même commit ; un refus peut quand même écrire audit/session | API `enterprise_transfer.py:34`, `catalogue_transfer.py`, `idempotency.py:18`, `storage_v2.py:213` ; web `transfer.py` |
| [08 Fournisseur de métadonnées](08-metadata-provider.svg) | Autorisations avant/après réseau ; verrou cache distinct du verrou métier ; quotas réservés avant HTTP ; repli stale | API `enterprise_metadata.py:58`, `metadata.py:419`, `wikimedia.py:32`, `enterprise_catalogue.py:106` ; web `metadata_views.py` |
| [09 Affiche publique](09-public-poster.svg) | Lecture du cache frais sans HTTP fournisseur ; contrôles d'URL/licence ; image demandée directement par le navigateur | API `enterprise_metadata.py:93`, `metadata.py:397` ; web `api_client.py` (`posters`, `safe_poster`), `templates/poster.html`, `__init__.py` (CSP) |
| [10 Lecture privée](10-private-read.svg) | Session invalide : exception sans commit ; session valide : last_seen et révision écrits même pour un GET | API `enterprise_auth.py:120,150`, `storage_v2.py:213` ; web `accounts.py` (`load_identity`, `account_headers`) |
| [Cas d'utilisation UC01–UC14](use-cases.svg) | Capacités des acteurs et héritage des rôles ; exploitation hors HTTP ; aucun parcours réseau prouvé | Blueprints catalogue/auth/collections/lending/reservations/transfer/insights/metadata ; `recovery.py`, `storage_v2.py` |

Les blocs D2 intitulés « alternative », « si » ou « sinon » décrivent des branches conceptuelles, pas une exécution successivement observée. Les appels internes et les opérations de stockage sont simplifiés ; les callbacks s'exécutent dans le processus API. La figure 01 décrit une consultation anonyme ; une identité web connectée ajoute notamment `/me` et les lectures privées de la fiche. Les routes API abrégées dans les figures 05/06 sont sous `/api/v1`.

Les dix séquences couvrent les mécanismes principaux et leurs points délicats. Elles ne remplacent pas une matrice exhaustive de chaque route, chaque erreur et chaque cas d'utilisation. Le filtre de frontière JSON local n'est pas présenté comme une propriété du déploiement distant.

## Outils et provenance

- D2 **0.9.0**, archive officielle `d2-v0.9.0-windows-amd64.tar.gz`. SHA-256 `5f63b643de8f5a6dfb922d172e1b5496e4caf47497c33c4427cf1127f28c340f`, comparé au champ `digest` de la [release officielle](https://github.com/d2lang/d2/releases/tag/v0.9.0). L'exécutable extrait a également été comparé au contenu de cette archive.
- PlantUML **1.2026.9**, [release officielle](https://github.com/plantuml/plantuml/releases/tag/v1.2026.9). Nouveau fichier `.render-tools/plantuml-1.2026.9.verified.jar`, SHA-256 `aa4a1d06f8911c4b842beff4828dd955be431692b631a312d04c0e9fab9581de`, comparé au digest officiel avant exécution. Java rapporte PlantUML `1.2026.9 / 18d0aae` ; Graphviz embarqué `2.44.1`.
- JRE portable **Eclipse Temurin 21.0.13+9**, archive existante `jre.zip`, SHA-256 `2332c0b4cff6bed722da3567c91d5e47568bcba863fa4945d0a8d6fc76158628`, conforme à la provenance Adoptium déjà enregistrée dans `.render-tools/java-provenance.json`. Les **315 fichiers extraits** ont été comparés octet pour octet par empreinte au contenu de l'archive. Aucune installation globale.
- L'ancien `.render-tools/plantuml.jar` est **rejeté** : SHA-256 observé `d640f1d382dd1607c20a3e53e62f97cbad99e579585c749f0077e4553d3114eb`, différent du digest officiel ; Java le déclare invalide/corrompu. Il est préservé pour diagnostic et n'est pas utilisé par `render.ps1`.
- Aperçus : Node **24.21.0**, `puppeteer-core` local verrouillé dans `.render-tools/package-lock.json`, Chrome local en mode sans interface. `render-preview.cjs` bloque toutes les requêtes autres que `file:` et `data:`. Ce contrôle lit des SVG locaux, pas l'application CineVault.

Seuls les téléchargements et la consultation des métadonnées officielles des outils ont utilisé le réseau. Aucun accès VM, application, secret ou VPN, aucune opération Git, aucun test applicatif/réseau dans ce travail.

## Reproduction locale

Depuis ce dossier, avec les outils portables déjà présents :

```powershell
./render.ps1
node ./render-preview.cjs
```

Les commandes effectives de rendu sont :

```powershell
./.render-tools/d2-v0.9.0/bin/d2.exe --theme 0 --pad 24 01-catalogue.d2 01-catalogue.svg
# Même commande pour chacune des dix sources D2.
./.render-tools/java/jdk-21.0.13+9-jre/bin/java.exe -jar ./.render-tools/plantuml-1.2026.9.verified.jar -charset UTF-8 -tsvg -nometadata use-cases.puml
```

`render.ps1` vérifie les empreintes des trois outils exécutés (D2, Java et JAR PlantUML), échoue si une compilation échoue et conserve les sorties dans `render-d2.log` et `render-plantuml.log`. `render-preview.cjs` génère `previews/*.png` et `visual-qa.json`. Les outils locaux volumineux sont des dépendances de rendu, pas des pièces à publier automatiquement.

## Contrôle visuel et limites

Onze SVG produits sans erreur ; onze aperçus PNG examinés visuellement. Les textes, accents, pointes de flèche et blocs alternatifs sont visibles ; aucun texte hors du cadre racine selon le contrôle géométrique des **282 éléments texte**. Ce contrôle géométrique complète la lecture visuelle et ne prouve pas à lui seul l'absence de tout chevauchement.

Les SVG restent vectoriels et zoomables. Les séquences détaillées demandent du zoom sur petit écran ; le diagramme global des quatorze cas est dense et comporte des croisements de liens. Pour un rapport imprimé, ouvrir chaque figure séparément et éviter de réduire toute une grande séquence à une seule petite vignette. Les captures PNG sont des aperçus, les SVG sont les artefacts de référence.

État documentaire uniquement : compilation et lisibilité contrôlées, cohérence statique revue. Ni fonctionnement actuel des VM, ni couverture académique exhaustive, ni validation de production ne sont conclus ici.

## Rattachement vérifié après la revue

Le contrôle principal du9novembre a vérifié les30 empreintes de source contre les checkouts propres : API `6a86f2eba9de4dd704c7d4a38d93ab75ff32adc5`, web `10612c999cef4a82b268b8d8f900222d713b4e2b`. Le correctif décrit plus haut comme local est désormais commité et déployé ; son comportement distant est vérifié séparément dans [la synthèse des validations](../validation-current.md). Cette précision ne transforme pas la revue statique des schémas en capture réseau.
