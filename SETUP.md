# New Machine Setup

Follow these steps in order when setting up MLEbotics on a new machine.

---

## Prerequisites

Install these before anything else:

- [Git](https://git-scm.com/download/win)
- [Node.js](https://nodejs.org/) (LTS)
- [pnpm](https://pnpm.io/installation) — `npm install -g pnpm`
- [VS Code](https://code.visualstudio.com/)

---

## Step 1 — Pull the latest code

If the repo is already on the machine, just pull:

```powershell
cd D:\MLEbotics
git pull origin main
```

> If the repo isn't there yet, clone it first:
> ```powershell
> git clone https://github.com/eddie7ch/MLEbotics.git D:\MLEbotics
> ```

---

## Step 2 — Run the setup script (one-time only)

```powershell
cd D:\MLEbotics
pwsh -ExecutionPolicy Bypass -File setup-machine.ps1
```

This will automatically:
- Set PowerShell execution policy to `RemoteSigned`
- Copy `start-session.ps1`, `end-session.ps1`, and `close-project.ps1` to `C:\Users\<you>\scripts\`
- Add aliases to your PowerShell profile so you can run them from any terminal
- Create 3 desktop shortcuts:
  - **START SESSION** — pulls latest and starts all dev servers
  - **MLEbotics Project Starter** — opens the VS Code workspace
  - **Close Project** — commits, pushes, and closes VS Code

---

## Step 3 — Install dependencies

```powershell
cd D:\MLEbotics\mlebotics.com
pnpm install
```

---

## Step 4 — Start working

Double-click **START SESSION** on your desktop.

That's it. It will pull the latest code and open all 4 dev servers automatically.

---

## Daily workflow

| Action | How |
|---|---|
| Start work | Double-click **START SESSION** on desktop |
| End work | Double-click **Close Project** on desktop |
| Restart a server | Run `dev-restart.ps1` inside `mlebotics.com/` |

---

## Dev server ports

| App | Port |
|---|---|
| Marketing (Astro) | 54321 |
| Console (Next.js) | 3001 |
| Studio (Next.js) | 3002 |
| Docs (Next.js) | 3003 |
