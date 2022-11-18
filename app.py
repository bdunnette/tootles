import random
from datetime import datetime, timedelta
from os import environ, path

from dotenv import load_dotenv
from flask import Flask, render_template
from mastodon import Mastodon
from zappa.asynchronous import task

app = Flask(__name__)
app.logger.info("Starting up...")
app.logger.info(f"Zappa is running in {app.config['ENV']} mode.")
app.logger.info(f"DEBUG={app.debug}")

# Load environment variables from .env file
dotenv_path = path.join(path.dirname(__file__), ".env")
load_dotenv(dotenv_path)


class Config:
    """Flask configuration variables."""

    # Mastodon Config
    API_BASE_URL = environ.get("API_BASE_URL", default="https://mspsocial.net")
    MASTODON_ACCESS_TOKEN = environ.get("MASTODON_ACCESS_TOKEN")


app.config.from_object(Config)

if app.debug is True:
    app.config["TEMPLATES_AUTO_RELOAD"] = True
app.logger.info("Config loaded.")
app.logger.debug(app.config)


@app.route("/")
def hello_world(toot_id=None):
    return render_template("index.html", toot_id=toot_id)


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
        # raise ValueError('No token provided')
        token = app.config["MASTODON_ACCESS_TOKEN"]
    masto = Mastodon(
        access_token=token, api_base_url=base_url, ratelimit_method="throw"
    )
    app.logger.debug(masto)
    if scheduled_at is None:
        scheduled_at = datetime.now() + timedelta(minutes=random.randint(5, 20))
    if status is None:
        status = f"This status was scheduled for tooting at {scheduled_at:%Y-%m-%d %H:%M:%S}. Make of that what you will."
    app.logger.info(f"Scheduling toot {status} for {scheduled_at} on {base_url}")
    scheduled = masto.status_post(
        status, scheduled_at=scheduled_at, visibility=visibility
    )
    app.logger.debug(scheduled)
    app.logger.info(f"Successfully scheduled toot {scheduled['id']}")


@app.route("/toot", methods=["POST"])
def toot_scheduler():
    """This returns immediately!"""
    schedule_toot()
    return "Your pie is being made!"


if __name__ == "__main__":
    app.run()
