% rebase('base.tpl', title=channel.display_name)
<header>
    <h1><img src="{{channel.profile_image_url}}" alt="{{channel.login}}" width="75">{{channel.display_name}}</h1>
    <div>{{channel.broadcaster_type}}</div>
    <div>{{channel.description}}</div>
</header>
<section>
    <form action="" method="get" id="follow">
        <button name="follow" value="toggle">{{"Unfollow" if channel.followed else "Follow"}}</button>
    </form>
    <form action="" method="get" id="vod">
        <button name="vod" value="archive">View Vods</button>
    </form>
    <form action="" method="get" id="clips">
        <label for="start">Start Date:</label>
        <input type="date" id="start" name="start" value="{{date.get('start') or ''}}">
        <label for="end">End Date:</label>
        <input type="date" id="end" name="end" value="{{date.get('end') or ''}}">
        <button name="clips" value="range">View Clips</button>
    </form>
</section>
<main>
    % if mode == "chat":
    <iframe id="chat_embed" src="https://www.twitch.tv/embed/{{channel.login}}/chat?darkpopout&parent=localhost" height="500" width="350"></iframe>
    % end
    % if mode == "vod":
    <h3>Past Broadcasts:</h3>
    % for vod in data:
    <article>
        <p>{{vod["title"]}}</p>
        <p>{{vod["duration"]}}</p>
        <form action="" method="get" id="video">
            <button name="video" value="{{vod['url']}}"><img src="{{vod['thumbnail_url']}}" alt=""></button>
        </form>
        <p>Created: {{vod['created_at']}} ago, {{vod['view_count']}} views</p>
    </article>
    % end
    % end
    % if mode == "clip":
    % for clip in data:
    <article>
        <p>{{clip['title']}}</p>
        <form action="" method="get" id="video">
            <button name="video" value="{{clip['url']}}"><img src="{{clip['thumbnail_url']}}" alt="" width="180"></button>
        </form>
        <p><img src="{{clip['box_art_url']}}" alt="" width="50">{{clip['game_name']}}</p>
        <p>{{clip['time_since']}} ago, {{clip['view_count']}} views</p>
        % if clip['vod_link']:
        <button name="video" value="{{clip['vod_link']}}" form="video">View VOD</button>
        % end
    </article>
    % end
    % end
</main>
