#!/usr/bin/env python3
""" Helper functions and classes for GUI controls """
import logging
import re

import tkinter as tk
from tkinter import ttk

from .tooltip import Tooltip
from .utils import ContextMenu, FileHandler, get_images

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


def set_slider_rounding(value, var, d_type, round_to, min_max):
    """ Set the underlying variable to correct number based on slider rounding """
    if d_type == float:
        var.set(round(float(value), round_to))
    else:
        steps = range(min_max[0], min_max[1] + round_to, round_to)
        value = min(steps, key=lambda x: abs(x - int(float(value))))
        var.set(value)


def adjust_wraplength(event):
    """ dynamically adjust the wraplength of a label on event """
    label = event.widget
    label.configure(wraplength=event.width - 1)


class ControlPanel(ttk.Frame):  # pylint:disable=too-many-ancestors
    """ A Panel for holding controls
        Also keeps tally if groups passed in, so that any options with special
        processing needs are processed in the correct group frame """

    def __init__(self, parent, options, label_width=20, columns=1, radio_columns=4,
                 header_text=None, blank_nones=True):
        logger.debug("Initializing %s: (parent: '%s', options: %s, label_width: %s, columns: %s, "
                     "radio_columns: %s, header_text: %s, blank_nones: %s)",
                     self.__class__.__name__, parent, options, label_width, columns, radio_columns,
                     header_text, blank_nones)
        gui_style = ttk.Style()

        gui_style.configure('BlueText.TLabelframe.Label', foreground="#0046D5", relief=tk.SOLID)
        super().__init__(parent)

        self.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.options = options
        self.label_width = label_width
        self.columns = columns
        self.radio_columns = radio_columns

        self.header_text = header_text
        self.group_frames = dict()

        self.canvas = tk.Canvas(self, bd=0, highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.mainframe, self.optsframe = self.get_opts_frame()
        self.optscanvas = self.canvas.create_window((0, 0), window=self.mainframe, anchor=tk.NW)

        self.build_panel(radio_columns, blank_nones)
        logger.debug("Initialized %s", self.__class__.__name__)

    def get_opts_frame(self):
        """ Return an autofill container for the options inside a main frame """
        mainframe = ttk.Frame(self.canvas)
        if self.header_text is not None:
            self.add_info(mainframe)
        optsframe = ttk.Frame(mainframe)
        optsframe.pack(expand=True, fill=tk.BOTH)
        holder = AutoFillContainer(optsframe, self.columns)
        logger.debug("Opts frames: '%s'", holder)
        return mainframe, holder

    def add_info(self, frame):
        """ Plugin information """
        gui_style = ttk.Style()
        gui_style.configure('White.TFrame', background='#FFFFFF')
        gui_style.configure('Header.TLabel', background='#FFFFFF', font=("", 9, "bold"))
        gui_style.configure('Body.TLabel', background='#FFFFFF', font=("", 9))

        info_frame = ttk.Frame(frame, style='White.TFrame', relief=tk.SOLID)
        info_frame.pack(fill=tk.X, side=tk.TOP, expand=True, padx=10, pady=10)
        label_frame = ttk.Frame(info_frame, style='White.TFrame')
        label_frame.pack(padx=5, pady=5, fill=tk.X, expand=True)
        for idx, line in enumerate(self.header_text.splitlines()):
            if not line:
                continue
            style = "Header.TLabel" if idx == 0 else "Body.TLabel"
            info = ttk.Label(label_frame, text=line, style=style, anchor=tk.W)
            info.pack(fill=tk.X, padx=0, pady=0, expand=True, side=tk.TOP)
        info.bind("<Configure>", adjust_wraplength)

    def build_panel(self, radio_columns, blank_nones):
        """ Build the options frame for this command """
        logger.debug("Add Config Frame")
        self.add_scrollbar()
        self.canvas.bind("<Configure>", self.resize_frame)

        for key, val in self.options.items():
            if key == "helptext":
                continue
            group = "_master" if val["group"] is None else val["group"]
            group_frame = self.get_group_frame(group)
            ctl = ControlBuilder(group_frame["frame"],
                                 key,
                                 val["type"],
                                 val["default"],
                                 label_width=self.label_width,
                                 selected_value=val["value"],
                                 choices=val["choices"],
                                 is_radio=val["gui_radio"],
                                 rounding=val["rounding"],
                                 min_max=val["min_max"],
                                 helptext=val["helptext"],
                                 sysbrowser=val.get("sysbrowser", None),
                                 checkbuttons_frame=group_frame["chkbtns"],
                                 radio_columns=radio_columns,
                                 blank_nones=blank_nones)
            if group_frame["chkbtns"].items > 0:
                group_frame["chkbtns"].parent.pack(side=tk.BOTTOM, fill=tk.X, anchor=tk.NW)
            val["selected"] = ctl.tk_var
            self.options[key]["_gui_option"] = ctl
        for key, val in self.options.items():
            if key == "helptext":
                continue
            filebrowser = val["_gui_option"].filebrowser
            if filebrowser is not None:
                filebrowser.set_context_action_option(self.options)
        logger.debug("Added Config Frame")

    def get_group_frame(self, group):
        """ Return a new group frame """
        group = group.lower()
        if self.group_frames.get(group, None) is None:
            logger.debug("Creating new group frame for: %s", group)
            is_master = group == "_master"
            opts_frame = self.optsframe.subframe
            if is_master:
                group_frame = ttk.Frame(opts_frame, name=group.lower())
            else:
                group_frame = ttk.LabelFrame(opts_frame,
                                             text="" if is_master else group.title(),
                                             name=group.lower(), style="BlueText.TLabelframe")

            group_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5, anchor=tk.NW)

            self.group_frames[group] = dict(frame=group_frame,
                                            chkbtns=self.checkbuttons_frame(group_frame))
        group_frame = self.group_frames[group]
        return group_frame

    def add_scrollbar(self):
        """ Add a scrollbar to the options frame """
        logger.debug("Add Config Scrollbar")
        scrollbar = ttk.Scrollbar(self, command=self.canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.config(yscrollcommand=scrollbar.set)
        self.mainframe.bind("<Configure>", self.update_scrollbar)
        logger.debug("Added Config Scrollbar")

    def update_scrollbar(self, event):  # pylint: disable=unused-argument
        """ Update the options frame scrollbar """
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def resize_frame(self, event):
        """ Resize the options frame to fit the canvas """
        logger.debug("Resize Config Frame")
        canvas_width = event.width
        self.canvas.itemconfig(self.optscanvas, width=canvas_width)
        logger.debug("Resized Config Frame")

    def checkbuttons_frame(self, frame):
        """ Build and format frame for holding the check buttons
            if is_master then check buttons will be placed in a LabelFrame
            otherwise in a standard frame """
        logger.debug("Add Options CheckButtons Frame")
        chk_frame = ttk.Frame(frame, name="chkbuttons")
        holder = AutoFillContainer(chk_frame, self.radio_columns)
        logger.debug("Added Options CheckButtons Frame")
        return holder


class AutoFillContainer():
    """ A container object that autofills columns """
    def __init__(self, parent, columns):
        logger.debug("Initializing: %s: (parent: %s, columns: %s)", self.__class__.__name__,
                     parent, columns)
        self.parent = parent
        self.columns = columns
        self._items = 0
        self._idx = 0
        self.subframes = self.set_subframes()
        logger.debug("Initialized: %s: (items: %s)", self.__class__.__name__, self.items)

    @property
    def items(self):
        """ Returns the number if items held in this containter """
        return self._items

    @property
    def subframe(self):
        """ Returns the next subframe to be populated """
        frame = self.subframes[self._idx]
        next_idx = self._idx + 1 if self._idx + 1 != self.columns else 0
        logger.debug("current_idx: %s, next_idx: %s", self._idx, next_idx)
        self._idx = next_idx
        return frame

    @property
    def last_subframe(self):
        """ Returns the last column """
        return self.subframes[self.columns - 1]

    def set_subframes(self):
        """ Set a subrame for each requested column """
        subframes = []
        for idx in range(self.columns):
            if self.columns != 1:
                name = "{}_{}".format(self.parent.winfo_name(), idx)
                subframe = ttk.Frame(self.parent, name=name)
                subframe.pack(padx=5, pady=5, side=tk.LEFT, anchor=tk.N, expand=True, fill=tk.X)
                subframes.append(subframe)
                logger.debug("Added subframe: %s", name)
            else:
                subframes.append(self.parent)
                logger.debug("Using parent as subframe: %s", self.parent.winfo_name())
            self._items += 1
        return subframes


class ControlBuilder():
    """
    Builds and returns a frame containing a tkinter control with label

    Currently only setup for config items

    Parameters
    ----------
    parent: tkinter object
        Parent tkinter object
    title: str
        Title of the control. Will be used for label text
    dtype: datatype object
        Datatype of the control.
    default: str
        Default value for the control
    selected_value: str, optional
        Selected value for the control. If None, default will be used
    choices: list or tuple, object
        Used for combo boxes and radio control option setting
    is_radio: bool, optional
        Specifies to use a Radio control instead of combobox if choices are passed
    rounding: int or float, optional
        For slider controls. Sets the stepping
    min_max: int or float, optional
        For slider controls. Sets the min and max values
    sysbrowser: dict, optional
        Adds Filesystem browser buttons to ttk.Entry options.
        Expects a dict: {sysbrowser: str, filetypes: str}
    helptext: str, optional
        Sets the tooltip text
    radio_columns: int, optional
        Sets the number of columns to use for grouping radio buttons
    label_width: int, optional
        Sets the width of the control label. Defaults to 20
    checkbuttons_frame: tk.frame, optional
        If a checkbutton frame is passed in, then checkbuttons will be placed in this frame
        rather than the main options frame
    control_width: int, optional
        Sets the width of the control. Default is to auto expand
    blank_nones: bool, optional
        Sets selected values to an empty string rather than None if this is true. Default is true
    """
    def __init__(self, parent, title, dtype, default,
                 selected_value=None, choices=None, is_radio=False, rounding=None,
                 min_max=None, sysbrowser=None, helptext=None, radio_columns=3, label_width=20,
                 checkbuttons_frame=None, control_width=None, blank_nones=True):
        logger.debug("Initializing %s: (parent: %s, title: %s, dtype: %s, default: %s, "
                     "selected_value: %s, choices: %s, is_radio: %s, rounding: %s, min_max: %s, "
                     "sysbrowser: %s, helptext: %s, radio_columns: %s, label_width: %s, "
                     "checkbuttons_frame: %s, control_width: %s, blank_nones: %s)",
                     self.__class__.__name__, parent, title, dtype, default, selected_value,
                     choices, is_radio, rounding, min_max, sysbrowser, helptext, radio_columns,
                     label_width, checkbuttons_frame, control_width, blank_nones)

        self.title = title
        self.default = default
        self.helptext = self.format_helptext(helptext)
        self.helpset = False
        self.label_width = label_width
        self.filebrowser = None

        self.frame = self.control_frame(parent)
        self.chkbtns = checkbuttons_frame
        self.control = self.set_control(dtype, choices, is_radio)
        self.tk_var = self.set_tk_var(dtype, selected_value, blank_nones)

        self.build_control(choices,
                           dtype,
                           rounding,
                           min_max,
                           sysbrowser,
                           radio_columns,
                           control_width)
        logger.debug("Initialized: %s", self.__class__.__name__)

    # Frame, control type and varable
    @staticmethod
    def control_frame(parent):
        """ Frame to hold control and it's label """
        logger.debug("Build control frame")
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X)
        logger.debug("Built control frame")
        return frame

    def format_helptext(self, helptext):
        """ Format the help text for tooltips """
        if helptext is None:
            return helptext
        logger.debug("Format control help: '%s'", self.title)
        if helptext.startswith("R|"):
            helptext = helptext[2:].replace("\nL|", "\n - ").replace("\n", "\n\n")
        else:
            helptext = helptext.replace("\n\t", "\n  - ").replace("%%", "%")
        helptext = ". ".join(i.capitalize() for i in helptext.split(". "))
        helptext = self.title + " - " + helptext
        logger.debug("Formatted control help: (title: '%s', help: '%s'", self.title, helptext)
        return helptext

    def set_control(self, dtype, choices, is_radio):
        """ Set the correct control type based on the datatype or for this option """
        if choices and is_radio:
            control = ttk.Radiobutton
        elif choices:
            control = ttk.Combobox
        elif dtype == bool:
            control = ttk.Checkbutton
        elif dtype in (int, float):
            control = ttk.Scale
        else:
            control = ttk.Entry
        logger.debug("Setting control '%s' to %s", self.title, control)
        return control

    def set_tk_var(self, dtype, selected_value, blank_nones):
        """ Correct variable type for control """
        logger.debug("Setting tk variable: (title: '%s', dtype: %s, selected_value: %s, "
                     "blank_nones: %s)",
                     self.title, dtype, selected_value, blank_nones)
        if dtype == bool:
            var = tk.BooleanVar
        elif dtype == int:
            var = tk.IntVar
        elif dtype == float:
            var = tk.DoubleVar
        else:
            var = tk.StringVar
        var = var(self.frame)
        val = self.default if selected_value is None else selected_value
        val = "" if val is None and blank_nones else val
        var.set(val)
        logger.debug("Set tk variable: (title: '%s', type: %s, value: '%s')",
                     self.title, type(var), val)
        return var

    # Build the full control
    def build_control(self, choices, dtype, rounding, min_max, sysbrowser, radio_columns,
                      control_width):
        """ Build the correct control type for the option passed through """
        logger.debug("Build confog option control")
        if self.control not in (ttk.Checkbutton, ttk.Radiobutton):
            self.build_control_label()
        self.build_one_control(choices,
                               dtype,
                               rounding,
                               min_max,
                               sysbrowser,
                               radio_columns,
                               control_width)
        logger.debug("Built option control")

    def build_control_label(self):
        """ Label for control """
        logger.debug("Build control label: (title: '%s')", self.title)
        title = self.title.replace("_", " ").title()
        lbl = ttk.Label(self.frame, text=title, width=self.label_width, anchor=tk.W)
        lbl.pack(padx=5, pady=5, side=tk.LEFT, anchor=tk.N)
        if self.helptext is not None:
            Tooltip(lbl, text=self.helptext, wraplength=720)

        logger.debug("Built control label: '%s'", self.title)

    def build_one_control(self, choices, dtype, rounding, min_max,
                          sysbrowser, radio_columns, control_width):
        """ Build and place the option controls """
        logger.debug("Build control: (title: '%s', control: %s, choices: %s, dtype: %s, "
                     "rounding: %s, sysbrowser: %s, min_max: %s: radio_columns: %s, "
                     "control_width: %s)", self.title, self.control, choices, dtype, rounding,
                     sysbrowser, min_max, radio_columns, control_width)
        if self.control == ttk.Scale:
            ctl = self.slider_control(dtype, rounding, min_max)
        elif self.control == ttk.Radiobutton:
            ctl = self.radio_control(choices, radio_columns)
        elif self.control == ttk.Checkbutton:
            ctl = self.control_to_checkframe()
        else:
            ctl = self.control_to_optionsframe(choices, sysbrowser)
        self.set_control_width(ctl, control_width)
        if self.control != ttk.Checkbutton:
            ctl.pack(padx=5, pady=5, fill=tk.X, expand=True)
            if self.helptext is not None and not self.helpset:
                Tooltip(ctl, text=self.helptext, wraplength=720)

        logger.debug("Built control: '%s'", self.title)

    @staticmethod
    def set_control_width(ctl, control_width):
        """ Set the control width if required """
        if control_width is not None:
            ctl.config(width=control_width)

    def radio_control(self, choices, columns):
        """ Create a group of radio buttons """
        logger.debug("Adding radio group: %s", self.title)
        all_help = [line for line in self.helptext.splitlines()]
        if any(line.startswith(" - ") for line in all_help):
            intro = all_help[0]
        helpitems = {re.sub(r'[^A-Za-z0-9\-]+', '',
                            line.split()[1].lower()): " ".join(line.split()[1:])
                     for line in all_help
                     if line.startswith(" - ")}

        ctl = ttk.LabelFrame(self.frame,
                             text=self.title.replace("_", " ").title(),
                             style="BlueText.TLabelframe")
        radio_holder = AutoFillContainer(ctl, columns)
        for idx, choice in enumerate(choices):
            frame_id = idx % columns
            radio = ttk.Radiobutton(radio_holder.subframe,
                                    text=choice.title(),
                                    value=choice,
                                    variable=self.tk_var)
            if choice.lower() in helpitems:
                self.helpset = True
                helptext = helpitems[choice.lower()].capitalize()
                helptext = "{}\n\n - {}".format(
                    intro,
                    '. '.join(item.capitalize() for item in helptext.split('. ')))
                Tooltip(radio, text=helptext, wraplength=400)
            radio.pack(anchor=tk.W)
            logger.debug("Adding radio option %s to column %s", choice, frame_id)
        return radio_holder.parent

    def slider_control(self, dtype, rounding, min_max):
        """ A slider control with corresponding Entry box """
        logger.debug("Add slider control to Options Frame: (title: '%s', dtype: %s, rounding: %s, "
                     "min_max: %s)", self.title, dtype, rounding, min_max)
        tbox = ttk.Entry(self.frame, width=8, textvariable=self.tk_var, justify=tk.RIGHT)
        tbox.pack(padx=(0, 5), side=tk.RIGHT)
        ctl = self.control(
            self.frame,
            variable=self.tk_var,
            command=lambda val, var=self.tk_var, dt=dtype, rn=rounding, mm=min_max:
            set_slider_rounding(val, var, dt, rn, mm))
        rc_menu = ContextMenu(tbox)
        rc_menu.cm_bind()
        ctl["from_"] = min_max[0]
        ctl["to"] = min_max[1]
        logger.debug("Added slider control to Options Frame: %s", self.title)
        return ctl

    def control_to_optionsframe(self, choices, sysbrowser):
        """ Standard non-check buttons sit in the main options frame """
        logger.debug("Add control to Options Frame: (title: '%s', control: %s, choices: %s)",
                     self.title, self.control, choices)
        if self.control == ttk.Checkbutton:
            ctl = self.control(self.frame, variable=self.tk_var, text=None)
        else:
            if sysbrowser is not None:
                self.filebrowser = FileBrowser(self.tk_var, self.frame, sysbrowser)
            ctl = self.control(self.frame, textvariable=self.tk_var)
            rc_menu = ContextMenu(ctl)
            rc_menu.cm_bind()
        if choices:
            logger.debug("Adding combo choices: %s", choices)
            ctl["values"] = [choice for choice in choices]
        logger.debug("Added control to Options Frame: %s", self.title)
        return ctl

    def control_to_checkframe(self):
        """ Add checkbuttons to the checkbutton frame """
        logger.debug("Add control checkframe: '%s'", self.title)
        chkframe = self.chkbtns.subframe
        ctl = self.control(chkframe,
                           variable=self.tk_var,
                           text=self.title.replace("_", " ").title(),
                           name=self.title.lower())
        Tooltip(ctl, text=self.helptext, wraplength=200)
        ctl.pack(side=tk.TOP, anchor=tk.W)
        logger.debug("Added control checkframe: '%s'", self.title)
        return ctl


class FileBrowser():
    """ Add FileBrowser buttons to control and handle routing """
    def __init__(self, tk_var, control_frame, sysbrowser_dict):
        logger.debug("Initializing: %s: (tk_var: %s, control_frame: %s, sysbrowser_dict: %s)",
                     self.__class__.__name__, tk_var, control_frame, sysbrowser_dict)
        self.tk_var = tk_var
        self.frame = control_frame
        self.browser = sysbrowser_dict["browser"]
        self.filetypes = sysbrowser_dict["filetypes"]
        self.action_option = sysbrowser_dict.get("action_option", None)
        self.command = sysbrowser_dict.get("command", None)
        self.destination = sysbrowser_dict.get("destination", None)
        self.add_browser_buttons()
        logger.debug("Initialized: %s", self.__class__.__name__)

    @property
    def helptext(self):
        """ Dict containing tooltip text for buttons """
        retval = dict(folder="Select a folder...",
                      load="Select a file...",
                      load_multi="Select one or more files...",
                      context="Select a file or folder...",
                      save="Select a save location...")
        return retval

    def add_browser_buttons(self):
        """ Add correct file browser button for control """
        logger.debug("Adding browser buttons: (sysbrowser: '%s'", self.browser)
        for browser in self.browser:
            img = get_images().icons[browser]
            action = getattr(self, "ask_" + browser)
            fileopn = ttk.Button(self.frame,
                                 image=img,
                                 command=lambda cmd=action: cmd(self.tk_var, self.filetypes))
            fileopn.pack(padx=(0, 5), side=tk.RIGHT)
            Tooltip(fileopn, text=self.helptext[browser], wraplength=200)
            logger.debug("Added browser buttons: (action: %s, filetypes: %s",
                         action, self.filetypes)

    def set_context_action_option(self, options):
        """ Set the tk_var for the source action option
            that dictates the context sensitive file browser. """
        if self.browser != ["context"]:
            return
        actions = {item["opts"][0]: item["selected"]
                   for item in options.values()}
        logger.debug("Settiong action option for opt %s", self.action_option)
        self.action_option = actions[self.action_option]

    @staticmethod
    def ask_folder(filepath, filetypes=None):
        """ Pop-up to get path to a directory
            :param filepath: tkinter StringVar object
            that will store the path to a directory.
            :param filetypes: Unused argument to allow
            filetypes to be given in ask_load(). """
        dirname = FileHandler("dir", filetypes).retfile
        if dirname:
            logger.debug(dirname)
            filepath.set(dirname)

    @staticmethod
    def ask_load(filepath, filetypes):
        """ Pop-up to get path to a file """
        filename = FileHandler("filename", filetypes).retfile
        if filename:
            logger.debug(filename)
            filepath.set(filename)

    @staticmethod
    def ask_load_multi(filepath, filetypes):
        """ Pop-up to get path to a file """
        filenames = FileHandler("filename_multi", filetypes).retfile
        if filenames:
            final_names = " ".join("\"{}\"".format(fname) for fname in filenames)
            logger.debug(final_names)
            filepath.set(final_names)

    @staticmethod
    def ask_save(filepath, filetypes=None):
        """ Pop-up to get path to save a new file """
        filename = FileHandler("savefilename", filetypes).retfile
        if filename:
            logger.debug(filename)
            filepath.set(filename)

    @staticmethod
    def ask_nothing(filepath, filetypes=None):  # pylint:disable=unused-argument
        """ Method that does nothing, used for disabling open/save pop up """
        return

    def ask_context(self, filepath, filetypes):
        """ Method to pop the correct dialog depending on context """
        logger.debug("Getting context filebrowser")
        selected_action = self.action_option.get()
        selected_variable = self.destination
        filename = FileHandler("context",
                               filetypes,
                               command=self.command,
                               action=selected_action,
                               variable=selected_variable).retfile
        if filename:
            logger.debug(filename)
            filepath.set(filename)
