from typing import Optional
import wx
import wx.media
import logging
import datetime
import doctest

import settings
from models import Task, User
from base_frame import BaseFrame
from canvas import Canvas


logger = logging.getLogger(__name__)


class LockFrame(BaseFrame):

    def __init__(self, task: Task, *args, **kw):
        super().__init__(*args, **kw)
        self.task = task
        self.stop_timer = wx.Timer(self)
        self.countdown_seconds = 300
        self.init_countdown_seconds()
        self.countdown_timer = wx.Timer(self)
        self.quit_timer = wx.Timer(self)

        box = wx.BoxSizer(orient=wx.VERTICAL)
        self.canvas = Canvas(self, self.countdown_seconds, self.BG_COLOR, "离开电脑，走动走动")
        self.canvas.SetMinSize(self.Parent.lock_frame_size)
        box.Add(self.canvas, wx.EXPAND)

        self.SetSizer(box)

        # Disable the close button
        self.SetWindowStyle(self.GetWindowStyle() & ~wx.CLOSE_BOX)

        # Disable the minimize button
        self.SetWindowStyle(self.GetWindowStyle() & ~wx.MINIMIZE_BOX)

        self.SetTitle(self.task.title)
        self.Show()
        self.Raise()
        self.Center()

        # ready to rest
        self.Bind(wx.EVT_TIMER, self.countdown, self.countdown_timer)
        self.countdown_timer.Start(1000)

        self.Bind(wx.EVT_TIMER, self.stop_lock, self.stop_timer)
        self.stop_timer.StartOnce(1000*self.countdown_seconds)

        self.play_music(str(settings.TOMATO_DONE_MP3))

    def init_countdown_seconds(self):
        user = self.get_user_info()
        if not user:
            return
        if user.today_tomato_count % 4 == 0:
            self.countdown_seconds = 30*60
        
        self.set_tips(f"今日已经成功完成了{user.today_tomato_count}🍂。当前还有{user.left_tomato_number}🍂")

    def stop_lock(self, event):
        self.countdown_timer.Destroy()
        self.stop_timer.Destroy()
        
        self.play_music(str(settings.REST_DONE_MP3))
        
        self.Bind(wx.EVT_TIMER, self.quit, self.quit_timer)
        self.quit_timer.StartOnce(40*1000)

    def quit(self, event):
        logger.info("to close")
        self.quit_timer.Destroy()
        self.Close()

    def countdown(self, event):
        self.countdown_seconds -= 1
        logger.info(f"countdown {self.countdown_seconds}")
        self.SetTitle(f"{self.task.title} - 休息倒计时 {self.format_seconds(self.countdown_seconds)}")
        self.canvas.update(self.countdown_seconds)

    def get_user_info(self) -> Optional[User]:
        url = self.pack_url("/mobile/user/info/")
        params = {
            'user_id': self.uid,
        }

        r = self.request("GET", url, params=params)
        if not r:
            return None

        data = r.json()
        if data['is_ok'] is False:
            self.set_error_tips(data['reason'])
            return None
        
        item = data['user']
        user = User(
            uid=item['uid'], 
            username=item['username'],
            sex_name = item['sex_name'],
            left_tomato_number=item['left_tomato_number'],
            email=item['email'],
            upload_header_url=item['upload_header_url'],
            is_vip=item['is_vip'],
            today_tomato_count=data['today_tomato_count']
        )
        return user
        



if __name__ == "__main__":
    doctest.testmod()
