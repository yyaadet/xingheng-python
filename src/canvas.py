import wx
import math
import random

import logging


logger = logging.getLogger(__name__)


class Canvas(wx.Panel):
    DEFAULT_SECONDS = 25*60

    def __init__(self, parent, seconds, color, title):
        super().__init__(parent)
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.Bind(wx.EVT_PAINT, self.OnPaint)

        self.seconds = seconds
        if self.seconds <= 0:
            self.seconds = self.DEFAULT_SECONDS
        self.color = color
        self.left_seconds = self.seconds
        self.title = title

    def set_seconds(self, seconds):
        self.seconds = seconds
        if self.seconds <= 0:
            self.seconds = self.DEFAULT_SECONDS
        self.Refresh()

    def update(self, left_seconds, title=None):
        self.left_seconds = left_seconds
        if title:
            self.title = title
        self.Refresh()

    def OnPaint(self, evt):
        w, h = self.GetClientSize()
        dc = wx.AutoBufferedPaintDC(self)
        dc.Clear()

        gc: wx.GraphicsContext = dc.GetGraphicsContext()

        #gc.SetBrush(wx.Brush(wx.WHITE))
        #gc.DrawRectangle(0, 0, w, h)

        gc.SetPen(wx.Pen(self.color, width=2))
        gc.SetBrush(wx.Brush(self.color))

        logger.info(f"left seconds {self.left_seconds}, seconds {self.seconds}")
        rect_height = h * (self.seconds - self.left_seconds) / self.seconds
        y = h - rect_height
        gc.DrawRectangle(0, y, w, rect_height)
        
        # write text
        font_size = 200
        while True:
            font = wx.Font(int(font_size), wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
            gc.SetFont(font, wx.WHITE)
            text_width, text_height = dc.GetTextExtent(self.title)
            if text_width > w *0.6:
                font_size = 0.9 * font_size
            else:
                break
        
        gc.SetFont(font, wx.WHITE)
        gc.SetPen(wx.Pen(wx.WHITE, width=2))
        text_width, text_height = dc.GetTextExtent(self.title)
        logger.info(f"final font size {font_size}, text ({text_width}, {text_height}), screen ({w}, {h})")
        title_y = h / 2 - text_height / 2
        title_x = w / 2  - text_width / 2
        gc.DrawText(self.title, title_x, title_y)
