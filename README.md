This repo helps you test charm development documentation, such as the [Ops documentation](https://canonical.com/juju/docs/ops/latest/). Tests are generated on-demand by an adversarial agent: the agent is skeptical of docs and tries to construct tests that validate its own view of the world.

To perform an adversarial test:

1. Identify a portion of documentation you want to test. Try to focus on a specific claim in the docs, not something like "this section is poor".

2. Create an issue in `basic-charms` with a link to the documentation page and a description of the claim you want to test. This could be a quote from the page or an explanation of something the page implies.

3. Run the [Probe issue](https://github.com/dwilding/basic-charms/actions/workflows/probe-issue.yaml) workflow, entering the issue number in the **Run workflow** UI.

4. Wait for a PR to be created.

    The PR will modify one or more of the basic charms (and possibly their unit tests or integration tests) to test the documentation claim you described in the issue.

    The basic charms are a known-good starting point, whose tests pass by default. The PR applies changes on top of this starting point, which minimizes your review burden.

    The agent doesn't trust the documentation. It forms its own understanding of how the code behaves, then creates a PR as an attempt to prove its understanding — aiming for passing CI. The PR description explains what the result means for the documentation. For example:

    > I believe the doc is wrong about `<claim>`. I added a test asserting `<what I believe is true>`, which is expected to pass. If CI passes, the doc is incorrect.

    Or, if the agent's understanding happens to match the documentation:

    > I believe `<claim>` is true. I added a test asserting it, which is expected to pass. If CI passes, the doc is correct.

5. Review the PR to make sure the agent's changes are meaningful and trustworthy. Once you're satisfied, approve the PR's workflow runs to trigger CI.

6. After the CI checks have completed, use the PR description to draw a conclusion about the documentation.

7. Decide how to fix the documentation — if needed.

The agentic workflow that creates the PR is explained in [AGENT_DESIGN.md](AGENT_DESIGN.md). It's a **highly experimental** workflow based on ideas explored in [SecondSkoll/generic-agentic-workflows](https://github.com/SecondSkoll/generic-agentic-workflows). It uses OpenCode, OpenRouter, and GLM-5.2.

Although I've tried to include strong guardrails, I'm not ready to make any security guarantees yet.
