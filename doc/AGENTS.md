# Repository Guidelines

## Project Structure & Module Organization
- Root contains Python services: `app_new.py` (Flask API, port 28888), `generation_controller.py`, and helpers like `content_agent.py`, `image_processor.py`.
- Utility modules: `utils/` contains `script_executor.py`, `image_uploader.py`, `remote_downloader.py` for common operations.
- Data inputs and outputs: `data/` for prompts/assets, `generated_images/` and `output/` for rendered results, `matchers/` for matching logic, `doc/` for reference docs.
- Frontend Next.js app lives in `frontend/` (`src/app`, `src/components`, `src/lib`), with static assets in `frontend/public/`.
- Configuration: `config.py` for application config, `.env` for environment variables (copy from `.env.example`).

## Deployment (Cloud Server Only)

### Production Mode
- Frontend and backend integrated into single Flask application
- Fixed port: 28888 (cloud server constraint)
- Frontend must be built and exported first: `cd frontend && npm run export`
- Start: `python app_new.py`
- Access: `http://YOUR_SERVER_IP:28888`

## Build and Deployment Commands

### Backend
- Install deps: `pip install -r requirements.txt` (Python 3.8+)
- Run production: `python app_new.py`
- Health check: `curl http://YOUR_SERVER_IP:28888/api/health`

### Frontend
- Install deps: `cd frontend && npm install` (Node 18+)
- Build: `npm run build`
- Export for production: `npm run export` (outputs to `../frontend_dist`)
- Lint: `npm run lint`

### Environment Variables
- Copy `.env.example` to `.env` and configure
- Key variables:
  - `PORT`: Server port (fixed: 28888)
  - `HOST`: Server host (default: 0.0.0.0)
  - `FRONTEND_BUILD_DIR`: Frontend build directory (default: frontend_dist)
  - `SCRIPT_TIMEOUT`: Script execution timeout in seconds (default: 120)
  - `LOG_FILE`: Log file path (default: logs/app.log)
  - `SECRET_KEY`: Flask secret key (must change in production)

## Coding Style & Naming Conventions
- TypeScript/React: prefer functional components, 2-space indent, PascalCase for components, camelCase for props/variables, keep JSX tidy with small helpers in `src/lib`. Use Tailwind utility classes and keep shared UI in `src/components/ui`.
- Python: follow PEP 8, 4-space indent, snake_case for functions/variables, PascalCase for classes. Keep configuration in `config.py`; avoid hardcoding secrets.

## Testing Guidelines
- Current automation is minimal; rely on `npm run lint` and manual flows until tests are added.
- Smoke checks: backend `curl http://YOUR_SERVER_IP:28888/api/health`; frontend sanity via chat flow.
- When adding tests, place UI tests as `*.test.tsx` under `frontend/src` and service tests as `tests/` with pytest or unittest; mock network/AI calls.

## Commit & Pull Request Guidelines
- Use imperative, scoped messages (e.g., `feat: add preset selector`, `fix: guard empty prompt`). Group related file changes per commit.
- PRs should describe intent, include setup/run steps, screenshots of UI changes. Link issues or tasks when available.

## Security & Configuration Tips
- Copy `.env.example` to `.env` and configure secrets via environment variables; never commit keys or personal data.
- In production, always set a strong `SECRET_KEY` in `.env`.
- Respect `.gitignore` for generated assets (`generated_images/`, `output/`, `.next/`, `node_modules/`, `frontend_dist/`).
- CORS is disabled (same-origin access only).
- Frontend API calls use relative paths (same-origin).

## API Routes
All API routes are handled by Flask (`app_new.py`):
- Core: `/api/start_generate`, `/api/job/<id>/status`, `/api/generate`, `/api/analyze`, `/api/health`
- Image processing: `/api/run-banana`, `/api/run-jimeng4`, `/api/run-3d-banana`, `/api/run-banana-pro-img-jd`, `/api/run-turn`
- Utilities: `/api/upload-image`, `/api/save-render`
- Static files: `/output/*`, `/generated_images/*`
- Frontend routes: `/`, `/detail`, `/joyai`

## Quick Start

### Cloud Server Deployment
```bash
# 1. Install dependencies
pip install -r requirements.txt
cd frontend && npm install && cd ..

# 2. Configure environment
cp .env.example .env
# Edit .env: set PORT=28888, SECRET_KEY

# 3. Build frontend
cd frontend && npm run export && cd ..

# 4. Configure firewall (open port 28888)
sudo ufw allow 28888/tcp

# 5. Start application
python app_new.py
# Access: http://YOUR_SERVER_IP:28888
```

For detailed deployment instructions, see `doc/DEPLOYMENT.md` and `doc/CLOUD_DEPLOYMENT.md`.
