import asyncio
import shutil
from datetime import datetime, timedelta, timezone
from shlex import split as lex
from subprocess import DEVNULL, Popen

import bottle as bt
import httpx
import peewee as pw
import toml

confdir = shutil.os.path.expanduser("~") + "/.config/twitch-py"
bt.TEMPLATE_PATH.insert(0, f"{confdir}/views")
db = pw.SqliteDatabase(f"{confdir}/data.db")
os_ = shutil.sys.platform.lower()


class App:
    process: Popen = None
    url = "http://localhost:8080/"
    messages = []
    error = None

    @classmethod
    def redirect_err(cls, error: str) -> bt.redirect:
        setattr(cls, "error", error)
        return bt.redirect("/error")

    @staticmethod
    def display(message: str = "") -> None:
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
                                   |_|    |___/ v1.2
            """.splitlines()
        )
        divide = ("─" * round(t.columns / 1.5)).center(t.columns) + "\n"
        print(logo, App.url.center(t.columns), sep="\n", end=divide)
        (m := App.messages).append(message)
        print(*[f" > {msg}" for msg in m[-min(len(m), (t.lines - 12)) :]], sep="\n")


@bt.hook("before_request")
def _connect_db() -> None:
    db.connect()
    if not any(
        path in bt.request.path
        for path in ["authenticate", "config", "settings", "error"]
    ):
        Db.check_user()


@bt.hook("after_request")
def _close_db() -> None:
    if not db.is_closed():
        db.close()


class BaseModel(pw.Model):
    class Meta:
        database = db


class User(BaseModel):
    id = pw.IntegerField()
    login = pw.TextField()
    display_name = pw.TextField()
    profile_image_url = pw.TextField()
    access_token = pw.TextField()


class Streamer(BaseModel):
    id = pw.IntegerField(primary_key=True)
    login = pw.TextField()
    display_name = pw.TextField()
    broadcaster_type = pw.TextField(default="user")
    description = pw.TextField(default="Twitch streamer")
    profile_image_url = pw.TextField()
    offline_image_url = pw.TextField(default="config/offline.jpg")
    followed = pw.BooleanField(default=False)


class Game(BaseModel):
    id = pw.IntegerField(primary_key=True)
    name = pw.TextField()
    box_art_url = pw.TextField()


class Helix:
    client_id = "o232r2a1vuu2yfki7j3208tvnx8uzq"
    redirect_uri = "http://localhost:8080/authenticate"
    app_scopes = "user:edit+user:edit:follows"
    endpoint = "https://api.twitch.tv/helix"
    oauth = (
        "https://id.twitch.tv/oauth2/authorize?client_id="
        f"{client_id}&redirect_uri={redirect_uri}"
        f"&response_type=token&scope={app_scopes}"
    )

    @staticmethod
    def headers() -> dict:
        return {
            "Client-ID": Helix.client_id,
            "Authorization": f"Bearer {User.get().access_token}",
        }

    @staticmethod
    def get(params: str) -> list[dict]:
        try:
            with httpx.Client(headers=Helix.headers()) as session:
                resp: list[dict] = session.get(f"{Helix.endpoint}/{params}").json()[
                    "data"
                ]
            return resp
        except httpx.HTTPError as e:
            App.display(f"Error in handling request with params {params}. Error: {e}")

    @staticmethod
    def get_iter(params: str) -> list[dict]:
        results, data = [], []
        with httpx.Client(headers=Helix.headers()) as session:
            while True:
                resp = session.get(f"{Helix.endpoint}/{params}").json()
                try:
                    data: list[dict] = resp["data"]
                except httpx.HTTPError as e:
                    App.display(f"Error with {resp}. Caused the error {e}")
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
        headers = {
            "Client-ID": Helix.client_id,
            "Authorization": f"Bearer {access_token}",
        }
        try:
            user: dict = httpx.get(f"{Helix.endpoint}/users", headers=headers).json()[
                "data"
            ][0]
        except httpx.HTTPError as e:
            App.display(f"Error occurred: {e}")
            shutil.sys.exit()
        user["access_token"] = access_token
        user["id"] = int(user["id"])
        return User.create(**user)

    @staticmethod
    def follows(id: int) -> set[int]:
        resp = Helix.get_iter(f"users/follows?from_id={id}&first=100")
        return {int(follow["to_id"]) for follow in resp}

    @staticmethod
    async def live(ids: set[int]) -> list[dict]:
        tmp = list(ids)
        id_lists = [
            tmp[x : x + 100] for x in range(0, len(tmp), 100)
        ]  # chunks of 100 ids
        async with httpx.AsyncClient(headers=Helix.headers()) as session:
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
        if db.table_exists("user") is False or User.get_or_none() is None:
            App.display("No user found. Please log in.")
            return bt.redirect(Helix.oauth)

    @staticmethod
    async def cache(ids: set[int], mode: str) -> None:
        """mode: 'users' or 'games'"""
        model = Streamer if mode == "users" else Game
        tmp = [i for i in ids if model.get_or_none(i) is None]
        if not tmp:
            return None
        id_lists = [tmp[x : x + 100] for x in range(0, len(tmp), 100)]
        async with httpx.AsyncClient(headers=Helix.headers()) as session:
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
            datum["id"] = int(datum["id"])
            if mode == "games":
                datum["box_art_url"] = datum["box_art_url"].replace(
                    "-{width}x{height}", "-285x380"
                )
            else:
                for key in Db.key_defaults:
                    if not datum[key]:
                        datum.pop(key)
            model.create(**datum)

    @staticmethod
    def update_follows() -> set[int]:
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

        async with httpx.AsyncClient(headers=Helix.headers()) as session:
            tasks = []
            for streamer in streamers:
                data = {"to_id": str(streamer.id), "from_id": str(User.get().id)}
                tasks.append(send(session, data, streamer))
            await asyncio.gather(*tasks)


@bt.route("/")
def index():
    follows = Db.update_follows()
    streams = Fetch.stream_info(asyncio.run(Fetch.live(follows)))
    return bt.template("index.tpl", User=User.get(), streams=streams)


@bt.route("/authenticate")
def authenticate():
    if access_token := bt.request.query.get("access_token"):
        db.create_tables([User, Streamer, Game])
        user = Fetch.user(access_token)
        App.display(f"Logged in as {user.display_name}")
        follows = Fetch.follows(user.get().id)
        asyncio.run(Db.cache(follows, "users"))
        Streamer.update(followed=True).execute()
        return bt.redirect("/")
    return bt.template("authenticate.tpl")


@bt.route("/<channel>")
def channel(channel, mode=None, data=None):
    try:
        channel: Streamer = Streamer.get(
            (Streamer.display_name == channel) | (Streamer.login == channel)
        )
    except pw.DoesNotExist:
        App.redirect_err("Page not found")
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
    query = bt.request.query.q
    t = bt.request.query.t
    mode, model, count = (
        ("games", Game, 10) if t == "categories" else ("users", Streamer, 5)
    )
    ids = {
        int(result["id"])
        for result in Helix.get(f"search/{t}?query={query}&first={count}")
    }
    asyncio.run(Db.cache(ids, mode=mode))
    results = model.select().where(model.id.in_(ids))
    return bt.template("search.tpl", query=query, mode=mode, results=results)


@bt.route("/following")
def following():
    Db.update_follows()
    follows = (
        Streamer.select()
        .where(Streamer.followed == True)
        .order_by(Streamer.display_name)
    )
    return bt.template("following.tpl", follows=follows)


@bt.route("/categories/<game_id>")
def browse(game_id="all"):
    if game_id == "all":
        return bt.redirect("/top/games")
    else:
        try:
            game: Game = Game.get(int(game_id))
            streams = Helix.get(f"streams?first=50&game_id={game_id}")
            data = Fetch.stream_info(streams)
            return bt.template("top.tpl", data=data, t="channels_filter", game=game)
        except httpx.HTTPError:
            App.redirect_err("Page not found")


@bt.route("/top/<t>")
def top(t):
    if t == "channels":
        top_streams = Helix.get("streams?first=50")
        data = Fetch.stream_info(top_streams)
    elif t == "games":
        games = [int(g["id"]) for g in Helix.get("games/top?first=100")]
        asyncio.run(Db.cache(set(games), mode="games"))
        data = list(Game.select().where(Game.id.in_(games)))
        data.sort(key=lambda x: games.index(x.id))
    else:
        App.redirect_err("Page not found")
    return bt.template("top.tpl", data=data, t=t)


@bt.route("/settings")
def settings():
    command = lex(f"open {confdir}/config/settings.toml")
    if bt.request.query.get("open"):
        Popen(command)
        return bt.redirect("/settings")
    try:
        config = toml.load(f"{confdir}/config/settings.toml")[f"{os_}"]
    except toml.TomlDecodeError as e:
        Popen(command)
        App.redirect_err(f"Could not parse settings file: {e}")
    return bt.template("settings.tpl", config=config)


@bt.route("/config/<filename:path>")
def send_static(filename):
    return bt.static_file(filename, root=f"{confdir}/config/")


@bt.route("/error")
def error_page():
    return bt.template("error_page.tpl", error=App.error)


def time_elapsed(start: str, d="") -> str:
    start = datetime.strptime(start, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    current = datetime.now(tz=timezone.utc)
    elapsed = round((current - start).total_seconds())
    delta = str(timedelta(seconds=elapsed))
    if "d" in delta:
        d = delta[: (delta.find("d") - 1)] + "d"
    h, m, s = delta.split(" ")[-1].split(":")
    return f"{d}{h}h{m}m"


def watch_video(channel: str = "", mode: str = "live", url: str = "") -> None:
    c = toml.load(f"{confdir}/config/settings.toml")[f"{os_}"]
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
    to_fetch = [vod_id for clip in clips if (vod_id := clip["video_id"])]
    async with httpx.AsyncClient(headers=Helix.headers()) as session:
        vod_data = await asyncio.gather(
            *(
                session.get(f"{Helix.endpoint}/videos?id={vod_id}")
                for vod_id in to_fetch
            )
        )
    vods = [resp.json()["data"][0] for resp in vod_data]
    for clip in clips:
        if clip["video_id"]:
            clip["vod"] = vods.pop(0)
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
    commands = []
    commands.append(
        lex(
            "curl -sL -o twitch-install.sh https://raw.githubusercontent.com/RaeedAhmed/twitch-py/master/install.sh"
        )
    )
    commands.append(lex("chmod +x twitch-install.sh"))
    commands.append(lex(f"./twitch-install.sh -{arg}"))
    commands.append(lex("rm twitch-install.sh"))
    for command in commands:
        Popen(command).wait()


if __name__ == "__main__":
    docs = """Usage: twitch-py [COMMAND]
    -h, --help      Display help for commands
    --update        Install twitch-py from latest git repo
    --uninstall     Remove all associated files from system
    """
    arg = shutil.sys.argv[1:]
    if not arg:
        App.display("Launching server...")
        try:
            bt.run(server="waitress", host="localhost", port=8080, quiet=True)
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
    elif arg[0] in ["--update", "update"]:
        install("i")
    elif arg[0] in ["--uninstall", "uninstall"]:
        install("u")
    else:
        print("Command not recognized. Use -h for help")
        print(docs)
    shutil.sys.exit()
