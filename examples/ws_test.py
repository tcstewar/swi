import swi

class Server(swi.SimpleWebInterface):
    def swi(self):
        return """<html><head><script>
function doInit() {
    var s;
    try {
        s = new WebSocket("ws://localhost:8083/test");
        s.onopen = function(e) { console.log("connected");};
        s.onclose = function(e) { console.log("connection closed");};
        s.onerror = function(e) { console.log("connection error");};
        s.onmessage = function(e) { console.log("message: " + e.data);};
    } catch(ex) {
        console.log("connection exception: " + ex);
    }
}
</script></head>
<body onload="doInit();">
</body>
</html>"""

    def ws_test(self, client):
        import time
        while True:
            client.write(time.strftime('%H:%M:%S'))
            time.sleep(1)




swi.browser(port=8083)
swi.start(Server, port=8083)

