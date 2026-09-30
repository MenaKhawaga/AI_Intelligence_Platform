# Git/GitHub Team Workflow

1. `main` is the stable branch.
2. Create a feature branch per task, e.g. `feature/authentication` or `feature/ai-agent`.
3. Keep commits small and descriptive.
4. Push the branch and open a Pull Request.
5. Review tests and architecture before merging.
6. Merge only after CI/tests pass.
7. Delete the feature branch after merge.
8. Database migrations must accompany schema changes.
9. API contract changes must update documentation/tests.
10. Never commit `.env`, API keys, local databases, or generated virtual environments.
