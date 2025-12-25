"""
体アニメーター - 体の自然な動きを制御

呼吸による上下の動き、アイドル時の左右揺れ、
発話時の傾きなど、体全体の動きを制御します。
"""

import pygame
import math


class BodyAnimator:
    """
    体の動きを制御するクラス

    以下の動きを組み合わせて自然な体の動きを実現：
    1. 呼吸モーション: ゆっくりとした上下の動き（常時）
    2. アイドル揺れ: 左右への微細な揺れ（待機中）
    3. スピーチ傾き: 発話時の動的な傾き

    座標変換:
    - offset_y: 縦方向のオフセット（呼吸モーション）
    - offset_x: 横方向のオフセット（アイドル揺れ）
    - rotation: 回転角度（発話時の傾き）
    - scale: スケール（呼吸時の拡大縮小）
    """

    def __init__(self):
        """体アニメーターを初期化"""
        # 呼吸モーション（常時動作）
        self.breath_time = 0.0           # 呼吸サイクル時間（秒）
        self.breath_cycle = 3.0          # 呼吸1サイクルの長さ（秒）
        self.breath_amplitude = 8.0      # 上下の振幅（ピクセル）
        self.breath_scale_amp = 0.015    # スケール変化の振幅

        # アイドル揺れ（待機中のみ）
        self.idle_time = 0.0             # アイドル揺れ時間（秒）
        self.idle_cycle = 4.5            # 揺れ1サイクルの長さ（秒）
        self.idle_amplitude = 5.0        # 左右の振幅（ピクセル）

        # スピーチ傾き（発話中のみ）
        self.speech_time = 0.0           # スピーチ動作時間（秒）
        self.speech_tilt_amp = 2.5       # 傾き角度の振幅（度）
        self.speech_tilt_speed = 2.0     # 傾きの速度

        # 現在の状態
        self.is_speaking = False
        self.is_idle = True

        # 最終更新時刻
        self.last_update = pygame.time.get_ticks()

    def start_speaking(self):
        """発話開始"""
        self.is_speaking = True
        self.is_idle = False
        self.speech_time = 0.0

    def stop_speaking(self):
        """発話停止"""
        self.is_speaking = False
        self.is_idle = True
        self.idle_time = 0.0

    def set_state(self, state):
        """
        アニメーション状態を設定

        Args:
            state (int): GUI状態
                - 0: IDLE（待機中）
                - 1: LISTENING（聞いている）
                - 2: PROCESSING（考え中）
                - 3: SPEAKING（発話中）
        """
        if state == 3:  # SPEAKING
            if not self.is_speaking:
                self.start_speaking()
        else:
            if self.is_speaking:
                self.stop_speaking()

    def update(self):
        """
        アニメーション状態を更新し、現在の体の変換パラメータを返す

        Returns:
            dict: 体の変換パラメータ
                - 'offset_x': 横方向のオフセット（ピクセル）
                - 'offset_y': 縦方向のオフセット（ピクセル）
                - 'rotation': 回転角度（度）
                - 'scale': スケール倍率
        """
        now = pygame.time.get_ticks()
        delta_time = (now - self.last_update) / 1000.0  # 秒に変換
        self.last_update = now

        # 各タイマーを更新
        self.breath_time += delta_time
        if self.is_idle:
            self.idle_time += delta_time
        if self.is_speaking:
            self.speech_time += delta_time

        # === 1. 呼吸モーション（常時）===
        # サイン波による滑らかな上下動
        breath_phase = (self.breath_time / self.breath_cycle) * 2 * math.pi
        offset_y = math.sin(breath_phase) * self.breath_amplitude

        # 呼吸に合わせた微細なスケール変化
        scale = 1.0 + math.sin(breath_phase) * self.breath_scale_amp

        # === 2. アイドル揺れ（待機中のみ）===
        offset_x = 0.0
        if self.is_idle:
            idle_phase = (self.idle_time / self.idle_cycle) * 2 * math.pi
            offset_x = math.sin(idle_phase) * self.idle_amplitude

        # === 3. スピーチ傾き（発話中のみ）===
        rotation = 0.0
        if self.is_speaking:
            # サイン波による左右の傾き
            speech_phase = self.speech_time * self.speech_tilt_speed
            rotation = math.sin(speech_phase) * self.speech_tilt_amp

            # 発話中は若干前のめり（Y方向に少し下げる）
            offset_y += 3.0

        return {
            'offset_x': offset_x,
            'offset_y': offset_y,
            'rotation': rotation,
            'scale': scale
        }
