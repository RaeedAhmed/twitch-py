% rebase('base.tpl', title="Top "+t.title())
<header>
% if t != "channels_filter":
    <h1>Top {{t.title()}}</h1>
% else:
    <h1>Top Streams in <img src="{{game.box_art_url}}" alt="" width="50"> {{game.name}}</h1>
% end
</header>
% if t == "games":
<main id="top_games">
% for game in data:
    <article>
        <a href="/categories/{{game.id}}"><img src="{{game.box_art_url}}" alt="" height="100" loading="lazy"></a>
        <p>{{game.name}}</p>
    </article>
% end
</main>
% end
% if t in ["channels", "channels_filter"]:
<main>
% for stream in data:
    <article>
        <h3><a href="/{{stream['user_login']}}"><img src="{{stream['profile_image_url']}}" alt="stream['user_name']" width="50"></a>{{stream["user_name"]}}</h3>
        <p>{{stream['title']}}</p>
        <div class="thumbnail">
            <a href="/{{stream['user_login']}}?watch=live"><img src="{{stream['thumbnail_url']}}" alt="{{stream['title']}}" width=100% height=100% loading="lazy"></a>
            <div class="bl">
                <i class="gg-timer"></i>
                <b>{{stream['uptime']}}</b>
            </div>
            <div class="br">
                <i class="gg-user"></i>
                <b> {{stream['viewer_count']}}</b>
            </div>
        </div>
        % if t == "channels":
        <p><a href="/categories/{{stream['game_id']}}"><img src="{{stream['box_art_url']}}" alt="{{stream['game_name']}}" width = 50 loading="lazy"></a>  {{stream['game_name']}}</p>
        % end
    </article>
% end
</main>
% end




