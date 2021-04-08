<html>
    <head>
        <title>{{title or 'TwitchPy'}}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <link rel="stylesheet" href="config/style.css" type="text/css">
    </head>
    <body>
        <nav>
            <ul>
                <li><a href="/">Home</a></li>
                <li><a href="/following">Following</a></li>
                <li><a href="/browse">Browse</a></li>
                <li><a href="/settings">Settings</a></li>
            </ul>
        </nav>
        % if defined('User'):
        <header>
            <section><img src="{{User.profile_image_url}}" alt="User.display_name" width="50" loading="lazy">Logged in as {{User.display_name}}</section>
        </header>
        % end
        <form action="/search">
            <select name="t" id="type-select">
                <option value="channels">Channels</option>
                <option value="categories">Categories</option>
            </select>
            <input type="search" name="q" placeholder="Search query">
            <button>Search</button>
        </form>
        {{!base}}
        <footer>
            <p>Written by Raeed Ahmed</p>
        </footer>
    </body>
</html>