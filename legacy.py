import os
from dataclasses import dataclass
from pathlib import Path

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame
import pyperclip

BUFFER = ""
CURSOR_POS = 0
SCROLL_OFFSET_Y = 0
SCROLL_OFFSET_X = 0

FILE_PATH = None


@dataclass
class Options:
    font_size = 15
    gutter_size = 30
    statusline_height = 20

    scroll_sens_x = 0.8
    scroll_sens_y = 1.0

    bg_color = (31, 31, 40)
    bg_selection_color = (34, 50, 73)
    line_color = (54, 54, 70)

    text_color = (220, 215, 186)
    text_selection_color = (220, 215, 186)

    cursor_color = (255, 160, 102)

    gutter_color = (42, 42, 55)
    gutter_line_no_color = (84, 84, 109)
    gutter_current_line_no_color = (255, 160, 102)

    statusline_color = (22, 22, 29)
    statusline_text_color = (200, 192, 147)


options = Options()

pygame.init()
pygame.font.init()

font = pygame.font.Font(
    pygame.font.match_font("monaspicearnerdfontmono"),
    size=options.font_size,
)

screen = pygame.display.set_mode(
    size=(0, 0), flags=pygame.RESIZABLE | pygame.WINDOWMAXIMIZED
)

pygame.display.set_caption(title="NEditor")


@dataclass
class Flags:
    flag_backspace_press: bool = False
    count_backspace_last: int = 0

    flag_left_press: bool = False
    count_left_last: int = 0
    flag_right_press: bool = False
    count_right_last: int = 0
    flag_up_press: bool = False
    count_up_last: int = 0
    flag_down_press: bool = False
    count_down_last: int = 0

    saved: bool = False
    saving: bool = False
    loading: bool = False

    prompt_file: bool = False
    tmp_file_path: str = ""
    pre_prompt_cursor_pos: int = 0

    selecting: bool = False
    display_selection: bool = False
    selection_anchor: int = 0
    selection_start: int = 0
    selection_end: int = 0


def update_flags(flags):
    flags.flag_backspace_press = False
    flags.flag_left_press = False
    flags.flag_right_press = False
    flags.flag_up_press = False
    flags.flag_down_press = False
    flags.count_backspace_last += 1
    flags.count_left_last += 1
    flags.count_right_last += 1
    flags.count_up_last += 1
    flags.count_down_last += 1


def insert(text):
    global BUFFER, CURSOR_POS
    if flags.prompt_file:
        flags.tmp_file_path = (
            flags.tmp_file_path[:CURSOR_POS] + text + flags.tmp_file_path[CURSOR_POS:]
        )
        CURSOR_POS += len(text)
        return

    BUFFER = BUFFER[:CURSOR_POS] + text + BUFFER[CURSOR_POS:]
    CURSOR_POS += len(text)


def backspace():
    global BUFFER, CURSOR_POS

    if CURSOR_POS == 0:
        return

    if flags.prompt_file:
        flags.tmp_file_path = (
            flags.tmp_file_path[: CURSOR_POS - 1] + flags.tmp_file_path[CURSOR_POS:]
        )
        CURSOR_POS -= 1
        return

    BUFFER = BUFFER[: CURSOR_POS - 1] + BUFFER[CURSOR_POS:]
    CURSOR_POS -= 1


def shift_cursor(n: int):
    global CURSOR_POS
    if flags.prompt_file:
        CURSOR_POS = max(0, min(len(flags.tmp_file_path), CURSOR_POS + n))
        return
    CURSOR_POS = max(0, min(len(BUFFER), CURSOR_POS + n))


def get_max_cols(screen):
    return (screen.get_width() - options.gutter_size) // font.size(" ")[0]


def hshift_cursor(n):
    global CURSOR_POS, SCROLL_OFFSET_X

    shift_cursor(n)
    if flags.prompt_file:
        visible = get_max_cols(screen)
        column = CURSOR_POS + 5
        if column < SCROLL_OFFSET_X:
            SCROLL_OFFSET_X = CURSOR_POS
        elif column >= SCROLL_OFFSET_X + visible:
            SCROLL_OFFSET_X = column - visible + 1
        return

    line_start = BUFFER.rfind("\n", 0, CURSOR_POS) + 1
    column = CURSOR_POS - line_start

    visible = get_max_cols(screen)

    if column < SCROLL_OFFSET_X:
        SCROLL_OFFSET_X = column
    elif column >= SCROLL_OFFSET_X + visible:
        SCROLL_OFFSET_X = column - visible + 1


def get_max_lines(screen):
    return int((screen.get_height() - options.statusline_height) // font.get_height())


def vshift_cursor(n: int):
    global BUFFER, CURSOR_POS, SCROLL_OFFSET_Y, screen
    if flags.prompt_file:
        return

    line_start = BUFFER.rfind("\n", 0, CURSOR_POS) + 1
    cursor_line = BUFFER.count("\n", 0, CURSOR_POS)

    x = CURSOR_POS - line_start + 1

    lines = BUFFER.splitlines(True)
    if not lines or lines[-1][-1] == "\n":
        lines = lines + [""]

    if not (0 <= cursor_line + n < len(lines)):
        return

    start = sum(map(len, lines[: cursor_line + n]))
    line = lines[cursor_line + n].rstrip("\n")
    CURSOR_POS = start + min(x, len(line) + 1) - 1

    if cursor_line + n >= SCROLL_OFFSET_Y + get_max_lines(screen):
        SCROLL_OFFSET_Y = cursor_line + n - get_max_lines(screen) + 1
    elif cursor_line + n <= SCROLL_OFFSET_Y:
        SCROLL_OFFSET_Y = cursor_line + n


def draw_bg(screen):
    global options, BUFFER
    screen.fill(options.bg_color)

    if flags.prompt_file:
        line = BUFFER.count("\n", 0, flags.pre_prompt_cursor_pos) - SCROLL_OFFSET_Y
    else:
        line = BUFFER.count("\n", 0, CURSOR_POS) - SCROLL_OFFSET_Y

    pygame.draw.rect(
        screen,
        options.line_color,
        pygame.Rect(0, line * font.get_height(), screen.get_width(), font.get_height()),
    )


def draw_text(screen):
    global BUFFER, options

    last_idx = 0
    for i, line in enumerate(
        BUFFER.splitlines(True)[
            SCROLL_OFFSET_Y : SCROLL_OFFSET_Y + get_max_lines(screen)
        ]
    ):
        if (
            flags.display_selection
            and last_idx + len(line) > flags.selection_start
            and last_idx < flags.selection_end
        ):
            local_start = max(0, flags.selection_start - last_idx)
            local_end = min(len(line), flags.selection_end - last_idx)
            t1 = font.render(
                line[SCROLL_OFFSET_X:local_start].replace("\n", ""),
                True,
                options.text_color,
            )
            t2 = font.render(
                line[local_start:local_end].replace("\n", ""),
                True,
                options.text_selection_color,
            )
            t3 = font.render(
                line[local_end:].replace("\n", ""),
                True,
                options.text_color,
            )

            pygame.draw.rect(
                screen,
                options.bg_selection_color,
                pygame.Rect(
                    options.gutter_size + font.size(line[:local_start])[0],
                    i * font.get_height(),
                    font.size(line[local_start:local_end].replace("\n", ""))[0],
                    font.get_height(),
                ),
            )
            screen.blit(t1, (options.gutter_size, i * font.get_height()))
            screen.blit(
                t2,
                (
                    options.gutter_size + font.size(line[:local_start])[0],
                    i * font.get_height(),
                ),
            )
            screen.blit(
                t3,
                (
                    options.gutter_size + font.size(line[SCROLL_OFFSET_X:local_end])[0],
                    i * font.get_height(),
                ),
            )

        else:
            text = font.render(
                (
                    line[SCROLL_OFFSET_X:]
                    if line and line[-1] != "\n"
                    else line[SCROLL_OFFSET_X:-1]
                ),
                True,
                options.text_color,
            )
            screen.blit(text, (options.gutter_size, i * font.get_height()))
        last_idx += len(line)


def draw_cursor(screen):
    global options

    if flags.prompt_file:
        column = CURSOR_POS + 5
        screen_column = column - SCROLL_OFFSET_X
        x = screen_column * font.size(" ")[0]

        pygame.draw.rect(
            screen,
            options.cursor_color,
            pygame.Rect(
                x,
                (screen.get_height() - options.statusline_height)
                + int((options.statusline_height - font.get_height()) // 2),
                2,
                font.get_height(),
            ),
        )
        return

    line_start = BUFFER.rfind("\n", 0, CURSOR_POS) + 1
    line = BUFFER.count("\n", 0, CURSOR_POS) - SCROLL_OFFSET_Y
    column = CURSOR_POS - line_start
    screen_column = column - SCROLL_OFFSET_X
    if screen_column < 0:
        return

    x = options.gutter_size + screen_column * font.size(" ")[0]
    y = line * font.get_height()

    pygame.draw.rect(
        screen,
        options.cursor_color,
        pygame.Rect(x, y, 2, font.get_height()),
    )


def draw_gutter(screen: pygame.Surface):
    global options, BUFFER, CURSOR_POS

    pygame.draw.rect(
        screen,
        options.gutter_color,
        pygame.Rect(0, 0, options.gutter_size, screen.get_height()),
    )
    if flags.prompt_file:
        cursor_line = (
            BUFFER.count("\n", 0, flags.pre_prompt_cursor_pos) - SCROLL_OFFSET_Y
        )
    else:
        cursor_line = BUFFER.count("\n", 0, CURSOR_POS) - SCROLL_OFFSET_Y
    for i in range(
        1, min(get_max_lines(screen), BUFFER.count("\n") + 1 - SCROLL_OFFSET_Y) + 1
    ):
        line_no = f"{SCROLL_OFFSET_Y + i}"
        text = font.render(
            line_no,
            True,
            (
                options.gutter_line_no_color
                if (i - 1) != cursor_line
                else options.gutter_current_line_no_color
            ),
        )
        screen.blit(
            text,
            (
                options.gutter_size - font.size(line_no)[0] - 1,
                (i - 1) * font.get_height(),
            ),
        )


def draw_statusline(screen):
    global options
    pygame.draw.rect(
        screen,
        options.statusline_color,
        pygame.Rect(
            0,
            screen.get_height() - options.statusline_height,
            screen.get_width(),
            options.statusline_height,
        ),
    )
    if flags.prompt_file:
        statusline_text = " "
        statusline_text += "[*] "
        statusline_text += flags.tmp_file_path
        text = font.render(statusline_text, True, options.statusline_text_color)
        screen.blit(
            text,
            (
                0,
                (screen.get_height() - options.statusline_height)
                + int((options.statusline_height - font.get_height()) // 2),
            ),
        )
        return

    statusline_text = " "
    if not flags.saved:
        statusline_text += "[*] "
    if FILE_PATH is None:
        statusline_text += "Unknown file"
    else:
        statusline_text += FILE_PATH
    text = font.render(statusline_text, True, options.statusline_text_color)
    screen.blit(
        text,
        (
            0,
            (screen.get_height() - options.statusline_height)
            + int((options.statusline_height - font.get_height()) // 2),
        ),
    )


def draw_ui(screen):
    draw_bg(screen)
    draw_text(screen)
    draw_gutter(screen)
    draw_statusline(screen)
    draw_cursor(screen)


def resolve_mouse_pos(x, y):
    global BUFFER, SCROLL_OFFSET_X, SCROLL_OFFSET_Y, options

    nlines = BUFFER.count("\n") + 1

    line_idx = min(nlines - 1, SCROLL_OFFSET_Y + y // font.get_height())
    lines = BUFFER.splitlines(True)
    if not lines or lines[-1][-1] == "\n":
        lines = lines + [""]

    line = lines[line_idx]
    line_start_idx = sum(map(len, lines[:line_idx]))
    return line_start_idx + max(
        0,
        min(
            len(line) - 1 if line and line[-1] == "\n" else len(line),
            SCROLL_OFFSET_X + int((x - options.gutter_size) // (font.size(" ")[0])),
        ),
    )


def save_file(file_path):
    global FILE_PATH, BUFFER
    path = Path(file_path)

    if not path.is_absolute():
        path = Path.cwd() / path

    path = path.resolve(strict=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(BUFFER)
    flags.saved = True
    if FILE_PATH is None:
        FILE_PATH = file_path


def load_file(file_path):
    global FILE_PATH, BUFFER
    path = Path(file_path)

    if not path.is_absolute():
        path = Path.cwd() / path

    path = path.resolve(strict=False)
    path.parent.mkdir(parents=True, exist_ok=True)

    path.touch(exist_ok=True)

    FILE_PATH = file_path
    flags.saved = True
    with open(path, "r") as f:
        BUFFER = f.read()


running = True
clock = pygame.time.Clock()
flags = Flags()

while running:
    clock.tick(60)

    update_flags(flags)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.TEXTINPUT:
            insert(event.text)
            hshift_cursor(0)
            vshift_cursor(0)
            flags.saved = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                if flags.prompt_file:
                    flags.prompt_file = False
                    CURSOR_POS = flags.pre_prompt_cursor_pos
                    flags.pre_prompt_cursor_pos = 0
                    if flags.saving:
                        save_file(flags.tmp_file_path)
                        flags.saving = False
                    elif flags.loading:
                        load_file(flags.tmp_file_path)
                        flags.loading = False
                else:
                    insert("\n")
                    vshift_cursor(0)
                    hshift_cursor(0)
                    flags.saved = False

            elif event.key == pygame.K_TAB:
                insert(" " * 4)
                hshift_cursor(0)
                flags.saved = False

            elif event.key == pygame.K_BACKSPACE:
                backspace()
                flags.flag_backspace_press = True
                flags.count_backspace_last = 0
                vshift_cursor(0)
                hshift_cursor(0)
                flags.saved = False

            elif event.key == pygame.K_LEFT:
                hshift_cursor(-1)
                flags.flag_left_press = True
                flags.count_left_last = 0

            elif event.key == pygame.K_RIGHT:
                hshift_cursor(1)
                flags.flag_right_press = True
                flags.count_right_last = 0

            elif event.key == pygame.K_UP:
                vshift_cursor(-1)
                flags.flag_up_press = True
                flags.count_up_last = 0

            elif event.key == pygame.K_DOWN:
                vshift_cursor(1)
                flags.flag_down_press = True
                flags.count_down_last = 0

            elif event.key == pygame.K_v and (
                event.mod & pygame.KMOD_META or event.mod & pygame.KMOD_CTRL
            ):
                paste = pyperclip.paste()
                insert(paste)
                hshift_cursor(0)
                vshift_cursor(0)
                flags.saved = False

            elif event.key == pygame.K_s and (
                event.mod & pygame.KMOD_META or event.mod & pygame.KMOD_CTRL
            ):
                if FILE_PATH is None:
                    flags.saving = True
                    flags.prompt_file = True
                    flags.tmp_file_path = ""
                    flags.pre_prompt_cursor_pos = CURSOR_POS
                    CURSOR_POS = 0
                else:
                    save_file(FILE_PATH)

            if event.key == pygame.K_c and (
                event.mod & pygame.KMOD_META or event.mod & pygame.KMOD_CTRL
            ):
                if flags.display_selection:
                    flags.display_selection = False
                    if flags.selection_end != flags.selection_start:
                        if flags.selection_end < flags.selection_start:
                            flags.selection_end, flags.selection_start = (
                                flags.selection_start,
                                flags.selection_end,
                            )
                        pyperclip.copy(
                            BUFFER[flags.selection_start : flags.selection_end]
                        )

            if event.key == pygame.K_o and (
                event.mod & pygame.KMOD_META or event.mod & pygame.KMOD_CTRL
            ):
                flags.loading = True
                flags.prompt_file = True
                flags.tmp_file_path = ""
                flags.pre_prompt_cursor_pos = CURSOR_POS
                CURSOR_POS = 0

        if event.type == pygame.MOUSEWHEEL:
            hscroll = event.x
            vscroll = event.y

            if abs(hscroll) > abs(vscroll):
                if BUFFER:
                    SCROLL_OFFSET_X += int(event.x * options.scroll_sens_x)
                    SCROLL_OFFSET_X = min(
                        max(0, max(map(len, BUFFER.splitlines(False))) - 1),
                        max(0, SCROLL_OFFSET_X),
                    )
            else:
                SCROLL_OFFSET_Y -= int(event.y * options.scroll_sens_y)
                SCROLL_OFFSET_Y = min(BUFFER.count("\n"), max(0, SCROLL_OFFSET_Y))

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                x, y = event.pos
                pos = resolve_mouse_pos(x, y)
                flags.selecting = True
                flags.display_selection = True
                flags.selection_anchor = pos
                flags.selection_start = pos
                flags.selection_end = pos
                CURSOR_POS = pos

        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                flags.selecting = False
                x, y = event.pos
                pos = resolve_mouse_pos(x, y)
                flags.selection_start = min(flags.selection_anchor, pos)
                flags.selection_end = max(flags.selection_anchor, pos)

                CURSOR_POS = pos
                if flags.selection_start == flags.selection_end:
                    flags.display_selection = False

        if event.type == pygame.MOUSEMOTION:
            if flags.selecting:
                x, y = event.pos
                pos = resolve_mouse_pos(x, y)

                flags.selection_start = min(flags.selection_anchor, pos)
                flags.selection_end = max(flags.selection_anchor, pos)
                CURSOR_POS = pos

    keys = pygame.key.get_pressed()

    if (
        keys[pygame.K_BACKSPACE]
        and not flags.flag_backspace_press
        and flags.count_backspace_last > 30
    ):
        backspace()
        vshift_cursor(0)
        hshift_cursor(0)
        flags.saved = False

    if keys[pygame.K_LEFT] and not flags.flag_left_press and flags.count_left_last > 30:
        hshift_cursor(-1)

    if (
        keys[pygame.K_RIGHT]
        and not flags.flag_right_press
        and flags.count_right_last > 30
    ):
        hshift_cursor(1)

    if keys[pygame.K_UP] and not flags.flag_up_press and flags.count_up_last > 30:
        vshift_cursor(-1)

    if keys[pygame.K_DOWN] and not flags.flag_down_press and flags.count_down_last > 30:
        vshift_cursor(1)

    draw_ui(screen)
    pygame.display.flip()

pygame.quit()
