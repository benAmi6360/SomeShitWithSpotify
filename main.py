from dotenv import dotenv_values
from spotify import SpotifyClient

CONFIG = dotenv_values('.env')

scope = ['playlist-read-private', 
         'playlist-read-collaborative', 
         'playlist-modify-private', 
         'playlist-modify-public', 
         'user-top-read',
         'user-read-private',
         'user-read-email']
sp = SpotifyClient(CONFIG['SPOTIFY_ID'], CONFIG['SPOTIFY_SECRET'], 'http://localhost:8000/callback', scope)
sp.get_currect_user_id()
while True:
    name = input("Enter a name for the playlist: ")
    desc = input("Describe the playlist: ")
    playlist = sp.create_playlist(name, desc)
    print("The id of your playlist,", playlist['id'])
    print("The playlist is at,", f'{playlist["external_urls"]["spotify"]}')

    ans = input("Do you want to add tracks to the playlist? (y/n): ")
    if ans.lower() != 'y':
        continue
    while True:
        do_quit = input("Enter 'q' to quit: ")
        if do_quit.lower() == 'q':
            break
        uri = input("Enter a track uri (to search for a track and get his uri type 's'): ")
        if uri.lower() == 's':
            name = input("Enter the name of the item: ")
            item_type = input("Enter the type of the item (leave blank for 'track'): ") or 'track'
            res = list(sp.search(name, item_type))
            for inx, val in enumerate(res):
                print(f"Index: {inx} {val}")
            index = int(input("Enter the index of the wanted track: "))
            uri = res[index][2]
        if sp.add_items_to_playlist(playlist['id'], [uri]):
            print("Item added successfully!")
        else: print("Item was not added, please try again :(")