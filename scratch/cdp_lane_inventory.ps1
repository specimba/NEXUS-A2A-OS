$v = Invoke-RestMethod http://127.0.0.1:9224/json/version
$t = Invoke-RestMethod http://127.0.0.1:9224/json/list
$pages = $t | Where-Object { $_.type -eq 'page' }
[pscustomobject]@{
    Browser     = $v.Browser
    TabCount    = $t.Count
    PageCount   = @($pages).Count
    GrokTabs    = @($pages | Where-Object { $_.url -match 'grok\.com' }).Count
    ZoTabs      = @($pages | Where-Object { $_.url -match 'zo\.computer' }).Count
    ChatGPTTabs = @($pages | Where-Object { $_.url -match 'chatgpt' }).Count
    CDP         = $v.'WebSocket-Debugger-Url'
} | Format-List