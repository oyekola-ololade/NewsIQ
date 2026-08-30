# Security Policy

## Public-package rules

- Never commit `.env`.
- Never commit OAuth client-secret JSON, service-account files, API keys, database passwords, private webhooks, tokens, or personal content.
- Configure secrets in n8n credentials, environment variables, or a managed secret store.
- Rotate any credential that may previously have appeared in a setup document or exported workflow.

## Known high-risk boundaries

- News and search APIs
- AI model APIs
- PostgreSQL
- Google Drive and TTS credentials
- Social-platform OAuth
- Twilio/WhatsApp
- S3-compatible object storage

## Reporting

If you find a secret or personal record in this repository, do not reuse it. Notify the repository owner privately and rotate the affected credential before further deployment.

