import random
import string
import json
import re
import time
import urllib.parse
import base64
import hmac
import hashlib

from requests import Session

class VRVAPI:
	"""A minimal implementation of VRV's OAuth-authenicated, document-based JSON REST API. Takes heavily from youtube-dl: https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/extractor/vrv.py"""

	api_domain: str = 'https://api.vrv.co'
	cms_signing: dict = None	
	api_params: dict

	def __init__(self, session: Session = Session()):
		self.session = session

		res = self.session.get("https://vrv.co")
		text = res.text
		app_config = re.search(r'window\.__APP_CONFIG__\s*=\s*({.+?})(?:</script>|;)', text).group(1)
		self.api_params = json.loads(app_config)['cxApiParams']
		self.api_domain = self.api_params.get("apiDomain", self.api_domain)
	
	def call_api(self, path, data=None):
		base_url = self.api_domain + '/core/' + path
		query = [
            ('oauth_consumer_key', self.api_params['oAuthKey']),
            ('oauth_nonce', ''.join([random.choice(string.ascii_letters) for _ in range(32)])),
            ('oauth_signature_method', 'HMAC-SHA1'),
            ('oauth_timestamp', int(time.time())),
        ]
		encoded_query = urllib.parse.urlencode(query)
		headers = {}
		if data:
			data = json.dumps(data).encode()
			headers['Content-Type'] = 'application/json'
		base_string = '&'.join([
            'POST' if data else 'GET',
            urllib.parse.quote(base_url, ''),
            urllib.parse.quote(encoded_query, '')])
		oauth_signature = base64.b64encode(hmac.new(
            (self.api_params['oAuthSecret'] + '&').encode('ascii'),
            base_string.encode(), hashlib.sha1).digest()).decode()
		encoded_query += '&oauth_signature=' + urllib.parse.quote(oauth_signature, '')
		if data:
			res = self.session.post('?'.join([base_url, encoded_query]), data=data, headers=headers)
		else:
			res = self.session.get('?'.join([base_url, encoded_query]), headers=headers)
		res.raise_for_status()
		return res.json()

	def call_cms(self, path):
		if not self.cms_signing:
			index = self.call_api('index')
			self.cms_signing = index.get('cms_signing') or {}
			if not self.cms_signing:
				for signing_policy in index.get("signing_policies", []):
					signing_path = signing_policy.get("path")
					if signing_path and signing_path.startswith("/cms/"):
						name, value = signing_policy.get("name"), signing_policy.get("value")
						if name and value:
							self.cms_signing[name] = value
		res = self.session.get(f"{self.api_domain}{path}", params=self.cms_signing)
		res.raise_for_status()
		return res.json()

	def get_cms_resource(self, resource_key):
		return self.call_api(
			"cms_resource",
			data={"resource_key": resource_key},
		)['__links__']['cms_resource']['href']
	
	def get_series(self, series_id):
		"""For Feed:
		description -> description
		title -> title
		id -> link as f'https://vrv.co/series/{id}'
		
		For WebfeedsCover:
		images['poster_wide'][:1] -> url

		For WebfeedsIcon:
		images['poster_tall'][0] -> url
		"""
		resource_path = self.get_cms_resource(f"cms:/series/{series_id}")
		return self.call_cms(resource_path)

	def get_seasons(self, series_id):
		resource_path = self.get_cms_resource(f"cms:/seasons?series_id={series_id}")
		return self.call_cms(resource_path)
		
	def get_episodes(self, season_id):
		resource_path = self.get_cms_resource(f"cms:/episodes?season_id={season_id}")
		return self.call_cms(resource_path)

	def get_episode(self, episode_id):
		"""For Item:
		episode_air_date -> pubDate as datetime.fromiso
		description -> description
		title -> title
		id -> link as f'https://vrv.co/watch/{id}
		id -> guid
		images['poster_tall'][:1] -> image (part of description)
		link + '#comments' -> comments

		For MediaItem:
		images['poster_tall'][:1] -> url (part of description)
		'image' -> medium
		'image/jpeg' -> type
		True -> isDefault
		"""
		resource_path = self.get_cms_resource(f"cms:/episodes/{episode_id}")
		return self.call_cms(resource_path)

	def get_season(self, season_id):
		resource_path = self.get_cms_resource(f"cms:/seasons/{season_id}")
		return self.call_cms(resource_path)

	@staticmethod
	def id_map(iterable):
		return map(
			lambda x: x["id"],
			iterable,
		)

	def get_all_season_episodes(self, season_id):
		episodes = self.id_map(self.get_episodes(season_id)["items"])
		yield from map(lambda x: self.get_episode(x), episodes)

	def get_all_series_episodes(self, series_id):
		seasons = self.id_map(self.get_seasons(series_id)["items"])
		for season in seasons:
			yield from self.get_all_season_episodes(season)

api = VRVAPI()
