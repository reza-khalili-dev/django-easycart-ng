
```markdown
# Contributing to django-easycart-ng

Thank you for considering contributing to `django-easycart-ng`! We welcome contributions from everyone.

---

## 🐛 Reporting Issues

If you find a bug, please open an issue on [GitHub Issues](https://github.com/reza-khalili-dev/django-easycart-ng/issues) and include:

- A clear description of the issue.
- Steps to reproduce the problem.
- Your environment (Python version, Django version, OS).
- Any relevant error logs or screenshots.

---

## 💡 Feature Requests

If you have an idea for a new feature, please open an issue with the **"enhancement"** label. Provide:

- A clear description of the feature.
- Why it would be useful.
- Any examples or references.

---

## 🛠️ Development Setup

1. **Fork the repository** and clone it locally:

   ```bash
   git clone https://github.com/your-username/django-easycart-ng.git
   cd django-easycart-ng



 2. **Set up a virtual environment:**

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate


3. **Install development dependencies:**

pip install -e .[dev]


4.**Run the tests to ensure everything works:**

pytest



📝 Code Guidelines
Follow PEP 8 for Python code.

Use Black for formatting (black .).

Use isort for sorting imports (isort .).

Use flake8 for linting (flake8).

Write docstrings for all functions and classes.

Write tests for new features and bug fixes.



🧪 Testing
**We use pytest for testing. To run the test suite:**
pytest


**To run tests with coverage:**
pytest --cov=cart



📦 Submitting a Pull Request

1.**Create a new branch for your feature or fix:**

git checkout -b feature/your-feature-name


2.**Make your changes and commit them with a clear message:**

git add .
git commit -m "feat: add your feature description"


3.**Push your branch to your fork:**

git push origin feature/your-feature-name


4.**Open a Pull Request on the main repository and describe your changes.**



📋 Commit Message Guidelines
We use Conventional Commits for commit messages:

feat: for new features.

fix: for bug fixes.

docs: for documentation changes.

style: for code style changes.

refactor: for code refactoring.

test: for test changes.

chore: for build/package changes.


📄 Code of Conduct
We are committed to providing a welcoming and inclusive environment. Please be respectful and considerate of others.

❓ Questions
If you have any questions, feel free to open an issue or contact the maintainer:

- **Reza Khalili** - [arsalankhalili688@gmail.com](mailto:arsalankhalili688@gmail.com)

Thank you for your contributions! 🚀



```bash
git add README.md CONTRIBUTING.md
git commit -m "docs: complete README and CONTRIBUTING documentation"
git push origin main