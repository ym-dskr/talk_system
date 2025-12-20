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
        
        pygame.display.flip()
        self.clock.tick(60)

    def set_state(self, state_code):
        self.state = state_code

    def quit(self):
        pygame.quit()
