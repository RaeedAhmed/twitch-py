% rebase('base.tpl', title="Settings")
<main>
    <table>
        <thead>
            <tr>
                <th colspan="2">settings.toml</th>
            </tr>
        </thead>
        <tbody>
            % for key in config:
            <tr>
                <td> {{key}} </th>
                <td> {{config[key]}} </td>
            </tr>
            % end
        </tbody>
    </table>
    <br>
    <form action="" method="get" id="open"><button name="open" value="true" type="submit">Open Settings</button></form>
    <br>
    <form action="" method="get" id="cache"><button name="cache" value="cache" type="submit">Clear Cache</button></form>
    <br>
    <form action="" method="get" id="logout"><button name="logout" value="logout" type="submit">Logout</button></form>
</main>
