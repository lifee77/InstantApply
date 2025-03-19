# Database Migrations

This directory contains database migration scripts created with Flask-Migrate.

## Usage

To create a new migration after model changes:
```
flask db migrate -m "Description of changes"
```

To apply migrations:
```
flask db upgrade
```

To roll back a migration:
```
flask db downgrade
```
