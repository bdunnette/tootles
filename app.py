from os import environ, path
from zoneinfo import ZoneInfo

import iso8601
from dotenv import load_dotenv
from flask import Flask, render_template, request
from flask_cors import CORS
from mastodon import Mastodon
from zappa.asynchronous import task

app = Flask(__name__)
CORS(app)
app.logger.info("Starting up...")
app.logger.info(f"Zappa is running in {app.config['ENV']} mode.")
app.logger.info(f"DEBUG={app.debug}")

# Load environment variables from .env file
dotenv_path = path.join(path.dirname(__file__), ".env")
load_dotenv(dotenv_path)


class Config:
    """Flask configuration variables."""

    # Mastodon Config
    API_BASE_URL = environ.get("API_BASE_URL", default="https://mastodon.social")


app.config.from_object(Config)

if app.debug is True:
    app.config["TEMPLATES_AUTO_RELOAD"] = True
app.logger.info("Config loaded.")


@app.route("/")
def hello_world(
    base_url=app.config["API_BASE_URL"],
):
    """Render the homepage."""
    return render_template("index.html", base_url=base_url)


@task
def schedule_toot(
    token=None,
    status=None,
    scheduled_at=None,
    base_url=app.config["API_BASE_URL"],
    visibility="private",
):
    """This takes a long time!"""
    if not token:
        raise ValueError("No token provided")
    if not status:
        raise ValueError("No status provided")
    if not scheduled_at:
        raise ValueError("No scheduled_at provided")
    scheduled_dt = iso8601.parse_date(scheduled_at)
    app.logger.info(f"Scheduling toot for {scheduled_dt}")
    masto = Mastodon(
        access_token=token, api_base_url=base_url, ratelimit_method="throw"
    )
    masto.status_post(status, scheduled_at=scheduled_dt, visibility=visibility)
    app.logger.info("Toot scheduled!")


@app.route("/toot", methods=["POST"])
def toot_scheduler():
    """This returns immediately!"""
    app.logger.debug(request.values)
    token = request.values.get("token")
    base_url = request.values.get("base_url")
    status = request.values.get("status")
    scheduled_at = request.values.get("scheduled_at")
    scheduled_dt = iso8601.parse_date(
        scheduled_at, default_timezone=ZoneInfo(request.values.get("timezone"))
    )
    app.logger.debug(scheduled_dt)
    scheduled_utc = scheduled_dt.astimezone(ZoneInfo("UTC")).isoformat()
    app.logger.debug(scheduled_utc)
    visibility = request.values.get("visibility")
    if visibility not in ["public", "unlisted", "direct"]:
        visibility = "private"
    scheduled = schedule_toot(
        base_url=base_url,
        token=token,
        status=status,
        scheduled_at=scheduled_utc,
        visibility=visibility,
    )
    return {"scheduled": scheduled}


if __name__ == "__main__":
    app.run()
