import wx
import wx.dataview
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import subprocess
import filecmp
import time
import shutil
import resource
from contest import (
        Contest, ContestError, ScoreSheet,
        ProblemResult,
        DATA_DIR_NAME, SRC_DIR_NAME, CONTEST_CONFIG_FILE_NAME,
        )
from program_result import (ProgramResultBar, result_color)


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

        1 and wx.CallAfter(lambda: self._open_contest(None))

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

        self.splitter_window = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE | wx.SP_BORDER)
        self.GetSizer().Add(self.splitter_window, wx.SizerFlags(1).Expand().Border(wx.ALL, 10))

        self._score_sheet = ScoreSheet(self.splitter_window, Contest.singleton)
        self._score_sheet.SetMinSize((0,0))  # otherwise it grows greedly
        self.splitter_window.Initialize(self._score_sheet)

        lower_panel = wx.Panel(self.splitter_window)
        lower_panel.SetSizer(wx.BoxSizer(wx.HORIZONTAL))

        self.status_panel = ProgramResultBar(lower_panel)
        lower_panel.GetSizer().Add(self.status_panel, wx.SizerFlags(1).Expand().Border(wx.TOP|wx.RIGHT, 5))

        self.btn_judge_selected = wx.Button(lower_panel, label="Judge selected")
        self.btn_judge_selected.Disable()
        self.Bind(wx.EVT_BUTTON, self._test_selected, self.btn_judge_selected)
        lower_panel.GetSizer().Add(self.btn_judge_selected, wx.SizerFlags(0).Border(wx.TOP, 5))

        self.status_panel.Bind(wx.EVT_LEFT_DOWN, self._click_status_box)
        self._score_sheet._selection_change_handler = self.btn_judge_selected.Enable

        self.splitter_window.SplitHorizontally(self._score_sheet, lower_panel)
        # status_box.SetBackgroundColour(wx.RED)
        self.Layout()

        self._lower_height = self.btn_judge_selected.GetSize()[1] + 5
        self.splitter_window.SetSashPosition(-self._lower_height - self.splitter_window.GetSashSize())
        self.Layout()

        self.Bind(wx.EVT_SIZE, self._on_resize) 

    def _on_resize(self, ev):
        # self.splitter_window.SetSashPosition( -self.btn_judge_selected.GetSize()[1] - self.splitter_window.GetSashSize() - 5)
        self.splitter_window.SetSashPosition(-self._lower_height - self.splitter_window.GetSashSize())
        self.Layout()

    def _click_status_box(self, ev):
        self._score_sheet.ClearSelection()

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

    class TestSelectedThread(threading.Thread):
        def __init__(self, frame):
            super().__init__()
            self.frame = frame

        def run(self):
            # TODO: fake modal: intercept clicks unless clicking 'cancel testing'
            # TODO: use another thread to avoid blocking
            # resource.setrlimit(resource.RLIMIT_CORE, (0, 0))   # not helping much
            with TemporaryDirectory(prefix="cena2") as tmp_dir:
                tmp_dir = Path(tmp_dir)
                for i, j, participant, problem in self.frame._score_sheet.get_selected():
                    self.frame._judge_program(tmp_dir, participant, problem)
                    assert len(list(tmp_dir.iterdir()))==0
                    wx.CallAfter(self.frame._score_sheet.DeselectCell, i, j)
            # TODO: cancel fake modal

    def _test_selected(self, ev):
        self.test_thread = MainFrame.TestSelectedThread(self)
        self.test_thread.start()

    def _judge_program(self, test_dir, participant, problem):
        # print('testing', test_dir, participant, problem, flush=True)
        participant.result.remove_problem(problem.name)
        wx.CallAfter(self.status_panel.set_message, "Compiling ...")
        error = self._prepare_program(test_dir, participant, problem)
        if error is not None:
            print(test_dir, participant, problem, error, flush=True)
            participant.result.set_problem(problem.name, ProblemResult(error))
            wx.CallAfter(self.status_panel.set_message, error)
        else:
            testcases = problem.get_testcases()
            wx.CallAfter(self.status_panel.make_placeholders, len(testcases))
            testcase_results = []
            for i, t in enumerate(testcases):
                result = self._judge_test_case(test_dir, participant, problem, t)
                wx.CallAfter(self.status_panel.set_nth, i, result_color[result])
                testcase_results.append(result)
                # print('case {}: {}'.format(len(testcase_results), testcase_results[-1]), flush=True)
            participant.result.set_problem(problem.name, ProblemResult(testcase_results))
            (test_dir/problem.name).unlink()

        self._score_sheet.ForceRefresh()

    def _prepare_program(self, test_dir, participant, problem):
        """
        Compile source into test_dir/problem.name
        Return None if succeeded, otherwise return error string
        """
        # TODO: somehow indicate the progress in the cell
        src_path = Contest.singleton.path / SRC_DIR_NAME / participant.name / (problem.name+'.cpp')

        if not src_path.exists():
            return 'Not found'

        completed_process = subprocess.run(['g++', '-std=c++17', '-o', str(test_dir/problem.name), str(src_path)])

        if completed_process.returncode != 0:
            return 'Compilation Error'

    def _judge_test_case(self, test_dir, participant, problem, testcase):
        shutil.copy(testcase.input_file_path, test_dir/(problem.name+'.in'))
        # TODO: TLE, MLE
        # TODO: refactor exe path
        completed_process = subprocess.run([str(test_dir/problem.name)], cwd=test_dir,
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if completed_process.returncode != 0:
            result = 'Runtime Error'
        elif not (test_dir/(problem.name+'.out')).is_file():
            result = 'Output Not Found'
        elif not filecmp.cmp(test_dir/(problem.name+'.out'), testcase.output_file_path):
            result = 'Wrong Answer'
        else:
            result = 'Accepted'

        for f in test_dir.iterdir():
            if f.name == problem.name:
                continue

            # TODO: error if not output
            try:
                f.unlink()
            except IsADirectoryError:
                shutil.rmtree(f)

        return result


def main():
    app = wx.App()
    main_frame = MainFrame()
    main_frame.Show()
    app.MainLoop()


if __name__=='__main__':
    main()
