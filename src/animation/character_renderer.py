"""
キャラクターレンダラー - 複数レイヤー画像の合成

Live2D風のキャラクターアニメーションを実現するため、
体・目・口のパーツを個別のレイヤーとして管理し、
動的に合成して1枚の画像を生成します。
"""

import pygame
import os


class CharacterRenderer:
    """
    キャラクターレイヤー画像の読み込み、スケーリング、合成を処理するクラス

    レイヤーは以下の順序で合成されます（奥から手前）：
    1. ベース（体）
    2. 目
    3. 口

    各レイヤーは初期化時にメモリにキャッシュされ、
    高速な合成処理を実現しています。
    """

    def __init__(self, screen_height, assets_dir):
        """
        キャラクターレンダラーを初期化

        Args:
            screen_height (int): 画面の高さ（ピクセル）
            assets_dir (str): キャラクターアセットディレクトリのパス
        """
        self.assets_dir = assets_dir
        self.cache = {}  # レイヤー画像のキャッシュ

        # ターゲットサイズを計算（画面高さの80%、アスペクト比維持）
        self.target_h = int(screen_height * 0.8)
        self.target_size = (self.target_h, self.target_h)  # 正方形を想定

        # 全アセットを読み込み
        self._load_assets()

    def _load_assets(self):
        """
        キャラクターの全レイヤーをメモリに読み込んでキャッシュ

        読み込まれるレイヤー：
        - ベース: 体レイヤー（1枚）
        - 口: 4種類（closed, small_open, medium_open, wide_open）
        - 目: 3種類（normal, blink_half, blink_closed）
        """
        print("Loading character assets...")

        # ベースレイヤー（体）を読み込み
        self._load_layer('base', 'base/body.png')

        # 口のバリエーションを読み込み
        mouth_states = ['closed', 'small_open', 'medium_open', 'wide_open']
        for mouth in mouth_states:
            key = f'mouth_{mouth}'
            path = f'mouths/{mouth}.png'
            self._load_layer(key, path)

        # 目のバリエーションを読み込み
        eye_states = ['normal', 'blink_half', 'blink_closed']
        for eye in eye_states:
            key = f'eye_{eye}'
            path = f'eyes/{eye}.png'
            self._load_layer(key, path)

        print(f"Loaded {len(self.cache)} character layers")

    def _load_layer(self, key, relative_path):
        """
        単一のレイヤー画像を読み込んでキャッシュに保存

        画像は自動的にターゲットサイズにスケーリングされ、
        透明度（アルファチャンネル）を保持したまま保存されます。

        Args:
            key (str): このレイヤーのキャッシュキー
            relative_path (str): assets_dirからの相対パス
        """
        full_path = os.path.join(self.assets_dir, relative_path)

        # ファイルが存在しない場合は透明なプレースホルダーを作成
        if not os.path.exists(full_path):
            print(f"Warning: {full_path} not found, using transparent placeholder")
            surf = pygame.Surface(self.target_size, pygame.SRCALPHA)
            surf.fill((0, 0, 0, 0))
            self.cache[key] = surf
            return

        try:
            # 画像を読み込み
            img = pygame.image.load(full_path)

            # アルファ透明度用に変換（ディスプレイが初期化されている場合のみ）
            # これにより高速な描画が可能になります
            if pygame.display.get_surface() is not None:
                img = img.convert_alpha()
            # ディスプレイ未初期化の場合でも、読み込み時に自動的にアルファが保持されます

            # ターゲットサイズにスケーリング（高品質なsmoothtransformを使用）
            scaled_img = pygame.transform.smoothscale(img, self.target_size)

            # スケーリング済みサーフェスをキャッシュ
            self.cache[key] = scaled_img

        except Exception as e:
            print(f"Error loading {full_path}: {e}")
            # エラー時は透明なプレースホルダーを使用
            surf = pygame.Surface(self.target_size, pygame.SRCALPHA)
            surf.fill((0, 0, 0, 0))
            self.cache[key] = surf

    def compose(self, mouth_state='closed', eye_state='normal'):
        """
        キャラクターレイヤーを1枚のサーフェスに合成

        指定された口と目の状態に応じて、各レイヤーを
        重ね合わせて最終的なキャラクター画像を生成します。

        Args:
            mouth_state (str): 使用する口の状態
                - 'closed': 口を閉じている
                - 'small_open': 少し開いている
                - 'medium_open': 中程度に開いている
                - 'wide_open': 大きく開いている
            eye_state (str): 使用する目の状態
                - 'normal': 通常（目を開いている）
                - 'blink_half': 半目
                - 'blink_closed': 目を閉じている

        Returns:
            pygame.Surface: 合成されたキャラクター画像
        """
        # 合成用の透明なサーフェスを作成
        composed = pygame.Surface(self.target_size, pygame.SRCALPHA)
        composed.fill((0, 0, 0, 0))

        # レイヤー1: ベース（体）- 常に表示
        if 'base' in self.cache:
            composed.blit(self.cache['base'], (0, 0))

        # レイヤー2: 目
        eye_key = f'eye_{eye_state}'
        if eye_key in self.cache:
            composed.blit(self.cache[eye_key], (0, 0))

        # レイヤー3: 口
        mouth_key = f'mouth_{mouth_state}'
        if mouth_key in self.cache:
            composed.blit(self.cache[mouth_key], (0, 0))

        return composed

    def get_size(self):
        """
        合成されたキャラクター画像のサイズを取得

        Returns:
            tuple: (幅, 高さ) のタプル
        """
        return self.target_size
