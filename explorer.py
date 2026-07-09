import os
import pathlib
from pathlib import Path

from pygame.constants import K_UP

from utils import (
    Event,
    ExplorerConfig,
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


class File:
    def __init__(self, path: Path):
        self.path = path

    @property
    def name(self):
        return self.path.name


class Directory:
    def __init__(self, path: Path):
        self.path: Path = path
        self.opened: bool = False
        self.children: list[Directory | File] | None = None

    def update_children(self):
        self.children = [
            Directory(p) if p.is_dir() else File(p) for p in self.path.iterdir()
        ]

    @property
    def name(self):
        return self.path.name

    def open(self):
        self.opened = True
        self.update_children()

    def close(self):
        self.opened = False

    def toggle(self):
        if self.opened:
            self.close()
        else:
            self.open()


Node = Directory | File
Depth = int
TreeEntry = tuple[Node, Depth]
Tree = list[TreeEntry]


class Explorer:
    def __init__(self, config: ExplorerConfig, surface: Surface):
        self.active_line: int = 0
        self.scroll_offset_x: int = 0
        self.scroll_offset_y: int = 0

        self.config: ExplorerConfig = config
        self.font: Font = pygame.font.Font(
            pygame.font.match_font(self.config.font_name),
            size=self.config.font_size,
        )

        repeat_key_list = [
            pygame.K_UP,
            pygame.K_DOWN,
        ]
        self.repeat: dict[Key, RepeatKey] = dict()
        for key in repeat_key_list:
            self.repeat[key] = RepeatKey()

        self.screen: Surface = surface

        self.selected: bool = False
        self.file_path: Path | None = None
        self.cwd: Path = Path.cwd()

        self.root: Directory = Directory(self.cwd)
        self.root.open()

        self.tree: list[TreeEntry] = self._flatten(self.root)

    def _flatten(self, node: Node, depth=0) -> Tree:
        result: Tree = [(node, depth)]

        if isinstance(node, File) or not node.opened:
            return result

        if node.children is None:
            node.update_children()
            assert node.children is not None, "Error updating children."

        children_sorted = sorted(
            node.children, key=lambda x: (isinstance(x, File), x.name.lower())
        )
        for child in children_sorted:
            result += self._flatten(child, depth=depth + 1)
        return result

    def _shift_line(self, n: int) -> None:
        self.active_line += n
        self.active_line = max(0, min(len(self.tree) - 1, self.active_line))

    def _handle_keydown(self, event: Event) -> None:
        if event.key == pygame.K_RETURN:
            item, _ = self.tree[self.active_line]
            if isinstance(item, Directory):
                item.toggle()
                self.tree = self._flatten(self.root)
            if isinstance(item, File):
                self.selected = True
                self.file_path = item.path

        elif event.key == pygame.K_UP:
            self._shift_line(-1)
            self.repeat[pygame.K_UP].press()

        elif event.key == pygame.K_DOWN:
            self._shift_line(1)
            self.repeat[pygame.K_DOWN].press()

    def _handle_mousewheel(self, event: Event) -> None:
        pass

    def _handle_mousebuttondown(self, event: Event) -> None:
        pass

    def handle_event(self, event: Event) -> None:
        match event.type:
            case pygame.KEYDOWN:
                self._handle_keydown(event)
            case pygame.MOUSEWHEEL:
                self._handle_mousewheel(event)
            case pygame.MOUSEBUTTONDOWN:
                self._handle_mousebuttondown(event)

    def tick(self) -> None:
        for key in self.repeat.keys():
            self.repeat[key].tick()

    def handle_pressed_keys(self, keys: PressedKeys) -> None:
        if keys[pygame.K_UP] and self.repeat[pygame.K_UP].check():
            self._shift_line(-1)

        if keys[pygame.K_DOWN] and self.repeat[pygame.K_DOWN].check():
            self._shift_line(1)

    def _draw_bg(self) -> None:
        self.screen.fill(self.config.theme.bg_color)
        pygame.draw.rect(
            self.screen,
            self.config.theme.line_color,
            pygame.Rect(
                0,
                self.active_line * self.font.get_height(),
                self.screen.get_width(),
                self.font.get_height(),
            ),
        )

    def _draw_tree(self) -> None:
        for i, (item, depth) in enumerate(self.tree):
            indent = " " * 4 * depth
            if isinstance(item, Directory):
                text = self.font.render(
                    indent + "[D] " + item.name, True, self.config.theme.directory_color
                )
                self.screen.blit(text, (0, i * self.font.get_height()))

            else:
                text = self.font.render(
                    indent + "[F] " + item.name, True, self.config.theme.file_color
                )
                self.screen.blit(text, (0, i * self.font.get_height()))

    def draw_ui(self) -> None:
        self._draw_bg()
        self._draw_tree()

    def reset(self) -> None:
        self.active_line = 0
        self.scroll_offset_x = 0
        self.scroll_offset_y = 0

        self.selected = False
        self.file_path = None
        self.cwd = Path.cwd()

        self.root = Directory(self.cwd)
        self.root.open()

        self.tree = self._flatten(self.root)
