import wx


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
    SIZE = (350, 250)

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
                self.menu_item('&Open contest'),
                self.menu_item('&Close contest'),
                self.menu_item('&Properties'),
                ]),
            ('&Contest', [
                self.menu_item('&Participate'),
                self.menu_item('&Host'),
                ]),
            ('&Help', [
                self.menu_item('&Manual'),
                self.menu_item('&About'),
                ]),
            ]))


def main():
    app = wx.App()
    main_frame = MainFrame()
    main_frame.Show()
    app.MainLoop()


if __name__=='__main__':
    main()
