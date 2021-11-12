from api import api
from datetime import datetime
from rfeed import Guid, Item, Feed
from extensions import MediaItem, WebfeedsIcon, WebfeedsCover, MediaContent, Webfeeds

def generate_episode_item(episode):
	"""For Item:
		episode_air_date -> pubDate as datetime.fromiso
		description -> description
		title -> title
		id -> link as f'https://vrv.co/watch/{id}'
		id -> guid
		images['thumbnail'][:1] -> image (part of description)
		link + '#comments' -> comments

		For MediaItem:
		images['thumbnail'][:1] -> url (part of description)
		'image' -> medium
		'image/jpeg' -> type
		True -> isDefault
	"""
	link = f'https://vrv.co/watch/{episode["id"]}'
	thumbnail = episode["images"]['thumbnail'][0][-1]["source"]

	media_item_info = {
		"url": thumbnail,
		"medium": "image",
		"type": "image/jpeg",
		"isDefault": True
	}

	media_item = MediaItem(**media_item_info)

	episode_info = {
		"title": episode["title"],
		"description": f'<img src="{thumbnail}" />\n<p>{episode["description"]}</p>',
		"link": link,
		"comments": link + "#comments",
		"guid": Guid(link),
		# Doesn't like Z
		"pubDate": datetime.fromisoformat(episode["episode_air_date"].replace("Z", "")),
		"extensions": [media_item]
	}

	return Item(**episode_info)


def generate_series_feed(series_id):
	"""For Feed:
		description -> description
		title -> title
		id -> link as f'https://vrv.co/series/{id}'
		
		For WebfeedsCover:
		images['poster_wide'][:1] -> url

		For WebfeedsIcon:
		images['poster_tall'][0] -> url
	"""
	
	series = api.get_series(series_id)
	episodes = api.get_all_series_episodes(series_id)

	images = series["images"]
	cover_url = images['poster_wide'][0][-1]["source"]
	icon_url = images['poster_tall'][0][0]["source"]

	cover = WebfeedsCover(cover_url)
	icon = WebfeedsIcon(icon_url)

	feed_info = {
		"title": series["title"],
		"description": series["description"],
		"link": f'https://vrv.co/series/{series["id"]}',
		"items": map(lambda x: generate_episode_item(x), episodes),
		"extensions": [MediaContent(), Webfeeds(), cover, icon,]
	}

	return Feed(**feed_info)

def generate_season_feed(season_id):
	season = api.get_season(season_id)
	episodes = api.get_all_season_episodes(season_id)

	feed_info = {
		"title": season["title"],
		"description": season["description"],
		"link": f'https://vrv.co/series/{season["series_id"]}',
		"items": map(lambda x: generate_episode_item(x), episodes),
		"extensions": [MediaContent(), Webfeeds(),]
	}
	
	return Feed(**feed_info)
