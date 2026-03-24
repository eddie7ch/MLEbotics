# Copilot Instructions — mlebotics.com

This workspace is primarily about the **mlebotics.com** website and platform.

## Project overview
- Monorepo managed with **pnpm workspaces + Turborepo**
- Deployed on **Vercel** (marketing/console/studio) and **Firebase** (functions/hosting)
- Apps: `apps/marketing`, `apps/console`, `apps/docs`, `apps/studio`
- Shared packages: `packages/`
- Cloud functions: `functions/`
- Infrastructure: `infra/`
- Internal tooling: `tools/`, `platform/`, `robotics/`, `dashboard/`

## Default assumptions
- When a question is asked without specifying a project, assume it is about **mlebotics.com**
- When editing or searching for code, start in the `apps/` or `packages/` directories first
- The site is at **https://mlebotics.com**
- Owner: **Eddie Chongtham** (eddie@mlebotics.com), Calgary, AB, Canada

## Tech stack
- Framework: Next.js (App Router)
- Package manager: pnpm
- Build system: Turborepo
- Hosting: Vercel + Firebase
- Language: TypeScript
