class Playlist:
    def __init__(self, response):
        self.__URI = response['uri']
        self.__ID = response['id']
        self.name = response['name']