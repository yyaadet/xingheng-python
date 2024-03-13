#!/opt/homebrew/Caskroom/miniconda/base/bin/python
import logging
from typing import Optional
import wx
from wx.adv import TBI_DEFAULT_TYPE, TaskBarIcon, TBI_DOCK, TBI_CUSTOM_STATUSITEM
import requests
import time
import datetime
import webbrowser
from urllib.parse import urlencode
import sys

import settings
from login_frame import LoginFrame
from base_frame import BaseFrame
from lock_frame import LockFrame
from models import Task
from canvas import Canvas


logger = logging.getLogger(__name__)

main_frame = None


class MainFrame(BaseFrame):

    def __init__(self, *args, **kw):
        global main_frame 

        super(MainFrame, self).__init__(*args, **kw)

        main_frame = self

        # initial ui
        self.taskbar_icon = MyTaskBarIcon(self)

        box = wx.BoxSizer(orient=wx.HORIZONTAL)

        self.tree_ctrl = wx.TreeCtrl(self)
        self.tree_ctrl.SetMinSize((-1, settings.APP_SIZE[1]))
        self.tree_ctrl.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_tree_sel_changed)
        box.Add(self.tree_ctrl, wx.ALL|wx.EXPAND)

        self.lock_frame = None
        self.lock_timer = wx.Timer(self)
        self.lock_listen_task_id = 0
        self.lock_start_time = None
        self.lock_frame_size = None

        self.last_sync_task_time = None
        self.countdown_seconds = 0
        self.countdown_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_countdown, self.countdown_timer)

        self.panel = wx.Panel(self)
        panel_vbox = wx.BoxSizer(orient=wx.VERTICAL)
        self.canvas = Canvas(self.panel, 25*60, self.BG_COLOR, "🍅")
        self.canvas.SetMinSize((-1, settings.APP_SIZE[1] - 200))
        panel_vbox.Add(self.canvas, flag=wx.EXPAND)

        panel_vbox.Add(0, 10)
        self.tomato_btn = wx.Button(self.panel, label="开番")
        self.Bind(wx.EVT_BUTTON, self.on_tomato_btn_click, self.tomato_btn)
        panel_vbox.Add(self.tomato_btn, flag=wx.ALIGN_CENTRE_HORIZONTAL|wx.ALL, border=0)

        panel_vbox.Add(0, 10)
        self.goto_detail_btn = wx.Button(self.panel, label="查看详情")
        self.Bind(wx.EVT_BUTTON, self.on_goto_detail_btn_clicked, self.goto_detail_btn)
        panel_vbox.Add(self.goto_detail_btn, flag=wx.ALIGN_CENTRE_HORIZONTAL, border=0)
        
        panel_vbox.Add(0, 10)
        self.goto_add_btn = wx.Button(self.panel, label="创建作业")
        self.Bind(wx.EVT_BUTTON, self.on_goto_add_btn_clicked, self.goto_add_btn)
        panel_vbox.Add(self.goto_add_btn, flag=wx.ALIGN_CENTRE_HORIZONTAL, border=0)

        self.panel.SetSizer(panel_vbox)
        self.panel.SetMinSize((-1, settings.APP_SIZE[1]))
        box.Add(self.panel, wx.ALL | wx.EXPAND)
        
        self.SetSizer(box)
        self.Center(wx.BOTH)

        self.tasks: list[Task] = []

        # initial data
        self.initial_token()
        self.sync_tasks()
        self.initial_tree()
        self.initial_lock_timer()
        self.initial_tomato_btn()
        self.countdown_timer.Start(1000)

        if not self.is_logined():
            LoginFrame(self, self, title="Login")
        else:
            self.Show()

    @classmethod
    def get_default(cls):
        global main_frame
        return main_frame

    def on_countdown(self, event):
        self.sync_tasks()
        
        if self.lock_listen_task_id:
            task = self.find_task(self.lock_listen_task_id)
            if not task:
                self.lock_listen_task_id = 0
            else:
                if self.countdown_seconds > 0:
                    self.countdown_seconds -= 1
                    self.canvas.update(self.countdown_seconds, self.format_seconds(self.countdown_seconds))
                logger.info(f"countdown seconds {self.countdown_seconds}")
                task.opening_tomato_left_seconds = self.countdown_seconds

        
        self.initial_tree()
        self.initial_lock_timer()
        self.initial_tomato_btn()

    def get_tasks(self, page=1, page_size=100) -> list[Task]:
        url = self.pack_url("/mobile/task/my/")
        params = {
            'status': 1,
            "order": "-id",
            "page": page,
            "page_size": page_size,
        }
        r = self.request("GET", url, params=params)
        if not r:
            return []
        data = r.json()
        if data['is_ok'] is False:
            self.set_error_tips(data['reason'])
            return []
        
        tasks = []
        for item in r.json()['tasks']:
            task = Task(
                id=item['id'],
                title=item['title'],
                status=item['status'],
                tomato_minute=item['tomato_minute'],
                project=item['project'],
                opening_tomato_id=item['opening_tomato_id'],
                opening_tomato_left_seconds=item['opening_tomato_left_seconds'],
                last_update_datetime=item['last_update_datetime'],
                tomato_number=item['tomato_number'],
                expect_tomato_number=item['expect_tomato_number'],
                dead_datetime=item['dead_datetime']
            )
            tasks.append(task)
        return tasks
    
    def get_opening_task(self) -> Optional[Task]:
        for task in self.tasks:
            if task.opening_tomato_id > 0:
                return task
            
        return None
    
    def initial_tree(self):
        selected_task = self.get_selected_task()

        self.tree_ctrl.DeleteAllItems()
        self.tree_ctrl.AddRoot('作业列表')
        root = self.tree_ctrl.RootItem

        for task in self.tasks:
            if task.opening_tomato_id > 0:
                title = f"{task.title}: {task.tomato_number}/{task.expect_tomato_number}🍅 - 开番{self.format_seconds(task.opening_tomato_left_seconds)}"
            else:
                title = f"{task.title}: {task.tomato_number}/{task.expect_tomato_number}🍅，{task.dead_datetime}截止"
            item = self.tree_ctrl.AppendItem(root, title, data=task.id)
            if selected_task and selected_task.id == task.id:
                self.tree_ctrl.SelectItem(item)
        
        self.tree_ctrl.ExpandAll()

    def on_tree_sel_changed(self, event):
        # Get the item that was activated
        item = event.GetItem()
        item_text = self.tree_ctrl.GetItemText(item)
        item_task_id = self.tree_ctrl.GetItemData(item)
        task = self.find_task(item_task_id)
        if not task:
            self.SetTitle(settings.APP_NAME)
            return
        # Print the text of the activated item
        logger.info(f"select item: {item_text}")

        # render panel
        if task.opening_tomato_id > 0 and self.lock_start_time:
            self.SetTitle(f"{task.title} - 定时器将在{self.lock_start_time.strftime('%H:%M:%S')}启动占屏，强制休息")
        else:
            self.SetTitle(task.title)

    def find_task(self, task_id) -> Optional[Task]:
        for task in self.tasks:
            if task.id == task_id:
                return task
            
            return None

    def initial_lock_timer(self):
        if self.lock_listen_task_id > 0:
            return
        opening_task = self.get_opening_task()
        if not opening_task:
            return
        
        if opening_task.opening_tomato_left_seconds <= 1:
            return
        
        if opening_task.id != self.lock_listen_task_id and self.lock_listen_task_id > 0:
            return
        
        self.lock_listen_task_id = opening_task.id
        wait_seconds = int(opening_task.opening_tomato_left_seconds)
        #wait_seconds = 5
        logger.info(f"wait seconds {wait_seconds}")
        self.countdown_seconds = wait_seconds
        self.lock_start_time = datetime.datetime.now() + datetime.timedelta(seconds=wait_seconds)
        self.Bind(wx.EVT_TIMER, self.start_lock, self.lock_timer)
        self.lock_timer.StartOnce(wait_seconds*1000)
        self.canvas.set_seconds(opening_task.tomato_minute*60)

    def start_lock(self, event):
        screen_width, screen_height = wx.DisplaySize()
        ratio = 0.68
        width = int(screen_width * ratio)
        height = int(screen_height * ratio)
        self.lock_frame_size = (width, height)
        task = self.find_task(self.lock_listen_task_id)
        self.lock_frame = LockFrame(task, self, size=(width, height), style=wx.SYSTEM_MENU | wx.STAY_ON_TOP)

        self.lock_listen_task_id = 0
        self.lock_frame = None
        self.lock_start_time = None
        self.lock_timer.Stop()

    def sync_tasks(self, sync_interval_seconds=30) -> bool:
        if self.last_sync_task_time:
            interval = datetime.datetime.now() - self.last_sync_task_time
            if interval.total_seconds() <= sync_interval_seconds:
                logger.info(f"interval {interval.total_seconds()} seconds is less than {sync_interval_seconds}, abort")
                return False
        
        if self.lock_listen_task_id > 0:
            logger.info(f"lock listen task id {self.lock_listen_task_id} is exists, abort")
            return False
        
        tasks = self.get_tasks()
        # merge new tasks
        old_id_tasks_map = {x.id: x for x in self.tasks}
        id_tasks_map = {x.id: x for x in tasks}
        old_id_tasks_map.update(id_tasks_map)
        
        self.tasks = sorted(old_id_tasks_map.values(), key=lambda x: x.last_update_datetime, reverse=True)
        self.last_sync_task_time = datetime.datetime.now()
        return True

    def initial_tomato_btn(self):
        task = self.get_selected_task()
        if not task:
            self.tomato_btn.SetLabel('开番')
            return
        
        if task.opening_tomato_id <= 0:
            self.tomato_btn.SetLabel('开番')
            return
        
        if task.opening_tomato_left_seconds > 0:
            self.tomato_btn.SetLabel(f"放弃 {self.format_seconds(task.opening_tomato_left_seconds)}")
            # self.tomato_btn.SetBackgroundColour((0xf0, 0xad, 0x4e, 0))
            # self.tomato_btn.SetForegroundColour((255, 255, 255))
        else:
            self.tomato_btn.SetLabel('收割')

    def on_tomato_btn_click(self, event):
        task = self.get_selected_task()
        if not task:
            return
        
        if task.opening_tomato_id <= 0:
            tomato_id = self.create_tomato(task)
            task.opening_tomato_id = tomato_id
            resp = self.start_tomato(task)
            if resp['is_ok']:
                self.play_music(str(settings.TOMATO_START_MP3))
        else:
            if task.opening_tomato_left_seconds > 0: 
                abandon_count = self.abandon_tomato(task)
                if abandon_count > 0:
                    self.set_tips(f'已经累计放弃了 {abandon_count} 次')
                    self.lock_timer.Stop()
                    self.lock_start_time = None
                    self.lock_listen_task_id = 0
                    self.countdown_seconds = 0
            else:
                self.harvest_tomato(task)

        self.sync_tasks(sync_interval_seconds=0)

    def get_selected_task(self) -> Optional[Task]:
        selected_item = self.tree_ctrl.GetSelection()
        if selected_item.IsOk() is False:
            self.set_error_tips("还没有选中任何作业")
            return None
        
        task_id = self.tree_ctrl.GetItemData(selected_item)
        task = self.find_task(task_id)
        if not task:
            self.set_error_tips("请先选择一项作业")
            return None
        
        self.set_error_tips('')
        return task

    def on_goto_detail_btn_clicked(self, event):
        task = self.get_selected_task()
        if not task:
            return

        url = self.pack_url(f"/task/info/{task.id}/?" + urlencode({'uid': self.uid, 'secret': self.token}))
        webbrowser.open(url)
    
    def on_goto_add_btn_clicked(self, event):
        url = self.pack_url(f"/task/add/?" + urlencode({'uid': self.uid, 'secret': self.token}))
        webbrowser.open(url)

    def create_tomato(self, task: Task) -> int:
        ''' Get tomato id
        Returns:
            {"is_ok": True, "tomato_id": tomato.id}
        '''
        url = self.pack_url('/tomato/create/')
        params = {
            'task_id': task.id
        }
        r = self.request("GET", url, params=params)
        if not r:
            return 0 
        
        data = r.json()
        if data['is_ok'] is False:
            self.set_error_tips(data['reason'])
            return 0
        
        return data['tomato_id']
    
    def start_tomato(self, task: Task) -> dict:
        '''
        Returns:
            {
                "is_ok": True,
                "start": tomato.start_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                "end": end.strftime("%Y-%m-%d %H:%M:%S"),
                "left_seconds": left_seconds
            }
        '''
        url = self.pack_url('/tomato/start/')
        params = {
            'tomato_id': task.opening_tomato_id
        }
        r = self.request('GET', url, params=params)
        if not r:
            return {}
        data = r.json()
        if data['is_ok'] is False:
            self.set_error_tips(data['reason'])
            return {}
        
        return data
    
    def abandon_tomato(self, task: Task) -> int:
        ''' Abandon tomato
        Returns:
            int: abandon count
        '''
        url = self.pack_url('/tomato/abandon/')
        params = {
            'tomato_id': task.opening_tomato_id
        }
        r = self.request('GET', url, params=params)
        if not r:
            return 0
        data = r.json()
        if data['is_ok'] is False:
            self.set_error_tips(data['reason'])
            return 0
        
        return data['abandon_count']

    def harvest_tomato(self, task: Task) -> dict:
        '''Harvest tomato
        Returns:
            {
                "is_ok": True,
                "today_tomato_number": today_tomato_number,
                "task_tomato_number": task.tomato_number,
                "user_tomato_number": profile.left_tomato_number,
                "experience": ExperienceValue.HARVEST_TOMATO,
                "task_is_done": task.tomato_number >= task.expect_tomato_number,
            }
        '''
        url = self.pack_url('/tomato/harvest/')
        params = {
            'tomato_id': task.opening_tomato_id
        }
        r = self.request('GET', url, params=params)
        if not r:
            return {}
        data = r.json()
        if data['is_ok'] is False:
            self.set_error_tips(data['reason'])
            return {}
        
        return data


class MyTaskBarIcon(TaskBarIcon):

    def __init__(self, frame: MainFrame):
        super().__init__(iconType=TBI_DEFAULT_TYPE)
        self.frame = frame

        self.SetIcon(wx.Icon(settings.LOGO_PATH, wx.BITMAP_TYPE_ICON), settings.APP_NAME)

        self.Bind(wx.EVT_MENU, self.OnTaskBarActivate, id=2)
        self.Bind(wx.EVT_MENU, self.OnTaskBarDeactivate, id=3)
        self.Bind(wx.EVT_MENU, self.OnTaskBarClose, id=4)

    def CreatePopupMenu(self):
        menu = wx.Menu(settings.APP_NAME)
        idx = 1
        opening_task = self.frame.get_opening_task()
        if not opening_task:
            menu.Append(idx, "等待开番中")           
        else:
            menu.Append(idx, f"{opening_task.title} {self.frame.format_seconds(opening_task.opening_tomato_left_seconds)}")   

        menu.AppendSeparator()        

        idx += 1
        menu.Append(idx, '打开')

        idx += 1
        menu.Append(idx, '隐藏')

        idx += 1
        menu.Append(idx, '退出')

        return menu

    def OnTaskBarClose(self, event):
        self.frame.Close()

    def OnTaskBarActivate(self, event):
        if not self.frame.IsShown():
            self.frame.Show()
            self.frame.Raise()

    def OnTaskBarDeactivate(self, event):
        if self.frame.IsShown():
            self.frame.Hide()

        

if __name__ == "__main__":
    app = wx.App()
    main_frame = MainFrame(None, title="行恒", size=settings.APP_SIZE)
    app.MainLoop()