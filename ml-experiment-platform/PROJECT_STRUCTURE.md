# Project Structure

```text
ml-experiment-platform/
├── backend/
│   ├── app/
│   │   ├── experiments/runner.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── schemas.py
│   │   └── database.py
│   ├── tests/test_api.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/App.tsx
│   ├── src/api.ts
│   ├── src/types.ts
│   ├── src/styles.css
│   ├── Dockerfile
│   └── package.json
├── k8s/
│   ├── backend-deployment.yaml
│   └── frontend-deployment.yaml
├── .github/workflows/ci.yml
├── docker-compose.yml
├── docs/resume_bullets.md
└── README.md
```
