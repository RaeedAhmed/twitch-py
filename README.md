# twitch-py

## Repo is unmaintained. Further developments will occur in [twottle](https://github.com/RaeedAhmed/twottle)


## Installation

### Requirements

- `streamlink` - [installation guide](https://streamlink.github.io/install.html)
- `Python >= 3.9` for building
- Media player of choice

Be sure to change the player and its arguments located in `~/.config/twitch-py/config/settings.toml` after program installation

### One-line install

You will need, among the above requirements:

- `curl`
- `unzip`

Use the one line install below after installing dependencies:

```bash
curl -sL https://raw.githubusercontent.com/RaeedAhmed/twitch-py/master/install.sh | bash -s -- -d
```

Run `twitch-py` to start the application

### Build application locally

Follow your distribution's instructions for installing `python3-venv` on your system
Run `./install -l` for a local installation

### Update/Uninstall

Run `twitch-py -h` to list any arguments to pass through. You can update or uninstall using the relevant flags.
Alternatively you can pass the `u` argument: `./install -u` to uninstall with the install script

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

```bash
streamlink -p mpv -a "--hwdec=auto --screen=1 --fs --keep-open=yes"
```

where mpv is the video player, and it's params are enclosed in double quotes

For example, you can change the screen the player uses by changing the `--screen` parameter

The best default settings for `streamlink` are passed by default, though if there is something you need to change you can edit the appropriate lines in the script located in the `watch_video` function
