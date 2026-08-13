# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import contextlib
import os
from collections.abc import AsyncIterator

import google.auth
from a2a.server.tasks import InMemoryTaskStore
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.runners import Runner
from google.cloud import logging as google_cloud_logging

from app.app_utils import services
from app.app_utils.a2a import attach_a2a_routes
from app.app_utils.reasoning_engine_adapter import (
    attach_reasoning_engine_routes,
)
from app.app_utils.typing import Feedback
from app.rss_manager import add_rss_source, fetch_live_rss_content, get_rss_sources

load_dotenv()
otel_to_cloud = os.environ.get(
    "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY", ""
).lower() in ("true", "1")
_, project_id = google.auth.default()
logging_client = google_cloud_logging.Client()
logger = logging_client.logger(__name__)
allow_origins = (
    os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else None
)

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Runner for the A2A path, sharing the same session/artifact services as the
    # adk_api and reasoning_engine paths (see services.py).
    from app.agent import app as adk_app
    from app.agent import root_agent

    runner = Runner(
        app=adk_app,
        session_service=services.get_session_service(),
        memory_service=services.get_memory_service(),
        artifact_service=services.get_artifact_service(),
        auto_create_session=True,
    )
    app.state.runner = runner
    app.state.agent_app_name = adk_app.name
    await attach_a2a_routes(
        app,
        agent=root_agent,
        runner=runner,
        task_store=InMemoryTaskStore(),
        rpc_path=f"/a2a/{adk_app.name}",
    )
    yield


app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    artifact_service_uri=services.ARTIFACT_SERVICE_URI,
    allow_origins=allow_origins,
    session_service_uri=services.SESSION_SERVICE_URI,
    memory_service_uri=services.MEMORY_SERVICE_URI,
    otel_to_cloud=otel_to_cloud,
    lifespan=lifespan,
)
app.title = "brewcraft-coffee"
app.description = "API for interacting with BrewCraft Specialty Coffee Concierge"

attach_reasoning_engine_routes(app)


class FeedRequest(BaseModel):
    name: str
    feed_url: str
    category: str = "Tech & AI"


@app.get("/api/feeds")
def list_feeds():
    """Returns currently registered RSS feed sources."""
    return get_rss_sources()


@app.post("/api/feeds")
def create_feed(feed: FeedRequest):
    """Registers a new RSS feed source."""
    res = add_rss_source(name=feed.name, feed_url=feed.feed_url, category=feed.category)
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res["message"])
    return res


@app.get("/admin/feeds", response_class=HTMLResponse)
def feed_admin_form():
    """Renders the web UI form to register and manage RSS feed sources."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RSS Feed Sources Manager | BrewCraft Portfolio</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0f172a;
            --card-bg: rgba(30, 41, 59, 0.7);
            --accent-color: #6366f1;
            --accent-hover: #4f46e5;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border-color: rgba(255, 255, 255, 0.1);
            --success-color: #10b981;
        }

        body {
            font-family: 'Inter', sans-serif;
            background: radial-gradient(circle at top left, #1e1b4b, #0f172a);
            color: var(--text-main);
            min-height: 100vh;
            margin: 0;
            padding: 2rem 1rem;
            display: flex;
            justify-content: center;
        }

        .container {
            max-width: 800px;
            width: 100%;
        }

        .header {
            text-align: center;
            margin-bottom: 2.5rem;
        }

        .header h1 {
            font-family: 'Outfit', sans-serif;
            font-size: 2.5rem;
            margin: 0 0 0.5rem 0;
            background: linear-gradient(135deg, #a5b4fc, #6366f1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .header p {
            color: var(--text-muted);
            font-size: 1.05rem;
        }

        .glass-card {
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 2rem;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3);
            margin-bottom: 2rem;
        }

        .form-group {
            margin-bottom: 1.5rem;
        }

        label {
            display: block;
            font-weight: 500;
            margin-bottom: 0.5rem;
            color: #cbd5e1;
        }

        input, select {
            width: 100%;
            padding: 0.85rem 1rem;
            border-radius: 8px;
            border: 1px solid var(--border-color);
            background: rgba(15, 23, 42, 0.6);
            color: #fff;
            font-size: 1rem;
            box-sizing: border-box;
            transition: all 0.2s ease;
        }

        input:focus, select:focus {
            outline: none;
            border-color: var(--accent-color);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.25);
        }

        button {
            width: 100%;
            padding: 0.95rem;
            border-radius: 8px;
            border: none;
            background: linear-gradient(135deg, #6366f1, #4f46e5);
            color: white;
            font-family: 'Outfit', sans-serif;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }

        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(99, 102, 241, 0.4);
        }

        #notification {
            display: none;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1.5rem;
            font-weight: 500;
        }

        .success {
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid var(--success-color);
            color: #34d399;
        }

        .error {
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid #ef4444;
            color: #f87171;
        }

        .feed-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }

        .feed-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem;
            border-bottom: 1px solid var(--border-color);
        }

        .feed-item:last-child {
            border-bottom: none;
        }

        .feed-info h4 {
            margin: 0 0 0.25rem 0;
            font-size: 1.1rem;
        }

        .feed-info p {
            margin: 0;
            color: var(--text-muted);
            font-size: 0.85rem;
        }

        .tag {
            background: rgba(99, 102, 241, 0.2);
            color: #a5b4fc;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📡 RSS Content Source Manager</h1>
            <p>Register new blog or research feeds for the Live Tech & RSS Content Fetcher</p>
        </div>

        <div id="notification"></div>

        <div class="glass-card">
            <form id="feedForm">
                <div class="form-group">
                    <label for="name">Publisher / Blog Name</label>
                    <input type="text" id="name" placeholder="e.g. Google DeepMind AI Blog" required>
                </div>

                <div class="form-group">
                    <label for="feed_url">RSS / Atom Feed URL</label>
                    <input type="url" id="feed_url" placeholder="https://blog.google/technology/ai/rss/" required>
                </div>

                <div class="form-group">
                    <label for="category">Category</label>
                    <select id="category">
                        <option value="AI & Agentic Systems">AI & Agentic Systems</option>
                        <option value="Cybersecurity">Cybersecurity</option>
                        <option value="Software Architecture">Software Architecture</option>
                        <option value="Coffee Tech & Innovations">Coffee Tech & Innovations</option>
                        <option value="Research & Publications">Research & Publications</option>
                    </select>
                </div>

                <button type="submit">➕ Register RSS Source</button>
            </form>
        </div>

        <div class="glass-card">
            <h2 style="font-family: 'Outfit'; font-size: 1.4rem; margin-top: 0;">Registered Sources</h2>
            <div id="feedListContainer">
                <ul class="feed-list" id="feedList">
                    <li style="text-align: center; color: var(--text-muted); padding: 1rem;">Loading active sources...</li>
                </ul>
            </div>
        </div>
    </div>

    <script>
        async function loadFeeds() {
            try {
                const res = await fetch('/api/feeds');
                const feeds = await res.json();
                const listEl = document.getElementById('feedList');
                listEl.innerHTML = '';

                if (feeds.length === 0) {
                    listEl.innerHTML = '<li style="text-align: center; color: var(--text-muted);">No RSS sources registered yet.</li>';
                    return;
                }

                feeds.forEach(f => {
                    const li = document.createElement('li');
                    li.className = 'feed-item';
                    li.innerHTML = `
                        <div class="feed-info">
                            <h4>${f.name}</h4>
                            <p>${f.feed_url}</p>
                        </div>
                        <span class="tag">${f.category}</span>
                    `;
                    listEl.appendChild(li);
                });
            } catch (err) {
                console.error(err);
            }
        }

        document.getElementById('feedForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const notification = document.getElementById('notification');
            notification.style.display = 'none';

            const name = document.getElementById('name').value;
            const feed_url = document.getElementById('feed_url').value;
            const category = document.getElementById('category').value;

            try {
                const res = await fetch('/api/feeds', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, feed_url, category })
                });

                const data = await res.json();

                if (res.ok && data.status === 'success') {
                    notification.className = 'success';
                    notification.innerText = data.message || 'RSS Feed source added successfully!';
                    notification.style.display = 'block';
                    document.getElementById('feedForm').reset();
                    loadFeeds();
                } else {
                    notification.className = 'error';
                    notification.innerText = data.detail || data.message || 'Failed to add RSS feed source.';
                    notification.style.display = 'block';
                }
            } catch (err) {
                notification.className = 'error';
                notification.innerText = 'Network error occurred while registering feed.';
                notification.style.display = 'block';
            }
        });

        loadFeeds();
    </script>
</body>
</html>
    """


@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    """Collect and log feedback."""
    logger.log_struct(feedback.model_dump(), severity="INFO")
    return {"status": "success"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
