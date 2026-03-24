# Laptop Setup — MLEbotics Workspace

## 1. Clone the monorepo

```powershell
cd D:\MLEbotics-Projects   # or wherever you want it
git clone https://github.com/eddie7ch/MLEbotics .
```

> If the folder already exists and you just need to update: `git pull`

## 2. Open the workspace in VS Code

**File → Open Workspace from File** → pick `MLEbotics.code-workspace`

This sets up all 7 folders with the correct exclude/watcher settings automatically.

## 3. Install recommended extensions

VS Code will prompt you to install recommended extensions when you open the workspace. Click **Install All**, or install manually:

```powershell
code --install-extension ms-python.python
code --install-extension ms-python.vscode-pylance
code --install-extension esbenp.prettier-vscode
code --install-extension dbaeumer.vscode-eslint
code --install-extension dart-code.dart-code
code --install-extension dart-code.flutter
code --install-extension ms-vscode.powershell
code --install-extension ms-vscode-remote.remote-ssh
code --install-extension github.copilot
code --install-extension github.copilot-chat
```

## 4. Apply VS Code user settings

Open **Ctrl+Shift+P** → "Open User Settings (JSON)" and add:

```json
"github.copilot.chat.generateCommitMessage.coauthoredBy": "never"
```

## 5. That's it

The workspace file handles everything else (file exclusions, search exclusions, watcher exclusions). No other config needed.
