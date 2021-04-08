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
    <a href="?open=true">Open Settings</a>
</main>
