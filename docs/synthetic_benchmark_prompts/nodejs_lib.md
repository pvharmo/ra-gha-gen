Create a GitHub repository environment to benchmark GitHub Actions workflow generation.

Repo theme: Node.js library.

You must generate:

    A minimal Node project (package.json, package-lock.json or pnpm-lock.yaml), with:
        npm run lint (ESLint) and npm test (Jest or Vitest).
        At least 3 tests, including one failing test that becomes passing only when NODE_ENV=test is set (to test env var handling).
    A README.md describing CI expectations in plain English.

Workflow requirements to benchmark:

    Workflow should generate an artifact that can be tested
