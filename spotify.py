import random
import requests
import json
import time
import sys
import string
import base64
import six.moves.urllib.parse as urllibparse
from multipledispatch import dispatch
from spotipy.oauth2 import RequestHandler, SpotifyStateError, SpotifyOauthError
from six.moves.BaseHTTPServer import HTTPServer


class SpotifyClient:
    API_URL = "https://api.spotify.com"
    ACCOUNTS_URL = "https://accounts.spotify.com"

    def __init__(self, clientid: str, clientsecret: str, redirect_uri: str, scope: list[str]) -> None:
        self.__BASIC_AUTH = base64.b64encode(str(clientid + ":" + clientsecret).encode()).decode()
        self.__CLIENT_SECRET = clientsecret
        self.__CLIENT_ID = clientid
        self.__REDIRECT_URI = redirect_uri
        self.__scope = scope
        self.__session = requests.Session()
        self.__auth_token = None
        self.__time_of_token = None
        self.__token_expires_in = None

    def add_scope(self, scope: str):
        self.__scope.append(scope)

    def _get_auth_url(self):
        self.__stored_state = self._generate_random_string(16)
        scope = ' '.join(self.__scope)
        url = f'{self.ACCOUNTS_URL}/authorize'
        params = {
            'client_id': self.__CLIENT_ID,
            'response_type': 'code',
            'redirect_uri': self.__REDIRECT_URI,
            'state': self.__stored_state,
            'scope': scope
        }
        query = urllibparse.urlencode(params)
        return "%s?%s" % (url, query)

    def _auth(self):
        if self.__time_of_token and self.__token_expires_in:
            if self.__time_of_token + self.__token_expires_in < time.clock_gettime(time.CLOCK_BOOTTIME):        
                self._get_auth_token(self.__refresh_token)
            return
        moshe = self._get_auth_url()
        print(moshe)
        server: HTTPServer = start_local_http_server(8000)
        server.handle_request()
        if server.error is not None:
            raise server.error
        elif self.__stored_state is not None and server.state != self.__stored_state:
            raise SpotifyStateError(self.state, server.state)
        elif server.auth_code is not None:
            auth_code = server.auth_code
        else:
            raise SpotifyOauthError("Server listening on localhost has not been accessed")
        self._get_auth_token(auth_code)
        self.__user_authed = True

    def _get_auth_token(self, auth_code):
        if self.__time_of_token:
            if self.__time_of_token + self.__token_expires_in < time.clock_gettime(time.CLOCK_BOOTTIME) and self.__user_authed:
                auth_code = self.__refresh_token
            elif self.__time_of_token + self.__token_expires_in > time.clock_gettime(time.CLOCK_BOOTTIME) and self.__auth_token:
                return
        response = self.__session.post(f'{self.ACCOUNTS_URL}/api/token', data={
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': self.__REDIRECT_URI
        }, headers={
            'Authorization': f'Basic {self.__BASIC_AUTH}',
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        self.__auth_token = response.json()['access_token']
        self.__refresh_token = response.json()['refresh_token']
        self.__time_of_token = time.clock_gettime(time.CLOCK_BOOTTIME)
        self.__token_expires_in = response.json()['expires_in']
    
    def get_currect_user_id(self):
        self._auth()
        res = self.__session.get(f'{self.API_URL}/v1/me', headers={
            'Authorization': f'Bearer {self.__auth_token}'
        })
        self.current_user_id = res.json()['id']
        return self.current_user_id

    def get_user_tracks(self, time_range='short_term', limit=5):
        self._auth()
        response = self.__session.get(f'{self.API_URL}/v1/me/top/tracks?time_range={time_range}&limit={limit}', headers={
            'Authorization': f'Bearer {self.__auth_token}'
        })
        names = [item['name'] for item in response.json()['items']]
        urls = [item['external_urls']['spotify'] for item in response.json()['items']]
        tracks = [(name, url) for name, url in zip(names, urls)]
        print(tracks)

    def add_items_to_playlist(self, id: str, tracks: list, position: int=None):
        """Adds an item to the playlist
        
        parameters: 
            -id - the playlist's spotify id

            -tracks - the list of uris to add to the playlist

            id and uri and explained here https://developer.spotify.com/documentation/web-api/concepts/spotify-uris-ids
        """
        self._auth()
        req_body = {
            "uris": tracks
        }
        if position:
            req_body["position"] = position
        res = self.__session.post(f'{self.API_URL}/v1/playlists/{id}/tracks', data=json.dumps(req_body),headers={
            'Authorization': f'Bearer {self.__auth_token}',
            'Content-Type': 'application/json',
            'Content-Length': str(sys.getsizeof(req_body))
        })
        print(res)
        if res.status_code == 201:
            return True
        return False

    def create_playlist(self, name, desc):
        name = name or 'New Playlist'
        desc = desc or 'Playlist Created by the CLI'
        self._auth()
        req_data = {
            'name': name,
            'description': desc,
        }
        response = self.__session.post(f'{self.API_URL}/v1/users/{self.current_user_id}/playlists',data=json.dumps(req_data), headers={
            'Authorization': f'Bearer {self.__auth_token}',
            'Content-Type': 'application/json',
            'Content-Length': str(sys.getsizeof(req_data))
        })
        return response.json()

    @staticmethod
    def _generate_random_string(length):
        possible = string.ascii_letters + string.digits
        return ''.join(random.choice(possible) for _ in range(length))


    def enter_playlist_id(self, id: str):
        self._auth()
        search_response = self.__session.get(f'{self.API_URL}/v1/playlists/{id}', headers={
            'Authorization': f'Bearer {self.__auth_token}'
        })
        artists = (track['track']['artists'] for track in search_response.json()['tracks']['items'])
        artists_names = [artist[0]['name'] for artist in artists]
        tracks_names = [track['track']['name'] for track in search_response.json()['tracks']['items']]
        tracks_id = [track['track']['id'] for track in search_response.json()['tracks']['items']]
        self.__tracks = ((name, artist, id) for name, artist, id in zip(tracks_names, artists_names, tracks_id))

    def search(self, name: str, item_type: str, limit: int=5):
        self._auth()
        search_response = self.__session.get(f'{self.API_URL}/v1/search?q={name}&type={item_type}&limit={limit}',
                                             headers={
            'Authorization': f'Bearer {self.__auth_token}'
                                             })
        artists = (track['artists'] for track in search_response.json()['tracks']['items'])
        artists_names = [artist[0]['name'] for artist in artists]
        tracks_names = [track['name'] for track in search_response.json()['tracks']['items']]
        tracks_uri = [track['uri'] for track in search_response.json()['tracks']['items']]
        return ((name, artist, uri) for name, artist, uri in zip(tracks_names, artists_names, tracks_uri))

    @dispatch(str, str, str)
    def search_track(self, name: str, artist: str, album: str):
        self._auth()
        search_response = self.__session.get(f'{self.API_URL}/v1/search?q={name}+artist:{artist}+album:{album}&type=track',
                                       headers={
                                           'Authorization': f'Bearer {self.__auth_token}'
                                       })
        try:
            return search_response.json()['tracks']['items'][0]['external_urls']['spotify']
        except KeyError as err:
            print(str(err))
            return "No track have been found, please check your parameters. If the issue still persists maybe you're searching for the wrong thing"

    @dispatch(str, str)
    def search_track(self, name: str, artist: str):
        self._auth()
        search_response = self.__session.get(f'{self.API_URL}/v1/search?q={name}+artist:{artist}&type=track', headers={
            'Authorization': f'Bearer {self.__auth_token}'
        })
        try:
            return search_response.json()['tracks']['items'][0]['external_urls']['spotify']
        except KeyError as err:
            print(str(err))
            return "No track have been found, please check your parameters. If the issue still persists maybe you're searching for the wrong thing"

    @dispatch(str)
    def search_track(self, name: str):
        self._auth()
        search_response = self.__session.get(f'{self.API_URL}/v1/search?q={name}&type=track', headers={
            'Authorization': f'Bearer {self.__auth_token}'
        })
        try:
            return search_response.json()['tracks']['items'][0]['external_urls']['spotify']
        except KeyError as err:
            print(str(err))
            return "No track have been found, please check your parameters. If the issue still persists maybe you're searching for the wrong thing"

def start_local_http_server(port, handler=RequestHandler):
    server = HTTPServer(("127.0.0.1", port), handler)
    server.allow_reuse_address = True
    server.auth_code = None
    server.auth_token_form = None
    server.error = None
    return server