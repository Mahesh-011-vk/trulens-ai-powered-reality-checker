# Contributing to TruthLens

Thank you for your interest in contributing! 🎉

## How to Contribute

### 🐛 Reporting Bugs
1. Check [existing issues](https://github.com/Mahesh-011-vk/trulens-ai-powered-reality-checker/issues) first
2. Open a new issue with:
   - Clear title describing the bug
   - Steps to reproduce
   - Expected vs actual behavior
   - Your OS, Python version, and Node.js version

### 💡 Suggesting Features
- Open a GitHub Discussion or Issue labeled `enhancement`
- Describe the use case clearly

### 🔧 Submitting Pull Requests

1. **Fork** the repository
2. **Create a branch**: `git checkout -b feature/your-feature-name`
3. **Make your changes** following the guidelines below
4. **Test** your changes locally (backend + frontend)
5. **Commit** with a clear message: `git commit -m "feat: add XYZ feature"`
6. **Push**: `git push origin feature/your-feature-name`
7. **Open a Pull Request** against the `main` branch

### Commit Message Convention
```
feat:     New feature
fix:      Bug fix
docs:     Documentation change
style:    Formatting, no logic change
refactor: Code restructure without feature change
test:     Adding or fixing tests
chore:    Build tools, dependency updates
```

## Development Setup

```bash
# Backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8000

# Frontend (separate terminal)
cd frontend && npm install && npm run dev
```

## Code Style
- **Python**: Follow PEP 8. Keep functions focused and documented.
- **JavaScript/React**: Use functional components with hooks. No class components.
- **CSS**: Add new styles to `App.css` using existing CSS variable tokens from `index.css`.

## Areas to Contribute

- 🔍 Additional fact-check API integrations (e.g., ClaimBuster, Factiverse)
- 🌍 Multi-language support
- 📊 Better model training datasets
- 🧪 Unit tests for the verification engine
- 🐳 Docker / docker-compose setup
- 📱 Mobile-responsive UI improvements

---

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
