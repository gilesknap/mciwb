# 2. Adopt python-copier-template for project structure

## Status

Accepted

## Context

We should use the following [python-copier-template](https://github.com/DiamondLightSource/python-copier-template).
The template will ensure consistency in developer
environments and package management.

## Decision

We have switched to using the template.

## Consequences

This module will use a fixed set of tools as developed in `python-copier-template`
and can pull from this template to update the packaging to the latest techniques.

As such, the developer environment may have changed, the following could be
different:

- linting
- formatting
- pip venv setup
- CI/CD
