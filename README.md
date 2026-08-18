# StudyWars

A live, multiplayer quiz game (Kahoot-style) where the host uploads their notes or a PDF, and AI generates the quiz questions automatically.

## How it works
1. Host uploads a PDF or pastes notes.
2. AI (Claude) reads the content and generates multiple-choice questions.
3. Host starts a live game room and shares a join code.
4. Players join from their phones/laptops and answer questions in real time.
5. Live leaderboard updates after every question.

## Stack
- **Backend:** Python, FastAPI, WebSockets, Anthropic Claude API
- **Frontend:** React (Vite), Tailwind CSS, React Router

## Local development

### 1. Get a Claude API key
Grab one from [console.anthropic.com](https://console.anthropic.com/).

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
It starts on `http://localhost:5173` and proxies `/api` and `/ws` requests through to the backend automatically — no extra config needed.

### 4. Play
Open `http://localhost:5173`, click **Host a Quiz**, upload a PDF or paste some notes, and go. Open a second browser tab (or another device on the same network) and click **Join a Quiz** with the room code to play along.

## Project structure
```
server/           FastAPI backend
  app/
    main.py       App entrypoint, CORS, router wiring
    ai.py         Claude integration (question generation)
    pdf_utils.py  PDF text extraction
    models.py     Question schema
    rooms.py      In-memory game/room state + scoring
    routers/      HTTP + WebSocket endpoints

client/           React frontend
  src/
    pages/        Home, Host, Join, Play
    components/   Host- and player-specific UI pieces
    hooks/        useGameSocket (WebSocket connection)
    lib/          API client, WebSocket URL builders
```
