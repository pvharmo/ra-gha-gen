# RA-GHA-GEN: GitHub Actions Workflow Generator

A research project that implements an intelligent agent system for analyzing GitHub repositories and generating optimized GitHub Actions workflows through iterative improvement cycles.

## Overview

This project creates an autonomous agent that:
1. Analyzes a GitHub repository's structure, dependencies, and requirements
2. Generates appropriate GitHub Actions workflows based on the analysis
3. Enters an iterative improvement loop where it:
   - Judges the generated workflow
   - Fixes identified issues
   - Runs static analysis tools (ActionLint and Zizmor)
   - Incorporates feedback from the analysis tools
   - Repeats until the workflow is optimized

## Project Structure

```
ra-gha-gen/
├── src/
│   ├── agent/           # Core agent logic and decision making
│   ├── analysis/        # Repository analysis components
│   ├── workflow/        # Workflow generation and validation
│   └── utils/           # Utility functions and helpers
├── tests/              # Test suite
├── examples/           # Example repositories and workflows
└── docs/              # Documentation
```

## Features

- **Repository Analysis**: Automated detection of project type, dependencies, and build requirements
- **Intelligent Workflow Generation**: Context-aware workflow creation based on repository characteristics
- **Iterative Improvement**: Self-correcting loop with static analysis integration
- **Multi-tool Validation**: Integration with ActionLint and Zizmor for workflow validation
- **Extensible Architecture**: Modular design for adding new analysis tools and validation methods

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd ra-gha-gen

# Install dependencies
pip install -e .
```

## Usage

```python
from src.agent.workflow_generator import WorkflowGenerator

# Initialize the generator
generator = WorkflowGenerator(repository_url="https://github.com/user/repo")

# Generate and optimize workflow
workflow = generator.generate_optimized_workflow()
```

## Dependencies

- Python 3.13+
- OpenAI API (for intelligent agent capabilities)
- GitHub CLI (for repository analysis)
- ActionLint (for workflow validation)
- Zizmor (for additional workflow analysis)

## Research Goals

This project explores:
- Autonomous code generation and refinement
- Integration of multiple static analysis tools
- Iterative improvement algorithms for code quality
- Agent-based software engineering workflows

## Contributing

Please read CONTRIBUTING.md for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see LICENSE.md for details.
