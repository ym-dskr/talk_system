"""
GUIハンドラー - Pygameベースのフルスクリーン表示とキャラクターアニメーション

リアルタイム音声対話中の視覚フィードバックを提供します。
Live2D風のキャラクターアニメーション、状態インジケーター、
日本語テキスト表示（自動ページネーション付き）を実装しています。

状態管理:
- 0: IDLE（待機中）
- 1: LISTENING（聞いている）- 緑色インジケーター
- 2: PROCESSING（考え中）- 黄色インジケーター
- 3: SPEAKING（発話中）- 口パクアニメーション

主要機能:
- フルスクリーン表示（800x600のフォールバック付き）
- Live2D風キャラクターアニメーション
- 日本語フォント対応
- 長文の自動ページ分割と自動切り替え
- 状態に応じたビジュアルフィードバック
"""

import pygame
import asyncio
import config

# ================================================================================
# アニメーションモジュールのインポート（絶対/相対インポート対応）
# ================================================================================
try:
    from src.animation.character_renderer import CharacterRenderer
    from src.animation.animation_controller import AnimationController
except ImportError:
    from .animation.character_renderer import CharacterRenderer
    from .animation.animation_controller import AnimationController


class GUIHandler:
    """
    Pygameベースのフルスクリーン表示とアニメーション管理

    リアルタイム音声対話中の視覚フィードバックを提供します。
    キャラクターアニメーション、状態インジケーター、テキスト表示を統合管理します。

    Attributes:
        screen (pygame.Surface): メイン描画サーフェス（フルスクリーン）
        screen_w (int): 画面幅（ピクセル）
        screen_h (int): 画面高さ（ピクセル）
        character (CharacterRenderer): レイヤーベースのキャラクター描画
        animator (AnimationController): アニメーション統合管理
        state (int): 現在の状態（0=Idle, 1=Listening, 2=Processing, 3=Speaking）
        running (bool): GUI実行中フラグ
        clock (pygame.time.Clock): フレームレート制御
        font (pygame.font.Font): 日本語フォント
        user_text (str): ユーザー発話テキスト
        agent_text (str): AI応答テキスト
        user_text_pages (list): ユーザーテキストのページ分割
        agent_text_pages (list): AIテキストのページ分割
        user_page_index (int): 現在のユーザーテキストページ番号
        agent_page_index (int): 現在のAIテキストページ番号
        last_page_switch_time (int): 最後のページ切り替え時刻（ミリ秒）
        page_switch_interval (int): ページ切り替え間隔（ミリ秒）
    """

    # ================================================================================
    # 状態定数
    # ================================================================================
    STATE_IDLE = 0         # 待機中
    STATE_LISTENING = 1    # 聞いている（緑色インジケーター）
    STATE_PROCESSING = 2   # 考え中（黄色インジケーター）
    STATE_SPEAKING = 3     # 発話中（口パクアニメーション）

    # ================================================================================
    # ページネーション設定
    # ================================================================================
    USER_TEXT_MAX_LINES = 2    # ユーザーテキストの最大行数
    AGENT_TEXT_MAX_LINES = 3   # AIテキストの最大行数
    PAGE_SWITCH_INTERVAL = 3000  # ページ切り替え間隔（3秒）

    def __init__(self):
        """
        GUIHandlerを初期化

        Pygameの初期化、フルスクリーン設定、キャラクターアニメーション、
        日本語フォント、テキスト表示の設定を行います。

        Note:
            - pygame.mixerは初期化しない（PyAudioとの競合回避）
            - フルスクリーン失敗時は800x600のウィンドウにフォールバック
            - 日本語フォントが見つからない場合はシステムフォントを使用
        """
        # ────────────────────────────────────────────────────────────
        # Pygame初期化（mixer除外でPyAudioとの競合回避）
        # ────────────────────────────────────────────────────────────
        pygame.display.init()  # ディスプレイモジュールのみ初期化
        if pygame.font.get_init() is False:
            pygame.font.init()

        # ────────────────────────────────────────────────────────────
        # フルスクリーン設定（失敗時はウィンドウモード）
        # ────────────────────────────────────────────────────────────
        try:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        except:
            print("Fullscreen failed, falling back to windowed")
            self.screen = pygame.display.set_mode((800, 600))

        pygame.display.set_caption("Kikai-kun")
        self.screen_w, self.screen_h = self.screen.get_size()

        # ────────────────────────────────────────────────────────────
        # Live2D風キャラクターアニメーションシステム初期化
        # ────────────────────────────────────────────────────────────
        try:
            print(f"Initializing character animation system...")
            print(f"Assets directory: {config.CHAR_ASSETS_DIR}")

            # キャラクター描画エンジン初期化
            self.character = CharacterRenderer(
                screen_height=self.screen_h,
                assets_dir=config.CHAR_ASSETS_DIR
            )
            print(f"CharacterRenderer created successfully")

            # アニメーション制御エンジン初期化
            self.animator = AnimationController(self.character)
            print(f"AnimationController created successfully")

        except Exception as e:
            print(f"ERROR initializing character animation: {e}")
            import traceback
            traceback.print_exc()

            # フォールバック: シンプルな四角形表示
            self.character = None
            self.animator = None
            print(f"Using fallback colored square")

        # ────────────────────────────────────────────────────────────
        # 状態管理とフレームレート制御
        # ────────────────────────────────────────────────────────────
        self.state = self.STATE_IDLE  # 初期状態: 待機中
        self.running = True           # GUI実行中フラグ
        self.clock = pygame.time.Clock()  # 60FPS制御

        # ────────────────────────────────────────────────────────────
        # 日本語フォント設定
        # ────────────────────────────────────────────────────────────
        try:
            # Raspberry Pi上の一般的な日本語フォントを順に試行
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

            # フォントが見つからない場合はシステムフォント
            if not font_loaded:
                self.font = pygame.font.SysFont(
                    "notosanscjk,ipaexgothic,ipagothic,takao,sans-serif", 32
                )
                print("Using system font")

        except Exception as e:
            print(f"Font loading error: {e}, using default")
            self.font = pygame.font.Font(None, 32)

        # ────────────────────────────────────────────────────────────
        # テキスト表示とページネーション
        # ────────────────────────────────────────────────────────────
        self.user_text = ""             # ユーザー発話テキスト
        self.agent_text = ""            # AI応答テキスト

        # ページ分割（長文対応）
        self.user_text_pages = []       # ユーザーテキストのページリスト
        self.agent_text_pages = []      # AIテキストのページリスト
        self.user_page_index = 0        # 現在表示中のユーザーテキストページ
        self.agent_page_index = 0       # 現在表示中のAIテキストページ

        # 自動ページ切り替え
        self.last_page_switch_time = 0  # 最後のページ切り替え時刻
        self.page_switch_interval = self.PAGE_SWITCH_INTERVAL  # 3秒間隔

    def update(self):
        """
        GUI更新とイベント処理

        フレームごとに呼び出され、イベント処理、画面描画、
        アニメーション更新、テキスト表示を行います。

        処理フロー:
        1. イベント処理（終了検知、キー入力）
        2. 背景クリア（白）
        3. 状態インジケーター描画（緑/黄色の円）
        4. キャラクターアニメーション描画
        5. ページ自動切り替え（3秒間隔）
        6. テキスト表示（ページネーション付き）
        7. 画面更新（60FPS）

        Note:
            - QキーまたはESCキーで終了
            - アニメーションがない場合はフォールバック表示
        """
        # ────────────────────────────────────────────────────────────
        # イベント処理
        # ────────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
                    self.running = False

        # ────────────────────────────────────────────────────────────
        # 背景クリア
        # ────────────────────────────────────────────────────────────
        self.screen.fill((255, 255, 255))  # 白背景

        # ────────────────────────────────────────────────────────────
        # 状態インジケーター（右上の円）
        # ────────────────────────────────────────────────────────────
        if self.state == self.STATE_LISTENING:
            # 緑色の円: ユーザー発話を聞いている状態
            pygame.draw.circle(self.screen, (0, 255, 0), (self.screen_w - 50, 50), 30)
        elif self.state == self.STATE_PROCESSING:
            # 黄色の円: AI応答を処理中
            pygame.draw.circle(self.screen, (255, 255, 0), (self.screen_w - 50, 50), 30)

        # ────────────────────────────────────────────────────────────
        # キャラクターアニメーション描画
        # ────────────────────────────────────────────────────────────
        if self.animator:
            # アニメーション状態を更新
            self.animator.set_state(self.state)

            # 現在のアニメーションフレームを取得
            character_surface = self.animator.get_frame()

            # 画面中央に配置して描画
            x = (self.screen_w - character_surface.get_width()) // 2
            y = (self.screen_h - character_surface.get_height()) // 2
            self.screen.blit(character_surface, (x, y))
        else:
            # フォールバック: シンプルな四角形
            # SPEAKING時は赤、それ以外は緑
            fallback_size = int(self.screen_h * 0.5)
            fallback_surf = pygame.Surface((fallback_size, fallback_size))
            fallback_surf.fill(
                (255, 0, 0) if self.state == self.STATE_SPEAKING else (0, 255, 0)
            )
            x = (self.screen_w - fallback_size) // 2
            y = (self.screen_h - fallback_size) // 2
            self.screen.blit(fallback_surf, (x, y))

        # ────────────────────────────────────────────────────────────
        # 自動ページ切り替え（3秒間隔）
        # ────────────────────────────────────────────────────────────
        current_time = pygame.time.get_ticks()
        if current_time - self.last_page_switch_time > self.page_switch_interval:
            self.last_page_switch_time = current_time

            # ユーザーテキストのページ切り替え（複数ページある場合）
            if len(self.user_text_pages) > 1:
                self.user_page_index = (self.user_page_index + 1) % len(self.user_text_pages)

            # AIテキストのページ切り替え（複数ページある場合）
            if len(self.agent_text_pages) > 1:
                self.agent_page_index = (self.agent_page_index + 1) % len(self.agent_text_pages)

        # ────────────────────────────────────────────────────────────
        # テキスト表示（ページネーション付き）
        # ────────────────────────────────────────────────────────────
        # ユーザーテキスト（画面上部、最大2行）
        if self.user_text_pages and self.user_page_index < len(self.user_text_pages):
            # ページ番号表示（複数ページの場合）
            page_indicator = (
                f" ({self.user_page_index + 1}/{len(self.user_text_pages)})"
                if len(self.user_text_pages) > 1 else ""
            )
            self._render_multiline_text(
                self.user_text_pages[self.user_page_index] + page_indicator,
                (0, 0, 0),  # 黒色
                20, 20,     # 左上からの位置
                max_width=self.screen_w - 40,
                max_lines=self.USER_TEXT_MAX_LINES
            )

        # AIテキスト（画面下部、最大3行）
        if self.agent_text_pages and self.agent_page_index < len(self.agent_text_pages):
            line_height = self.font.get_height() + 2
            agent_y = self.screen_h - (self.AGENT_TEXT_MAX_LINES * line_height + 30)
            # ページ番号表示（複数ページの場合）
            page_indicator = (
                f" ({self.agent_page_index + 1}/{len(self.agent_text_pages)})"
                if len(self.agent_text_pages) > 1 else ""
            )
            self._render_multiline_text(
                self.agent_text_pages[self.agent_page_index] + page_indicator,
                (0, 0, 255),  # 青色
                20, agent_y,  # 左下からの位置
                max_width=self.screen_w - 40,
                max_lines=self.AGENT_TEXT_MAX_LINES
            )

        # ────────────────────────────────────────────────────────────
        # 画面更新（60FPS）
        # ────────────────────────────────────────────────────────────
        pygame.display.flip()
        self.clock.tick(60)

    def _split_text_into_pages(self, text, max_width, max_lines):
        """
        テキストを複数ページに分割（日本語対応）

        長いテキストを指定された最大幅と最大行数に収まるように
        複数ページに分割します。文字単位で改行判定を行うため、
        日本語にも対応しています。

        Args:
            text (str): 分割するテキスト
            max_width (int): 1行の最大幅（ピクセル）
            max_lines (int): 1ページの最大行数

        Returns:
            list: ページごとのテキストリスト

        Note:
            - 文字単位で幅を計算（日本語/英語混在OK）
            - 最大幅を超える場合は自動的に改行
            - max_lines行ごとに新しいページを作成
        """
        lines = []
        current_line = ""

        # 文字単位で改行判定（日本語対応）
        for char in text:
            test_line = current_line + char
            test_surface = self.font.render(test_line, True, (0, 0, 0))

            if test_surface.get_width() <= max_width:
                # まだ幅に収まる
                current_line = test_line
            else:
                # 幅を超えた: 改行
                if current_line:
                    lines.append(current_line)
                    current_line = char
                else:
                    # 1文字だけで幅を超える場合
                    lines.append(char)
                    current_line = ""

        # 最後の行を追加
        if current_line:
            lines.append(current_line)

        # 複数行を複数ページに分割
        pages = []
        for i in range(0, len(lines), max_lines):
            page = "\n".join(lines[i:i + max_lines])
            pages.append(page)

        return pages if pages else [""]

    def _render_multiline_text(self, text, color, x, y, max_width, max_lines=3):
        """
        複数行テキストを描画

        改行コード（\\n）で分割された複数行のテキストを
        指定された位置に描画します。

        Args:
            text (str): 描画するテキスト（改行コード含む）
            color (tuple): RGB色タプル (例: (0, 0, 0) = 黒)
            x (int): X座標（左端）
            y (int): Y座標（上端）
            max_width (int): 最大幅（未使用、将来の拡張用）
            max_lines (int): 最大行数（デフォルト: 3）

        Note:
            - 改行コードで分割して各行を個別に描画
            - max_linesを超える行は表示されない
        """
        lines = text.split('\n')

        # 各行を描画
        line_height = self.font.get_height() + 2
        for i, line in enumerate(lines[:max_lines]):
            line_surface = self.font.render(line, True, color)
            self.screen.blit(line_surface, (x, y + i * line_height))

    def set_state(self, state_code):
        """
        GUI状態を設定

        アニメーション状態とインジケーター表示を更新します。

        Args:
            state_code (int): 状態コード
                - 0: IDLE（待機中）
                - 1: LISTENING（聞いている）
                - 2: PROCESSING（考え中）
                - 3: SPEAKING（発話中）
        """
        self.state = state_code

    def set_user_text(self, text):
        """
        ユーザー発話テキストを設定

        ユーザーの発話テキストを受け取り、ページ分割して表示準備します。

        Args:
            text (str): ユーザー発話のテキスト

        Note:
            - "You: " プレフィックスを自動追加
            - 最大2行/ページで自動分割
            - ページインデックスを0にリセット
        """
        self.user_text = text
        self.user_text_pages = self._split_text_into_pages(
            f"You: {text}",
            self.screen_w - 40,
            self.USER_TEXT_MAX_LINES
        )
        self.user_page_index = 0
        self.last_page_switch_time = pygame.time.get_ticks()

    def set_agent_text(self, text):
        """
        AI応答テキストを設定

        AIの応答テキストを受け取り、ページ分割して表示準備します。

        Args:
            text (str): AI応答のテキスト

        Note:
            - "Kikai-kun: " プレフィックスを自動追加
            - 最大3行/ページで自動分割
            - ページインデックスを0にリセット
        """
        self.agent_text = text
        self.agent_text_pages = self._split_text_into_pages(
            f"Kikai-kun: {text}",
            self.screen_w - 40,
            self.AGENT_TEXT_MAX_LINES
        )
        self.agent_page_index = 0
        self.last_page_switch_time = pygame.time.get_ticks()

    def quit(self):
        """
        GUIを終了

        Pygameを正常に終了します。
        """
        pygame.quit()
