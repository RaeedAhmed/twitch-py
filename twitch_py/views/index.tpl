% rebase('base.tpl', title="Home - "+User.display_name, user=User)
<main class="grid">
    % for stream in streams:
        <article class="card">
            <h3><a href="{{stream['user_login']}}"><img src="{{stream['profile_image_url']}}" alt="stream['user_name']" width="75"></a>  {{stream["user_name"]}}</h3>
            <p title="{{stream['title']}}">{{stream['title']}}</p>
            <div class="thumbnail">
                <a href="{{stream['user_login']}}?watch=live"><img src="{{stream['thumbnail_url']}}" alt="{{stream['title']}}" width=100% height=100% loading="lazy"></a>
                <div class="bl">
                    <i class="gg-timer"></i>
                    <b>{{stream['uptime']}}</b>
                </div> 
                <div class="br">
                    <i class="gg-user"></i>
                    <b> {{stream['viewer_count']}}</b>
                </div>
            </div>
            <p><a href="/categories/{{stream['game_id']}}"><img src="{{stream['box_art_url']}}" alt="{{stream['game_name']}}" width = 50 loading="lazy"></a>  {{stream['game_name']}}</p>
        </article>
    % end
</main>

