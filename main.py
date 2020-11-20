import wx
import wx.dataview
from pathlib import Path
from contest import (
        Contest, ContestError, ScoreSheet,
        DATA_DIR_NAME, SRC_DIR_NAME, CONTEST_CONFIG_FILE_NAME,
        )


def menu_bar(menus):
    bar = wx.MenuBar()
    for menu in menus:
        bar.Append(_populate_menu(menu[1]), menu[0])
    return bar


def _populate_menu(items):
    menu = wx.Menu()
    for item in items:
        if isinstance(item, tuple):
            menu.AppendSubMenu(_populate_menu(item[1]), item[0])
        elif isinstance(item, wx.MenuItem):
            menu.Append(item)
        else:
            raise ValueError('unsupported menu item type: {}'.format(item))
    return menu


class MainFrame(wx.Frame):
    TITLE = 'Cena2'
    SIZE = (800, 600)

    def menu_item(self, text, handler=None):
        item = wx.MenuItem(id=wx.ID_ANY, text=text);
        if handler is not None:
            self.Bind(wx.EVT_MENU, handler, item)
        return item

    def __init__(self):
        super().__init__(None, title=MainFrame.TITLE, size=MainFrame.SIZE)

        # Menu bar
        self.SetMenuBar(menu_bar([
            ('&File', [
                self.menu_item('&Open contest', handler=self._open_contest),
                self.menu_item('&Close contest', handler=self._close_contest),
                wx.MenuItem(),
                self.menu_item('&Properties', handler=self._properties),
                ]),
            ('&Contest', [
                self.menu_item('&Participate', handler=self._participate_contest),
                self.menu_item('&Host', handler=self._host_contest),
                ]),
            ('&Help', [
                self.menu_item('&Manual', handler=self._show_manual),
                self.menu_item('&About', handler=self._show_about),
                ]),
            ]))

    def _open_contest_prepare(self):
        if False:
            dialog = wx.DirDialog(self, defaultPath=".")
            dialog.ShowModal()
            path = dialog.GetPath()
        else:
            path = './sample_contest'

        if not path:
            return

        path = Path(path)
        for subdir in (DATA_DIR_NAME, SRC_DIR_NAME):
            if not (path/subdir).is_dir():
                wx.MessageBox("Dir '{}' not found in {}".format(subdir, path), style=wx.ICON_ERROR)
                return

        if not (path/CONTEST_CONFIG_FILE_NAME).exists():
            yes_no = wx.MessageBox('No config found. Do you want to create a contest here?', style=wx.YES_NO)
            if yes_no == wx.NO:
                return

            Contest.init_and_open(path)
            return

        Contest.open(path)

    def _open_contest(self, ev):
        try:
            self._open_contest_prepare()
        except ContestError:
            pass
        else:
            self._render_contest()

    def _render_contest(self):
        self.SetSizer(wx.BoxSizer(wx.VERTICAL))

        splitter_window = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE | wx.SP_BORDER)
        self.GetSizer().Add(splitter_window, wx.SizerFlags(1).Expand().Border(wx.ALL, 10))

        self._score_sheet = ScoreSheet(splitter_window, Contest.singleton)
        self._score_sheet.SetMinSize((0,0))  # otherwise it grows greedly
        splitter_window.Initialize(self._score_sheet)

        tmp_panel = wx.Panel(splitter_window)
        tmp_panel.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
        self.status_box = wx.StaticBox(tmp_panel)
        self.status_box.SetMinSize((0,40))
        tmp_panel.GetSizer().Add(self.status_box, wx.SizerFlags(1).Expand().Border(wx.RIGHT, 5))
        btn_sizer = wx.BoxSizer(wx.VERTICAL)
        tmp_panel.GetSizer().Add(btn_sizer, wx.SizerFlags(0).Expand())
        self.btn_judge_selected = wx.Button(tmp_panel, label="Judge selected")
        btn_sizer.AddSpacer(10)
        btn_sizer.Add(self.btn_judge_selected)

        splitter_window.SplitHorizontally(self._score_sheet, tmp_panel, -60)

        self.Layout()

    def _close_contest(self, ev):
        # TODO: disable the menu item after closing contest
        Contest.close()
        self._contest_panel.Destroy()

    def _properties(self, ev):
        raise NotImplementedError

    def _participate_contest(self, ev):
        raise NotImplementedError

    def _host_contest(self, ev):
        raise NotImplementedError

    def _show_manual(self, ev):
        raise NotImplementedError

    def _show_about(self, ev):
        raise NotImplementedError


def main():
    app = wx.App()
    main_frame = MainFrame()
    main_frame.Show()
    app.MainLoop()


if __name__=='__main__':
    main()
