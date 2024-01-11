# Azure Toolkit
## What's it for
This is a collection of some pieces of code that I've found useful to develop with Azure's Graph API. 
It aims to include all things :
- Authentication : To get started quickly with all flavours of OAuth2 and other authentication methods
- Graph API : To abstract as much as possible from the Graph API logic and focus on a more pythonic way of doing things
- Utilities : To make life easier when working with the Graph API, such as integrated callback servers, user interfaces for interactive flows, logging, etc...

## How to use it
### Authentication
Everything starts with an ```Azure Client``` object. This object is the entry point to the toolkit and is used to authenticate and interact with the Graph API.
The ```Azure Client``` object needs a few config parameters to be instantiated. These parameters are the following :
- ```tenant_id``` : The tenant ID of the Azure AD tenant you want to authenticate against
- ```client_id``` : The client ID of the application you want to authenticate with
- ```secret``` : The client secret of the application you want to authenticate with
- ```scopes``` : The scopes you want to request access to
- ```redirect_uri``` : The redirect URI you want to use for the interactive authentication flow in the case of delegated permissions
You should store those parameters in a JSON file and load them through the ```Azure Client``` such as in the code snippet below :
```python
from azure_toolkit import AzureClient
client = AzureClient(path="path/to/config.json", interactive=True)
```
From there, you can instantiate any of the Graph API components you want to use.
```python	
from azure_toolkit import Graph_Mail
mail = Graph_Mail(client)
mail.read_mails()
```

### Building 
To easily build the library, you can simply use poetry
```bash 
poetry build
```
