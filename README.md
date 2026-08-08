# Epic Events CRM

Application CRM en ligne de commande développée en Python pour gérer les employés, les clients, les contrats et les événements de l’entreprise fictive **Epic Events**.

Le projet repose sur une architecture en couches afin de séparer clairement l’interface utilisateur, les règles métier et l’accès aux données.

---

## Fonctionnalités

### Authentification

- Connexion par email et mot de passe
- Mots de passe hachés avec bcrypt
- Génération de jetons JWT
- Gestion de la session utilisateur
- Expiration des jetons d’accès
- Déconnexion sécurisée

### Gestion des employés

Fonctionnalités réservées au service gestion :

- Lister les employés
- Consulter un employé
- Créer un employé
- Modifier un employé
- Supprimer un employé
- Empêcher la suppression de son propre compte
- Attribution des rôles `GESTION`, `COMMERCIAL` et `SUPPORT`

### Gestion des clients

- Création d’un client par un commercial
- Consultation et modification selon les permissions
- Détection des emails en doublon
- Association automatique du client au commercial connecté
- Suppression d’un client selon les règles métier

### Gestion des contrats

- Création d’un contrat pour un client
- Gestion du montant total et du montant restant
- Signature d’un contrat
- Consultation des contrats
- Liste des contrats non signés
- Liste des contrats non soldés
- Modification selon le rôle et la propriété du contrat
- Suppression réservée au service gestion

### Gestion des événements

- Création d’un événement à partir d’un contrat signé
- Gestion des dates, du lieu, du nombre de participants et des notes
- Consultation des événements selon le rôle
- Affectation d’un employé du support
- Retrait d’un employé du support
- Liste des événements sans support
- Modification par le service gestion ou le support affecté
- Suppression réservée au service gestion

### Supervision

- Remontée des erreurs techniques avec Sentry
- Distinction entre erreurs métier et erreurs inattendues
- Environnement Sentry configurable
- Aucune donnée personnelle envoyée par défaut

---

## Rôles et permissions

### GESTION

Le service gestion peut notamment :

- gérer les employés ;
- consulter tous les clients ;
- consulter et modifier les contrats ;
- consulter les contrats non signés et non soldés ;
- consulter et modifier tous les événements ;
- affecter ou retirer un membre du support ;
- supprimer des contrats et des événements.

### COMMERCIAL

Un commercial peut notamment :

- créer et gérer ses clients ;
- créer des contrats pour ses propres clients ;
- consulter et modifier ses propres contrats ;
- consulter ses contrats non soldés ;
- créer un événement pour un contrat signé lui appartenant ;
- consulter les événements liés à ses contrats.

### SUPPORT

Un employé du support peut notamment :

- consulter les clients ;
- consulter les contrats ;
- consulter les événements qui lui sont affectés ;
- modifier les événements qui lui sont affectés.

Les autorisations sont vérifiées dans la couche `services`, indépendamment des menus affichés dans l’interface.

---

## Architecture

```text
OC_P12_EpicEvents/
│
├── app/
│   ├── controllers/
│   ├── database/
│   ├── models/
│   ├── repositories/
│   ├── services/
│   ├── session/
│   └── utils/
│
├── migrations/
├── tests/
│   ├── functional/
│   ├── integration/
│   ├── unit/
│   ├── conftest.py
│   ├── factories.py
│   └── README.md
│
├── .env.example
├── .flake8
├── .gitignore
├── alembic.ini
├── main.py
├── pytest.ini
├── requirements.txt
└── README.md
```

### Organisation des couches

```text
Interface CLI
    ↓
Controllers
    ↓
Services
    ↓
Repositories
    ↓
SQLAlchemy
    ↓
PostgreSQL
```

- Les **controllers** gèrent les entrées et sorties de la console.
- Les **services** appliquent les règles métier et les autorisations.
- Les **repositories** effectuent les requêtes SQLAlchemy.
- Les **models** décrivent les tables et leurs relations.
- `CurrentSession` conserve l’employé et le jeton de la session active.
- Les utilitaires gèrent les exceptions, les mots de passe, les JWT et Sentry.

---

## Technologies utilisées

- Python 3
- PostgreSQL
- SQLAlchemy 2
- Alembic
- psycopg
- PyJWT
- bcrypt
- python-dotenv
- Sentry SDK
- pytest
- pytest-cov
- Flake8
- Black

---

## Prérequis

- Python 3.11 ou version ultérieure
- PostgreSQL
- Git
- Un environnement virtuel Python
- Un projet Sentry facultatif pour la supervision des erreurs

---

## Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/mouquettom/Epic-Events-PostgresSQL.git
cd Epic-Events-PostgresSQL
```

### 2. Créer l’environnement virtuel

Sous macOS ou Linux :

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Sous Windows :

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

---

## Configuration de l’environnement

Copier le fichier d’exemple :

```bash
cp .env.example .env
```

Puis renseigner les variables dans `.env` :

```env
DB_USER=epic_user
DB_PASSWORD=your_database_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=epic_events

JWT_SECRET_KEY=replace_with_a_long_random_secret

SENTRY_DSN=
SENTRY_ENVIRONMENT=development
```

Le fichier `.env` contient des informations sensibles et ne doit jamais être versionné.

### Générer une clé JWT

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### Configurer Sentry

Après avoir créé un projet Python sur Sentry, récupérer le DSN dans :

```text
Settings → Projects → Client Keys (DSN)
```

Puis l’ajouter dans `.env` :

```env
SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0
SENTRY_ENVIRONMENT=development
```

L’application fonctionne également sans Sentry si `SENTRY_DSN` reste vide.

---

## Configuration de PostgreSQL

Exemple de création de la base et de l’utilisateur :

```sql
CREATE DATABASE epic_events;

CREATE USER epic_user
WITH PASSWORD 'your_database_password';

GRANT ALL PRIVILEGES
ON DATABASE epic_events
TO epic_user;
```

Se connecter ensuite à la base et attribuer les droits nécessaires sur le schéma :

```sql
\c epic_events
GRANT USAGE, CREATE
ON SCHEMA public
TO epic_user;
```

---

## Migrations Alembic

Alembic constitue la méthode recommandée pour créer et mettre à jour le schéma.

Appliquer toutes les migrations :

```bash
alembic upgrade head
```

Afficher la migration active :

```bash
alembic current
```

Afficher l’historique :

```bash
alembic history
```

Créer une nouvelle migration après modification des modèles :

```bash
alembic revision --autogenerate -m "Description de la migration"
```

Puis l’appliquer :

```bash
alembic upgrade head
```

Le script `app/database/init_db.py` peut être utilisé dans certains contextes de développement, mais Alembic doit rester la source de vérité pour le schéma du projet.

---

## Création du premier compte gestion

Une fois la base et les tables prêtes :

```bash
python -m app.database.create_admin
```

Le compte créé reçoit automatiquement le rôle `GESTION`.

---

## Lancement de l’application

```bash
python main.py
```

Après connexion, le menu affiché dépend du rôle de l’employé.

---

## Sécurité

### Mots de passe

Les mots de passe sont hachés avec bcrypt et ne sont jamais stockés en clair.

La politique actuelle exige au moins huit caractères.

### JWT

Les jetons JWT :

- sont signés avec `HS256` ;
- contiennent l’identifiant de l’employé ;
- expirent après soixante minutes ;
- utilisent une clé secrète provenant du fichier `.env`.

### Variables sensibles

Les éléments suivants ne doivent jamais être ajoutés au dépôt Git :

- `.env`
- mots de passe PostgreSQL
- clé JWT
- jetons JWT
- secrets d’intégration
- informations personnelles réelles

---

## Sentry

Sentry est initialisé au démarrage lorsque `SENTRY_DSN` est défini.

Les exceptions métier telles que :

- `ValidationError`
- `AuthorizationError`
- `DuplicateError`
- `NotFoundError`

sont affichées à l’utilisateur sans être considérées comme des erreurs techniques.

Les exceptions inattendues sont envoyées à Sentry depuis `main.py`.

La configuration désactive l’envoi automatique de données personnelles :

```python
send_default_pii=False
```

---

## Tests

Les tests sont divisés en trois catégories.

### Tests unitaires

```bash
pytest tests/unit -v
```

### Tests d’intégration

```bash
pytest tests/integration -v
```

### Tests fonctionnels

```bash
pytest tests/functional -v
```

### Exécuter toute la suite

```bash
pytest
```

Lors de la dernière validation du projet :

```text
481 tests réussis
95 % de couverture globale
```

Ces valeurs peuvent évoluer avec les prochaines modifications du code.

### Couverture

```bash
pytest --cov=app --cov-report=term-missing
```

Générer un rapport HTML :

```bash
pytest --cov=app --cov-report=html
```

Le rapport est ensuite disponible dans :

```text
htmlcov/index.html
```

---

## Qualité du code

### Black

Vérifier le formatage :

```bash
black --check app tests main.py
```

Appliquer le formatage :

```bash
black app tests main.py
```

### Flake8

```bash
flake8 app tests main.py
```

---

## Principales règles métier

- Seul un employé de gestion peut administrer les employés.
- Un employé ne peut pas supprimer son propre compte.
- Seul un commercial peut créer un client.
- Un commercial ne peut modifier que ses propres clients.
- Seul un commercial peut créer un contrat.
- Un contrat ne peut être créé que pour un client appartenant au commercial.
- Le montant restant ne peut pas être négatif ni dépasser le montant total.
- Un événement ne peut être créé que pour un contrat signé.
- Seul le service gestion peut affecter un membre du support.
- Un membre du support ne peut modifier que les événements qui lui sont affectés.
- Les erreurs techniques inattendues sont transmises à Sentry.

---

## Pistes d’amélioration

- Adapter dynamiquement les sous-menus aux permissions de chaque rôle
- Empêcher explicitement la suppression d’un client possédant des contrats
- Filtrer la liste des clients d’un commercial selon sa propriété
- Compléter la validation des champs lors de la modification d’un employé
- Ajouter une commande de réinitialisation de mot de passe
- Centraliser la configuration des variables d’environnement
- Ajouter une interface web ou une API REST
- Automatiser les contrôles avec une intégration continue

---

## Auteur

Projet réalisé dans le cadre du parcours de développement Python OpenClassrooms.

---

## Licence

Projet pédagogique. Ajouter une licence adaptée avant toute réutilisation ou publication publique.
