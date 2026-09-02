# Architecture

StumbleBreach has two cooperating layers.

1. **The operating model**: templates, roles, scope rules, branch separation,
   and evidence conventions decide who may do what and where records belong.
2. **The deterministic harness**: scripts and files track coverage, validate
   finding structure, identify likely duplicates, and prepare roll-ups.

The operating model drives the harness. The harness does not make decisions or
run work on its own.

```text
authorized private engagement
        |
        v
planner (on main) --> scaffolds engagement branch from template
        |
        v
mastermind / recon / worker roles (on engagement branch)
        |
        v
coverage + queue + deterministic scripts
        |
        v
karma (adversarial review) --> reviewed evidence and report
```

The reusable tool contains the templates, scripts, and MCP source. A private
engagement supplies the actual scope, targets, credentials, evidence, and
findings. That separation makes the tool safe to share without sharing anyone's
engagement. Company profiles (`profiles/<company>/`) hold reusable knowledge
base data about a target organization and live on main -- they are not
engagement-specific.

This repository is the **engine**; the role instructions that drive it are the
**playbook**, authored privately and kept out of the public tree. See
[Engine and playbook](ENGINE-AND-PLAYBOOK.md) for that split.

See [Harness](HARNESS.md), [Roles](ROLES.md), and [Branching](BRANCHING.md).
