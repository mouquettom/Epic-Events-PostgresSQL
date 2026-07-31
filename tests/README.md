# Tests -- Epic Events CRM

## Objectif

Ce dossier contient l'ensemble des tests automatisés du projet **Epic
Events CRM**.

Les tests sont organisés par niveau afin de garantir :

-   la validation de la logique métier ;
-   la fiabilité des accès aux données ;
-   le bon fonctionnement des scénarios utilisateurs ;
-   la non-régression lors des évolutions du projet.

------------------------------------------------------------------------

# Architecture

``` text
tests/
│
├── conftest.py
├── factories.py
│
├── unit/
├── integration/
└── functional/
```

## Tests unitaires (`unit/`)

Les tests unitaires vérifient le comportement d'une classe ou d'une
fonction de manière isolée à l'aide de mocks.

Ils couvrent notamment :

-   Controllers
-   Services
-   Utilitaires (`password.py`)

Exemples :

-   `test_auth_controller.py`
-   `test_client_service.py`
-   `test_event_controller.py`

------------------------------------------------------------------------

## Tests d'intégration (`integration/`)

Les tests d'intégration vérifient la communication entre plusieurs
composants réels de l'application.

Ils couvrent notamment :

-   les repositories SQLAlchemy ;
-   la connexion PostgreSQL ;
-   le service d'authentification.

Exemples :

-   `test_client_repository.py`
-   `test_contract_repository.py`
-   `test_auth_service.py`

------------------------------------------------------------------------

## Tests fonctionnels (`functional/`)

Les tests fonctionnels reproduisent les principaux scénarios métier de
l'application.

Ils permettent de valider les workflows complets selon les différents
rôles :

-   Gestion
-   Commercial
-   Support

Ils vérifient notamment :

-   les permissions ;
-   les créations, modifications et suppressions ;
-   les parcours utilisateurs.

Exemples :

-   `test_management_workflow.py`
-   `test_commercial_workflow.py`
-   `test_support_workflow.py`
-   `test_permissions_workflow.py`

------------------------------------------------------------------------

# Exécution des tests

Lancer tous les tests :

``` bash
pytest
```

Mode verbeux :

``` bash
pytest -v
```

Exécuter uniquement les tests unitaires :

``` bash
pytest tests/unit
```

Exécuter uniquement les tests d'intégration :

``` bash
pytest tests/integration
```

Exécuter uniquement les tests fonctionnels :

``` bash
pytest tests/functional
```

------------------------------------------------------------------------

# Couverture de code

Générer le rapport de couverture :

``` bash
pytest --cov=app --cov-report=term-missing
```

------------------------------------------------------------------------

# Résultat

À la date de rédaction de ce document :

-   481 tests exécutés
-   95 % de couverture de code

Cette couverture concerne l'ensemble des couches applicatives :

-   Controllers
-   Services
-   Repositories
-   Workflows fonctionnels
-   Authentification
-   Gestion des permissions