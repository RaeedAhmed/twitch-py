% rebase('base.tpl', title="Following")
<header>
    <h1>Following {{len(follows)}} streamers</h1>
</header>
<input type="text" id="nameFilter" onkeyup="filterFunction()" placeholder="Filter by name...">
<section id="follow">
    % for follow in follows:
    <article>
        <a href="/{{follow.login}}"><img src="{{follow.profile_image_url}}" alt="" width="75" loading="lazy"></a>
        <p>{{follow.display_name}}</p>
    </article>
    % end
</section>
<script>
    function filterFunction() {
        var input, filter, section, article, p, i, txt;
        input = document.getElementById("nameFilter");
        filter = input.value.toUpperCase();
        section = document.getElementById("follow");
        article = section.getElementsByTagName("article");
        for (i=0;i<article.length;i++){
            p = article[i].getElementsByTagName("p")[0];
            txt = p.textContent || p.innerText;
            if(txt.toUpperCase().indexOf(filter) > -1) {
                article[i].style.display = "";
            } else {
                article[i].style.display = "none"
            }
        }
    }
</script>