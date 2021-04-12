% rebase('base.tpl', title=channel.display_name)
<header>
    <h1><img src="{{channel.profile_image_url}}" alt="{{channel.login}}" width="75" loading="lazy">{{channel.display_name}}</h1>
    <div>{{channel.broadcaster_type}}</div>
    <div>{{channel.description}}</div>
    <form action="https://www.twitch.tv/popout/{{channel.login}}/chat" target="_blank"><button>Chat</button></form>
</header>
<section>
    <form action="" method="get" id="follow">
        <button name="follow" value="{{'Unfollow' if channel.followed else 'Follow'}}">{{"Unfollow" if channel.followed else "Follow"}}</button>
    </form>
    <form action="" method="get" id="vod">
        <button name="vod" value="archive">View Vods</button>
    </form>
    <form action="" method="get" id="clips">
        <label for="start">Start Date:</label>
        <input type="date" id="start" name="start" value="{{date.get('start') or ''}}" required>
        <label for="end">End Date:</label>
        <input type="date" id="end" name="end" value="{{date.get('end') or ''}}" required>
        <button name="clips" value="range">View Clips</button>
    </form>
</section>
<main>
    % if mode == "vod":
        <h3>Past Broadcasts:</h3>
        % for vod in data:
        <article>
            <p>{{vod["title"]}}</p>
            <div class="thumbnail">
                <a href="?video={{vod['url']}}"><img src="{{vod['thumbnail_url']}}" alt="" loading="lazy" width=100% height=100%></a>
                <div class="tr">
                    <i class="gg-calendar"></i>
                    <b>{{vod['created_at']}}</b>
                </div>
                <div class="bl">
                    <i class="gg-time"></i>
                    <b>{{vod["duration"]}}</b>
                </div>
                <div class="br">
                    <i class="gg-eye"></i>
                    <b>{{vod['view_count']}}</b>
                </div>
            </div>
        </article>
        % end
    % end
    % if mode == "clip":
        % for clip in data:
            <article>
                <p>{{clip['title']}}</p>
                <div class="thumbnail">
                    <a href="?video={{clip['url']}}"><img src="{{clip['thumbnail_url']}}" alt="" width="100%" height="100%" loading="lazy"></a>
                    <div class="tr">
                        <i class="gg-calendar"></i>
                        <b>{{clip['time_since']}}</b>
                    </div>
                    <div class="br">
                        <i class="gg-eye"></i>
                        <b>{{clip['view_count']}}</b>
                    </div>
                </div>
                % if clip['game_id']:
                <p><a href="/categories/{{clip['game_id']}}"><img src="{{clip['box_art_url']}}" alt="" width="50" loading="lazy"></a>{{clip['game_name']}}</p>
                % end
                % if clip['vod_link']:
                <form action="" method="get" id="video">
                    <button name="video" value="{{clip['vod_link']}}" form="video">View VOD</button>
                </form>
                % end
            </article>
        % end
    % end
</main>
