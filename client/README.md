# StudyWars frontend

[Play the live demo](https://studywars-lime.vercel.app/), or follow the
[local development instructions](../README.md#local-development) to run your own copy.

The frontend uses React 19, Vite 8, React Router, and Tailwind CSS 4. Start the FastAPI
backend on port 8000, then run these commands from this `client/` directory:

```bash
npm ci
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` and `/ws` to the local backend.

Checks run from this directory:

```bash
npm run lint -- --deny-warnings
npm test
npm run build
```

The repository-root [Vercel configuration](../vercel.json) builds and deploys both the
frontend and backend. See the main README for [deployment](../README.md#deployment),
[game instructions](../README.md#playing-a-game), and [the API reference](../README.md#api-reference).
