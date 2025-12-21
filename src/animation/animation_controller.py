"""
アニメーションコントローラー - キャラクターアニメーション全体の調整

口パクアニメーターと瞬きアニメーターを統合し、
アプリケーションの状態に応じて適切なアニメーションを実行します。
"""

from .mouth_animator import MouthAnimator
from .eye_animator import EyeAnimator


class AnimationController:
    """
    口と目のアニメーターを調整し、キャラクターの状態を管理するクラス

    状態機械:
    0 - IDLE:       待機中、口は閉じている、まばたきあり
    1 - LISTENING:  聞いている、口は閉じている、まばたきあり
    2 - PROCESSING: 考え中、口は閉じている、まばたきあり
    3 - SPEAKING:   発話中、口パクアニメーション実行、まばたきあり

    口と目のアニメーションは独立して動作し、
    より自然なキャラクター表現を実現しています。
    """

    def __init__(self, character_renderer):
        """
        アニメーションコントローラーを初期化

        Args:
            character_renderer (CharacterRenderer): レイヤー合成用のレンダラー
        """
        self.renderer = character_renderer
        self.mouth_animator = MouthAnimator()  # 口パク制御
        self.eye_animator = EyeAnimator()      # 瞬き制御

        self.state = 0  # 現在のGUI状態

    def set_state(self, state):
        """
        アニメーション状態を更新

        状態が変化した際、各アニメーターに適切な指示を送ります。
        特にSPEAKING状態への遷移時は口パクを開始します。

        Args:
            state (int): GUI状態
                - 0: IDLE（待機中）
                - 1: LISTENING（聞いている）
                - 2: PROCESSING（考え中）
                - 3: SPEAKING（発話中）
        """
        prev_state = self.state
        self.state = state

        # 状態遷移を処理
        if state == 3:  # SPEAKING
            if prev_state != 3:  # 発話開始
                self.mouth_animator.start_speaking()
        else:
            if prev_state == 3:  # 発話終了
                self.mouth_animator.stop_speaking()

    def get_frame(self):
        """
        現在のアニメーションフレームを生成

        各アニメーターから現在の状態（口の形、目の状態）を取得し、
        レンダラーを使用して合成された画像を生成します。

        Returns:
            pygame.Surface: 現在のフレームの合成されたキャラクター画像
        """
        # 各サブアニメーターを更新
        mouth_state = self.mouth_animator.update()
        eye_state = self.eye_animator.update()

        # フレームを合成して返す
        return self.renderer.compose(
            mouth_state=mouth_state,
            eye_state=eye_state
        )
