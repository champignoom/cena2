import yaml
import wx.dataview
import wx.grid


DATA_DIR_NAME = 'data'
SRC_DIR_NAME = 'src'
SAMPLE_DIR_NAME = 'sample'
PROBLEMS_FILE_NAME = 'problems.pdf'
CONTEST_CONFIG_FILE_NAME = 'config.yaml'
RESULT_FILE_NAME = 'result.yaml'


class MyRenderer(wx.grid.GridCellRenderer):
    BORDER_WIDTH = 3

    def __init__(self, table):
        super().__init__()
        self.__table = table

    def Draw(self, grid, attr, dc, rect, row, col, is_selected):
        pen_width = 3
        # is_selected = is_selected and self.__table.is_selectable(row, col)

        dc.SetPen(wx.Pen())
        color = grid.GetSelectionBackground() if is_selected else attr.GetBackgroundColour()
        dc.SetBrush(wx.Brush(color))
        dc.DrawRectangle(rect)

        r = grid.GetTable().GetValue(row, col)
        if not is_selected:
            inner_rect = wx.Rect(rect.GetX()+pen_width, rect.GetY()+pen_width, rect.GetWidth()-2*pen_width, rect.GetHeight()-2*pen_width)
            dc.SetBrush(wx.LIGHT_GREY_BRUSH)
            dc.DrawRectangle(inner_rect.GetPosition(), inner_rect.GetSize().Scale(r[0], 1))

        dc.SetTextForeground(grid.GetSelectionForeground() if is_selected else attr.GetTextColour())
        dc.DrawLabel(r[1], rect, wx.ALIGN_CENTER)


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


class ScoreGridTable(wx.grid.GridTableBase):
    def __init__(self, contest):
        super().__init__()
        self.contest = contest
        self.ordered_names = sorted(contest.participants.keys())

    def GetNumberRows(self):
        return len(self.ordered_names)

    def GetNumberCols(self):
        return 1 + len(self.contest.config.problems)  # col 0: total score

    def GetRowLabelValue(self, row):
        return self.ordered_names[row]

    def GetColLabelValue(self, col):
        return 'Total' if col==0 else self.contest.config.problems[col-1].name

    def GetValue(self, row, col):
        r = self.contest.participants[self.ordered_names[row]].result
        if col==0:
            return (r.total()/400., str(r.total()))
        else:
            name = self.contest.config.problems[col-1].name
            try:
                score = r.problems[name].total()
            except KeyError:
                return (0., '-')
            return (score/100, str(score))

    def is_selectable(self, row, col):
        return col>0


class ScoreSheet(wx.grid.Grid):
    def __init__(self, parent, contest):
        super().__init__(parent)
        self.EnableEditing(False)
        self.DisableDragRowSize()
        self.DisableDragColSize()

        self.SetCornerLabelValue("I'm corner")

        self.__table = ScoreGridTable(contest)
        self.SetTable(self.__table, True)
        self.SetColSize(0, self.GetColSize(0)*1.5)

        self.SetDefaultRenderer(MyRenderer(self.__table))
        self.dodge_first_column(0)
        
        # self.SetSelectionForeground(self.GetCellHighlightColour())  # otherwise transparent selection border
        self.EnableGridLines(False)

        self.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.check_select_cell)
        self.Bind(wx.grid.EVT_GRID_RANGE_SELECT, self.check_select_range)
        # self.Bind(wx.EVT_LEFT_DOWN, self.process_mouse)

    def dodge_first_column(self, row):
        if self.__table.GetNumberCols() > 1:
            self.SetGridCursor(row, 1)

    def check_select_cell(self, ev):
        if ev.Selecting() and ev.GetCol()==0:
            ev.Veto()
            self.dodge_first_column(ev.GetRow())

    def check_select_range(self, ev):
        if ev.Selecting() and ev.GetLeftCol()==0:
            # ev.Veto()   # not working
            self.DeselectCol(0)

# not working
#    def process_mouse(self, ev):
#        print(ev.GetPosition(), self.CalcUnscrolledPosition(ev.GetPosition()), flush=True)

class Problem:
    def __init__(self, data):
        if isinstance(data, str):
            self.name = data
        else:
            raise NotImplementedError


class ContestConfig:
    def __init__(self, data):
        self.problems = [Problem(p) for p in data]

    def dump(self, path):
        raise NotImplementedError

    @staticmethod
    def from_names(names):
        return ContestConfig(names)

    @staticmethod
    def from_file(path):
        with open(path) as f:
            data = yaml.load(f, Loader=yaml.CLoader)
        return ContestConfig(data)


class ProblemResult:
    def __init__(self, data):
        if isinstance(data, str):
            self._score = 0
        elif isinstance(data, list):
            self._score = 10 * data.count('Accepted')
        else:
            raise ContestError("Invalid result type: {}".format(type(data)))

    def total(self):
        return self._score


class Result:
    def __init__(self, data):
        self.problems = data
        self._score = sum(v.total() for _,v in self.problems.items())

    @staticmethod
    def from_path(path):
        # TODO: check yaml exception
        with open(path) as f:
            data = yaml.load(f, Loader=yaml.CLoader)

        if data is None:
            return Result.fresh()

        return Result({k: ProblemResult(v) for k,v in data.items()})

    @staticmethod
    def fresh():
        return Result({})

    def total(self):
        return self._score


class Participant:
    def __init__(self, path):
        self.name = path.name
        self.path = path
        if (path/RESULT_FILE_NAME).exists():
            self.result = Result.from_path(path/RESULT_FILE_NAME)
        else:
            self.result = Result.fresh()
        

class Contest:
    singleton = None

    def __init__(self, path, config):
        self._path = path
        self.config = config
        self.participants = {p.name: Participant(p) for p in (path/SRC_DIR_NAME).iterdir()}

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
        config.dump(path)
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


class ContestError(Exception):
    pass
