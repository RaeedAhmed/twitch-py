% rebase('base.tpl', title="Search Results")
<header>
    <h2>Search results for "{{query}}" in {{mode.title()}}:</h2>
</header>
<main>
    % if mode == "games":
    % for result in results:
    <article>
        <p><a href="/categories/{{result.id}}"><img src="{{result.box_art_url}}" alt="{{result.name}}" width="100" loading="lazy"></a>{{result.name}}</p>
    </article>
    % end
    % else:
    % for result in results:
    <article>
        <p><a href="/{{result.login}}"><img src="{{result.profile_image_url}}" alt="{{result.display_name}}" width="75" loading="lazy"></a>{{result.display_name}} - {{result.broadcaster_type}}</p>
        <p>{{result.description}}</p>
    </article>
    % end
    % end
</main>