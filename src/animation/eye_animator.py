"""
EyeAnimator - Controls eye blinking animation
"""

import pygame
import random


class EyeAnimator:
    """
    Handles natural eye blinking animation independent of speech.

    Blinks occur at random intervals (3-6 seconds) with a smooth
    animation sequence.
    """

    def __init__(self):
        """Initialize the eye animator"""
        # Blink animation sequence
        self.blink_sequence = [
            'normal',
            'blink_half',
            'blink_closed',
            'blink_half',
            'normal'
        ]

        # Animation state
        self.blink_index = 0
        self.is_blinking = False

        # Timing
        self.last_blink_time = pygame.time.get_ticks()
        self.next_blink_delay = random.randint(3000, 6000)  # 3-6 seconds
        self.blink_frame_duration = 50  # milliseconds per blink frame
        self.blink_frame_start = 0

    def update(self):
        """
        Update animation state and return current eye state.

        Returns:
            str: Current eye state ('normal', 'blink_half', 'blink_closed')
        """
        now = pygame.time.get_ticks()

        # Handle active blink animation
        if self.is_blinking:
            # Check if it's time to advance to next blink frame
            if now - self.blink_frame_start > self.blink_frame_duration:
                self.blink_index += 1
                self.blink_frame_start = now

                # Check if blink is complete
                if self.blink_index >= len(self.blink_sequence):
                    # Blink finished
                    self.is_blinking = False
                    self.blink_index = 0
                    self.last_blink_time = now
                    # Schedule next blink with random delay
                    self.next_blink_delay = random.randint(3000, 6000)

            return self.blink_sequence[self.blink_index]

        # Check if it's time to start a new blink
        if now - self.last_blink_time > self.next_blink_delay:
            self.is_blinking = True
            self.blink_index = 0
            self.blink_frame_start = now
            return self.blink_sequence[0]

        # Default: eyes open
        return 'normal'
