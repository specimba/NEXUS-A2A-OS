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
      // Find all divs or paragraphs or sections that contain text
      const divs = [...document.querySelectorAll("div, p, pre, code")];
      // Filter out divs with children, so we only get leaf nodes or nodes with direct text
      const leafText = divs.filter(el => {
        const text = el.innerText || "";
        return text.length > 50 && el.children.length <= 2;
      });
      return leafText.slice(-15).map(el => ({
        tag: el.tagName,
        className: el.className,
        text: (el.innerText || "").slice(0, 150)
      }));
    })()`,
    returnByValue: true
  }}));

  ws.addEventListener('message', (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id === 1) {
      console.log('Recent text nodes:');
      console.log(JSON.stringify(msg, null, 2));
      ws.close();
    }
  });
}
run().catch(console.error);
