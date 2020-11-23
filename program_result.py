# matrix of squares

import wx


class ProgramResultBar(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent, wx.ID_ANY)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(sizer)

    def clear_bar(self):
        # TODO: avoid frequent creation/removal of children
        self.GetSizer().Clear(True)
        self.blocks = None

    def set_message(self, text):
        self.clear_bar()
        self.GetSizer().AddStretchSpacer()
        self.GetSizer().Add(wx.StaticText(self, wx.ID_ANY, text), wx.SizerFlags().Center())
        self.GetSizer().AddStretchSpacer()
        self.Layout()

    def set_block_size(self, size):
        raise NotImplementedError

    def make_placeholders(self, n):
        # TODO: check size
        self.clear_bar()
        self.blocks = []
        self.GetSizer().AddStretchSpacer()

        for i in range(n):
            if i>0 and i%5==0:
                self.GetSizer().AddSpacer(10)

            self.blocks.append(wx.Window(self, wx.ID_ANY, size=(20,20), style=wx.BORDER_RAISED))
            # tmp_window.SetBackgroundColour(result_color['Runtime Error'])
            self.GetSizer().Add(self.blocks[-1], wx.SizerFlags().Center().Border(wx.ALL, 1))

        self.GetSizer().AddStretchSpacer()

        self.Layout()

    def set_nth(self, n, color):
        self.blocks[n].SetBackgroundColour(color)


class TestcaseResultBlock(wx.Window):
    pass


result_color = {
        # predefined colors (wx.RED, wx.GREEN, ...) are not initialized until wx.App()
        'Accepted': wx.Colour(0, 255, 0),
        'Wrong Answer': wx.Colour(255, 0, 0),
        'Runtime Error': wx.Colour(255, 100, 100),
        'Time Limit Exceeded': wx.Colour(200, 200, 0),
        'Memory Limit Exceeded': wx.Colour(150, 150, 0),
        'Output Not Found': wx.Colour(200, 200, 200),
        }
