<!DOCTYPE html>

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {
            font-family: Consolas, monaco, monospace;
            --font: Consolas, monaco, monospace;
            color: #f2f3f4;
            --text-color: #f2f3f4;
            background-color: #0e0e10;
            --bg-color: #0e0e10;
        }

        html {
            scrollbar-gutter: stable force;
            scrollbar-width: thin;
            scrollbar-color: dimgrey black;
        }
    </style>
    <title>Caching</title>
    <script>
        function getHash() {
            url = window.location.href.replace('#', '?')
            window.location = url
        }
    </script>
</head>

<body onload="getHash()">
    <h1>Building Cache...</h1>
</body>

</html>