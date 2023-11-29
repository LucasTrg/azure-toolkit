import json

import requests

from .azure_auth import AzureAuth


class GraphMail:
    def __init__(self, azureAuth: AzureAuth):
        self.auth_client = azureAuth

    def read_mails(self, inbox="Inbox", uid="me", n=10):
        url = f"https://graph.microsoft.com/v1.0/users/{uid}/mailFolders/{inbox}/messages?$orderby=receivedDateTime+desc&$select=sender,subject,body,receivedDateTime&$top={500 if n==-1 else n}"
        if uid == "me":
            url = f"https://graph.microsoft.com/v1.0/me/mailFolders/{inbox}/messages?$orderby=receivedDateTime+desc&$select=sender,subject,body,receivedDateTime"

        print(url)
        r = requests.get(
            url,
            headers={
                "Authorization": "Bearer " + self.auth_client.bearer_token,
                "Content-Type": "application/json",
                "Accept": "application/json;odata.metadata=minimal",
                "Prefer": 'outlook.body-content-type="text"',
            },
        )

        if r.status_code >= 300:
            raise ConnectionError(str(r.status_code) + str(r.content))
        # print(r.content)
        r_json = json.loads(r.content.decode("utf-8").replace("'", '\\"'))

        data = []
        data = r_json["value"]
        while "@odata.nextLink" in r_json.keys() and (len(data) < n or n == -1):
            print()
            print("NEXT PAGE", r_json["@odata.nextLink"])
            print()
            r = requests.get(
                r_json["@odata.nextLink"],
                headers={
                    "Authorization": "Bearer " + self.auth_client.bearer_token,
                    "Content-Type": "application/json",
                    "Accept": "application/json;odata.metadata=minimal",
                },
            )
            r_json = json.loads(r.content.decode("utf-8").replace("'", '\\"'))
            if "value" in r_json.keys():
                data += r_json["value"]

        return data[:n]

    def write_draft(self, message=None, text="INSERT TEMPLATE HERE"):
        draft = {
            "isDraft": True,
            "body": {
                "contentType": "html",
                "content": f"{text}",
            },
        }
        return draft

        # url_patch = f"https://graph.microsoft.com/v1.0/me/messages/{id}"
        # r = requests.patch(
        #     url_patch,
        #     headers={
        #         "Authorization": "Bearer " + self.auth_client.bearer_token,
        #         "Content-Type": "application/json",
        #         "Accept": "application/json;odata.metadata=minimal",
        #     },
        #     data=draft,
        # )
        # print(r.status_code)
        # print(r.content)
        # print(r.json())
        # print("")

    def list_inboxes(self, uid="me"):
        url = f"https://graph.microsoft.com/v1.0/users/{uid}/mailFolders/?includeHiddenFolders=true&$expand=childFolders"
        if uid == "me":
            url = f"https://graph.microsoft.com/v1.0/me/mailFolders/?includeHiddenFolders=true&$expand=childFolders"

        r = requests.get(
            url,
            headers={
                "Authorization": "Bearer " + self.auth_client.bearer_token,
                "Content-Type": "application/json",
                "Accept": "application/json;odata.metadata=minimal",
            },
        )
        # print(url)
        r_json = json.loads(r.content.decode("utf-8").replace("'", '\\"'))
        # print(f"a")
        if r.status_code >= 300:
            raise ConnectionError(str(r.status_code) + str(r.content))
        # print(r.content)
        data = r_json["value"]  # may need to be commented
        while "@odata.nextLink" in r_json.keys():
            r = requests.get(
                r_json["@odata.nextLink"],
                headers={
                    "Authorization": "Bearer " + self.auth_client.bearer_token,
                    "Content-Type": "application/json",
                    "Accept": "application/json;odata.metadata=minimal",
                },
            )
            r_json = json.loads(r.content.decode("utf-8").replace("'", '\\"'))
            data += r_json["value"]

        return data

    def attach_file(self, uid, mid, attachment_name, file):
        url = f"/users/{uid}/messages/{mid}/attachments"

        if type(file) == str:
            with open(file, "rb") as f:
                file = f.read()

        r = requests.post(
            url,
            headers={
                "Authorization": "Bearer" + self.auth_client.bearer_token,
                "Content-Type": "application/json",
                "Accept": "application/json;odata.metadata=minimal",
            },
            data={
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": attachment_name,
                "contentBytes": file,
            },
        )
        print(r.status_code)
        print(r.json())

    def post_draft(self, draft, mid, uid):
        url = f"https://graph.microsoft.com/v1.0/users/{uid}/messages/{mid}/createReply"

        r = requests.post(
            url,
            headers={
                "Authorization": "Bearer " + self.auth_client.bearer_token,
                "Content-Type": "application/json",
                "Accept": "application/json;odata.metadata=minimal",
            },
        )

        print(r.status_code)
        if r.status_code >= 400:
            print(f"Error sending draft\n{r.content}")
        else:
            print("Draft sent")
        # print(r.content)
        # print(r.json())
        # print("")
        reply_id = r.json()["id"]
        reply_body = r.json()["body"]["content"]
        patch_url = f"https://graph.microsoft.com/v1.0//users/{uid}/messages/{reply_id}"

        patch = {
            "body": {
                "contentType": "html",
                "content": draft + reply_body,
            }
        }
        patch = json.dumps(patch)
        r = requests.patch(
            patch_url,
            headers={
                "Authorization": "Bearer " + self.auth_client.bearer_token,
                "Content-Type": "application/json",
                "Accept": "application/json;odata.metadata=minimal",
            },
            data=patch,
        )
        # print(r.status_code)
        # print(r.content)
