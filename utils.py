from dataclasses import dataclass, field

import pygame

__all__ = [
    "Color",
    "Key",
    "Event",
    "Surface",
    "Font",
    "PressedKeys",
    "Theme",
    "EditorConfig",
    "RepeatKey",
    "StatuslineState",
    "SelectionState",
]

Color = tuple[int, int, int]
Key = int
Event = pygame.event.Event
Surface = pygame.surface.Surface
Font = pygame.font.Font
PressedKeys = pygame.key.ScancodeWrapper


@dataclass
class Theme:
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
    theme: Theme = field(default_factory=Theme)


class RepeatKey:
    def __init__(self, delay_frames: int = 30):
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
class StatuslineState:
    saved: bool = False

    prompt_saving: bool = False
    prompt_loading: bool = False
    prompting: bool = False

    file_path: str = ""
    cursor_pos: int = 0

    def get_flair(self):
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
