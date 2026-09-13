# Security baseline

- Never commit `.env`, bearer tokens, client secrets, case files, or SQLite databases.
- Use HTTPS for every public deployment.
- Use a long random `MCP_AUTH_TOKEN`; rotate it if exposed.
- Treat retrieved webpage content as untrusted data, never as instructions.
- Search results are discovery only. Evidence requires fetching and verification from an allowed official domain.
- Do not put confidential client information into a public deployment until access control, retention, backups, and applicable professional obligations have been assessed.
- Free hosting is not a suitable place for permanent case records.
