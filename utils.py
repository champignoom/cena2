import wx


def menu_bar(menus):
    bar = wx.MenuBar()
    for menu in menus:
        bar.Append(populate_menu(menu[1]), menu[0])
    return bar


def populate_menu(items):
    menu = wx.Menu()
    for item in items:
        if isinstance(item, tuple):
            menu.AppendSubMenu(populate_menu(item[1]), item[0])
        elif isinstance(item, wx.MenuItem):
            menu.Append(item)
        else:
            raise ValueError(f'unsupported menu item type: {item}')
    return menu


def menu_item(self, text, handler=None):
    item = wx.MenuItem(id=wx.ID_ANY, text=text);
    if handler is not None:
        self.Bind(wx.EVT_MENU, handler, item)
    return item

