% rebase('base.tpl', title="Building Cache...")
<head>
    <script>
        function getHash() {
            url = window.location.href.replace('#', '?')
            window.location = url
        }
    </script>
</head>

<body onload="getHash()">
    <h1>Building cache...</h1>
</body>