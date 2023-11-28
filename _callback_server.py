import os
from queue import Queue

from flask import Flask, request

app = Flask(__name__)

code_queue = Queue()
token_queue = Queue()


@app.route("/token_request")
def token_callback():
    print("Callback server token answer", request.args)
    if "access_token" in request.args:
        token = request.args.get("access_token")
        token_queue.put(token)

        return f"Token received! "


@app.route("/auth")
def auth_callback():
    print("Callback server received request", request.method)

    if "code" in request.args:
        authorization_code = request.args.get("code")
        state = request.args.get("state")
        code_queue.put((authorization_code, state))
        if os.path.isfile("code.txt"):
            os.remove("code.txt")
        with open("code.txt", "w") as f:
            f.write(authorization_code)
            # f.write(state)
        return f"""Authorization code received! You can close this tab.\n
        <a href='localhost:8501/code={authorization_code}> Click here to continue </a>"""
    elif "access_token" in request.args:
        token = request.args.get("access_token")
        token_queue.put(token)
        return f"Token received! "
    else:
        return f"Invalid request"


@app.route("/shutdown")
def shutdown():
    func = request.environ.get("werkzeug.server.shutdown")
    if func is None:
        raise RuntimeError("Not running with the Werkzeug Server")
    func()


def run(host="localhost", port=8000, ssl_context=None):
    app.run(host=host, port=port, ssl_context=ssl_context)
    return app


if __name__ == "__main__":
    run()
