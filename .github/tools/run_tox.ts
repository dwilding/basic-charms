import { tool } from "@opencode-ai/plugin";
import path from "path";

export default tool({
  description:
    "Run tox -e format,lint,unit for a single charm inside an isolated Docker container. " +
    "Use this to validate your changes before finishing. The charm name must be one of: " +
    "kepler, kosmos, meteor, micron. The output (including any lint or test failures) " +
    "is returned to you so you can fix issues and call the tool again.",
  args: {
    charm: tool.schema
      .string()
      .describe("Charm directory name: kepler, kosmos, meteor, or micron"),
  },
  async execute(args, context) {
    const valid = ["kepler", "kosmos", "meteor", "micron"];
    if (!valid.includes(args.charm)) {
      return `Invalid charm "${args.charm}". Must be one of: ${valid.join(", ")}`;
    }
    const script = path.join(
      context.worktree,
      ".github",
      "scripts",
      "run_tox_in_container.py",
    );
    try {
      // Redirect stderr to stdout so the agent sees error messages too.
      const proc =
        Bun.$`uv run --script ${script} --repo-root ${context.worktree} --charm-dir ${args.charm} --tox-env format,lint,unit 2>&1`.nothrow();
      const output = await proc.text();
      return output.trim();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      return `run_tox failed with an error. This may be a Docker or environment issue. Error: ${msg}`;
    }
  },
});
