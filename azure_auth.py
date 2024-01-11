import json
import os
import threading
import time
import webbrowser
from random import randint
from urllib.parse import quote

import pkce
import requests

from _callback_server import code_queue
from _callback_server import run as run_callback_server
from _callback_server import token_queue


class AzureAuth:
    """Class in charge of connecting to sharepoint and downloading the excel file
    Based on https://learn.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-auth-code-flow
    """

    def __init__(self, interactive=True, path="config/azure.json"):
        # Load config file
        with open(path) as config_file:
            config = json.load(config_file)
        self.interactive = interactive
        # Load config variables
        self.client_secret = config["secret"]
        self.tenant_id = config["tenant_id"]
        self.client_id = config["client_id"]
        self.code_redirect_uri = config["code_redirect_uri"]
        self.token_redirect_uri = config["token_redirect_uri"]
        self.scope = config["scope"]
        self.auth_code = ""
        if interactive:
            self.code_verif, self.code_challenge = pkce.generate_pkce_pair()

            self.start_callback_server()

    def start_callback_server(self):
        """
        Opens a flask server to handle the OAuth2 authentication callback from AD
        """
        kwargs = {
            "host": "0.0.0.0",
        }
        if self.code_redirect_uri.startswith("https"):
            kwargs["ssl_context"] = "adhoc"
        callback_thread = threading.Thread(target=run_callback_server, kwargs=kwargs)
        callback_thread.setDaemon(True)
        callback_thread.start()
        self.call_back_server = callback_thread

    def request_authorization_code(self):
        """Opens a web browser to get the user to authenticate and authorize the app
        Args:
            path_to_resource (str): The path to the resource to be accessed
        """
        # Open a web browser or embedded web view for user authentication

        # url = f"https://login.microsoftonline.com/common/oauth2/authorize?response_type=code&client_id={self.client_id}&redirect_uri={self.redirect_uri}&resource={path_to_resource}"

        # The state is here to check for CSRF attacks
        self.state = randint(0, 1000000)
        url = f"""https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/authorize?client_id={self.client_id}
                &response_type=code
                &redirect_uri={quote(self.code_redirect_uri)}
                &response_mode=query
                &scope={quote(self.scope)}
                &prompt=consent
                &state={self.state}
                &code_challenge={quote(self.code_challenge)}
                &code_challenge_method=S256"""

        # webbrowser.open(path_to_resource)
        webbrowser.open(url)
        return url
        # webbrowser.open(f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/authorize?client_id={self.client_id}")
        # self.download_ressource(path_to_resource)

    def set_authorization_code(self, auth_code):
        """Saves the token received from the server
        args:
            auth_code (str): The authorization code returned by the server
        """
        # print("Sharepoint connector :", auth_code)
        self.auth_code = auth_code
        # self.browser.close()

    def request_s2s_bearer_token(self, user, pwd):
        url = (
            f"""https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"""
        )

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "password",
            "username": user,
            "password": pwd,
        }

        r = requests.post(
            url,
            data=data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )

        print("Token Acquisition", r.status_code)
        # print(r.content)
        # print(r.json())
        if "access_token" not in r.json():
            raise ConnectionError(r.json())
        self.set_bearer_token(r.json()["access_token"])
        # print(self.bearer_token)
        return r.json()["access_token"]

    def request_bearer_token(self):
        """Requests a bearer token from the server using the authorization code"""
        url = (
            f"""https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"""
        )
        data = {
            "client_id": self.client_id,
            # "client_secret": self.client_secret,
            "scope": self.scope,
            "code": quote(self.auth_code),
            "redirect_uri": self.token_redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": self.code_verif,
        }
        # print("Requesting token")

        resp = requests.post(url, data=data)
        print("Token Acquisition", resp.status_code)
        # print(resp.content)
        # print(resp.json())
        if "access_token" not in resp.json():
            raise ConnectionError(resp.json())
        self.set_bearer_token(resp.json()["access_token"])
        # self.set_refresh_token(resp.json()["refresh_token"])

    def request_spo_token(self):
        """Requests a bearer token from the server using the authorization code"""
        url = (
            f"""https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"""
        )
        data = {
            "client_id": self.client_id,
            "scope": self.scope,
            "code": self.auth_code,
            "redirect_uri": self.token_redirect_uri,
            "grant_type": "refresh_token",
            "code_verifier": self.code_verif,
        }
        # print("Requesting token")

        resp = requests.post(url, data=data)
        # print("Token Acquisition", resp.status_code)
        # print(resp.content)

    def set_bearer_token(self, bearer_token):
        """Saves the token received from the server
        args:
            bearer_token (str): The bearer token returned by the server
        """
        # Set the token
        # print("Sharepoint TOKEN :", bearer_token)
        # print("")
        self.bearer_token = bearer_token

    def set_refresh_token(self, refresh_token):
        """Saves the token received from the server
        args:
            refresh_token (str): The refresh token returned by the server
        """
        # Set the token
        self.refresh_token = refresh_token

    def get_state(self) -> int:
        return self.state

    def poll_code(self, *args, **kwargs):
        """
        Polls the callback server to see if the user has authenticated
        Returns:
            bool: True if the clock should continue, False if the server has received a token and the clock should stop
        """
        if os.path.isfile("code.txt"):
            print("Reading code from file")
            with open("code.txt", "r") as f:
                code = f.read()
            # print("CODE Received from file" + code)
            os.remove("code.txt")
            self.set_authorization_code(code)
            self.request_bearer_token()
            return False

        elif not code_queue.empty():
            code, state = code_queue.get()
            # print("CODE Received" + code)
            if int(state) != int(self.state):
                print(
                    "State mismatch : the state received is not the same as the one sent",
                    state,
                    self.state,
                )
                return False
            self.set_authorization_code(code)
            self.request_bearer_token()
            # self.SharePointConnector.download_ressource(self.SharePointConnector.resource)
            # Clock.schedule_interval(self.poll_token, 1)
            return False
        else:
            return True

    def poll_token(self, *args, **kwargs):
        """
        Polls the callback server to see if the auth server has answered a bearer token
        Returns:
            bool: True if the clock should continue, False if the server has received a token and the clock should stop
        """
        if not token_queue.empty():
            token = token_queue.get()
            # print("TOKEN Received" + token)

            self.SharePointConnector.set_bearer_token(token)
            # content = self.SharePointConnector.download_ressource()
            return False
        else:
            return True

    def is_in_group(self, group_id, uid="me"):
        """Checks if a user belongs to a given security group
        # Note it might be wise to support multiple group_id check for instance to facilitate giving the user multiple credetials at once.

        Args:
            group_id (str): Security group id
            uid (str, optional): ID to check. Defaults to "me".

        Returns:
            bool: True if the user belongs to the group, False otherwise
        """
        if uid == "me":
            url = f"https://graph.microsoft.com/v1.0/me/getMemberGroups"
        else:
            url = f"https://graph.microsoft.com/v1.0/users/{id}/getMemberGroups"

        data = {"securityEnabledOnly": False}

        headers = {
            "Authorization": "Bearer " + self.bearer_token,
            "Content-Type": "application/json",
            "Accept": "application/json;odata.metadata=minimal",
        }

        r = requests.post(url=url, headers=headers, data=data)
        print("Group check", r.status_code)
        r_json = json.loads(r.content.decode("utf-8").replace("'", '\\"'))
        print("Group check memberships", r_json["value"])
        return group_id in r_json["value"]

    def connect(self):
        """
        Starts the interactive authentication process, and wait for an answer on the callback server.
        """
        self.request_authorization_code()
        while not self.poll_code():
            time.sleep(1)
        self.shutdown_callback_server()

    def shutdown_callback_server(self):
        pass
        # callback_server.shutdown()
