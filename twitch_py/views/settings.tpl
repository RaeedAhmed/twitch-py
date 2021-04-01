% rebase('base.tpl', title="Settings")
<div>Settings</div>
<div>Allow multiple streams: {{config['general']['multi-stream']}} <div>("true"/"false")</div></div>
<div>Player: {{config['player'][os]['app']}} <div>("mpv", "vlc")</div></div>
<div>Player args: {{config['player'][os]['args']}} <div>("--arg1=value1 --arg2=value2")</div></div>