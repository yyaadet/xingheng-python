import wx
import requests
import json
import logging
import os
import traceback

import settings


logger = logging.getLogger(__name__)


class BaseFrame(wx.Frame):
    BG_COLOR = (0x13, 0x1d, 0x27, 255)

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.token = ""
        self.uid = -1
        self.status_bar: wx.StatusBar = self.CreateStatusBar()

        self.initial_token()

    def initial_token(self):
        if settings.TOKEN_PATH.exists():
            data = json.loads(settings.TOKEN_PATH.read_text())
            self.token = data['secret']
            self.uid = data['uid']

    def set_error_tips(self, msg):
        if not msg:
            self.status_bar.SetStatusText('')
        else:
            self.status_bar.SetStatusText(f"错误：{msg}")

    def set_tips(self, msg):
        self.status_bar.SetStatusText(f"{msg}")

    def request(self, *args, **kwargs):
        try:
            if 'params' in kwargs:
                kwargs['params'].update({
                    'uid': self.uid,
                    'secret': self.token,
                    'app_version': settings.APP_VERSION,
                    'app_build': settings.APP_BUILD,
                    'app_platform': settings.APP_PLATFORM,
                })
            else:
                kwargs['params'] = {
                    'uid': self.uid,
                    'secret': self.token,
                    'app_version': settings.APP_VERSION,
                    'app_build': settings.APP_BUILD,
                    'app_platform': settings.APP_PLATFORM,
                }

            if 'SSL_CERT_FILE' in os.environ and os.environ['SSL_CERT_FILE']:
                kwargs['cert'] = os.environ['SSL_CERT_FILE']
                kwargs['verify'] = False
            r = requests.request(*args, **kwargs)
            logger.info(f"{r.url}, args {args}, kwargs {kwargs}, response {r.text}")
        except Exception as e:
            logger.warning(f"args {args}, kwargs {kwargs}, exception: {e}, {traceback.format_exc(10)}")
            self.set_error_tips(e)
            return None

        return r
    
    def pack_url(self, path):
        return f"https://{settings.SERVER_HOST}{path}"
    
    @classmethod
    def format_seconds(cls, seconds) -> str:
        minutes = int(seconds / 60)
        left = int(seconds) % 60
        return f"{minutes:02d}:{left:02d}"
            
    def is_logined(self):
        if self.token:
            return True
        return False