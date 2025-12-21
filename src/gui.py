import pygame
import asyncio
import config

# Try absolute import first, fall back to relative
try:
    from src.animation.character_renderer import CharacterRenderer
    from src.animation.animation_controller import AnimationController
except ImportError:
    from .animation.character_renderer import CharacterRenderer
    from .animation.animation_controller import AnimationController

class GUIHandler:
    def __init__(self):
        # pygame.init() initializes all modules including mixer, which invalidates PyAudio on Pi
        pygame.display.init() 
        if pygame.font.get_init() is False:
            pygame.font.init()
        # Helper for fullscreen toggling if needed, but defaults to fullscreen
        try:
             self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        except:
             print("Fullscreen failed, falling back to windowed")
             self.screen = pygame.display.set_mode((800, 600))
             
        pygame.display.set_caption("Kikai-kun")
        self.screen_w, self.screen_h = self.screen.get_size()

        # Initialize Live2D-style character animation system
        try:
            print(f"Initializing character animation system...")
            print(f"Assets directory: {config.CHAR_ASSETS_DIR}")
            self.character = CharacterRenderer(
                screen_height=self.screen_h,
                assets_dir=config.CHAR_ASSETS_DIR
            )
            print(f"CharacterRenderer created successfully")
            self.animator = AnimationController(self.character)
            print(f"AnimationController created successfully")
        except Exception as e:
            print(f"ERROR initializing character animation: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to simple colored square
            self.character = None
            self.animator = None
            print(f"Using fallback colored square")
        self.state = 0 # 0: Waiting/Idle, 1: Listening, 2: Processing, 3: Speaking
        self.running = True
        self.clock = pygame.time.Clock()

        # Text display - Use Japanese font
        try:
            # Try common Japanese fonts on Raspberry Pi
            font_candidates = [
                "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
                "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf",
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/truetype/takao-gothic/TakaoPGothic.ttf"
            ]
            font_loaded = False
            for font_path in font_candidates:
                try:
                    import os
                    if os.path.exists(font_path):
                        self.font = pygame.font.Font(font_path, 32)
                        print(f"Loaded font: {font_path}")
                        font_loaded = True
                        break
                except:
                    continue

            if not font_loaded:
                # Fallback to system font with Japanese support
                self.font = pygame.font.SysFont("notosanscjk,ipaexgothic,ipagothic,takao,sans-serif", 32)
                print("Using system font")
        except Exception as e:
            print(f"Font loading error: {e}, using default")
            self.font = pygame.font.Font(None, 32)

        self.user_text = ""
        self.agent_text = ""

        # Pagination for long text
        self.user_text_pages = []
        self.agent_text_pages = []
        self.user_page_index = 0
        self.agent_page_index = 0
        self.last_page_switch_time = 0
        self.page_switch_interval = 3000  # 3 seconds per page

    def update(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
                    self.running = False

        self.screen.fill((255, 255, 255)) # White background
        
        # Listening Indicator (Green Circle in top right)
        if self.state == 1: # LISTENING
            pygame.draw.circle(self.screen, (0, 255, 0), (self.screen_w - 50, 50), 30)
        elif self.state == 2: # PROCESSING (Yellow)
            pygame.draw.circle(self.screen, (255, 255, 0), (self.screen_w - 50, 50), 30)


        # Render animated character
        if self.animator:
            # Update animation state
            self.animator.set_state(self.state)

            # Get current animation frame
            character_surface = self.animator.get_frame()

            # Center and blit character
            x = (self.screen_w - character_surface.get_width()) // 2
            y = (self.screen_h - character_surface.get_height()) // 2
            self.screen.blit(character_surface, (x, y))
        else:
            # Fallback: draw simple square
            fallback_size = int(self.screen_h * 0.5)
            fallback_surf = pygame.Surface((fallback_size, fallback_size))
            fallback_surf.fill((0, 255, 0) if self.state != 3 else (255, 0, 0))
            x = (self.screen_w - fallback_size) // 2
            y = (self.screen_h - fallback_size) // 2
            self.screen.blit(fallback_surf, (x, y))

        # Auto-switch pages for long text
        current_time = pygame.time.get_ticks()
        if current_time - self.last_page_switch_time > self.page_switch_interval:
            self.last_page_switch_time = current_time

            # Switch user text page
            if len(self.user_text_pages) > 1:
                self.user_page_index = (self.user_page_index + 1) % len(self.user_text_pages)

            # Switch agent text page
            if len(self.agent_text_pages) > 1:
                self.agent_page_index = (self.agent_page_index + 1) % len(self.agent_text_pages)

        # Display text with pagination
        # User text at top (max 2 lines per page)
        if self.user_text_pages and self.user_page_index < len(self.user_text_pages):
            page_indicator = f" ({self.user_page_index + 1}/{len(self.user_text_pages)})" if len(self.user_text_pages) > 1 else ""
            self._render_multiline_text(self.user_text_pages[self.user_page_index] + page_indicator, (0, 0, 0), 20, 20, max_width=self.screen_w - 40, max_lines=2)

        # Agent text at bottom (max 3 lines per page)
        if self.agent_text_pages and self.agent_page_index < len(self.agent_text_pages):
            line_height = self.font.get_height() + 2
            agent_y = self.screen_h - (3 * line_height + 30)
            page_indicator = f" ({self.agent_page_index + 1}/{len(self.agent_text_pages)})" if len(self.agent_text_pages) > 1 else ""
            self._render_multiline_text(self.agent_text_pages[self.agent_page_index] + page_indicator, (0, 0, 255), 20, agent_y, max_width=self.screen_w - 40, max_lines=3)

        pygame.display.flip()
        self.clock.tick(60)

    def _split_text_into_pages(self, text, max_width, max_lines):
        """Splits text into multiple pages that fit within max_lines"""
        lines = []
        current_line = ""

        # Character-by-character wrapping (works better for Japanese)
        for char in text:
            test_line = current_line + char
            test_surface = self.font.render(test_line, True, (0, 0, 0))

            if test_surface.get_width() <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                    current_line = char
                else:
                    lines.append(char)
                    current_line = ""

        if current_line:
            lines.append(current_line)

        # Split lines into pages
        pages = []
        for i in range(0, len(lines), max_lines):
            page = "\n".join(lines[i:i + max_lines])
            pages.append(page)

        return pages if pages else [""]

    def _render_multiline_text(self, text, color, x, y, max_width, max_lines=3):
        """Renders text with automatic character-based wrapping for Japanese"""
        lines = text.split('\n')

        # Render each line
        line_height = self.font.get_height() + 2
        for i, line in enumerate(lines[:max_lines]):
            line_surface = self.font.render(line, True, color)
            self.screen.blit(line_surface, (x, y + i * line_height))

    def set_state(self, state_code):
        self.state = state_code

    def set_user_text(self, text):
        self.user_text = text
        self.user_text_pages = self._split_text_into_pages(f"You: {text}", self.screen_w - 40, 2)
        self.user_page_index = 0
        self.last_page_switch_time = pygame.time.get_ticks()

    def set_agent_text(self, text):
        self.agent_text = text
        self.agent_text_pages = self._split_text_into_pages(f"Kikai-kun: {text}", self.screen_w - 40, 3)
        self.agent_page_index = 0
        self.last_page_switch_time = pygame.time.get_ticks()

    def quit(self):
        pygame.quit()
