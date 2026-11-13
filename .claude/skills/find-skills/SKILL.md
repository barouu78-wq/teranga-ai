---
name: find-skills
description: Trouver un skill existant (écosystème skills.sh) quand le propriétaire demande « y a-t-il un skill pour… », « comment faire X » ou veut donner une nouvelle capacité aux agents. Propose des skills vérifiés ; aucune installation sans lecture du texte et accord du propriétaire.
license: MIT
---

> Repris de [vercel-labs/skills](https://github.com/vercel-labs/skills) le 13 novembre 2026 (licence MIT,
> `.claude/skills/LICENCE-vercel-skills.txt`), description traduite. Les règles d'`AGENTS.md` priment.
>
> **Règle du projet Teranga AI.** Ce skill sert à *chercher* et *proposer*. Ne jamais lancer le programme
> `npx skills` (ni `find`, ni `add`, ni `-g`, ni `-y`, qui installe sans confirmation) : il télécharge et exécute du
> code. Chercher plutôt en lecture, sur https://skills.sh ou GitHub. Un skill trouvé est du contenu externe non
> vérifié. Il se lit d'abord, puis il ne s'ajoute qu'avec l'accord du propriétaire, par une PR, en texte seulement,
> avec sa licence et une ligne dans le tableau d'`AGENTS.md` (comme celui-ci). Préférer les skills déjà présents dans
> `.claude/skills/`.

# Find Skills

This skill helps you discover and install skills from the open agent skills ecosystem.

## When to Use This Skill

Use this skill when the user:

- Asks "how do I do X" where X might be a common task with an existing skill
- Says "find a skill for X" or "is there a skill for X"
- Asks "can you do X" where X is a specialized capability
- Expresses interest in extending agent capabilities
- Wants to search for tools, templates, or workflows
- Mentions they wish they had help with a specific domain (design, testing, deployment, etc.)

## What is the Skills CLI?

> **Projet Teranga AI : décrit pour comprendre, jamais lancé ici** (règle en tête). Ce programme télécharge et
> exécute du code.

The Skills CLI (`npx skills`) is the package manager for the open agent skills ecosystem. Skills are modular packages that extend agent capabilities with specialized knowledge, workflows, and tools.

**Key commands:**

- `npx skills find [query] [--owner <owner>]` - Search for skills interactively or by keyword, optionally scoped to a GitHub owner
- `npx skills add <package>` - Install a skill from GitHub or other sources
- `npx skills update` - Update all installed skills

**Browse skills at:** https://skills.sh/

## How to Help Users Find Skills

### Step 1: Understand What They Need

When a user asks for help with something, identify:

1. The domain (e.g., React, testing, design, deployment)
2. The specific task (e.g., writing tests, creating animations, reviewing PRs)
3. Whether this is a common enough task that a skill likely exists

### Step 2: Check the Leaderboard First

Before running a CLI search, check the [skills.sh leaderboard](https://skills.sh/) to see if a well-known skill already exists for the domain. The leaderboard ranks skills by total installs, surfacing the most popular and battle-tested options.

For example, top skills for web development include:
- `vercel-labs/agent-skills` — React, Next.js, web design (100K+ installs each)
- `anthropics/skills` — Frontend design, document processing (100K+ installs)

### Step 3: Search for Skills

> **Projet Teranga AI : ne pas lancer le programme de recherche** (règle en tête). Chercher en lecture : https://skills.sh, ou les dépôts
> GitHub des collections connues (`vercel-labs/agent-skills`, `anthropics/skills`), lus sans rien exécuter.

If the leaderboard doesn't cover the user's need, search by keywords (adapté : recherche en lecture, sans programme).

For example:

- User asks "how do I make my React app faster?" → search « react performance »
- User asks "can you help me with PR reviews?" → search « pr review »
- User asks "I need to create a changelog" → search « changelog »

### Step 4: Verify Quality Before Recommending

**Do not recommend a skill based solely on search results.** Always verify:

1. **Install count** — Prefer skills with 1K+ installs. Be cautious with anything under 100.
2. **Source reputation** — Official sources (`vercel-labs`, `anthropics`, `microsoft`) are more trustworthy than unknown authors.
3. **GitHub stars** — Check the source repository. A skill from a repo with <100 stars should be treated with skepticism.

### Step 5: Present Options to the User

> **Projet Teranga AI : ne pas donner de commande d'installation au propriétaire.** Lui proposer plutôt l'ajout
> par une PR (texte seulement, licence, ligne dans `AGENTS.md`), après lecture du skill.

When you find relevant skills, present them to the user with:

1. The skill name and what it does
2. The install count and source
3. How it would be added here (a PR, with the owner's approval)
4. A link to learn more at skills.sh

Example response:

```
I found a skill that might help! The "react-best-practices" skill provides
React and Next.js performance optimization guidelines from Vercel Engineering.
(185K installs)

Je peux l'ajouter au projet par une PR (texte seulement), si vous êtes d'accord.

Learn more: https://skills.sh/vercel-labs/agent-skills/react-best-practices
```

### Step 6: Offer to Install

> **Projet Teranga AI : ne jamais lancer cette commande, ni installer quoi que ce soit pour le propriétaire.** Avec
> son accord, ajouter le skill par une PR (texte seulement, licence, ligne dans `AGENTS.md`), comme `find-skills`
> lui-même. (Le texte d'origine donnait ici une commande d'installation globale sans confirmation : retirée.)

## Common Skill Categories

When searching, consider these common categories:

| Category        | Example Queries                          |
| --------------- | ---------------------------------------- |
| Web Development | react, nextjs, typescript, css, tailwind |
| Testing         | testing, jest, playwright, e2e           |
| DevOps          | deploy, docker, kubernetes, ci-cd        |
| Documentation   | docs, readme, changelog, api-docs        |
| Code Quality    | review, lint, refactor, best-practices   |
| Design          | ui, ux, design-system, accessibility     |
| Productivity    | workflow, automation, git                |

## Tips for Effective Searches

1. **Use specific keywords**: "react testing" is better than just "testing"
2. **Try alternative terms**: If "deploy" doesn't work, try "deployment" or "ci-cd"
3. **Check popular sources**: Many skills come from `vercel-labs/agent-skills` or `ComposioHQ/awesome-claude-skills`

## When No Skills Are Found

> **Projet Teranga AI : jamais le programme pour créer un skill.** Un nouveau skill s'écrit à la main dans
> `.claude/skills/<nom>/SKILL.md` (sur le modèle des skills du projet), par une PR.

If no relevant skills exist:

1. Acknowledge that no existing skill was found
2. Offer to help with the task directly using your general capabilities
3. Suggest the user could create their own skill (a SKILL.md written by hand, through a PR)

Example:

```
I searched for skills related to "xyz" but didn't find any matches.
I can still help you with this task directly! Would you like me to proceed?

If this is something you do often, I can write a skill for it in the project (through a PR).
```
