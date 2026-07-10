import os
from pathlib import Path

from utils import (
    EditorConfig,
    Event,
    Font,
    Key,
    PressedKeys,
    RepeatKey,
    SelectionState,
    StatuslineState,
    Surface,
)

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame
import pyperclip

pygame.init()
pygame.font.init()


class Editor:
    def __init__(self, config: EditorConfig, surface: Surface) -> None:
        self.buffer: str = ""
        self.cursor: int = 0
        self.scroll_offset_x: int = 0
        self.scroll_offset_y: int = 0

        self.config: EditorConfig = config
        self.font: Font = pygame.font.Font(
            pygame.font.match_font(self.config.font_name),
            size=self.config.font_size,
        )

        repeat_key_list = [
            pygame.K_BACKSPACE,
            pygame.K_LEFT,
            pygame.K_RIGHT,
            pygame.K_UP,
            pygame.K_DOWN,
        ]
        self.repeat: dict[Key, RepeatKey] = dict()
        for key in repeat_key_list:
            self.repeat[key] = RepeatKey()

        self._saved: bool = False
        self.status: StatuslineState = StatuslineState()
        self.selection: SelectionState = SelectionState()
        self.screen: Surface = surface

        self.file_path: Path | None = None

    def _get_cursor_rowcol(self) -> tuple[int, int]:
        if self.status.prompting:
            row = 0
            col = self.cursor + len(self.status.get_flair())
            return row, col

        row = self.buffer.count("\n", 0, self.cursor)

        row_idx = self.buffer.rfind("\n", 0, self.cursor) + 1
        col = self.cursor - row_idx

        return row, col

    def _resolve_mouse_pos(self, x: int, y: int) -> int:
        nlines = self.buffer.count("\n") + 1

        line_idx = max(
            0, min(nlines - 1, self.scroll_offset_y + y // self.font.get_height())
        )

        lines = self._get_buffer_lines()

        line = lines[line_idx]
        line_start_idx = sum(map(len, lines[:line_idx]))
        return line_start_idx + max(
            0,
            min(
                len(line) - 1 if line and line[-1] == "\n" else len(line),
                self.scroll_offset_x
                + int((x - self.config.gutter_size) // (self.font.size(" ")[0])),
            ),
        )

    def _get_max_cols(self) -> int:
        if self.status.prompting:
            return self.screen.get_width() // self.font.size(" ")[0]
        return int(
            (self.screen.get_width() - self.config.gutter_size)
            // self.font.size(" ")[0]
        )

    def _get_max_rows(self) -> int:
        return int(
            (self.screen.get_height() - self.config.statusline_height)
            // self.font.get_height()
        )

    def _get_buffer_lines(self) -> list[str]:
        lines = self.buffer.splitlines(True)
        if not lines or lines[-1][-1] == "\n":
            lines = lines + [""]
        return lines

    def _insert_text(self, text: str) -> None:
        if self.status.prompting:
            self.status.file_path = (
                self.status.file_path[: self.cursor]
                + text
                + self.status.file_path[self.cursor :]
            )
            self.cursor += len(text)
            return

        self.buffer = self.buffer[: self.cursor] + text + self.buffer[self.cursor :]
        self.cursor += len(text)

    def _backspace_text(self) -> None:
        if self.cursor == 0:
            return

        if self.status.prompting:
            self.status.file_path = (
                self.status.file_path[: self.cursor - 1]
                + self.status.file_path[self.cursor :]
            )
            self.cursor -= 1
            return

        self.buffer = self.buffer[: self.cursor - 1] + self.buffer[self.cursor :]
        self.cursor -= 1

    def _shift_cursor(self, n: int) -> None:
        if self.status.prompting:
            self.cursor = max(0, min(len(self.status.file_path), self.cursor + n))
            return
        self.cursor = max(0, min(len(self.buffer), self.cursor + n))

    def _hshift_cursor(self, n: int) -> None:
        self._shift_cursor(n)

        if self.status.prompting:
            visible = self._get_max_cols()
            _, col = self._get_cursor_rowcol()

            if col < self.scroll_offset_x + len(self.status.get_flair()):
                self.scroll_offset_x = self.cursor
            elif col >= self.scroll_offset_x + visible:
                self.scroll_offset_x = col - visible + 1

            return

        _, col = self._get_cursor_rowcol()
        visible = self._get_max_cols()

        if col < self.scroll_offset_x:
            self.scroll_offset_x = col
        elif col >= self.scroll_offset_x + visible:
            self.scroll_offset_x = col - visible + 1

    def _vshift_cursor(self, n: int) -> None:
        if self.status.prompting:
            return

        row, col = self._get_cursor_rowcol()

        lines = self._get_buffer_lines()
        if not (0 <= row + n < len(lines)):
            return

        start = sum(map(len, lines[: row + n]))
        line = lines[row + n].rstrip("\n")
        self.cursor = start + min(col, len(line))

        if row + n >= self.scroll_offset_y + self._get_max_rows():
            self.scroll_offset_y = row + n - self._get_max_rows() + 1
        elif row + n <= self.scroll_offset_y:
            self.scroll_offset_y = row + n

    def _handle_textinput(self, event: Event) -> None:
        self._insert_text(event.text)
        self._hshift_cursor(0)
        self._vshift_cursor(0)
        self.status.saved = False

    def _save_file(self, path: Path) -> None:

        if not path.is_absolute():
            path = Path.cwd() / path

        path = path.resolve(strict=False)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.buffer)
        self.status.saved = True
        if self.file_path is None:
            self.file_path = path

    def _load_file(self, path: Path) -> None:

        if not path.is_absolute():
            path = Path.cwd() / path

        path = path.resolve(strict=False)
        path.parent.mkdir(parents=True, exist_ok=True)

        path.touch(exist_ok=True)

        self.file_path = path
        self.status.saved = True
        with open(path, "r") as f:
            self.buffer = f.read()

    def _handle_keydown(self, event: Event) -> None:

        if event.key == pygame.K_RETURN:
            if self.status.prompting:
                self.status.prompting = False

                self.cursor = self.status.saved_state.cursor_pos
                self.scroll_offset_x = self.status.saved_state.scroll_offset_x
                self.scroll_offset_y = self.status.saved_state.scroll_offset_y

                if self.status.prompt_saving:
                    self._save_file(Path(self.status.file_path))
                    self.status.prompt_saving = False

                elif self.status.prompt_loading:
                    self._load_file(Path(self.status.file_path))
                    self.status.prompt_loading = False
            else:
                self._insert_text("\n")
                self._vshift_cursor(0)
                self._hshift_cursor(0)
                self.status.saved = False

        elif event.key == pygame.K_TAB:
            self._insert_text(" " * 4)
            self._hshift_cursor(0)
            self.status.saved = False

        elif event.key == pygame.K_BACKSPACE:
            self.repeat[event.key].press()
            self._backspace_text()
            self._vshift_cursor(0)
            self._hshift_cursor(0)
            self.status.saved = False

        elif event.key == pygame.K_LEFT:
            self.repeat[event.key].press()
            self._hshift_cursor(-1)
            self._vshift_cursor(0)

        elif event.key == pygame.K_RIGHT:
            self.repeat[event.key].press()
            self._hshift_cursor(1)
            self._vshift_cursor(0)

        elif event.key == pygame.K_UP:
            self.repeat[event.key].press()
            self._vshift_cursor(-1)

        elif event.key == pygame.K_DOWN:
            self.repeat[event.key].press()
            self._vshift_cursor(1)

        elif event.key == pygame.K_v and (
            event.mod & pygame.KMOD_META or event.mod & pygame.KMOD_CTRL
        ):
            self._insert_text(pyperclip.paste())
            self._hshift_cursor(0)
            self._vshift_cursor(0)
            self.status.saved = False

        if event.key == pygame.K_c and (
            event.mod & pygame.KMOD_META or event.mod & pygame.KMOD_CTRL
        ):
            if self.selection.display:
                self.selection.display = False
                if self.selection.end != self.selection.start:
                    if self.selection.end < self.selection.start:
                        self.selection.end, self.selection.start = (
                            self.selection.start,
                            self.selection.end,
                        )
                    pyperclip.copy(
                        self.buffer[self.selection.start : self.selection.end]
                    )

        elif event.key == pygame.K_s and (
            event.mod & pygame.KMOD_META or event.mod & pygame.KMOD_CTRL
        ):
            if self.file_path is None:
                self.status.prompt_saving = True
                self.status.prompting = True
                self.status.file_path = ""

                self.status.saved_state.cursor_pos = self.cursor
                self.status.saved_state.scroll_offset_x = self.scroll_offset_x
                self.status.saved_state.scroll_offset_y = self.scroll_offset_y

                self.cursor = 0
                self.scroll_offset_x = 0
                self.scroll_offset_y = 0
            else:
                self._save_file(self.file_path)

        if event.key == pygame.K_o and (
            event.mod & pygame.KMOD_META or event.mod & pygame.KMOD_CTRL
        ):
            self.status.prompt_loading = True
            self.status.prompting = True
            self.status.file_path = ""

            self.status.saved_state.cursor_pos = 0
            self.status.saved_state.scroll_offset_x = 0
            self.status.saved_state.scroll_offset_y = 0

            self.cursor = 0
            self.scroll_offset_x = 0
            self.scroll_offset_y = 0

    def _handle_mousewheel(self, event: Event) -> None:
        if abs(event.x) > abs(event.y):
            if self.buffer or self.status.prompting:
                self.scroll_offset_x += int(event.x * self.config.scroll_sens_x)
                if self.status.prompting:
                    self.scroll_offset_x = min(
                        len(self.status.file_path), max(0, self.scroll_offset_x)
                    )

                    _, col = self._get_cursor_rowcol()
                    if col < self.scroll_offset_x + len(self.status.get_flair()):
                        self._hshift_cursor(
                            self.scroll_offset_x + len(self.status.get_flair()) - col
                        )
                    elif col >= self.scroll_offset_x + self._get_max_cols():
                        self._hshift_cursor(
                            self.scroll_offset_x + self._get_max_cols() - col
                        )

                else:
                    self.scroll_offset_x = min(
                        max(0, max(map(len, self.buffer.splitlines(False))) - 1),
                        max(0, self.scroll_offset_x),
                    )

                    _, col = self._get_cursor_rowcol()
                    if col < self.scroll_offset_x:
                        self._hshift_cursor(self.scroll_offset_x - col + 1)
                    elif col + 1 > self.scroll_offset_x + self._get_max_cols():
                        self._hshift_cursor(
                            self.scroll_offset_x + self._get_max_cols() - col - 1
                        )
        else:
            if not self.status.prompting:
                self.scroll_offset_y -= int(event.y * self.config.scroll_sens_y)
                self.scroll_offset_y = min(
                    self.buffer.count("\n"), max(0, self.scroll_offset_y)
                )
                row, _ = self._get_cursor_rowcol()
                if row < self.scroll_offset_y:
                    self._vshift_cursor(self.scroll_offset_y - row)
                elif row + 1 > self.scroll_offset_y + self._get_max_rows():
                    self._vshift_cursor(
                        self.scroll_offset_y + self._get_max_rows() - row - 1
                    )

    def _handle_mousebuttondown(self, event: Event) -> None:
        if self.status.prompting:
            return

        if event.button == 1:
            pos = self._resolve_mouse_pos(event.pos[0], event.pos[1])
            self.selection.selecting = True
            self.selection.display = True
            self.selection.anchor = pos
            self.selection.start = pos
            self.selection.end = pos
            self.cursor = pos
            self._hshift_cursor(0)
            self._vshift_cursor(0)

    def _handle_mousebuttonup(self, event: Event) -> None:
        if self.status.prompting:
            return

        if event.button == 1:
            self.selection.selecting = False

            pos = self._resolve_mouse_pos(event.pos[0], event.pos[1])
            self.selection.start = min(self.selection.anchor, pos)
            self.selection.end = max(self.selection.anchor, pos)
            self.cursor = pos
            self._hshift_cursor(0)
            self._vshift_cursor(0)

            if self.selection.start == self.selection.end:
                self.selection.display = False

    def _handle_mousemotion(self, event) -> None:
        if self.status.prompting:
            return

        if self.selection.selecting:
            pos = self._resolve_mouse_pos(event.pos[0], event.pos[1])

            self.selection.start = min(self.selection.anchor, pos)
            self.selection.end = max(self.selection.anchor, pos)
            self.cursor = pos
            self._hshift_cursor(0)
            self._vshift_cursor(0)

    def handle_event(self, event: Event) -> None:
        match event.type:
            case pygame.TEXTINPUT:
                self._handle_textinput(event)
            case pygame.KEYDOWN:
                self._handle_keydown(event)
            case pygame.MOUSEWHEEL:
                self._handle_mousewheel(event)
            case pygame.MOUSEBUTTONDOWN:
                self._handle_mousebuttondown(event)
            case pygame.MOUSEBUTTONUP:
                self._handle_mousebuttonup(event)
            case pygame.MOUSEMOTION:
                self._handle_mousemotion(event)

    def tick(self) -> None:
        for key in self.repeat.keys():
            self.repeat[key].tick()

    def handle_pressed_keys(self, keys: PressedKeys) -> None:
        if keys[pygame.K_BACKSPACE] and self.repeat[pygame.K_BACKSPACE].check():
            self._backspace_text()
            self._vshift_cursor(0)
            self._hshift_cursor(0)
            self.status.saved = False

        if keys[pygame.K_LEFT] and self.repeat[pygame.K_LEFT].check():
            self._hshift_cursor(-1)
            self._vshift_cursor(0)

        if keys[pygame.K_RIGHT] and self.repeat[pygame.K_RIGHT].check():
            self._hshift_cursor(1)
            self._vshift_cursor(0)

        if keys[pygame.K_UP] and self.repeat[pygame.K_UP].check():
            self._vshift_cursor(-1)

        if keys[pygame.K_DOWN] and self.repeat[pygame.K_DOWN].check():
            self._vshift_cursor(1)

    def _draw_bg(self) -> None:
        self.screen.fill(self.config.theme.bg_color)

        if self.status.prompting:
            line = (
                self.buffer.count("\n", 0, self.status.saved_state.cursor_pos)
                - self.status.saved_state.scroll_offset_y
            )
        else:
            line = self.buffer.count("\n", 0, self.cursor) - self.scroll_offset_y

        pygame.draw.rect(
            self.screen,
            self.config.theme.line_color,
            pygame.Rect(
                0,
                line * self.font.get_height(),
                self.screen.get_width(),
                self.font.get_height(),
            ),
        )
        return

    def _draw_text(self) -> None:
        if self.status.prompting:
            scroll_offset_x = self.status.saved_state.scroll_offset_x
            scroll_offset_y = self.status.saved_state.scroll_offset_y
        else:
            scroll_offset_x = self.scroll_offset_x
            scroll_offset_y = self.scroll_offset_y

        lines = self._get_buffer_lines()
        last_idx = sum(len(line) for line in lines[:scroll_offset_y])
        for i, line in enumerate(
            lines[scroll_offset_y : scroll_offset_y + self._get_max_rows()]
        ):
            if (
                self.selection.display
                and last_idx + len(line) > self.selection.start
                and last_idx < self.selection.end
            ):
                local_start = max(0, self.selection.start - last_idx)
                local_end = min(len(line), self.selection.end - last_idx)

                t1_text = line[scroll_offset_x:local_start].replace("\n", "")

                t2_text = line[
                    max(scroll_offset_x, local_start) : max(scroll_offset_x, local_end)
                ].replace("\n", "")

                t3_text = line[max(scroll_offset_x, local_end) :].replace("\n", "")

                t1 = self.font.render(
                    t1_text,
                    self.config.antialias_text,
                    self.config.theme.text_color,
                )
                t2 = self.font.render(
                    t2_text,
                    self.config.antialias_text,
                    self.config.theme.text_selection_color,
                )
                t3 = self.font.render(
                    t3_text,
                    self.config.antialias_text,
                    self.config.theme.text_color,
                )

                t1_width = self.font.size(t1_text)[0]
                t2_width = self.font.size(t2_text)[0]

                pygame.draw.rect(
                    self.screen,
                    self.config.theme.bg_selection_color,
                    pygame.Rect(
                        self.config.gutter_size + t1_width,
                        i * self.font.get_height(),
                        t2_width,
                        self.font.get_height(),
                    ),
                )

                self.screen.blit(
                    t1, (self.config.gutter_size, i * self.font.get_height())
                )
                self.screen.blit(
                    t2,
                    (
                        self.config.gutter_size + t1_width,
                        i * self.font.get_height(),
                    ),
                )
                self.screen.blit(
                    t3,
                    (
                        self.config.gutter_size + t1_width + t2_width,
                        i * self.font.get_height(),
                    ),
                )

            else:
                text = self.font.render(
                    (
                        line[scroll_offset_x:]
                        if line and line[-1] != "\n"
                        else line[scroll_offset_x:-1]
                    ),
                    self.config.antialias_text,
                    self.config.theme.text_color,
                )

                self.screen.blit(
                    text, (self.config.gutter_size, i * self.font.get_height())
                )

            last_idx += len(line)

    def _draw_gutter(self) -> None:
        if self.status.prompting:
            cursor = self.status.saved_state.cursor_pos
            scroll_offset_y = self.status.saved_state.scroll_offset_y
        else:
            cursor = self.cursor
            scroll_offset_y = self.scroll_offset_y

        pygame.draw.rect(
            self.screen,
            self.config.theme.gutter_color,
            pygame.Rect(0, 0, self.config.gutter_size, self.screen.get_height()),
        )
        cursor_line = self.buffer.count("\n", 0, cursor) - scroll_offset_y

        for i in range(
            1,
            min(
                self._get_max_rows(), self.buffer.count("\n") + 1 - self.scroll_offset_y
            )
            + 1,
        ):
            line_no = f"{scroll_offset_y + i}"
            text = self.font.render(
                line_no,
                self.config.antialias_text,
                (
                    self.config.theme.gutter_line_no_color
                    if (i - 1) != cursor_line
                    else self.config.theme.gutter_current_line_no_color
                ),
            )
            self.screen.blit(
                text,
                (
                    self.config.gutter_size - self.font.size(line_no)[0] - 1,
                    (i - 1) * self.font.get_height(),
                ),
            )

    def _draw_statusline(self) -> None:
        pygame.draw.rect(
            self.screen,
            self.config.theme.statusline_color,
            pygame.Rect(
                0,
                self.screen.get_height() - self.config.statusline_height,
                self.screen.get_width(),
                self.config.statusline_height,
            ),
        )
        if self.status.prompting:
            statusline_text = ""
            statusline_text += self.status.get_flair()
            statusline_text += self.status.file_path[self.scroll_offset_x :]
            text = self.font.render(
                statusline_text,
                self.config.antialias_text,
                self.config.theme.statusline_text_color,
            )
            self.screen.blit(
                text,
                (
                    0,
                    (self.screen.get_height() - self.config.statusline_height)
                    + int(
                        (self.config.statusline_height - self.font.get_height()) // 2
                    ),
                ),
            )
            return

        statusline_text = ""
        statusline_text += self.status.get_flair()
        if self.file_path is None:
            statusline_text += "Unknown file"
        else:
            statusline_text += str(self.file_path)

        text = self.font.render(
            statusline_text,
            self.config.antialias_text,
            self.config.theme.statusline_text_color,
        )
        self.screen.blit(
            text,
            (
                0,
                (self.screen.get_height() - self.config.statusline_height)
                + int((self.config.statusline_height - self.font.get_height()) // 2),
            ),
        )

    def _draw_cursor(self) -> None:
        if self.status.prompting:
            column = self.cursor + len(self.status.get_flair())
            screen_column = column - self.scroll_offset_x
            x = screen_column * self.font.size(" ")[0]

            pygame.draw.rect(
                self.screen,
                self.config.theme.cursor_color,
                pygame.Rect(
                    x,
                    (self.screen.get_height() - self.config.statusline_height)
                    + int(
                        (self.config.statusline_height - self.font.get_height()) // 2
                    ),
                    2,
                    self.font.get_height(),
                ),
            )
            return

        line_start = self.buffer.rfind("\n", 0, self.cursor) + 1
        line = self.buffer.count("\n", 0, self.cursor) - self.scroll_offset_y
        column = self.cursor - line_start
        screen_column = column - self.scroll_offset_x
        if screen_column < 0:
            return

        x = self.config.gutter_size + screen_column * self.font.size(" ")[0]
        y = line * self.font.get_height()

        pygame.draw.rect(
            self.screen,
            self.config.theme.cursor_color,
            pygame.Rect(x, y, 2, self.font.get_height()),
        )
        return

    def draw_ui(self) -> None:
        self._draw_bg()
        self._draw_text()
        self._draw_gutter()
        self._draw_statusline()
        self._draw_cursor()
