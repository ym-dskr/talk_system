"""
口パクアニメーター - 発話中の口の動きを制御

発話状態に応じて口の形を4段階で切り替え、
自然な口パクアニメーションを実現します。
"""

import pygame
import random


class MouthAnimator:
    """
    発話中の口の動きを制御するクラス

    口の状態を4段階（closed, small_open, medium_open, wide_open）で
    順次切り替え、各状態の持続時間をランダム化することで、
    機械的でない自然な口パクを実現しています。

    タイミング制御:
    - 各フレーム: 80-120msのランダム間隔
    - フレーム総数: 4段階
    - 1サイクル: 約320-480ms
    """

    def __init__(self):
        """口パクアニメーターを初期化"""
        # 口の状態シーケンス（アニメーション順）
        self.mouth_states = ['closed', 'small_open', 'medium_open', 'wide_open']

        # アニメーション状態
        self.current_index = 0           # 現在の口の状態インデックス
        self.last_update = 0             # 最後に更新した時刻（ミリ秒）
        self.update_interval = 100       # 更新間隔（ミリ秒）
        self.speaking = False            # 発話中かどうか

    def start_speaking(self):
        """
        口パクアニメーションを開始

        SPEAKING状態に遷移した際に呼ばれます。
        """
        self.speaking = True
        self.last_update = pygame.time.get_ticks()

    def stop_speaking(self):
        """
        口パクアニメーションを停止

        非SPEAKING状態に遷移した際に呼ばれ、
        口を閉じた状態にリセットします。
        """
        self.speaking = False
        self.current_index = 0  # closedにリセット

    def update(self):
        """
        アニメーション状態を更新し、現在の口の状態を返す

        発話中の場合、設定された間隔ごとに次の口の形に進みます。
        間隔はランダム化され（80-120ms）、より自然な動きを実現します。

        Returns:
            str: 現在の口の状態
                - 'closed': 口を閉じている
                - 'small_open': 少し開いている
                - 'medium_open': 中程度に開いている
                - 'wide_open': 大きく開いている
        """
        if not self.speaking:
            return 'closed'

        now = pygame.time.get_ticks()

        # 更新間隔が経過したかチェック
        if now - self.last_update > self.update_interval:
            # 次の口の状態に進む（循環）
            self.current_index = (self.current_index + 1) % len(self.mouth_states)
            self.last_update = now

            # 次の更新間隔をランダム化（80-120ms）
            # これにより機械的でない自然な動きを実現
            self.update_interval = random.randint(80, 120)

        return self.mouth_states[self.current_index]
