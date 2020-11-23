import re
import yaml
import wx.dataview
import wx.adv
import wx.grid

from utils import menu_bar, populate_menu, menu_item

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
        self._order_col = None
        self._order_reverse = None

    def sort_by(self, col):
        if self._order_col != col:
            self._order_col = col
            self._order_reverse = True
        else:
            self._order_reverse = not self._order_reverse

        def key(name):
            participant = self.contest.participants[name]
            if col==0:
                return participant.result.total()
            problem = self.contest.config.problems[col-1]
            if problem.name not in participant.result.problems:
                return -1
            return participant.result.problems[problem.name].total()

        self.ordered_names.sort(key=key, reverse=self._order_reverse)

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

    def get_participant(self, row):
        return self.contest.participants[self.ordered_names[row]]

    def get_problem(self, col):
        assert col>0
        return self.contest.config.problems[col-1]


class ProblemConfigDialog(wx.adv.PropertySheetDialog):
    def __init__(self, parent, problem):
        super().__init__(parent, wx.ID_ANY)
        self.problem = problem

        self.CreateButtons(wx.OK | wx.CANCEL)  # | wx.HELP)


class ScoreSheet(wx.grid.Grid):
    def __init__(self, parent, contest):
        super().__init__(parent)
        self.EnableEditing(False)
        # self.DisableDragRowSize()
        # self.DisableDragColSize()

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

        print('selectionforeground={}, cellbackground={}, '.format(self.GetSelectionForeground(), self.GetDefaultCellBackgroundColour()), flush=True)
        # self.SetSelectionForeground(wx.RED)
        self.SetCellHighlightPenWidth(0)  # no cursor border

        self._selection_change_handler = None

        self.GetGridWindow().Bind(wx.EVT_LEFT_DOWN, self.check_click)
        self.GetGridWindow().Bind(wx.EVT_CHAR, self.check_key)
        self.Bind(wx.grid.EVT_GRID_LABEL_LEFT_CLICK, self.label_left_click)
        self.Bind(wx.grid.EVT_GRID_LABEL_LEFT_DCLICK, self.label_left_click)
        self.Bind(wx.grid.EVT_GRID_LABEL_RIGHT_CLICK, self.label_right_click)
        self.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.label_right_click)

    def sort_by(self, col):
        self.GetTable().sort_by(col)
        self.ForceRefresh()

    def label_left_click(self, ev):
        if ev.GetCol() != 0:
            ev.Skip()
            return

        self.sort_by(ev.GetCol())

    def label_right_click(self, ev):
        menu = wx.Menu()
        menu.Append(menu_item(self, "Sort by this column", lambda ev: self.sort_by(col)))
        col = ev.GetCol()
        if col > 0:
            menu.Append(menu_item(self, "Configure this problem", lambda ev: ProblemConfigDialog(self, self.GetTable().contest.config.problems[col-1]).ShowModal()))
        self.PopupMenu(menu)

    def check_click(self, ev):
        cell = self.XYToCell(self.CalcUnscrolledPosition(ev.GetPosition()))
        if cell[0] < 0:
            self.ClearSelection()
        ev.Skip()

    def check_key(self, ev):
        if ev.GetKeyCode() == wx.WXK_CONTROL_A:
            self.SelectAll()
        ev.Skip()

    def dodge_first_column(self, row):
        if self.__table.GetNumberCols() > 1:
            self.SetGridCursor(row, 1)

    def check_select_cell(self, ev):
        if ev.Selecting() and ev.GetCol()==0:
            ev.Veto()
            self.dodge_first_column(ev.GetRow())
            return

        if not self.IsSelection():
            self.SelectBlock(ev.GetRow(), ev.GetCol(), ev.GetRow(), ev.GetCol())

    def check_select_range(self, ev):
        if ev.Selecting() and ev.GetLeftCol()==0:
            # ev.Veto()   # not working
            self.DeselectCol(0)
            return

        self._selection_change_handler(self.IsSelection())
        if not self.IsSelection():
            self._focus_changed(None)
        elif ev.GetLeftCol()==ev.GetRightCol() and ev.GetTopRow()==ev.GetBottomRow():
            self._focus_changed((self.__table.get_participant(ev.GetTopRow()), self.__table.get_problem(ev.GetLeftCol())))

    def get_selected(self):
        selected_cells = []
        if self.IsSelection():
            for tl, br in zip(self.GetSelectionBlockTopLeft(), self.GetSelectionBlockBottomRight()):
                for i in range(tl.GetRow(), br.GetRow()+1):
                    for j in range(tl.GetCol(), br.GetCol()+1):
                        selected_cells.append((i,j))
            selected_cells.sort()
        else:
            selected_cells.append((self.GetGridCursorRow(), self.GetGridCursorCol()))

        return ((i, j, self.__table.get_participant(i), self.__table.get_problem(j)) for i,j in selected_cells)

# not working
#    def process_mouse(self, ev):
#        print(ev.GetPosition(), self.CalcUnscrolledPosition(ev.GetPosition()), flush=True)


class TestCase:
    def __init__(self, input_file_path, output_file_path):
        self.input_file_path = input_file_path
        self.output_file_path = output_file_path


class Problem:
    def __init__(self, data_path, data):
        if isinstance(data, str):
            self.name = data
            self.tmp_testcases = []

            data_path /= self.name
            if not data_path.is_dir():
                return

            input_file_paths = set(data_path.glob(self.name+'*.in')) & {p.with_suffix('.in') for p in data_path.glob(self.name+'*.out')}
            input_file_paths = sorted(input_file_paths, key=lambda s: re.split(r'(\d+)', s.name))
            self.tmp_testcases = [TestCase(i, i.with_suffix('.out')) for i in input_file_paths]
        else:
            raise NotImplementedError

    def get_testcases(self):
        return self.tmp_testcases

    def __repr__(self):
        return '<Problem {}>'.format(self.name)


class ContestConfig:
    def __init__(self, contest_path, data):
        self.problems = [Problem(contest_path/DATA_DIR_NAME, p) for p in data]

    def dump(self, path):
        raise NotImplementedError


class ProblemResult:
    def __init__(self, data):
        self.data = data
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

    def remove_problem(self, name):
        if name not in self.problems:
            return
        self._score -= self.problems[name].total()
        del self.problems[name]

    def set_problem(self, name, r):
        self.remove_problem(name)
        self.problems[name] = r
        self._score += r.total()


class Participant:
    def __init__(self, path):
        self.name = path.name
        self.path = path
        if (path/RESULT_FILE_NAME).exists():
            self.result = Result.from_path(path/RESULT_FILE_NAME)
        else:
            self.result = Result.fresh()

    def __repr__(self):
        return '<Participant {}>'.format(self.name)
        

class Contest:
    singleton = None

    def __init__(self, path, config):
        self.path = path
        self.config = config
        self.participants = {p.name: Participant(p) for p in (path/SRC_DIR_NAME).iterdir()}

    @staticmethod
    def init_and_open(path):
        assert (path/DATA_DIR_NAME).is_dir()

        problem_names = []
        for sub in (path/DATA_DIR_NAME).iterdir():
            if not sub.is_dir():
                raise ContestError('not a directory: {}'.format(sub))
            if not Contest.is_valid_name(sub.name):
                raise ContestError('not a valid name: {}'.format(sub.name))
            problem_names.append(sub.name)

        config = ContestConfig(path, problem_names)
        config.dump(path / CONTEST_CONFIG_FILE_NAME)
        Contest.singleton = Contest(path, config)

    @staticmethod
    def open(path):
        with open(path/CONTEST_CONFIG_FILE_NAME) as f:
            data = yaml.load(f, Loader=yaml.CLoader)
        config = ContestConfig(path, data)
        Contest.singleton = Contest(path, config)

    @staticmethod
    def close():
        # TODO: stop watching data and src
        Contest.singleton = None


class ContestError(Exception):
    pass
