# Repository practices

## ADRs (architecture decision records) · step 0.1

A short file per decision (or per group of related small decisions) recording context, options, the choice and when to revisit it. It stops settled questions being reopened by accident, and gives coding agents the "why" along with the "what". A changed decision gets a new ADR that supersedes the old one.

## One repo vs many · step 0.1

Separate repos show clean boundaries (the gateway is usable by any agent) but cost coordination: versioned contracts, several CI setups. Starting with one repo and splitting later is cheap; merging repos later is harder.

## Public-repo hygiene · step 0.1

Every commit carries an author email, visible to anyone on a public repo. GitHub's noreply address (`ID+username@users.noreply.github.com`) keeps the real one private; it was set per repo before the first push. Rewriting a commit's author is easy before pushing and messy after.

## Licences · step 0.1

MIT lets anyone use the code with attribution. Apache-2.0 is similar but adds an explicit patent grant.
