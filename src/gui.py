import pygame
import asyncio
from config import CHAR_OPEN_IMG, CHAR_CLOSED_IMG

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
        
        try:
            raw_closed = pygame.image.load(CHAR_CLOSED_IMG).convert_alpha()
            raw_open = pygame.image.load(CHAR_OPEN_IMG).convert_alpha()
            
            # Scale to fit height (e.g. 80% of screen height)
            target_h = int(self.screen_h * 0.8)
            ratio = target_h / raw_closed.get_height()
            target_w = int(raw_closed.get_width() * ratio)
            
            self.img_closed = pygame.transform.smoothscale(raw_closed, (target_w, target_h))
            self.img_open = pygame.transform.smoothscale(raw_open, (target_w, target_h))
            
        except Exception as e:
            print(f"Error loading images: {e}")
            # Fallback
            self.img_closed = pygame.Surface((300, 300))
            self.img_closed.fill((0, 255, 0))
            self.img_open = pygame.Surface((300, 300))
            self.img_open.fill((255, 0, 0))

        self.current_img = self.img_closed
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

        
        # Simple animation logic: if speaking, toggle between open/closed
        if self.state == 3: # SPEAKING
            # Simple toggle every 5 frames (~100ms at 60fps)
            if (pygame.time.get_ticks() // 150) % 2 == 0:
                self.current_img = self.img_open
            else:
                self.current_img = self.img_closed
        else:
            self.current_img = self.img_closed

        # Center image
        x = (self.screen_w - self.current_img.get_width()) // 2
        y = (self.screen_h - self.current_img.get_height()) // 2
        self.screen.blit(self.current_img, (x, y))

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
