# Security Notes

This repository is a local prototype intended for controlled development and demonstration environments. It should not be exposed directly to untrusted public traffic.

The implemented controls include HTTP and HTTPS target validation, strict custom alias validation, bounded collision retries, process local rate limiting, privacy conscious click analytics, agent output policy checks, bounded workflow retries, rollback, safe stop, and mandatory human release approval.

Before production use, add authentication, authorization, distributed rate limiting, abuse and phishing detection, managed secrets, centralized audit export, SAST, dependency scanning, SBOM generation, and a production database.
