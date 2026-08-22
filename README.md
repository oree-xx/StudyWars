<div align="center">
  <img src="docs/brand/logo.svg" alt="StudyWars" width="760" />

  **Turn your notes into a live, multiplayer quiz in seconds.**

  Upload a PDF or paste your notes, let AI write the questions, and host a Kahoot style
  game your friends can join from their phones.

  [![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
  [![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
  [![Vite](https://img.shields.io/badge/Vite-8-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
  [![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-4-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
  [![Claude API](https://img.shields.io/badge/AI-Claude-D97757?logo=anthropic&logoColor=white)](https://www.anthropic.com/)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## Contents

- [How it works](#how-it-works)
- [Features](#features)
- [Screenshots](#screenshots)
- [Tech stack](#tech-stack)
- [Architecture](#architecture)
- [Getting started](#getting-started)
- [Playing a game](#playing-a-game)
- [API reference](#api-reference)
- [Project structure](#project-structure)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

## How it works

```mermaid
flowchart LR
    A["📄 Host uploads<br/>PDF or notes"] --> B["🤖 Claude generates<br/>multiple-choice questions"]
    B --> C["🎮 Host opens a<br/>live game room"]
    C --> D["📱 Players join<br/>with a room code"]
    D --> E["⚡ Real-time quiz<br/>+ live leaderboard"]
```

1. **Host uploads a PDF or pastes notes.**
2. **AI reads the content** and generates multiple choice questions automatically.
3. **Host starts a live game room** and shares a short join code.
4. **Players join** from their phones or laptops — no account needed.
5. **Everyone answers in real time**, and the leaderboard updates after every question.

## Features

- 🧠 **AI-generated quizzes** — drop in a PDF or raw notes, get 1–20 multiple-choice questions back, powered by the Claude API.
- ⚡ **Real-time gameplay** — rooms, questions, reveals, and scoring are all pushed live over WebSockets.
- 🏆 **Live leaderboard** — scores update after every question so players can see where they stand.
- 📱 **No install for players** — join from any browser with a room code and a name.
- 🎛️ **Host controls** — start the game, reveal answers, and advance questions on your own pace.
- 🖥️ **Two synced views** — a big-screen host view for the room, and a lightweight player view for each device.

## Screenshots

| Home | Host setup | Review questions |
|:---:|:---:|:---:|
| ![Home screen](docs/screenshots/home.jpg) | ![Host setup form](docs/screenshots/host-setup.jpg) | ![Review generated questions](docs/screenshots/question-review.jpg) |

| Join a quiz | Host lobby | Live question |
|:---:|:---:|:---:|
| ![Join a quiz](docs/screenshots/join-quiz.jpg) | ![Host lobby with a player joined](docs/screenshots/host-lobby.jpg) | ![Live question on the host screen](docs/screenshots/host-live-question.jpg) |

| Player answering | leaderboard | Final results |
|:---:|:---:|:---:|
| ![Player answer options](docs/screenshots/player-answer-options.jpg) | ![Reveal screen with leaderboard](docs/screenshots/host-reveal.jpg) | ![Final results screen](docs/screenshots/final-results.jpg) |

## Tech stack

| Layer | Tech |
|---|---|
| Backend | Python, [FastAPI](https://fastapi.tiangolo.com/), native WebSockets, [Anthropic Claude API](https://www.anthropic.com/) |
| Frontend | [React](https://react.dev/) (Vite), [React Router](https://reactrouter.com/), [Tailwind CSS](https://tailwindcss.com/) |
| PDF parsing | [pypdf](https://pypi.org/project/pypdf/) |
| Realtime | WebSockets (host + player channels per room) |
| State | In-memory room/game state on the server (no database required) |

## Architecture

```mermaid
flowchart TB
    subgraph Client["React (Vite) — :5173"]
        Home["Home"]
        Host["Host page"]
        Join["Join / Play page"]
    end

    subgraph Server["FastAPI — :8000"]
        HTTP["/api/generate-questions<br/>/api/rooms"]
        WSHost["/ws/host/{room_code}"]
        WSPlayer["/ws/player/{room_code}"]
        Rooms["Room manager<br/>(in-memory state + scoring)"]
        AI["Claude integration"]
    end

    Claude[("Anthropic<br/>Claude API")]

    Host -- "upload PDF / notes" --> HTTP
    HTTP -- "generate_questions()" --> AI --> Claude
    Host -- "create room" --> HTTP --> Rooms
    Host <-- "start / next / reveal" --> WSHost --> Rooms
    Join <-- "join / answer" --> WSPlayer --> Rooms
```

The frontend never talks to Claude directly, the backend generates the questions, creates the
room, and then fans out live game state to every connected socket via the `Room` object in
`app/rooms.py`.

## Getting started

### Prerequisites

- [Python 3.11+](https://www.python.org/downloads/)
- [Node.js 18+](https://nodejs.org/) and npm
- A [Claude API key](https://console.anthropic.com/)

### 1. Clone the repo

```bash
git clone https://github.com/oree-xx/StudyWars.git
cd StudyWars
```

### 2. Backend setup

```bash
cd server
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt

copy .env.example .env         # Windows
# cp .env.example .env         # macOS/Linux
```

Open `server/.env` and paste in your `ANTHROPIC_API_KEY`.

Run the backend:

```bash
uvicorn app.main:app --reload
```

It starts on `http://localhost:8000`. Check it's alive at `http://localhost:8000/health`.

### 3. Frontend setup

In a separate terminal:

```bash
cd client
npm install
npm run dev
```

It starts on `http://localhost:5173` and proxies `/api` and `/ws` requests through to the
backend automatically — no extra config needed.

## Playing a game

1. Open `http://localhost:5173`.
2. Click **Host a Quiz**, upload a PDF or paste some notes, pick a question count, and generate.
3. Share the room code that appears in the lobby.
4. On a second device (or another browser tab), click **Join a Quiz**, enter the code and a
   name.
5. Once everyone's in, the host starts the game — questions, reveals, and the leaderboard all
   sync live to every player.

## API reference

### HTTP

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check. |
| `POST` | `/api/generate-questions` | Accepts a PDF file (`multipart/form-data`) or `notes` text plus `num_questions` (1–20); returns AI-generated multiple-choice questions. |
| `POST` | `/api/rooms` | Creates a game room from a list of questions; returns a `room_code` and a `host_token`. |

### WebSockets

| Path | Role | Notes |
|---|---|---|
| `/ws/host/{room_code}?token=...` | Host | Authenticated with the room's `host_token`. Sends `start_game`, `next_question`, `reveal_now`; receives room/player state. |
| `/ws/player/{room_code}?name=...` | Player | Joins the lobby by name. Sends `answer` with an `option_index`; receives live question, reveal, and leaderboard updates. |

## Project structure

```
server/                FastAPI backend
  app/
    main.py             App entrypoint, CORS, router wiring
    config.py            Settings (.env loading)
    ai.py                Claude integration (question generation)
    pdf_utils.py          PDF text extraction
    models.py             Question schema
    rooms.py               In-memory game/room state + scoring
    routers/
      questions.py          POST /api/generate-questions
      rooms.py                POST /api/rooms
      ws.py                     WebSocket endpoints (host + player)

client/                React frontend
  src/
    pages/               Home, Host, Join, Play
    components/
      host/                Setup form, lobby, live question, reveal, results
      play/                 Waiting screen, answer options, reveal
      Leaderboard.jsx        Shared leaderboard UI
    hooks/
      useGameSocket.js      WebSocket connection hook
    lib/
      api.js                REST API client
      ws.js                  WebSocket URL builders
      optionColors.js         Answer-option color mapping
```

## Roadmap

- [ ] Persist rooms/scores beyond process restarts
- [ ] Support image-based question generation (diagrams, slides)
- [ ] Per-question timers and speed bonuses
- [ ] Exportable results (CSV / share link)

## Contributing

Issues and pull requests are welcome. If you're adding a feature, please open an issue first to
discuss what you'd like to change.

## License

Distributed under the [MIT License](LICENSE).
