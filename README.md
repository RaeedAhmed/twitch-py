# twitch-py
## Installation
Ensure that the latest python version as well as `pip` are installed on your device.
```bash
git clone https://github.com/RaeedAhmed/twitch-py.git
cd twitch-py
```
### Download executable
Quick installation:
Ensure either `wget` or `curl` is installed on your machine

In `twitch-py/`:
```bash
./install
```
After restarting the shell, run the program:
```bash
twitch-py
```

### Local installation
If you would like to modify the script as well as have the convenience of an executable:
Ensure the you are able to access python's `venv` module. You may need to install it:
```bash
sudo apt install python3-venv # for Debian systems
```
Installation via `venv` and `pyinstaller` is dont with the `-c` flag:
```bash
./install -c # compile your own binary
twitch-py # in a new shell
```

### Python Interpreter
If you prefer modifying the code yourself before running, you can run the script directly:
**Create a virtual environment**

This can be done in a number of ways, but using python built-in `venv` module:
```bash
python3 -m venv .venv
source .venv/bin/activate
```
Installing dependencies and running:
```bash
pip install .
./install -p # -p to setup config files only
python twitch_py/main.py
```

### Uninstall
Remove executable and config files from system with the `-u` flag:
```bash
./install -u
```
## Usage
Go to `localhost:8080` and follow login prompt if not signed in.

### /
List of live streams of users you have followed
- Thumbnails launch videos
- Profile pictures redirect to `channel pages`
- Boxarts redirect to a list of top streams in that `category`

### /Following
List of all users followed
- Filter channel by name text

### /Streams
View top streams on the entirety of Twitch

### /Games
View top 100 categories on Twitch based on total viewcount
- Click on a boxart to redirect to top streams within that category

### /ChannelName
- View channel type and description
- Open channel's live chat in new window
- (Un)follow the channel (updated immediately)
- View all past broadcasts aka "vods"
- Choose a date range to filter top viewed clips in that range

### Search
Click on 'Channel' (selected by default) or 'Category' to obtain relevant results

### /Settings
Either directly navigate to `~/.config/twitch-py/config/settings.toml` or click on the 'settings' page in the webapp and open the file from there

`multi` refers to allowing multiple instances of videos to play at the same time. The default setting is `False`

`app` can be any video player that `streamlink` [can interface with](https://streamlink.github.io/players.html)

`args` are the video player arguments you would normally pass through on the command line. Note that the arguments must be contained in double quote as [instructed here:](https://streamlink.github.io/cli.html#player-options)
```
streamlink -p mpv -a "--hwdec=auto --screen=1 --fs --keep-open=yes"
```
where mpv is the video player, and it's params are enclosed in double quotes

For example, you can change the screen the player uses by changing the `--screen` parameter

The best default settings for `streamlink` are passed by default, though if there is something you need to change you can edit the appropriate lines in the script located in the `watch_video` function