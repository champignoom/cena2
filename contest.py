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

CONFIG_TIME_LIMIT = 'time limit'
CONFIG_MEMORY_LIMIT = 'memory limit'
CONFIG_TOTAL_SCORE = 'total score'
CONFIG_CN_NAME = 'chinese name'


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
        if col==0:
            return 'Total'
        p = self.contest.config.problems[col-1]
        return p.name if p.cn_name is None else p.cn_name

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


class ProblemConfigDialog(wx.Dialog):
    def __init__(self, parent, problem):
        super().__init__(parent, wx.ID_ANY, style=wx.RESIZE_BORDER, title=f"Problem Config: {problem.name}")
        self.problem = problem

        sizer = wx.BoxSizer(wx.VERTICAL)
        panel = wx.Panel(self, wx.ID_ANY)
        sizer.Add(panel, wx.SizerFlags(1).Expand().Border(wx.ALL, 5))

        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        grid_sizer = wx.FlexGridSizer(2, 10, 10)

        # TODO: validators

        grid_sizer.Add(wx.StaticText(panel, wx.ID_ANY, "Name"), wx.SizerFlags().Right().CenterVertical())
        self._name_ctrl = wx.TextCtrl(panel, wx.ID_ANY, value=self.problem.name)
        grid_sizer.Add(self._name_ctrl)

        grid_sizer.Add(wx.StaticText(panel, wx.ID_ANY, "Chinese name"), wx.SizerFlags().Right().CenterVertical())
        self._cn_name_ctrl = wx.TextCtrl(panel, wx.ID_ANY, value=self.problem.cn_name or "")
        grid_sizer.Add(self._cn_name_ctrl)

        grid_sizer.Add(wx.StaticText(panel, wx.ID_ANY, "Time limit"), wx.SizerFlags().Right().CenterVertical())
        time_limit_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._time_limit_ctrl = wx.TextCtrl(panel, wx.ID_ANY, value=str(self.problem.time_limit or ""))
        self._time_limit_ctrl.SetHint("1")
        time_limit_sizer.Add(self._time_limit_ctrl)
        time_limit_sizer.Add(wx.StaticText(panel, wx.ID_ANY, label="s"), wx.SizerFlags().CenterVertical().Border(wx.LEFT, 5))
        grid_sizer.Add(time_limit_sizer)

        grid_sizer.Add(wx.StaticText(panel, wx.ID_ANY, "Memory limit"), wx.SizerFlags().Right().CenterVertical())
        memory_limit_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._memory_limit_ctrl = wx.TextCtrl(panel, wx.ID_ANY, value=str(self.problem.memory_limit or ""))
        self._memory_limit_ctrl.SetHint("512")
        memory_limit_sizer.Add(self._memory_limit_ctrl)
        memory_limit_sizer.Add(wx.StaticText(panel, wx.ID_ANY, "MB"), wx.SizerFlags().CenterVertical().Border(wx.LEFT, 5))
        grid_sizer.Add(memory_limit_sizer)

        grid_sizer.Add(wx.StaticText(panel, wx.ID_ANY, "Total score"), wx.SizerFlags().Right().CenterVertical())
        self._total_score_ctrl = wx.TextCtrl(panel, wx.ID_ANY, value=str(self.problem.total_score or ""))
        self._total_score_ctrl.SetHint("100")
        grid_sizer.Add(self._total_score_ctrl)

        grid_sizer.Add(wx.StaticText(panel, wx.ID_ANY, "Testcases"), wx.SizerFlags().Right().CenterVertical())
        grid_sizer.Add(wx.StaticText(panel, wx.ID_ANY, "<Not Implemented>"))
        panel_sizer.Add(grid_sizer, wx.SizerFlags(1).Expand())
        panel.SetSizer(panel_sizer)

        sizer.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), wx.SizerFlags(0).Expand().Border(wx.ALL, 5))

        self.SetSizerAndFit(sizer)

        self.Bind(wx.EVT_BUTTON, self.__on_ok, id=wx.ID_OK)

    def __on_ok(self, ev):
        if self.__save_config():
            self.Close()

    def __save_config(self):
        """
        Return True if sucessfully saved.
        Otherwise return False and the dialog is supposed to be preservedd.
        """
        new_name = self._name_ctrl.GetValue()
        if new_name and new_name != self.problem.name and Contest.singleton.config.exist_problem_with_name(new_name):
            wx.MessageBox(f"Problem {new_name} already exists")
            return False

        try:
            self.problem.name         = None if self._name_ctrl.IsEmpty()         else self._name_ctrl.GetValue()
            self.problem.cn_name      = None if self._cn_name_ctrl.IsEmpty()      else self._cn_name_ctrl.GetValue()
            self.problem.time_limit   = None if self._time_limit_ctrl.IsEmpty()   else float(self._time_limit_ctrl.GetValue())
            self.problem.memory_limit = None if self._memory_limit_ctrl.IsEmpty() else float(self._memory_limit_ctrl.GetValue())
            self.problem.total_score  = None if self._total_score_ctrl.IsEmpty()  else int(self._total_score_ctrl.GetValue())
            # FIXME: exclude negative value
        except (TypeError, ValueError) as e:
            wx.MessageBox(str(e))
            return False

        Contest.singleton.save_config()

        return True


        # time limit
        # memory limit
        # chinese name
        # name
        # total score
        # (show autodetected testcases, update when name is modified, or:)
        # testcases
        #   input, output, score


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

        # self.SetSelectionForeground(wx.RED)
        self.SetCellHighlightPenWidth(0)  # no cursor border

        self._selection_change_handler = None

        self.GetGridWindow().Bind(wx.EVT_LEFT_DOWN, self.check_click)
        self.GetGridWindow().Bind(wx.EVT_CHAR, self.check_key)
        self.Bind(wx.grid.EVT_GRID_LABEL_LEFT_CLICK, self.label_left_click)
        self.Bind(wx.grid.EVT_GRID_LABEL_LEFT_DCLICK, self.label_left_click)
        self.Bind(wx.grid.EVT_GRID_LABEL_RIGHT_CLICK, self.label_right_click)
        # self.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.label_right_click)

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
            self.__assign_vals()
        elif isinstance(data, dict):
            if len(data)!=1:
                raise ContestError
            self.name = list(data.keys())[0]
            if not isinstance(self.name, str) or not re.fullmatch(r'[a-z]+', self.name):
                raise ContestError(f"wrong name format: {self.name}")
            val = data[self.name] or {}
            self.__assign_vals(
                    cn_name = val.get(CONFIG_CN_NAME),
                    time_limit = val.get(CONFIG_TIME_LIMIT),
                    memory_limit = val.get(CONFIG_MEMORY_LIMIT),
                    total_score = val.get(CONFIG_TOTAL_SCORE),
                    )
            # TODO: warn extra arguments
        else:
            raise ContestError

        self.tmp_testcases = []

        data_path /= self.name
        if not data_path.is_dir():
            return

        input_file_paths = set(data_path.glob(self.name+'*.in')) & {p.with_suffix('.in') for p in data_path.glob(self.name+'*.out')}
        input_file_paths = sorted(input_file_paths, key=lambda s: re.split(r'(\d+)', s.name))
        self.tmp_testcases = [TestCase(i, i.with_suffix('.out')) for i in input_file_paths]

    def __assign_vals(self, /, cn_name=None, time_limit=None, memory_limit=None, total_score=None):
        self.cn_name = cn_name
        self.time_limit = time_limit and float(time_limit)
        self.memory_limit = memory_limit and float(memory_limit)
        self.total_score = total_score and int(total_score)

    def get_testcases(self):
        return self.tmp_testcases

    def to_dict(self):
        # TODO: testcases
        d = {
                CONFIG_CN_NAME: self.cn_name,
                CONFIG_TIME_LIMIT: self.time_limit,
                CONFIG_MEMORY_LIMIT: self.memory_limit,
                CONFIG_TOTAL_SCORE: self.total_score,
                }
        d = {k:v for k,v in d.items() if v is not None}
        return self.name if not d else {self.name: d}

    def __repr__(self):
        return '<Problem {}>'.format(self.name)


class ContestConfig:
    def __init__(self, contest_path, data):
        self.problems = [Problem(contest_path/DATA_DIR_NAME, p) for p in data]

    def exist_problem_with_name(self, name):
        return any(p.name == new_name for p in self.problems)

    def to_dict(self):
        return [p.to_dict() for p in self.problems]


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

    def save_config(self):
        with open(self.path/CONTEST_CONFIG_FILE_NAME, 'w') as f:
            yaml.dump(self.config.to_dict(), f, Dumper=yaml.CDumper, encoding='utf-8', allow_unicode=True)

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
        Contest.singleton = Contest(path, config)
        Contest.singleton.save_config()

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
