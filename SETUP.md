# Pushing this repo to GitHub

The build session had **no GitHub access** (the `gh` CLI is not installed and no
GitHub connector was available), so the repository was built and committed
locally. Below are the exact commands to create the remote and push. Run them
yourself.

The local repo is already initialized with a clean commit history and a local
git identity (`Adam Selzer <hello@aselzer.com>`):

```bash
cd ~/code/rules-as-code-mcp
git log --oneline      # four commits, logical stages
```

## Option A — with the GitHub CLI (recommended)

```bash
# one-time, if needed:
brew install gh
gh auth login

# from the repo:
cd ~/code/rules-as-code-mcp
gh repo create rules-as-code-mcp --public --source=. --remote=origin --push
```

That creates the repo under your account and pushes `main` in one step.

## Option B — without the CLI

1. Create an empty repo named `rules-as-code-mcp` at https://github.com/new
   (no README, license, or .gitignore, since this repo already has them).
2. Then:

```bash
cd ~/code/rules-as-code-mcp
git branch -M main
git remote add origin git@github.com:<your-username>/rules-as-code-mcp.git
git push -u origin main
```

(Use the `https://github.com/<your-username>/rules-as-code-mcp.git` URL instead if
you authenticate over HTTPS.)

## Verify the push

```bash
git remote -v
git log --oneline origin/main
```

## Note on commit identity

Your global git config currently has malformed values (the name and email contain
stray quote characters), so this repo sets a clean identity locally instead. If you
want to fix the global config as well:

```bash
git config --global user.name "Adam Selzer"
git config --global user.email "hello@aselzer.com"
```
