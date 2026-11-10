# Contrat réel de la paire web/API

`scripts/check_enterprise_pair.py` démarre l’API dans un processus et un interpréteur distincts sur la boucle locale, avec un magasin JSON temporaire, des clés et une identité synthétique neufs. Le frontend utilise ses vraies routes Flask, sa session, son contrôle CSRF et son client HTTP. Aucun service ou compte du laboratoire n’est utilisé.

```console
python scripts/check_enterprise_pair.py --api-root ../cinevault-api --web-root ../cinevault-web --report reports/pair-check.json
```

L’interpréteur appelant doit posséder les dépendances du web. Par défaut, le même exécutable Python sert au processus API ; `--api-python` permet un environnement distinct possédant les dépendances API. Le processus API ferme son serveur à la fermeture de son entrée ; cette fermeture évite de laisser le descendant de l’interpréteur venv Windows actif.

La CI crée un environnement par service et transmet explicitement l’interpréteur API. Leurs listes épinglées ne doivent pas être fusionnées : elles peuvent contenir des versions différentes d’un même paquet, notamment Gunicorn. Le premier essai distant a détecté ce conflit d’installation ; la correction garde les deux ensembles de dépendances intacts.

Le contrôle vérifie connexion avec contexte client signé, bearer réel, édition inchangée des listes, persistance exacte et refus des éditions concurrentes. Trois cas couvrent les séparateurs, guillemets, Unicode, CR/LF/NUL et trente noms/genres de longueur maximale avec caractères astraux. Il vérifie aussi cinq échecs de réauthentification puis429 même avec le bon secret. Le reçu identifie les commits, l’empreinte des sources applicatives et si celles-ci correspondent à un état Git propre.

La version v1 a réellement échoué sur l’altération des acteurs ; la paire API `c0a6d616` / web `53735465` réussit localement. Le workflow `Enterprise JSON pair contract` épingle les deux commits complets et exécute ce contrôle sur Ubuntu et Windows. Sa présence n’est pas une preuve de réussite distante : consulter la CI de la révision publiée.

Cette frontière ne simule pas le transport web–API, mais l’entrée navigateur est le client de test Flask. Ce gate ne valide ni Docker, ni Swarm, ni HTTPS, ni la couche MongoDB. Les tests Playwright, les contrôles d’image et les futurs contrats MongoDB restent séparés. Les échecs critiques ne sont pas assouplis pour faire correspondre deux moteurs.
