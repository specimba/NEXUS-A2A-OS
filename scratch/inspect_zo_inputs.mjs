async function run() {
  const list = await fetch('http://127.0.0.1:9224/json/list').then(r => r.json());
  const zo = list.find(t => t.title.includes('Zo') || t.url.includes('zo.computer'));
  if (!zo) {
    console.log('Zo not found');
    return;
  }
  const ws = new WebSocket(zo.webSocketDebuggerUrl);
  await new Promise(r => ws.addEventListener('open', r));
  ws.send(JSON.stringify({ id: 1, method: 'Runtime.evaluate', params: {
    expression: `(() => {
      const el = [...document.querySelectorAll("textarea, [contenteditable='true'], input")];
      return el.map((x, index) => ({
        index,
        tag: x.tagName,
        outer: x.outerHTML.slice(0, 400),
        placeholder: x.getAttribute("placeholder") || x.placeholder || "",
        ariaLabel: x.getAttribute("aria-label") || "",
        className: x.className
      }));
    })()`,
    returnByValue: true
  }}));
  ws.addEventListener('message', (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id === 1) {
      console.log(JSON.stringify(msg, null, 2));
      ws.close();
    }
  });
}
run().catch(console.error);
