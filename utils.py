from dataclasses import dataclass, field
from pathlib import Path

import pygame

Color = tuple[int, int, int]
Key = int
Event = pygame.event.Event
Surface = pygame.surface.Surface
Font = pygame.font.Font
PressedKeys = pygame.key.ScancodeWrapper


@dataclass
class EditorTheme:
    bg_color: Color = (25, 23, 36)  # base #191724
    bg_selection_color: Color = (64, 61, 82)  # highlight_med #403d52
    line_color: Color = (33, 32, 46)  # highlight_low #21202e
    text_color: Color = (224, 222, 244)  # text #e0def4
    text_selection_color: Color = (224, 222, 244)  # text #e0def4
    cursor_color: Color = (235, 188, 186)  # rose #ebbcba
    gutter_color: Color = (31, 29, 46)  # surface #1f1d2e
    gutter_line_no_color: Color = (110, 106, 134)  # muted #6e6a86
    gutter_current_line_no_color: Color = (196, 167, 231)  # iris #c4a7e7
    statusline_color: Color = (31, 29, 46)  # surface #1f1d2e
    statusline_text_color: Color = (144, 140, 170)  # subtle #908caa


@dataclass
class EditorConfig:
    font_name: str = "monaspicearnerdfontmono"
    font_size: int = 15
    gutter_size: int = 30
    statusline_height: int = 20
    render_fps: int = 60
    antialias_text: bool = True

    scroll_sens_x: float = 0.8
    scroll_sens_y: float = 1.0

    hold_delay: float = 0.5

    statusline_unsaved_flair: str = " [*] "
    statusline_saved_flair: str = " "
    theme: EditorTheme = field(default_factory=EditorTheme)


@dataclass
class ExplorerTheme:
    bg_color: Color = (25, 23, 36)
    file_color: Color = (255, 255, 255)
    directory_color: Color = (255, 0, 124)
    connector_color: Color = (255, 255, 124)
    line_color: Color = (33, 32, 46)


@dataclass
class ExplorerConfig:
    font_name: str = "monaspicearnerdfontmono"
    font_size: int = 15

    theme: ExplorerTheme = field(default_factory=ExplorerTheme)


class RepeatKey:
    def __init__(self, delay_frames: int = 30) -> None:
        self.delay: int = delay_frames
        self.press_flag: bool = False
        self.frame_count: int = 0

    def tick(self) -> None:
        self.press_flag = False
        self.frame_count += 1

    def press(self) -> None:
        self.press_flag = True
        self.frame_count = 0

    def check(self) -> bool:
        return not self.press_flag and self.frame_count >= self.delay


@dataclass
class EditorState:
    cursor_pos: int = 0
    scroll_offset_x: int = 0
    scroll_offset_y: int = 0


@dataclass
class StatuslineState:
    saved: bool = False

    prompt_saving: bool = False
    prompt_loading: bool = False
    prompting: bool = False

    file_path: str = ""
    saved_state: EditorState = field(default_factory=EditorState)

    def get_flair(self) -> str:
        if self.saved:
            return " "
        else:
            return " [*] "


@dataclass
class SelectionState:
    selecting: bool = False
    display: bool = False
    anchor: int = 0
    start: int = 0
    end: int = 0


class File:
    def __init__(self, path: Path) -> None:
        self.path = path

    @property
    def name(self) -> str:
        return self.path.name


class Directory:
    def __init__(self, path: Path) -> None:
        self.path: Path = path
        self.opened: bool = False
        self.children: list[Directory | File] | None = None

    def update_children(self) -> None:
        self.children = [
            Directory(p) if p.is_dir() else File(p) for p in self.path.iterdir()
        ]

    @property
    def name(self) -> str:
        return self.path.name

    def open(self) -> None:
        self.opened = True
        self.update_children()

    def close(self) -> None:
        self.opened = False

    def toggle(self) -> None:
        if self.opened:
            self.close()
        else:
            self.open()


Node = Directory | File
Depth = int
TreeEntry = tuple[Node, Depth]
Tree = list[TreeEntry]
