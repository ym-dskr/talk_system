"""
瞬きアニメーター - 目の瞬きを制御

発話状態に関係なく独立して動作し、
ランダムな間隔で自然な瞬きアニメーションを実現します。
"""

import pygame
import random


class EyeAnimator:
    """
    自然な目の瞬きを制御するクラス

    瞬きは3-6秒のランダムな間隔で発生し、
    各瞬きは5フレーム（normal → half → closed → half → normal）で構成されます。
    口パクアニメーションとは完全に独立して動作し、
    より自然なキャラクター表現を実現しています。

    瞬きシーケンス:
    - フレーム1: normal（通常）
    - フレーム2: blink_half（半目） - 50ms
    - フレーム3: blink_closed（閉じ） - 50ms
    - フレーム4: blink_half（半目） - 50ms
    - フレーム5: normal（通常）
    合計: 150ms（瞬き1回）
    """

    def __init__(self):
        """瞬きアニメーターを初期化"""
        # 瞬きアニメーションシーケンス
        self.blink_sequence = [
            'normal',        # 目を開いている
            'blink_half',    # 半目
            'blink_closed',  # 目を閉じている
            'blink_half',    # 半目
            'normal'         # 目を開いている
        ]

        # アニメーション状態
        self.blink_index = 0           # 現在の瞬きシーケンス内位置
        self.is_blinking = False       # 瞬き実行中かどうか

        # タイミング制御
        self.last_blink_time = pygame.time.get_ticks()  # 最後に瞬きした時刻
        self.next_blink_delay = random.randint(3000, 6000)  # 次の瞬きまでの待機時間（3-6秒）
        self.blink_frame_duration = 50  # 瞬きの各フレーム持続時間（ミリ秒）
        self.blink_frame_start = 0      # 現在のフレームの開始時刻

    def update(self):
        """
        アニメーション状態を更新し、現在の目の状態を返す

        瞬き中は50msごとにシーケンスを進行し、
        瞬きが完了したら次の瞬きまでのランダムな待機時間を設定します。

        Returns:
            str: 現在の目の状態
                - 'normal': 通常（目を開いている）
                - 'blink_half': 半目
                - 'blink_closed': 目を閉じている
        """
        now = pygame.time.get_ticks()

        # 瞬き実行中の処理
        if self.is_blinking:
            # フレーム持続時間が経過したかチェック
            if now - self.blink_frame_start > self.blink_frame_duration:
                self.blink_index += 1
                self.blink_frame_start = now

                # 瞬きシーケンスが完了したかチェック
                if self.blink_index >= len(self.blink_sequence):
                    # 瞬き完了
                    self.is_blinking = False
                    self.blink_index = 0
                    self.last_blink_time = now
                    # 次の瞬きまでのランダムな待機時間を設定（3-6秒）
                    self.next_blink_delay = random.randint(3000, 6000)

            return self.blink_sequence[self.blink_index]

        # 次の瞬きを開始すべきかチェック
        if now - self.last_blink_time > self.next_blink_delay:
            self.is_blinking = True
            self.blink_index = 0
            self.blink_frame_start = now
            return self.blink_sequence[0]

        # デフォルト: 目を開いている
        return 'normal'
