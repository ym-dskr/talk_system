"""
手アニメーター - 手の自然な動きとジェスチャーを制御

アイドル時の微細な動き、発話時のジェスチャーなど、
左右の手を個別に制御して自然な動きを実現します。
"""

import pygame
import math
import random


class HandAnimator:
    """
    左右の手の動きを制御するクラス

    以下の動きを組み合わせて自然な手の動きを実現：
    1. アイドル動作: ゆっくりとした上下の動き（待機中）
    2. スピーチジェスチャー: 発話時の動的な動き
    3. 左右非対称: 左右の手が異なるタイミングで動く

    座標変換:
    - left_offset_y: 左手の縦方向オフセット
    - left_rotation: 左手の回転角度
    - right_offset_y: 右手の縦方向オフセット
    - right_rotation: 右手の回転角度
    """

    def __init__(self):
        """手アニメーターを初期化"""
        # 左手のアニメーション
        self.left_time = random.uniform(0, math.pi * 2)  # 位相をランダム化
        self.left_idle_cycle = 5.0       # アイドル動作のサイクル（秒）
        self.left_idle_amp = 4.0         # アイドル時の振幅（ピクセル）

        # 右手のアニメーション（左手と位相をずらす）
        self.right_time = random.uniform(0, math.pi * 2)
        self.right_idle_cycle = 6.0      # 左手と少し異なるサイクル
        self.right_idle_amp = 5.0

        # スピーチジェスチャー
        self.speech_time = 0.0
        self.gesture_interval = 1.5      # ジェスチャー間隔（秒）
        self.last_gesture_time = 0.0
        self.current_gesture = None      # 現在のジェスチャー種類
        self.gesture_progress = 0.0      # ジェスチャーの進行度（0.0～1.0）

        # 利用可能なジェスチャータイプ
        self.gesture_types = [
            'wave_left',      # 左手を振る
            'wave_right',     # 右手を振る
            'point',          # 両手で指す動き
            'open',           # 両手を開く
            'rest'            # 休憩（小さな動き）
        ]

        # 状態
        self.is_speaking = False
        self.is_idle = True

        # 最終更新時刻
        self.last_update = pygame.time.get_ticks()

    def start_speaking(self):
        """発話開始"""
        self.is_speaking = True
        self.is_idle = False
        self.speech_time = 0.0
        self.last_gesture_time = 0.0
        self.current_gesture = None

    def stop_speaking(self):
        """発話停止"""
        self.is_speaking = False
        self.is_idle = True
        self.current_gesture = None

    def set_state(self, state):
        """
        アニメーション状態を設定

        Args:
            state (int): GUI状態
        """
        if state == 3:  # SPEAKING
            if not self.is_speaking:
                self.start_speaking()
        else:
            if self.is_speaking:
                self.stop_speaking()

    def _get_idle_motion(self):
        """
        アイドル時の手の動きを計算

        Returns:
            dict: 手の変換パラメータ
        """
        # 左手: ゆっくりとした上下動
        left_phase = (self.left_time / self.left_idle_cycle) * 2 * math.pi
        left_offset_y = math.sin(left_phase) * self.left_idle_amp
        left_rotation = math.sin(left_phase * 0.5) * 2.0  # 微細な回転

        # 右手: 左手と異なるリズムで動く
        right_phase = (self.right_time / self.right_idle_cycle) * 2 * math.pi
        right_offset_y = math.sin(right_phase) * self.right_idle_amp
        right_rotation = math.sin(right_phase * 0.5) * -2.0

        return {
            'left_offset_y': left_offset_y,
            'left_rotation': left_rotation,
            'right_offset_y': right_offset_y,
            'right_rotation': right_rotation
        }

    def _get_gesture_motion(self):
        """
        スピーチジェスチャーの動きを計算

        Returns:
            dict: 手の変換パラメータ
        """
        # 新しいジェスチャーを開始すべきか
        if self.current_gesture is None or self.speech_time - self.last_gesture_time > self.gesture_interval:
            self.current_gesture = random.choice(self.gesture_types)
            self.last_gesture_time = self.speech_time
            self.gesture_progress = 0.0

        # ジェスチャーの進行度を更新（0.0～1.0でループ）
        elapsed = self.speech_time - self.last_gesture_time
        self.gesture_progress = (elapsed % self.gesture_interval) / self.gesture_interval

        # イージング関数（sin波で滑らかに）
        eased_progress = (math.sin((self.gesture_progress * 2 - 0.5) * math.pi) + 1) / 2

        # ジェスチャー種類に応じた動き
        if self.current_gesture == 'wave_left':
            # 左手を振る
            left_offset_y = -15 * eased_progress
            left_rotation = 15 * math.sin(eased_progress * math.pi * 4)
            right_offset_y = 0
            right_rotation = 0

        elif self.current_gesture == 'wave_right':
            # 右手を振る
            left_offset_y = 0
            left_rotation = 0
            right_offset_y = -15 * eased_progress
            right_rotation = -15 * math.sin(eased_progress * math.pi * 4)

        elif self.current_gesture == 'point':
            # 両手で前を指す
            left_offset_y = -10 * eased_progress
            left_rotation = 5 * eased_progress
            right_offset_y = -10 * eased_progress
            right_rotation = -5 * eased_progress

        elif self.current_gesture == 'open':
            # 両手を広げる
            left_offset_y = -8 * math.sin(eased_progress * math.pi)
            left_rotation = 10 * eased_progress
            right_offset_y = -8 * math.sin(eased_progress * math.pi)
            right_rotation = -10 * eased_progress

        else:  # 'rest'
            # 小さな動き（休憩）
            left_offset_y = 3 * math.sin(eased_progress * math.pi * 2)
            left_rotation = 2 * math.sin(eased_progress * math.pi)
            right_offset_y = 3 * math.sin(eased_progress * math.pi * 2 + math.pi)
            right_rotation = -2 * math.sin(eased_progress * math.pi)

        return {
            'left_offset_y': left_offset_y,
            'left_rotation': left_rotation,
            'right_offset_y': right_offset_y,
            'right_rotation': right_rotation
        }

    def update(self):
        """
        アニメーション状態を更新し、現在の手の変換パラメータを返す

        Returns:
            dict: 手の変換パラメータ
        """
        now = pygame.time.get_ticks()
        delta_time = (now - self.last_update) / 1000.0  # 秒に変換
        self.last_update = now

        # タイマーを更新
        if self.is_idle:
            self.left_time += delta_time
            self.right_time += delta_time

        if self.is_speaking:
            self.speech_time += delta_time

        # 状態に応じて動きを計算
        if self.is_speaking:
            return self._get_gesture_motion()
        else:
            return self._get_idle_motion()
