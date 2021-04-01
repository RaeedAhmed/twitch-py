A simple webapp for managing Twitch user follows and browsing live streams/videos-on-demand to launch via streamlink.

```bash
git clone https://github.com/RaeedAhmed/twitch-py.git
python3 -m venv .venv
source .venv/bin/activate
pip install .
nox -s app
```
Go to `localhost:8080` and follow login prompt if not signed in.
