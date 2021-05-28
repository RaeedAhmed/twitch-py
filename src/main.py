import asyncio
import shutil
from collections import namedtuple
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from shlex import split as lex
from subprocess import DEVNULL, Popen

import bottle as bt
import httpx
import peewee as pw
import toml
from waitress import serve

confdir = shutil.os.path.expanduser("~") + "/.config/twitch-py"
bt.TEMPLATE_PATH.insert(0, f"{confdir}/views")
cachedir = shutil.os.path.expanduser("~") + "/.cache/twitch-py"
db = pw.SqliteDatabase(f"{confdir}/data.db")
os_ = shutil.sys.platform.lower()
Image = namedtuple("Image", "id url")
Result = namedtuple("Result", "query model")


class App:
    process: Popen = None  # Holds process id of current stream/vod
    url = "http://localhost:8080/"  # Index page of local site
    messages = []  # Log of events since application start
    errors = {
        400: "Bad Request",
        404: "Not Found",
        500: "Server Error",
        502: "Bad Gateway",
    }

    @staticmethod
    def display(message: str = "") -> None:
        """
        Reprints terminal screen with most recent event messages

        Re-centers logo and change list length based on terminal size
        """
        shutil.os.system("clear")
        t = shutil.get_terminal_size()
        logo = "\n".join(
            line.center(t.columns)
            for line in """
 _            _ _       _                           
| |___      _(_) |_ ___| |__        _ __  _   _     
| __\ \ /\ / / | __/ __| '_ \ _____| '_ \| | | |    
| |_ \ V  V /| | || (__| | | |_____| |_) | |_| |    
 \__| \_/\_/ |_|\__\___|_| |_|     | .__/ \__, |    
                                   |_|    |___/ v1.5
            """.splitlines()
        )
        divide = ("─" * round(t.columns / 1.5)).center(t.columns) + "\n"
        print(logo, App.url.center(t.columns), sep="\n", end=divide)
        (m := App.messages).append(message)
        print(*[f" > {msg}" for msg in m[-min(len(m), (t.lines - 12)) :]], sep="\n")


@bt.hook("before_request")
def _connect_db() -> None:
    """
    The following is run at the start of each page request (user action on webpage)
    """
    db.connect()
    if not any(
        path in bt.request.path
        for path in ["authenticate", "config", "settings", "error"]
    ):
        Db.check_user()  # Redirect to login if no user in data.db
        Db.check_cache()  # If no cache but user login, run initial cache from follows


@bt.hook("after_request")
def _close_db() -> None:
    """
    The following is run after server fulfills page request
    """
    if not db.is_closed():
        db.close()  # Terminate connection with data.db


class BaseModel(pw.Model):
    """
    Base class for database models, where data.db is the shared database
    """

    class Meta:
        database = db


class User(BaseModel):
    """
    Model/table for the user login. Necessary to store access token for
    Twitch Helix API requests
    """

    id = pw.IntegerField()
    login = pw.TextField()
    display_name = pw.TextField()
    profile_image_url = pw.TextField()
    access_token = pw.TextField()


class Streamer(BaseModel):
    """
    Model/table for all Twitch streamers. Holds data for displaying content
    on webpages, and boolean for whether streamer is followed by the user.
    """

    id = pw.IntegerField(primary_key=True)
    login = pw.TextField()
    display_name = pw.TextField()
    broadcaster_type = pw.TextField(default="user")  # If not partner/affiliate
    description = pw.TextField(default="Twitch streamer")  # Default if no description
    profile_image_url = pw.TextField()
    followed = pw.BooleanField(default=False)


class Game(BaseModel):
    """
    Holds data for presenting game names and box art. The box art stored
    is a specified size that exists for all games (some sizes are incompatible)
    """

    id = pw.IntegerField(primary_key=True)
    name = pw.TextField()
    box_art_url = pw.TextField()


class Helix:
    """
    Application information to interface with the Helix API
    """

    client_id = "o232r2a1vuu2yfki7j3208tvnx8uzq"
    redirect_uri = "http://localhost:8080/authenticate"
    app_scopes = "user:edit+user:edit:follows+user:read:follows"
    endpoint = "https://api.twitch.tv/helix"
    oauth = (
        "https://id.twitch.tv/oauth2/authorize?client_id="
        f"{client_id}&redirect_uri={redirect_uri}"
        f"&response_type=token&scope={app_scopes}"
    )

    @staticmethod
    def headers() -> dict:
        """
        Prepares headers with app id and stored user-access-token from authentication
        """
        return {
            "Client-ID": Helix.client_id,
            "Authorization": f"Bearer {User.get().access_token}",
        }

    @staticmethod
    def get(params: str) -> list[dict]:
        """
        Blueprint for http requests specifically for Helix API
        Includes necessary client-id and user access token
        Input `params` is used to specify API endpoint as so:

        https://api.twitch.tv/helix/<params>

        The response is of json format
        ```
        {
            "data": [{},{}],
            "pagination":...
        }
        ```
        and the `data` key is selected, which is of type `list[dict]`
        """
        try:
            with httpx.Client(headers=Helix.headers(), timeout=None) as session:
                resp: list[dict] = session.get(f"{Helix.endpoint}/{params}").json()[
                    "data"
                ]
            return resp
        except httpx.HTTPError as e:
            App.display(f"Error in handling request with params {params}. Error: {e}")
            bt.abort(code=502, text=f"Error in handling request with params {params}")

    @staticmethod
    def get_iter(params: str) -> list[dict]:
        """
        Blueprint for http requests specifically for Helix API
        Includes necessary client-id and user access token
        Input `params` is used to specify API endpoint as so:

        https://api.twitch.tv/helix/<params>

        The response is of json format
        ```
        {
            "data": [{},{}],
            "pagination":
            {"cursor" : [0-9a-zA-Z]+}
        }
        ```

        The response's `data` field (of type `list[dict]`) is appended to `results`

        The `pagination` cursor, if it exists, is used as a request parameter for a
        subsequent request at the same endpoint to show the next series of results

        Iterates requests with new index of results until no more data is found
        """
        results, data = [], []
        with httpx.Client(headers=Helix.headers(), timeout=None) as session:
            while True:
                resp = session.get(f"{Helix.endpoint}/{params}").json()
                try:
                    data: list[dict] = resp["data"]
                except httpx.HTTPError as e:
                    App.display(f"Error with {resp}. Caused the error {e}")
                    bt.abort(
                        code=502, text=f"Error with request {Helix.endpoint}/{params}"
                    )
                if data == []:
                    break
                results += data
                if resp["pagination"] == {}:
                    return results
                pagination = resp["pagination"]["cursor"]
                if "after" in params:
                    params = params[: (params.rfind("=") + 1)] + pagination
                else:
                    params = params + f"&after={pagination}"
        return results


class Fetch:
    @staticmethod
    def user(access_token: str) -> User:
        """
        Once user logs in via the twitch portal, the access token taken from
        the /authentication uri is used to fetch user data and populate the 'user'
        table in `data.db`.

        https://api.twitch.tv/helix/users

        headers contain unique user access token (required)
        """
        headers = {
            "Client-ID": Helix.client_id,
            "Authorization": f"Bearer {access_token}",
        }
        try:
            user: dict = httpx.get(
                f"{Helix.endpoint}/users", headers=headers, timeout=None
            ).json()["data"][0]
        except Exception as e:
            App.display(f"Error occurred: {e}")
            bt.abort(code=500, text="Error in fetching user data")
            shutil.sys.exit()
        user["access_token"] = access_token
        user["id"] = int(user["id"])
        return User.create(**user)

    @staticmethod
    def follows(id: int) -> set[int]:
        """
        Fetches id numbers of user's followed channels.
        https://api.twitch.tv/helix/users/follows?from_id=<user_id>
        """
        resp = Helix.get_iter(f"users/follows?from_id={id}&first=100")
        return {int(follow["to_id"]) for follow in resp}

    @staticmethod
    async def live(ids: set[int]) -> list[dict]:
        """
        Input: set of user ids.
        Splits ids in chunks of 100 (limit of API endpoint) and fetches stream data.
        If channel is not live, data is empty, thus only live stream info is returned.
        https://api.twitch.tv/helix/streams?user_id=<id1>&...&user_id=<id100>
        """
        tmp = list(ids)
        id_lists = [tmp[x : x + 100] for x in range(0, len(tmp), 100)]
        async with httpx.AsyncClient(headers=Helix.headers(), timeout=None) as session:
            stream_list: list[httpx.Response] = await asyncio.gather(
                *(
                    session.get(
                        f"{Helix.endpoint}/streams?{'&'.join([f'user_id={i}' for i in i_list])}"
                    )
                    for i_list in id_lists
                )
            )
        streams = []
        for resp in stream_list:
            data: list[dict] = resp.json()["data"]
            if data:
                streams += data
        return streams

    @staticmethod
    def stream_info(streams: list[dict]) -> list[dict]:
        """
        From stream data, cache games and users from their ids.
        Caching fetches additional data which is then appended to stream data dict
        """

        async def cache():
            tasks = []
            for args in [("game_id", "games"), ("user_id", "users")]:
                ids = {int(i) for stream in streams if (i := stream[args[0]])}
                tasks.append(Db.cache(ids, mode=args[1]))
            await asyncio.gather(*tasks)

        asyncio.run(cache())
        for stream in streams:
            channel: Streamer = Streamer.get(int(stream["user_id"]))
            try:
                game = Game.get(int(stream["game_id"]))
                stream["box_art_url"] = game.box_art_url
            except ValueError:
                stream[
                    "box_art_url"
                ] = "https://static-cdn.jtvnw.net/ttv-static/404_boxart.jpg"
            stream["profile_image_url"] = channel.profile_image_url
            stream["uptime"] = time_elapsed(stream["started_at"])
            stream["thumbnail_url"] = stream["thumbnail_url"].replace(
                "-{width}x{height}", ""
            )
        streams.sort(key=lambda stream: stream["viewer_count"], reverse=True)
        return streams


class Db:
    key_defaults = ["broadcaster_type", "description", "offline_image_url"]

    @staticmethod
    def check_user() -> bt.redirect:
        """
        Check if User is logged in (table exists in data.db).
        Redirect to authentication page if no user
        """
        if db.table_exists("user") is False or User.get_or_none() is None:
            App.display("No user found. Please log in.")
            return bt.redirect(Helix.oauth)

    @staticmethod
    def check_cache():
        """Initial creation of database tables and caching if tables do not exist"""
        if (Streamer.table_exists() and Game.table_exists()) is False:
            db.create_tables([Streamer, Game])
            App.display("Building cache")
            follows = Fetch.follows(User.get().id)
            asyncio.run(Db.cache(follows, "users"))
            Streamer.update(followed=True).execute()

    @staticmethod
    async def cache(ids: set[int], mode: str) -> None:
        """
        Caching mode: 'users' or 'games'.
        If game/streamer id does not exist in database, send to caching.
        https://api.twitch.tv/helix/<'games' or 'users'>?id=<id1>&id=<id2>...
        """

        model = Streamer if mode == "users" else Game
        tag = "box_art_url" if mode == "games" else "profile_image_url"

        tmp = [i for i in ids if model.get_or_none(i) is None]
        if not tmp:
            return None
        id_lists = [tmp[x : x + 100] for x in range(0, len(tmp), 100)]

        async with httpx.AsyncClient(headers=Helix.headers(), timeout=None) as session:
            resps: list[httpx.Response] = await asyncio.gather(
                *(
                    session.get(
                        f"{Helix.endpoint}/{mode}?{'&'.join([f'id={i}' for i in i_list])}"
                    )
                    for i_list in id_lists
                )
            )

        data = []
        for resp in resps:
            datum: list[dict] = resp.json()["data"]
            if datum:
                data += datum
        for datum in data:
            if mode == "games":
                datum["box_art_url"] = datum["box_art_url"].replace(
                    "-{width}x{height}", "-285x380"
                )
            else:
                for key in Db.key_defaults:
                    if not datum[key]:  # Remove to replace with key's default
                        datum.pop(key)

        # `tag` key different for game datum and user datum
        images = [Image(datum["id"], datum[tag]) for datum in data]

        def download_image(image: Image) -> None:
            """Get image data from url, write to file with `mode` directory
            and datum `id` as the filename"""
            data = httpx.get(image.url).content
            with open(f"{cachedir}/{mode}/{image.id}.jpg", "wb") as f:
                f.write(data)

        with ThreadPoolExecutor() as tp:
            tp.map(download_image, images)

        for datum in data:
            datum[tag] = f"/cache/{mode}/{datum['id']}.jpg"  # Point to file path
            datum["id"] = int(datum["id"])
            model.create(**datum)  # Discards unused keys

    @staticmethod
    def update_follows() -> set[int]:
        """
        Fetch user's current follows and cache

        Toggle channel follow if follow in database and current do not match
        """
        follows = Fetch.follows(User.get().id)
        asyncio.run(Db.cache(follows, "users"))
        streamers: list[Streamer] = [streamer for streamer in Streamer.select()]
        to_toggle = set()
        for streamer in streamers:
            sid = streamer.id
            if (sid in follows and streamer.followed is not True) or (
                sid not in follows and streamer.followed is True
            ):
                to_toggle.add(streamer)
        if to_toggle:
            asyncio.run(Db.toggle_follow(to_toggle))
        return follows

    @staticmethod
    async def toggle_follow(streamers: set[Streamer]) -> None:
        """Send http POST or DELETE based on value of follow after toggling"""
        url = f"{Helix.endpoint}/users/follows"

        async def send(session: httpx.AsyncClient, data: dict, streamer: Streamer):
            Streamer.update(followed=not streamer.followed).where(
                Streamer.id == streamer.id
            ).execute()
            if streamer.followed is True:
                App.display(f"Unfollowing {streamer.display_name}")
                await session.delete(url, params=data)
            else:
                App.display(f"Following {streamer.display_name}")
                await session.post(url, params=data)

        async with httpx.AsyncClient(headers=Helix.headers(), timeout=None) as session:
            tasks = []
            for streamer in streamers:
                data = {"to_id": str(streamer.id), "from_id": str(User.get().id)}
                tasks.append(send(session, data, streamer))
            await asyncio.gather(*tasks)


@bt.route("/")
def index():
    """Index of web application. Displays live streams of user's follows"""
    follows = Db.update_follows()
    streams = Fetch.stream_info(asyncio.run(Fetch.live(follows)))
    return bt.template("index.tpl", User=User.get(), streams=streams)


@bt.route("/authenticate")
def authenticate():
    """
    User is prompted with login portal. After login, uri redirect includes
    access token. Javascript in `authenticate.tpl` grabs this token which is
    used to fetch user information which is then cached along with token.
    """
    if access_token := bt.request.query.get("access_token"):
        User.create_table()
        user = Fetch.user(access_token)
        App.display(f"Logged in as {user.display_name}")
        return bt.redirect("/")
    return bt.template("authenticate.tpl")


@bt.route("/<channel>")
def channel(channel, mode=None, data=None):
    """Profile page of channel"""
    try:
        channel: Streamer = Streamer.get(
            (Streamer.display_name == channel) | (Streamer.login == channel)
        )
    except pw.DoesNotExist:
        bt.abort(code=404, text="User does not exist")
    date = {"start": "", "end": ""}
    if bt.request.query.get("follow"):
        asyncio.run(Db.toggle_follow({channel}))
        bt.redirect(f"/{channel.login}")
    elif bt.request.query.get("watch"):
        watch_video(channel.login)
        return """<script>setTimeout(function () { window.history.back() });</script>"""
    elif bt.request.query.get("vod"):
        mode = "vod"
        vods = Helix.get_iter(f"videos?user_id={channel.id}&type=archive")
        data = process_data(vods, mode)
    elif bt.request.query.get("clips"):
        mode = "clip"
        start = bt.request.query.get("start") + "T00:00:00Z"
        end = bt.request.query.get("end") + "T00:00:00Z"
        clips = Helix.get(
            f"clips?broadcaster_id={channel.id}&first=100&started_at={start}&ended_at={end}"
        )
        data = process_data(clips, mode="clip")
        data = sorted(data, key=lambda info: info["view_count"], reverse=True)
        date = {"start": start[:-10], "end": end[:-10]}
    elif url := bt.request.query.get("video"):
        watch_video(mode="vod", url=url)
        return """<script>setTimeout(function () { window.history.back() });</script>"""
    elif bt.request.query.get("close"):
        bt.redirect(f"/{channel.login}")
    return bt.template("channel.tpl", channel=channel, mode=mode, data=data, date=date)


@bt.route("/search")
def search():
    """
    List results that match search query string and cache results based on id
    For categories, display data from database based on id
    For channels, display data from database as well as request data from endpoint
    """
    query = bt.request.query.q
    t = bt.request.query.t
    mode, model, count = (
        ("games", Game, 10) if t == "categories" else ("users", Streamer, 5)
    )
    search_results = Helix.get(f"search/{t}?query={query}&first={count}")
    ids = {int(result["id"]) for result in search_results}

    asyncio.run(Db.cache(ids, mode=mode))
    if t == "categories":
        results = model.select().where(model.id.in_(ids))
    else:
        results = [
            Result(result, model.get_by_id(int(result["id"])))
            for result in search_results
        ]
    return bt.template("search.tpl", query=query, mode=mode, results=results)


@bt.route("/following")
def following():
    """Read data.db for users with `followed == True`"""
    Db.update_follows()
    follows = (
        Streamer.select()
        .where(Streamer.followed == True)
        .order_by(Streamer.display_name)
    )
    return bt.template("following.tpl", follows=follows)


@bt.route("/categories/<game_id>")
def browse(game_id="all"):
    """
    `/all` View list of games by viewer count
    `/<game_id>` View top streams under game category
    """
    if game_id == "all":
        return bt.redirect("/top/games")
    else:
        try:
            game: Game = Game.get(int(game_id))
            streams = Helix.get(f"streams?first=50&game_id={game_id}")
            data = Fetch.stream_info(streams)
            return bt.template("top.tpl", data=data, t="channels_filter", game=game)
        except httpx.HTTPError:
            bt.abort(code=404, text=f"Cannot find streams for game id {game_id}")


@bt.route("/top/<t>")
def top(t):
    """
    `/games` View list of top games by total viewer count
    `/streams` View list of top streams across platform
    """
    if t == "channels":
        top_streams = Helix.get("streams?first=50")
        data = Fetch.stream_info(top_streams)
    elif t == "games":
        games = [int(g["id"]) for g in Helix.get("games/top?first=100")]
        asyncio.run(Db.cache(set(games), mode="games"))
        data = list(Game.select().where(Game.id.in_(games)))
        data.sort(key=lambda x: games.index(x.id))
    else:
        bt.abort(code=400, text="Not a valid type for /top")
    return bt.template("top.tpl", data=data, t=t)


@bt.route("/settings")
def settings():
    """
    Settings page to view current settings, open settings file,
    clear cache, and log out.
    """
    command = lex(f"xdg-open {confdir}/static/settings.toml")
    if bt.request.query.get("open"):
        Popen(command)
        return bt.redirect("/settings")
    elif bt.request.query.get("cache"):
        App.display("Clearing cache...")
        db.drop_tables([Streamer, Game])
        shutil.os.system(f"rm -f {cachedir}/games/* {cachedir}/users/*")
        return bt.redirect("/settings")
    elif bt.request.query.get("logout"):
        App.display("Logging out...")
        db.drop_tables([User, Streamer, Game])
        return bt.redirect("/settings")
    try:
        config = toml.load(f"{confdir}/static/settings.toml")[f"{os_}"]
    except toml.TomlDecodeError as e:
        Popen(command)
        bt.abort(code=404, text="Could not parse settings.toml")
    return bt.template("settings.tpl", config=config)


@bt.route("/static/<filename:path>")
def send_static(filename):
    """Serve files located in configuration directory"""
    return bt.static_file(filename, root=f"{confdir}/static/")


@bt.route("/cache/<filename:path>")
def cache(filename):
    """Serve images cached in ~/.cache/twitch-py"""
    return bt.static_file(filename, root=f"{cachedir}/")


@bt.error(400)
def error400(error):
    return bt.template("error_page.tpl", code=App.errors[400], error=error)


@bt.error(404)
def error404(error):
    return bt.template("error_page.tpl", code=App.errors[404], error=error)


@bt.error(500)
def error500(error):
    return bt.template("error_page.tpl", code=App.errors[500], error=error)


@bt.error(502)
def error502(error):
    return bt.template("error_page.tpl", code=App.errors[502], error=error)


def time_elapsed(start: str, d="") -> str:
    """Use 'started_at' key and current time to calculated time since"""
    start = datetime.strptime(start, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    current = datetime.now(tz=timezone.utc)
    elapsed = round((current - start).total_seconds())
    delta = str(timedelta(seconds=elapsed))
    if "d" in delta:
        d = delta[: (delta.find("d") - 1)] + "d"
    h, m, s = delta.split(" ")[-1].split(":")
    return f"{d}{h}h{m}m"


def watch_video(channel: str = "", mode: str = "live", url: str = "") -> None:
    """
    Save process if of running video as App attribute for later termination.
    Passes through player and arg settings from `settings.toml`.
    """
    c = toml.load(f"{confdir}/static/settings.toml")[f"{os_}"]
    if c["multi"] is False and App.process is not None:
        App.process.terminate()
    if mode == "live":
        App.display(f"Launching stream twitch.tv/{channel}")
        command = f'streamlink -l none -p {c["app"]} -a "{c["args"]}" \
                --twitch-disable-ads --twitch-low-latency twitch.tv/{channel} best'
    else:
        App.display(f"Launching video: {url}")
        command = f'{c["app"]} {c["args"]} --really-quiet {url}'
    p = Popen(lex(command), stdout=DEVNULL)
    if c["multi"] is False:
        App.process = p


def process_data(data: list[dict], mode: str) -> list[dict]:
    """
    Format data of vod/clip for presenting. For clips, cache game data
    and fetch relevant vod with timestamp of clip.
    """
    if mode == "vod":
        for vod in data:
            vod["thumbnail_url"] = vod["thumbnail_url"].replace(
                "%{width}x%{height}", "480x270"
            )
            if not vod["thumbnail_url"]:
                vod[
                    "thumbnail_url"
                ] = "https://vod-secure.twitch.tv/_404/404_processing_320x180.png"
            vod["created_at"] = time_elapsed(vod["created_at"])
    if mode == "clip":
        for clip in data:
            clip.setdefault(
                "box_art_url", "https://static-cdn.jtvnw.net/ttv-static/404_boxart.jpg"
            )
            clip.setdefault("game_name", "Streaming")
            clip["time_since"] = time_elapsed(clip["created_at"])
            clip["thumbnail_url"] = clip["thumbnail_url"].rsplit("-", 1)[0] + ".jpg"
        asyncio.run(
            Db.cache(
                {int(gid) for clip in data if (gid := clip["game_id"])}, mode="games"
            )
        )
        for clip in data:
            try:
                game: Game = Game.get(int(clip["game_id"]))
                clip["box_art_url"] = game.box_art_url
                clip["game_name"] = game.name
            except ValueError:
                pass
        asyncio.run(vod_from_clip(data))
    return data


async def vod_from_clip(clips: list[dict]) -> list[dict]:
    """
    Fetch vod clip was taken from if it exists. Calculate timestamp of clip in
    vod using formatted date strings.
    """
    to_fetch = [vod_id for clip in clips if (vod_id := clip["video_id"])]
    async with httpx.AsyncClient(headers=Helix.headers(), timeout=None) as session:
        vod_data = await asyncio.gather(
            *(
                session.get(f"{Helix.endpoint}/videos?id={vod_id}")
                for vod_id in to_fetch
            )
        )
    vods = [resp.json()["data"][0] for resp in vod_data]
    for clip in clips:
        if clip["video_id"]:
            clip["vod"] = vods.pop(0)  # Consume vod if vod exists for clip
            vod_id, timestamp = clip["video_id"], clip["created_at"]
            vod_start = datetime.strptime(
                clip["vod"]["created_at"], "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=timezone.utc)
            timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
            elapsed = round((timestamp - vod_start).total_seconds() - 61)
            if "h" not in clip["vod"]["duration"]:
                clip["vod"]["duration"] = f"0h{clip['vod']['duration']}"
            minutes, seconds = divmod(elapsed, 60)
            hours, minutes = divmod(minutes, 60)
            clip[
                "vod_link"
            ] = f"http://www.twitch.tv/videos/{vod_id}/?t={hours}h{minutes}m{seconds}s"
        else:
            clip["vod_link"] = None
    return clips


def install(arg: str) -> None:
    """Run the latest installation script without having to clone repo if app installed"""
    commands = [
        "curl -sL -o twitch-install.sh https://raw.githubusercontent.com/RaeedAhmed/twitch-py/master/install.sh",
        "chmod +x twitch-install.sh",
        f"./twitch-install.sh -{arg}",
        "rm twitch-install.sh",
    ]
    for command in commands:
        Popen(lex(command)).wait()


if __name__ == "__main__":
    docs = """Usage: twitch-py [COMMAND]
    -h, --help          Display help for commands
    -c, --clear-cache   Clear cached data while preserving login
    -s, --settings      Open settings file to edit
    --update            Install twitch-py from latest git repo
    --uninstall         Remove all associated files from system
    """
    arg = shutil.sys.argv[1:]
    if not arg:
        App.display("Launching server...")
        try:
            serve(app=bt.app(), host="localhost", threads=16, port=8080)
        except KeyboardInterrupt:
            pass
        except httpx.HTTPError as e:
            App.display(f"Error: {e}. Retrying...")
            bt.redirect(bt.request.path)
        finally:
            App.display("Exiting...")
    elif len(arg) > 1:
        print("Too many arguments. Use -h for help")
    elif arg[0] in ["-h", "--help", "help"]:
        print(docs)
    elif arg[0] in ["-c", "--clear-cache"]:
        try:
            App.display("Clearing cache...")
            db.drop_tables([Streamer, Game])
            shutil.os.system(f"rm -f {cachedir}/games/* {cachedir}/users/*")
        except pw.OperationalError:
            App.display("Database or cache does not exist")
    elif arg[0] in ["--update", "update"]:
        install("d")
    elif arg[0] in ["--uninstall", "uninstall"]:
        install("u")
    elif arg[0] in ["-s", "--settings"]:
        cmd = lex(f"xdg-open {confdir}/static/settings.toml")
        Popen(cmd)
    else:
        print("Command not recognized. Use -h for help")
        print(docs)
    shutil.sys.exit()
