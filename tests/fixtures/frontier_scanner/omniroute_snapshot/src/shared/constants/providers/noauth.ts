export const NOAUTH_PROVIDERS = {
  opencode: {
    id: "opencode",
    alias: "oc",
    name: "OpenCode Free",
    website: "https://opencode.ai",
    noAuth: true,
    hasFree: true,
    serviceKinds: ["llm"],
    freeNote: "No API key required - upstream says rate limits apply.",
  },
  github: { id: "github", alias: "gh", name: "GitHub Copilot" },
};
