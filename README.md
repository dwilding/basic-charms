This repo helps you adversarially test charm development documentation, such as the [Ops documentation](https://canonical.com/juju/docs/ops/latest/).

To perform an adversarial test:

1. Identify the portion of documentation you want to disprove. Try to focus on a specific claim in the docs, not something like "this section is poor".

2. Open an issue in `basic-charms` with a link to the documentation page and a description of what you want to disprove. This could be a quote from the page or an explanation of something the page implies.

3. Run the [Validate doc issue](https://github.com/dwilding/basic-charms/actions/workflows/validate-doc-issue.yaml) workflow, entering the issue number in the **Run workflow** UI.

4. Wait for a PR to be created.

    The PR will modify one or more of the basic charms (and possibly their unit tests or integration tests) in an attempt to disprove the documentation claim that you described in the issue.

    The basic charms are a known-good starting point, whose tests pass by default. The PR applies changes on top of this starting point, which minimizes your review burden.

    The PR will explain the chain of reasoning and how to interpret the test results. For example:I don

    > I added a unit test that [...], which is expected to fail, meaning that I couldn't disprove what the documentation claims. In other words, the claim is correct.

5. Review the PR to make sure the test is meaningful and the conclusion is valid.

6. Decide how to fix the documentation — if needed.

The agentic workflow that creates the PR is explained in [AGENT_DESIGN.md](AGENT_DESIGN.md). It's a **highly experimental** workflow based on ideas explored in [SecondSkoll/generic-agentic-workflows](https://github.com/SecondSkoll/generic-agentic-workflows). It uses OpenCode, OpenRouter, and GLM-5.2.

Although I've tried to include strong guardrails, I'm not ready to make any security guarantees yet.
