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
    const result =
      await Bun.$`uv run --script ${script} --repo-root ${context.worktree} --charm-dir ${args.charm} --tox-env format,lint,unit`.text();
    return result.trim();
  },
});
