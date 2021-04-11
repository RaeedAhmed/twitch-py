% rebase('base.tpl', title="Home - "+User.display_name, user=User)
<main>
    <h2>Following:</h2>
    % for stream in streams:
        <article>
            <h3><a href="{{stream['user_login']}}"><img src="{{stream['profile_image_url']}}" alt="stream['user_name']" width="50"></a>{{stream["user_name"]}}</h3>
            <p>{{stream['title']}}</p>
            <div class="thumbnail">
                <a href="{{stream['user_login']}}?watch=live"><img src="{{stream['thumbnail_url']}}" alt="{{stream['title']}}" width=100% height=100% loading="lazy"></a>
                <b class="bl">⏱️{{stream['uptime']}}</b>
                <b class="br">🔴 {{stream['viewer_count']}}</b>
            </div>
            <p><a href="/categories/{{stream['game_id']}}"><img src="{{stream['box_art_url']}}" alt="{{stream['game_name']}}" width = 50 loading="lazy"></a>  {{stream['game_name']}}</p>
        </article>
    % end
</main>

