import os
import base64

cookie_secret = base64.b64encode(os.urandom(32)).decode('utf-8')
print(cookie_secret)
