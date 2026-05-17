# CLAUDE.md

## Skill routing

When the user's request matches an available skill, invoke it via the Skill tool.
When in doubt, invoke the skill. Never ask the user to type `/skill` — just run it.

### Routing rules

| User says / asks | Invoke |
|---|---|
| Product ideas, brainstorming, "I have an idea", "is this worth building" | `/office-hours` |
| Strategy, scope, "think bigger", "is this ambitious enough" | `/plan-ceo-review` |
| Architecture, technical design, data flow | `/plan-eng-review` |
| Design system, brand guidelines, "create DESIGN.md" | `/design-consultation` |
| Design plan review, visual consistency | `/plan-design-review` |
| Full review pipeline (CEO + design + eng + DX) | `/autoplan` |
| Bugs, errors, "why is this broken", stack traces, "it was working yesterday" | `/investigate` |
| Systematic debugging with root cause analysis | `/systematic-debugging` |
| QA testing, "does this work?", "test this site", "find bugs" | `/qa` |
| Bug report only, "just report bugs", don't fix | `/qa-only` |
| Code review, diff check, "review this PR" | `/review` |
| Receiving code review feedback, before implementing suggestions | `/receiving-code-review` |
| Requesting code review, before merging | `/requesting-code-review` |
| Visual polish, "does this look good?", UI inconsistency | `/design-review` |
| Ship, deploy, PR, "push to main", "get it deployed" | `/ship` |
| Land, merge, verify production | `/land-and-deploy` |
| Save progress, "save my work" | `/context-save` |
| Resume context, "where was I" | `/context-restore` |
| Security audit, threat model, pentest review, OWASP | `/cso` |
| Security review of pending changes | `/security-review` |
| Performance, page speed, lighthouse, bundle size | `/benchmark` |
| Post-deploy monitoring, "watch production", canary | `/canary` |
| Code quality, "health check", linter + test + type check | `/health` |
| Developer experience test, "try the onboarding", API design | `/devex-review` |
| Frontend design, build web components/pages | `/frontend-design` |
| Design variants, "show me options", "I don't like how this looks" | `/design-shotgun` |
| Turn design into HTML/CSS, "build me a page" | `/design-html` |
| Design to PDF, "make a PDF", export markdown | `/make-pdf` |
| Scrape data from page, "extract from" | `/scrape` |
| Implement a plan with review checkpoints | `/executing-plans` |
| Writing implementation plans, spec to plan | `/writing-plans` |
| Test-driven development | `/test-driven-development` |
| Subagent-driven implementation with parallel tasks | `/subagent-driven-development` |
| Dispatching parallel independent tasks | `/dispatching-parallel-agents` |
| Isolated git worktree for feature work | `/using-git-worktrees` |
| Finishing a branch, merge/PR/cleanup decisions | `/finishing-a-development-branch` |
| Post-ship documentation update | `/document-release` |
| Weekly retro, "what did we ship" | `/retro` |
| Learnings management, "what have we learned" | `/learn` |
| Freeze edits to specific directory | `/freeze` |
| Safety mode, destructive command warnings | `/careful` |
| Full safety (freeze + careful) | `/guard` |
| Upgrade gstack | `/gstack-upgrade` |
| Configure deploy settings | `/setup-deploy` |
| Import browser cookies for authenticated testing | `/setup-browser-cookies` |
| Claude API / Anthropic SDK coding | `/claude-api` |
| Simplify, reuse, quality review of changed code | `/simplify` |
| Configure settings.json / hooks / permissions | `/update-config` |
| Configure HUD display | `/claude-hud:configure` |
| Setup gbrain | `/setup-gbrain` |

### Default routing

- `[/investigate]` or `[/systematic-debugging]` for any bug/error/stack trace
- `[/office-hours]` for any new product idea or feature brainstorm
- `[/plan-eng-review]` for architecture questions involving >2 files
- `[/review]` before merging, landing, or creating a PR
- `[/writing-plans]` for multi-step implementation tasks before coding
- `[/ship]` when code is ready to push/deploy
- `[/context-save]` after completing a significant logical unit
- `[/test-driven-development]` when implementing features or fixes
