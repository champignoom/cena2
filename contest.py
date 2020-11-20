import yaml
import wx.dataview
import wx.grid


DATA_DIR_NAME = 'data'
SRC_DIR_NAME = 'src'
SAMPLE_DIR_NAME = 'sample'
PROBLEMS_FILE_NAME = 'problems.pdf'
CONTEST_CONFIG_FILE_NAME = 'config.yaml'


class MyRenderer(wx.grid.GridCellRenderer):
    def Draw(self, grid, attr, dc, rect, row, col, is_selected):
        dc.SetPen(wx.Pen())
        dc.SetBrush(wx.LIGHT_GREY_BRUSH)
        dc.DrawRectangle(rect.GetPosition(), rect.GetSize().Scale(0.8, 1))
        BORDER_WIDTH = 3
        dc.SetPen(wx.Pen(wx.WHITE if not is_selected else wx.BLACK, width=BORDER_WIDTH))
        dc.SetBrush(wx.NullBrush)
        dc.DrawRectangle(rect)
        dc.DrawLabel('{:.2f}'.format(grid.GetTable().GetValue(row, col)), rect, wx.ALIGN_CENTER)


class MyGridTable(wx.grid.GridTableBase):
    def GetNumberRows(self):
        return 30

    def GetNumberCols(self):
        return 5

    def GetRowLabelValue(self, row):
        return ('John', 'Bob', 'Alice')[row%3]

    def GetColLabelValue(self, col):
        return 'Problem {}'.format(col)

    def GetValue(self, row, col):
        return (row+1)/(col+1)

    def SetValue(self, row, col, value):
        pass


class ContestConfig:
    def __init__(self):
        pass

    @staticmethod
    def from_names(names):
        # FIXME
        pass

    @staticmethod
    def from_file(path):
        # FIXME
        pass


class Contest:
    singleton = None

    def __init__(self, path, config):
        self._path = path
        self.config = config

    @staticmethod
    def init_and_open(path):
        assert (path/DATA_DIR_NAME).is_dir()

        problem_names = []
        for sub in (path/DATA_DIR_NAME).iterdir():
            if not sub.is_dir():
                raise ContestConfig('not a directory: {}'.format(sub))
            if not Contest.is_valid_name(sub.name):
                raise ContestConfig('not a valid name: {}'.format(sub.name))
            problem_names.append(sub.name)

        config = ContestConfig.from_names(problem_names)
        Contest.singleton = Contest(path, config)

    @staticmethod
    def open(path):
        config = ContestConfig.from_file(path / CONTEST_CONFIG_FILE_NAME)
        Contest.singleton = Contest(path, config)

    @staticmethod
    def close():
        # TODO: stop watching data and src
        Contest.singleton = None

    @staticmethod
    def _fake_data_view(parent):
        ctrl = wx.dataview.DataViewListCtrl(parent)
        ctrl.AppendTextColumn('name')
        ctrl.AppendProgressColumn('problem1')
        ctrl.AppendProgressColumn('problem2')
        ctrl.AppendProgressColumn('problem3')
        ctrl.AppendProgressColumn('problem4')

        ctrl.AppendItem(['John', 10, 40, 20, 30])
        ctrl.AppendItem(['Bob', 100, 20, 70, 50])
        ctrl.AppendItem(['Alice', 10, 40, 20, 33])
        ctrl.AppendItem(['David', 90, 60, 28, 40])
        return ctrl

    @staticmethod
    def _fake_grid(parent):
        grid = wx.grid.Grid(parent)
        grid.EnableEditing(False)
        grid.DisableDragRowSize()
        grid.DisableDragColSize()
        # grid.DisableDragGridSize()

        grid.SetCornerLabelValue("I'm corner")

        # grid.CreateGrid(3, 3)
        # grid.SetColLabelValue(0, "Total")
        # grid.SetColLabelValue(1, "Problem 1")
        # grid.SetColLabelValue(2, "Problem 2")
        # grid.SetColLabelValue(3, "Problem 3")
        # grid.SetColLabelValue(4, "Problem 4")

        # grid.SetRowLabelValue(0, "John")
        # grid.SetRowLabelValue(1, "Bob")
        # grid.SetRowLabelValue(2, "Alice")
        
        grid.SetTable(MyGridTable(), True)

        grid.SetDefaultRenderer(MyRenderer())
        
        grid.SetSelectionForeground(wx.BLACK)
        grid.SetGridLineColour(wx.WHITE)
        # grid.UseNativeColHeader(True) # get rid of the annoying border around the first column header
        return grid


class ContestException(Exception):
    pass
