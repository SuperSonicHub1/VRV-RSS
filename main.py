"""Future additions: comments
https://api.vrv.co/talkbox/guestbooks/G4VUQMQGW/comments?page=1&page_size=50
Comments are in reverse chronological order!"""

from generators import generate_series_feed, generate_season_feed
from api import api
from flask import Flask, render_template, request, redirect, url_for
from flask_caching import Cache

THREE_HOURS = 60 * 60 * 3

app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache'})

@app.route("/")
def index():
	return render_template("index.html")

@app.route('/lookup')
def lookup():
	return redirect(
		url_for(
			request.args.get("type"), 
			id=request.args.get("id"),
		)
	)

@app.route("/season_preview")
def season_preview():
	series_id = request.args.get("id")

	series = api.get_series(series_id)
	seasons = api.get_seasons(series_id)

	season_id_tuples = map(
		lambda x: (x["title"], x["id"]),
		seasons["items"]
	)

	return render_template("seasons.html", title=series["title"], seasons=season_id_tuples)

@app.route("/series/<id>")
@cache.cached(timeout=THREE_HOURS)
def series(id: str):
	feed = generate_series_feed(id)
	return app.response_class(feed.rss(), mimetype='application/rss+xml')

@app.route("/season/<id>")
@cache.cached(timeout=THREE_HOURS)
def season(id: str):
	feed = generate_season_feed(id)
	return app.response_class(feed.rss(), mimetype='application/rss+xml')

app.run(host='0.0.0.0', port=8080)
