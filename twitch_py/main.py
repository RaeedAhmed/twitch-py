import asyncio
from datetime import datetime, timedelta, timezone
from platform import system
from subprocess import PIPE, Popen

import httpx
import toml
from bottle import (
    abort,
    error,
    hook,
    redirect,
    request,
    route,
    run,
    static_file,
    template,
)
from httpx import Response
from peewee import (
    BooleanField,
    DoesNotExist,
    IntegerField,
    Model,
    SqliteDatabase,
    TextField,
)

db = SqliteDatabase("data.db")


@hook("before_request")
def _connect_db():
    db.connect()


@hook("after_request")
def _close_db():
    if not db.is_closed():
        db.close()


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    id = IntegerField()
    login = TextField()
    display_name = TextField()
    profile_image_url = TextField()
    access_token = TextField()


class Streamer(BaseModel):
    id = IntegerField(primary_key=True)
    login = TextField()
    display_name = TextField()
    broadcaster_type = TextField(default="user")
    description = TextField(default="Twitch user")
    profile_image_url = TextField()
    offline_image_url = TextField(default="config/offline.jpg")
    followed = BooleanField(default=False)


class Game(BaseModel):
    id = IntegerField(primary_key=True)
    name = TextField()
    box_art_url = TextField()


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
    def headers():
        return {"Client-ID": Helix.client_id, "Authorization": f"Bearer {User.get().access_token}"}

    @staticmethod
    def get(params: str):
        with httpx.Client(headers=Helix.headers()) as session:
            resp: list[dict] = session.get(f"{Helix.endpoint}/{params}").json()["data"]
        return resp

    @staticmethod
    def get_iter(params: str) -> list[dict]:
        results, data = [], []
        with httpx.Client(headers=Helix.headers()) as session:
            while True:
                resp = session.get(f"{Helix.endpoint}/{params}").json()
                try:
                    data: list[dict] = resp["data"]
                except Exception:
                    print(f"Error with {resp}")
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
        user: dict = httpx.get(f"{Helix.endpoint}/users", headers=headers).json()["data"][0]
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
        id_lists = [tmp[x : x + 100] for x in range(0, len(tmp), 100)]  # chunks of 100 ids
        async with httpx.AsyncClient(headers=Helix.headers()) as session:
            stream_list: list[Response] = await asyncio.gather(
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
        asyncio.run(Db.cache({int(stream["game_id"]) for stream in streams}, mode="games"))
        asyncio.run(Db.cache({int(stream["user_id"]) for stream in streams}, mode="users"))
        for stream in streams:
            channel: Streamer = Streamer.get(int(stream["user_id"]))
            try:
                game = Game.get(int(stream["game_id"]))
                stream["box_art_url"] = game.box_art_url
            except ValueError:
                stream["box_art_url"] = "https://static-cdn.jtvnw.net/ttv-static/404_boxart.jpg"
            stream["profile_image_url"] = channel.profile_image_url
            stream["uptime"] = time_elapsed(stream["started_at"])
            stream["thumbnail_url"] = stream["thumbnail_url"].replace("-{width}x{height}", "")
        streams.sort(key=lambda stream: stream["viewer_count"], reverse=True)
        return streams


class Db:
    key_defaults = ["broadcaster_type", "description", "offline_image_url"]

    @staticmethod
    async def cache(ids: set[int], mode: str) -> None:
        """mode: 'users' or 'games'"""
        model = Streamer if mode == "users" else Game
        tmp = [i for i in ids if model.get_or_none(i) is None]
        if not tmp:
            return None
        id_lists = [tmp[x : x + 100] for x in range(0, len(tmp), 100)]
        print("Caching...")
        async with httpx.AsyncClient(headers=Helix.headers()) as session:
            resps: list[Response] = await asyncio.gather(
                *(
                    session.get(f"{Helix.endpoint}/{mode}?{'&'.join([f'id={i}' for i in i_list])}")
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
                datum["box_art_url"] = datum["box_art_url"].replace("-{width}x{height}", "")
            else:
                for key in Db.key_defaults:
                    if not datum[key]:
                        datum.pop(key)
            model.create(**datum)
        print("\x1b[1A\x1b[2K\x1b[1A")

    @staticmethod
    def update_follows() -> set[int]:
        past_follows = {s.id for s in Streamer.select().where(Streamer.followed == True)}
        follows = Fetch.follows(User.get().id)
        asyncio.run(Db.cache(follows, "users"))
        streamers = [streamer for streamer in Streamer.select()]
        for streamer in streamers:
            uid = streamer.id
            if uid not in (past_follows and follows) or uid in (past_follows and follows):
                pass
            else:
                Db.toggle_follow(streamer)
        return follows

    @staticmethod
    def toggle_follow(channel: Streamer) -> None:
        data = {"to_id": str(channel.id), "from_id": str(User.get().id)}
        with httpx.Client(headers=Helix.headers(), params=data) as session:
            url = f"{Helix.endpoint}/users/follows"
            if channel.followed is True:
                session.delete(url)
            else:
                session.post(url)
        Streamer.update(followed=not channel.followed).where(Streamer.id == channel.id).execute()


@route("/")
def index():
    if db.table_exists("user"):
        follows = Db.update_follows()
        streams = Fetch.stream_info(asyncio.run(Fetch.live(follows)))
        return template("index.tpl", User=User.get(), streams=streams)
    else:
        return redirect(Helix.oauth)


@route("/authenticate")
def authenticate():
    if access_token := request.query.get("access_token"):
        db.create_tables([User, Streamer, Game])
        user = Fetch.user(access_token)
        follows = Fetch.follows(user.get().id)
        asyncio.run(Db.cache(follows, "users"))
        Streamer.update(followed=True).execute()
        return redirect("/")
    return template("authenticate.tpl")


@route("/<channel>")
def channel(channel, mode=None, data=None):
    try:
        channel: Streamer = Streamer.get(
            (Streamer.display_name == channel) | (Streamer.login == channel)
        )
    except DoesNotExist:
        abort(code=404, text="Page not found")
    date = {"start": "", "end": ""}
    if request.query.get("follow"):
        Db.toggle_follow(channel)
        redirect(f"/{channel.login}")
    elif request.query.get("watch"):
        watch_video(channel.login)
        return """<script>setTimeout(function () { window.history.back() });</script>"""
    elif request.query.get("vod"):
        mode = "vod"
        vods = Helix.get_iter(f"videos?user_id={channel.id}&type=archive")
        data = process_data(vods, mode)
    elif request.query.get("clips"):
        mode = "clip"
        start = request.query.get("start") + "T00:00:00Z"
        end = request.query.get("end") + "T00:00:00Z"
        clips = Helix.get(
            f"clips?broadcaster_id={channel.id}&first=100&started_at={start}&ended_at={end}"
        )
        data = process_data(clips, mode="clip")
        data = sorted(data, key=lambda info: info["view_count"], reverse=True)
    elif url := request.query.get("video"):
        watch_video(mode="vod", url=url)
        return """<script>setTimeout(function () { window.history.back() });</script>"""
    elif request.query.get("close"):
        redirect(f"/{channel.login}")
    return template("channel.tpl", channel=channel, mode=mode, data=data, date=date)


@route("/search")
def search():
    query = request.query.q
    t = request.query.t
    mode, model, count = ("games", Game, 10) if t == "categories" else ("users", Streamer, 5)
    ids = {int(result["id"]) for result in Helix.get(f"search/{t}?query={query}&first={count}")}
    asyncio.run(Db.cache(ids, mode=mode))
    results = model.select().where(model.id.in_(ids))
    return template("search.tpl", query=query, mode=mode, results=results)


@route("/following")
def following():
    Db.update_follows()
    follows = Streamer.select().where(Streamer.followed == True).order_by(Streamer.display_name)
    return template("following.tpl", follows=follows)


@route("/categories/<game>")
def browse(game="all"):
    if game == "all":
        pass


@route("/top/<t>")
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
        abort(code=404, text="Page not found")
    return template("top.tpl", data=data, t=t)


@route("/settings")
def settings():
    os_ = system()
    if request.query.get("open"):
        if os_ == "Linux":
            Popen("open config/settings.toml", shell=True, close_fds=True)
            return redirect("/settings")
    config = toml.load("config/settings.toml")[f"{os_}"]
    return template("settings.tpl", config=config)


@route("/config/<filename:path>")
def send_static(filename):
    return static_file(filename, root="config/")


@error(404)
def error404(error):
    return template(
        """<p>Page does not exist.</p><p>For developer: {{error}}</p>""",
        error=error,
    )


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
    os_ = system()
    c = toml.load("config/settings.toml")[f"{os_}"]
    if c["multi"] is False:
        if os_ == "Linux":
            pid, e = Popen("pgrep mpv", shell=True, stdout=PIPE).communicate()
            pid = pid.decode().strip()
            if pid != "":
                Popen(f"kill {pid}", shell=True, stdout=PIPE).wait()

    if os_ == "Linux":
        if mode == "live":
            print("\x1b[1A\x1b[2K\x1b[1A", f"Launching stream twitch.tv/{channel}", sep="\n")
            Popen(
                f'streamlink -l none -p {c["app"]} -a "{c["args"]}" \
                    --twitch-disable-ads --twitch-low-latency twitch.tv/{channel} best',
                shell=True,
                close_fds=True,
            )
        else:
            print("\x1b[1A\x1b[2K\x1b[1A", f"Launching video: {url}", sep="\n")
            Popen(
                f'{c["app"]} {c["args"]} --really-quiet {url}',
                shell=True,
                close_fds=True,
            )


def process_data(data: list[dict], mode: str) -> list[dict]:
    if mode == "vod":
        for vod in data:
            vod["thumbnail_url"] = vod["thumbnail_url"].replace("%{width}x%{height}", "480x270")
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
            Db.cache({int(gid) for clip in data if (gid := clip["game_id"])}, mode="games")
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
            *(session.get(f"{Helix.endpoint}/videos?id={vod_id}") for vod_id in to_fetch)
        )
    vods = [resp.json()["data"][0] for resp in vod_data]
    for clip in clips:
        if clip["video_id"]:
            clip["vod"] = vods.pop(0)
            vod_id, timestamp = clip["video_id"], clip["created_at"]
            vod_start = datetime.strptime(clip["vod"]["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
            timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
            elapsed = round((timestamp - vod_start).total_seconds() - 61)
            if "h" not in clip["vod"]["duration"]:
                clip["vod"]["duration"] = f"0h{clip['vod']['duration']}"
            hours = elapsed // 3600
            elapsed %= 3600
            minutes = elapsed // 60
            elapsed %= 60
            seconds = elapsed
            clip[
                "vod_link"
            ] = f"http://www.twitch.tv/videos/{vod_id}/?t={hours}h{minutes}m{seconds}s"
        else:
            clip["vod_link"] = None
    return clips


if __name__ == "__main__":
    run(server="waitress", host="localhost", port=8080)
