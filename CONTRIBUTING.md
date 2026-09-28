# Contributing to DR-TBAtlas

Thank you for your interest in contributing to DR-TBAtlas! We welcome community contributions to help improve this genomic explorer for *Mycobacterium tuberculosis* drug resistance mutations.

## How to Report Bugs

If you find a bug, please check the existing issues on our GitHub repository to see if it has already been reported. If not, you can open a new bug report using [GitHub Issues](https://github.com/falatfernando/dr-tbatlas/issues).

When reporting a bug, please include:
- A clear, descriptive title.
- Steps to reproduce the issue.
- Expected vs. actual behavior.
- Python and Dash versions, browser details, and operating system.
- Relevant screenshots or error logs if available.

## How to Suggest Features

We welcome ideas for new features and improvements! To suggest a feature:
1. Search the existing issues to see if the feature has already been proposed.
2. Open a new issue on GitHub and describe the proposed feature, why it is useful, and how you envision it working.

## Pull Request Process

To submit code changes or documentation updates, please follow this process:

1. **Fork the Repository**: Create your own copy of the repository on GitHub.
2. **Clone the Fork**: Clone the repository to your local machine:
   ```bash
   git clone https://github.com/YOUR-USERNAME/dr-tbatlas.git
   cd dr-tbatlas
   ```
3. **Create a Branch**: Create a new branch for your work:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. **Implement and Test**: Make your changes and write tests to ensure they work as expected. Ensure all tests pass by running:
   ```bash
   pytest tests/
   ```
5. **Commit and Push**: Commit your changes with descriptive messages and push to your fork:
   ```bash
   git add .
   git commit -m "Add feature to visualize custom mutations"
   git push origin feature/your-feature-name
   ```
6. **Submit a Pull Request**: Go to the original repository on GitHub and open a pull request (PR) from your feature branch to the `main` branch. Provide a clear description of the changes in the PR description.
