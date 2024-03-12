import wx
import requests
import logging
import traceback
import json
import settings
from base_frame import BaseFrame


logger = logging.getLogger(__name__)


class LoginFrame(BaseFrame):

    def __init__(self, frame, *args, **kw):
        super().__init__(*args, **kw)

        self.parent_frame = frame

        panel = wx.Panel(self)

        box = wx.GridBagSizer(0, 0)
        self.username_label = wx.StaticText(panel, label="用户名：")
        box.Add(self.username_label, pos=(0, 0), span=(1, 1), flag=wx.ALL, border=5)

        self.username_text = wx.TextCtrl(panel)
        box.Add(self.username_text, pos=(0, 1), span=(1, 1), flag=wx.EXPAND|wx.ALL, border=5)

        self.password_label = wx.StaticText(panel, label="密码：")
        box.Add(self.password_label, (1, 0), span=(1, 1), flag=wx.ALL, border=5)

        self.password_text = wx.TextCtrl(panel, style=wx.TE_PASSWORD)
        box.Add(self.password_text, (1, 1), span=(1, 1), flag=wx.ALL|wx.EXPAND, border=5)

        self.login_btn = wx.Button(panel, label="登陆")
        self.login_btn.Bind(wx.EVT_BUTTON, self.on_button_click)
        self.login_btn.SetMinSize((200, 30))
        box.Add(self.login_btn, (2, 1), span=(1, 1), flag=wx.ALL, border=5)

        panel.SetSizerAndFit(box)
        self.Center()
        self.Show()
        self.Raise()

    def on_button_click(self, event):
        url = f'https://{settings.SERVER_HOST}/account/mobile/get_token/'
        params = {
            'username': self.username_text.GetValue(),
            'password': self.password_text.GetValue()
        }
        r = self.request('GET', url, params=params)
        if not r:
            return
        
        if r.status_code != 200:
            logger.warn(f"get {url} failed: status code {r.status_code}, response {r.text}")
            self.set_error_tips(r.text)
            return
        data = r.json()
        logger.info(f'response {data}')
        if data['is_ok'] is False:
            logger.warning(f"failed to login: {data}")
            self.set_error_tips(f'登陆失败, {data["reason"]}')
            return
            
        self.on_success(data)

    def on_success(self, data):
        self.status_bar.SetStatusText("登陆成功")
        self.username_text.SetEditable(False)
        self.password_text.SetEditable(False)
        settings.TOKEN_PATH.write_text(json.dumps(data))

        self.Close()

        self.parent_frame.initial_token()
        self.parent_frame.Show()

