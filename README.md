# StArranja
This repo holds the code for the **StArranja** car workshop management backbone. \
It provides a way to interact with a single workshop's data, including clients and their respective vehicles, car checking 
appointments, work orders and invoices.

## Contributing
If you want to contribute to our project, head on to the [contributing file](CONTRIBUTING.md) to get to know our workflow
 and start contributing!

When you understand our workflow, it's time to setup your development environment! \
1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
2. Sync your env with uv: `uv sync`
3. Enter your development environment: `source .venv/scripts/activate`

## Notes
At each commit, a [quality code action](.github/workflows/ci.yml) runs to check code linting, formatting and typing. \
This helps us developers ensure our code maintains a high quality standard and catch possible bugs early on. However, for 
those that eat a lot of cheese this gets to a point where each commit is a CI pipeline failure, preventing merges.
So, to prevent that, pre-commit hooks were integrated in the repository! Everything is configured and you only need to install it.
For that you should run:
```shell
pre-commit install
```

Now, every time you commit, the checks are ran and if failed, they prevent your commit to go through!
