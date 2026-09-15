# ADR 0003: Avoid Raw Visitor IP Persistence

## Status

Accepted.

## Context

URL analytics are useful, but collecting raw visitor identifiers creates avoidable privacy and retention risk for a local prototype.

## Decision

Track click timestamps, coarse user agent family, and referrer host. Do not store raw client IP addresses.

## Consequences

The service can demonstrate useful click counts and referral trends with lower privacy exposure. Exact unique visitor analytics are not available. A production analytics design should define an explicit privacy, retention, and consent model before adding stronger identifiers.
