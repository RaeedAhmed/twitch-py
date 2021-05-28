% rebase('base.tpl', title="Search Results")
<header>
    <h2>Search results for "{{query}}" in {{mode.title()}}:</h2>
</header>
<main>
    % if mode == "games":
    % for result in results:
    <article>
        <p><a href="/categories/{{result.id}}"><img src="{{result.box_art_url}}" alt="{{result.name}}" width="100" loading="lazy"></a>  {{result.name}}</p>
    </article>
    % end
    % else:
    % for result in results:
    <article>
        <div><a href="/{{result.model.login}}"><img src="{{result.model.profile_image_url}}" alt="profile" width="75" loading="lazy"></a>  <h2 style="display: inline-block;">{{result.model.display_name}}</h2>  <div style="display: inline-block;" broadcaster-type="{{result.model.broadcaster_type}}"></div></div>
        % if result.query["is_live"] is True:
        <form action="/{{result.model.login}}">
            <button name="watch" id="watch" value="live">Watch Live</button>
        </form>
        <p>Playing {{result.query["game_name"]}} | {{result.query["title"]}}</p>
        % end
        <p>{{result.model.description}}</p>
    </article>
    % end
    % end
</main>