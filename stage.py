import os

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame

from editor import Editor, EditorConfig


class Stage:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode(
            (0, 0), flags=pygame.RESIZABLE | pygame.WINDOWMAXIMIZED
        )
        pygame.display.set_caption(title="NEditor")
        self.editor = Editor(config=EditorConfig(), surface=self.screen)

    def run(self):
        running = True
        clock = pygame.time.Clock()

        while running:
            clock.tick(self.editor.config.render_fps)
            self.editor.tick()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                else:
                    self.editor.hande_event(event)

            keys = pygame.key.get_pressed()
            self.editor.handle_pressed_keys(keys)
            self.editor.draw_ui()
            pygame.display.flip()
