% rebase('base.tpl', title="Settings")
<main>
    <table>
        % for key in config:
        <tr>
            <th>{{key}}</th>
            <td>{{config[key]}}</td>
        </tr>
        % end
    </table>
    <form action="" method="get" id="open"><button name="open" value="true" type="submit">Open Settings</button></form>
</main>
