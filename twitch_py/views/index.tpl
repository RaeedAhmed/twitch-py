% rebase('base.tpl', title="Home - "+User.display_name)
<header>
    <section><img src="{{User.profile_image_url}}" alt="User.display_name" width="50">Logged in as {{User.display_name}}</section>
</header>
<main>
    <h2>Following:</h2>\\
    % for stream in streams:
    <article>
        <h3><a href="{{stream['user_login']}}"><img src="{{stream['profile_image_url']}}" alt="stream['user_name']" width="50"></a>{{stream["user_name"]}}</h3>
        <p>{{stream['title']}}</p>
        <a href="{{stream['user_login']}}?watch=live"><img src="{{stream['thumbnail_url']}}" alt="{{stream['title']}}" width="250"></a>
        <p><img src="{{stream['box_art_url']}}" alt="{{stream['game_name']}}" width = 50> Playing {{stream['game_name']}}</p>
        <p>Streaming for {{stream['uptime']}} to {{stream['viewer_count']}} viewers</p>
    </article>
    % end
</main>

