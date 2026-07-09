import os

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
os.environ["SDL_VIDEO_HIGHDPI_DISABLED"] = "0"

import pygame

from editor import Editor, EditorConfig
from explorer import Explorer, ExplorerConfig


class Stage:
    def __init__(self) -> None:
        pygame.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode(
            (0, 0), flags=pygame.RESIZABLE | pygame.WINDOWMAXIMIZED
        )
        pygame.display.set_caption(title="NEditor")
        self.editor = Editor(config=EditorConfig(), surface=self.screen)
        self.explorer = Explorer(config=ExplorerConfig(), surface=self.screen)

        self.active = self.explorer

    def run(self) -> None:
        running = True
        clock = pygame.time.Clock()

        while running:
            clock.tick(self.editor.config.render_fps)
            self.active.tick()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_t and (
                        event.mod & pygame.KMOD_META | event.mod & pygame.KMOD_CTRL
                    ):
                        if isinstance(self.active, Explorer):
                            self.active = self.editor
                        else:
                            self.active = self.explorer

                self.active.handle_event(event)

            keys = pygame.key.get_pressed()
            self.active.handle_pressed_keys(keys)
            self.active.draw_ui()

            if isinstance(self.active, Explorer):
                file = self.active.file_path
                if file is not None:
                    self.editor._load_file(file)
                    self.active.reset()
                    self.active = self.editor

            pygame.display.flip()
