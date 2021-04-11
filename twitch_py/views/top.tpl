% rebase('base.tpl', title="Top "+t.title())
<h1>Top {{t.title()}}</h1>
% if t == "games":
<main>
% for game in data:
    <article>
        <img src="{{game.box_art_url}}" alt="" width="50">
        <p>{{game.name}}</p>
    </article>
% end
</main>
% end
% if t == "channels":
<main>
    % for stream in data:
    <article>
        <h3><a href="{{stream['user_login']}}"><img src="{{stream['profile_image_url']}}" alt="stream['user_name']" width="50"></a>{{stream["user_name"]}}</h3>
        <p>{{stream['title']}}</p>
        <div class="thumbnail">
            <a href="{{stream['user_login']}}?watch=live"><img src="{{stream['thumbnail_url']}}" alt="{{stream['title']}}" width=100% height=100% loading="lazy"></a>
            <b class="bl">⏱️{{stream['uptime']}}</b>
            <b class="br">🔴 {{stream['viewer_count']}}</b>
        </div>
        <p><img src="{{stream['box_art_url']}}" alt="{{stream['game_name']}}" width = 50 loading="lazy">  {{stream['game_name']}}</p>
    </article>
    % end
</main>
% end