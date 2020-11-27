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
import asyncio
import multiprocessing
import os
import signal
from itertools import islice
from contest import (
        Contest, ContestError, ScoreSheet,
        ProblemResult,
        DATA_DIR_NAME, SRC_DIR_NAME, CONTEST_CONFIG_FILE_NAME,
        )
from program_result import (ProgramResultBar, result_color)
from utils import menu_bar, populate_menu, menu_item


def split_every(n, gen):
    i = iter(gen)
    while True:
        r = list(islice(i, n))
        if not r:
            return
        yield r


def get_global_config_path():
    # TODO: handle windows
    return Path.home() / ".cena2"


class DefaultPropertiesDialog(wx.Dialog):
    # TODO: reset default
    # TODO: save to home
    def __init__(self, parent):
        super().__init__(parent, wx.ID_ANY, style=wx.RESIZE_BORDER, title="Default Config")
        sizer = wx.BoxSizer(wx.VERTICAL)
        panel = wx.Panel(self, wx.ID_ANY)
        sizer.Add(panel, wx.SizerFlags(1).Expand().Border(wx.ALL, 5))

        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        grid_sizer = wx.FlexGridSizer(2, 10, 10)

        grid_sizer.Add(wx.StaticText(panel, wx.ID_ANY, "Time limit"), wx.SizerFlags().Right().CenterVertical())
        time_limit_sizer = wx.BoxSizer(wx.HORIZONTAL)
        time_limit_ctrl = wx.TextCtrl(panel, wx.ID_ANY)
        time_limit_ctrl.SetHint("1")
        time_limit_sizer.Add(time_limit_ctrl)
        time_limit_sizer.Add(wx.StaticText(panel, wx.ID_ANY, label="s"), wx.SizerFlags().CenterVertical().Border(wx.LEFT, 5))
        grid_sizer.Add(time_limit_sizer)

        grid_sizer.Add(wx.StaticText(panel, wx.ID_ANY, "Memory limit"), wx.SizerFlags().Right().CenterVertical())
        memory_limit_sizer = wx.BoxSizer(wx.HORIZONTAL)
        memory_limit_ctrl = wx.TextCtrl(panel, wx.ID_ANY)
        memory_limit_ctrl.SetHint("512")
        memory_limit_sizer.Add(memory_limit_ctrl)
        memory_limit_sizer.Add(wx.StaticText(panel, wx.ID_ANY, "MB"), wx.SizerFlags().CenterVertical().Border(wx.LEFT, 5))
        grid_sizer.Add(memory_limit_sizer)

        grid_sizer.Add(wx.StaticText(panel, wx.ID_ANY, "Total score"), wx.SizerFlags().Right().CenterVertical())
        total_score_ctrl = wx.TextCtrl(panel, wx.ID_ANY)
        total_score_ctrl.SetHint("100")
        grid_sizer.Add(total_score_ctrl)

        panel_sizer.Add(grid_sizer, wx.SizerFlags(1).Expand())
        panel.SetSizer(panel_sizer)

        sizer.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), wx.SizerFlags(0).Expand().Border(wx.ALL, 5))
        self.SetSizerAndFit(sizer)


class MainFrame(wx.Frame):
    TITLE = 'Cena2'
    SIZE = (800, 600)

    def __init__(self):
        super().__init__(None, title=MainFrame.TITLE, size=MainFrame.SIZE)

        self.SetSizer(wx.BoxSizer(wx.VERTICAL))

        # Menu bar
        self._close_contest_menu_item = menu_item(self, '&Close contest', handler=self._close_contest)
        self.SetMenuBar(menu_bar([
            ('&File', [
                menu_item(self, '&Open contest', handler=self._open_contest),
                self._close_contest_menu_item,
                wx.MenuItem(),
                menu_item(self, '&Properties', handler=self._properties),
                ]),
            ('&Contest', [
                menu_item(self, '&Participate', handler=self._participate_contest),
                menu_item(self, '&Host', handler=self._host_contest),
                ]),
            ('&Help', [
                menu_item(self, '&Manual', handler=self._show_manual),
                menu_item(self, '&About', handler=self._show_about),
                ]),
            ]))
        self._close_contest_menu_item.Enable(False)

        1 and wx.CallAfter(lambda: self._open_contest(None))

    def _open_contest_prepare(self):
        if Contest.singleton is not None:
            self._do_close_contest()

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
        except ContestError as s:
            print(s, flush=True)
        else:
            self._close_contest_menu_item.Enable()
            self._render_contest()
            self.Layout()

    def _render_contest(self):
        self._score_sheet = ScoreSheet(self, Contest.singleton)
        self._score_sheet.SetMinSize((0,0))  # otherwise it grows greedly
        self.GetSizer().Add(self._score_sheet, wx.SizerFlags(1).Expand().Border(wx.ALL, 10))

        lower_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.GetSizer().Add(lower_sizer, wx.SizerFlags().Expand().Border(wx.ALL ^ wx.TOP, 10))

        self.status_panel = ProgramResultBar(self)
        lower_sizer.Add(self.status_panel, wx.SizerFlags(1).Expand().Border(wx.TOP|wx.RIGHT, 5))

        self.btn_judge_selected = wx.Button(self, label="&Judge selected")
        self.btn_judge_selected.Disable()
        self.Bind(wx.EVT_BUTTON, self._test_selected, self.btn_judge_selected)
        lower_sizer.Add(self.btn_judge_selected, wx.SizerFlags(0).Border(wx.TOP, 5))

        # self.status_panel.Bind(wx.EVT_LEFT_DOWN, self._click_status_box)
        self._score_sheet._selection_change_handler = self.btn_judge_selected.Enable
        self._score_sheet._focus_changed = self.handle_focus_changed

        # status_box.SetBackgroundColour(wx.RED)
        self.Layout()

    def handle_focus_changed(self, focus):
        if focus is None:
            self.btn_judge_selected.Disable()
            self.status_panel.clear_bar()
        else:
            # TODO: prevent selection change during testing
            self.btn_judge_selected.Enable()
            participant, problem = focus
            data = participant.result.problems.get(problem.name)
            if data is None:
                self.status_panel.set_message('Not tested')
            elif isinstance(data.data, str):
                self.status_panel.set_message(data.data)
            else:
                self.status_panel.make_placeholders(len(data.data))
                for i,v in enumerate(data.data):
                    self.status_panel.set_nth(i, result_color[v])
            self.status_panel.Layout()

    # def _click_status_box(self, ev):
    #     self._score_sheet.ClearSelection()

    def _close_contest(self, ev):
        self._do_close_contest()

    def _do_close_contest(self):
        # TODO: disable the menu item after closing contest
        Contest.close()
        self.GetSizer().Clear(True)
        self.Layout()
        self._close_contest_menu_item.Enable(False)

    def _properties(self, ev):
        DefaultPropertiesDialog(self).ShowModal()

    def _participate_contest(self, ev):
        raise NotImplementedError

    def _host_contest(self, ev):
        raise NotImplementedError

    def _show_manual(self, ev):
        raise NotImplementedError

    def _show_about(self, ev):
        info = wx.adv.AboutDialogInfo()
        info.AddDeveloper(("John Doe"));
        info.AddDocWriter(("Donald Duck"));
        info.AddArtist(("Scrooge Mc.Duck"));
        info.AddTranslator(("Mickey Mouse"));
        info.SetDescription(("Sample wxWidgets application for testing wxAboutBox() function."));
        info.SetName("Cena2");
        icon = wx.Icon("arch-logo.ico")
        icon = wx.GetApp().GetTopWindow().GetIcon()
        print(icon)
        info.SetIcon(icon);
        info.SetLicence(("Public Domain"));
        wx.adv.AboutBox(info);

    async def _do_test_selected(self):
        # TODO: fake modal: intercept clicks unless clicking 'cancel testing'
        # TODO: use another thread to avoid blocking
        # resource.setrlimit(resource.RLIMIT_CORE, (0, 0))   # not helping much
        with TemporaryDirectory(prefix="cena2") as test_dir, TemporaryDirectory(prefix="cena2") as exe_dir:
            test_dir = Path(test_dir)
            exe_dir = Path(exe_dir)
            n_core = multiprocessing.cpu_count()
            for chunk in split_every(n_core, self._score_sheet.get_selected()):
                wx.CallAfter(self.status_panel.set_message, "Compiling ...")

                compilation_results = await asyncio.gather(*(self._prepare_program(exe_dir/str(i), participant, problem)
                    for i, (row, col, participant, problem) in enumerate(chunk)))

                for i, (row, col, participant, problem) in enumerate(chunk):
                    if compilation_results[i] is None:
                        self._judge_program(test_dir, exe_dir/str(i), participant, problem)
                        assert len(list(test_dir.iterdir()))==0
                    else:
                        participant.result.set_problem(problem.name, ProblemResult(compilation_results[i]))

                    wx.CallAfter(self._score_sheet.DeselectCell, row, col)

                for f in exe_dir.iterdir():
                    f.unlink()
        # TODO: cancel fake modal

    def _test_selected(self, ev):
        threading.Thread(target=lambda: asyncio.run(self._do_test_selected())).start()

    def _judge_program(self, test_dir, exe_path, participant, problem):
        """
        The participants' programs are supposed to be run alone without concurrency,
        so every subprocess is synchronous.
        """
        # print('testing', test_dir, participant, problem, flush=True)
        # error = self._prepare_program(test_dir, participant, problem)
        # if error is not None:
        #     print(test_dir, participant, problem, error, flush=True)
        #     participant.result.set_problem(problem.name, ProblemResult(error))
        #     wx.CallAfter(self.status_panel.set_message, error)
        # else:

        testcases = problem.get_testcases()
        wx.CallAfter(self.status_panel.make_placeholders, len(testcases))
        testcase_results = []
        for i, t in enumerate(testcases):
            result = self._judge_test_case(test_dir, exe_path, participant, problem, t)
            wx.CallAfter(self.status_panel.set_nth, i, result_color[result])
            testcase_results.append(result)
            # print('case {}: {}'.format(len(testcase_results), testcase_results[-1]), flush=True)
        participant.result.set_problem(problem.name, ProblemResult(testcase_results))

        wx.CallAfter(self._score_sheet.ForceRefresh)

    async def _prepare_program(self, exe_path, participant, problem):
        """
        Compile source into test_dir/problem.name
        Return None if succeeded, otherwise return error string
        """
        participant.result.remove_problem(problem.name)
        # TODO: somehow indicate the progress in the cell
        # wx.CallAfter(self.status_panel.set_message, "Compiling ...")

        src_path = Contest.singleton.path / SRC_DIR_NAME / participant.name / (problem.name+'.cpp')

        if not src_path.exists():
            return 'Not found'

        process = await asyncio.create_subprocess_exec('g++', '-std=c++17', '-o', str(exe_path), str(src_path))
        if await process.wait() != 0:
            return 'Compilation Error'

    @staticmethod
    def _handle_signals():
        signal.signal(signal.SIGFPE, lambda: os.exit(5))

    def _judge_test_case(self, test_dir, exe_path, participant, problem, testcase):
        shutil.copy(testcase.input_file_path, test_dir/(problem.name+'.in'))
        # TODO: TLE, MLE
        # TODO: refactor exe path
        time_limit = problem.time_limit or 0.9
        memory_limit = problem.memory_limit or 128

        start_time = time.time()
        end_time = None
        process = subprocess.Popen([str(exe_path)], cwd=test_dir,
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                preexec_fn=MainFrame._handle_signals,   # FIXME: doesn't work, must handle in c. see <https://stackoverflow.com/q/65042144>
                )

        process_result = None
        def waiter():
            nonlocal process_result
            nonlocal end_time
            process_result = os.wait4(process.pid, 0)
            end_time = time.time()

        timer_thread = threading.Thread(target=waiter)
        timer_thread.start()
        timer_thread.join(time_limit)
        # print(process_result)
        print(f'ellapsed time: {end_time - start_time if end_time is not None else "TLE"}', flush=True)

        if timer_thread.is_alive():
            # TODO FIXME: kill thread by killing process
            process.kill()
            timer_thread.join()
            result = 'Time Limit Exceeded'
        elif process_result[1] != 0:
            result = 'Runtime Error'
            print(f'error code = {process_result[1]}', flush=True)
        elif not (test_dir/(problem.name+'.out')).is_file():
            result = 'Output Not Found'
        elif not filecmp.cmp(test_dir/(problem.name+'.out'), testcase.output_file_path):
            result = 'Wrong Answer'
        elif process_result[2].ru_maxrss > memory_limit*1024:
            # TODO: ru_maxrss is highly plantform-dependent
            result = 'Memory Limit Exceeded'
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
