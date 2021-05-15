<!DOCTYPE html>
<html>
    <head>
        <title>{{title or 'TwitchPy'}}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <link rel="stylesheet" href="/static/style.css" type="text/css">
        <link href="https://css.gg/css?=|calendar-dates|eye|search|time|timer|user-add|user-remove|user" rel="stylesheet">
    </head>
    <body>
        <nav>
            <ul>
                <li><a href="/" class="nav">Home</a></li>
                <li><a href="/following" class="nav">Following</a></li>
                <li><a href="/top/channels" class="nav">Streams</a></li>
                <li><a href="/top/games" class="nav">Games</a></li>
                <li><a href="/settings" class="nav">Settings</a></li>
                <li class="search">
                    <form action="/search">
                        <div class="radio-toolbar">
                            <input id="1" type="radio" value="channels" name="t" checked>
                            <label for="1">Channel</label>
                            <input id="2" type="radio" value="categories" name="t">
                            <label for="2">Category</label>
                            <input type="search" name="q" placeholder="Search..." minlength="1" required>
                            <button><i class="gg-search"></i></button>
                        </div>
                    </form>
                </li>
            </ul>
        </nav>
        % if defined('User'):
            <header>
                <section><img src="{{User.profile_image_url}}" alt="User.display_name" width="50" loading="lazy"> {{User.display_name}}</section>
            </header>
        % end
        {{!base}}
        <footer>
            <p>Written by Raeed Ahmed</p>
        </footer>
    </body>
</html>