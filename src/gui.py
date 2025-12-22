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
        self.agent_text_pages = []      # AIテキスト dominance
        self.user_page_index = 0        # 現在表示中のユーザーテキストページ
        self.agent_page_index = 0       # 現在表示中のAIテキストページ

        # 自動ページ切り替え
        self.last_page_switch_time = 0  # 最後のページ切り替え時刻
        self.page_switch_interval = self.PAGE_SWITCH_INTERVAL  # 3秒間隔

        # タイピングエフェクト設定
        self.agent_display_count = 0.0  # 表示すべき文字数（浮動小数点で滑らかに）
        self.agent_full_text = ""       # 受信済みのAIテキスト全文
        self.typing_speed = 0.012       # 1msあたりの進む文字数 (約12文字/秒。人間の平均的な発話速度)
        self.last_update_time = 0       # 最終更新時刻

        # デザイン設定
        self.color_user_bg = (240, 248, 255, 180)  # ユーザー用背景（薄い水色、半透明）
        self.color_agent_bg = (255, 240, 245, 180) # AI用背景（薄いピンク、半透明）
        self.color_text_main = (50, 50, 50)        # 基本テキスト色（濃いグレー）

    def update(self):
        """
        GUI更新とイベント処理
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
        # タイピングエフェクトの更新 (AIテキストのみ)
        # ────────────────────────────────────────────────────────────
        current_time = pygame.time.get_ticks()
        delta_ms = current_time - self.last_update_time
        self.last_update_time = current_time

        if self.agent_full_text:
            text_len = len(self.agent_full_text)
            
            # 1. 話し終わった直後で未完了の場合は、速度を上げて追いつく
            actual_typing_speed = self.typing_speed
            
            # 話している最中（SPEAKING）なら、文字が先に行き過ぎないように抑制
            # 終わっていたら（IDLE等）、少し早めに残りを出す
            if self.state != self.STATE_SPEAKING:
                actual_typing_speed *= 2.0
            
            # 2. ページ分割を考慮した表示
            if self.agent_display_count < text_len:
                # 経過時間に合わせて文字カウントを進める
                prev_count = int(self.agent_display_count)
                self.agent_display_count += actual_typing_speed * delta_ms
                
                # 最大文字数を超えないように制限
                if self.agent_display_count > text_len:
                    self.agent_display_count = float(text_len)
                
                new_count = int(self.agent_display_count)
                
                # 文字数が増えた場合のみページ再計算 (負荷軽減)
                if new_count > prev_count:
                    # 🆕 プレフィックスを付けた全長を先に計算し、そこから表示分を切り出す
                    # これにより、途中で改行位置がズレるのを防ぐ
                    full_display = f"Kikai-kun: {self.agent_full_text}"
                    # プレフィックス(11文字)分をオフセットとして考慮
                    typed_len = new_count + 11 
                    
                    self.agent_text_pages = self._split_text_into_pages(
                        full_display[:typed_len],
                        self.screen_w - 60,
                        self.AGENT_TEXT_MAX_LINES
                    )
                    # タイピング中は常に最新ページを表示
                    self.agent_page_index = len(self.agent_text_pages) - 1

        # 割り込み時（LISTENINGへの遷移時ではなく、明示的なresetで消す運用に変更）
        # ただし、前の会話が残っている状態で新しいユーザー発話が「確定」したら消したい

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
        # ユーザーテキスト（画面上部中心付近、最大2行）
        if self.user_text_pages and self.user_page_index < len(self.user_text_pages):
            page_indicator = (
                f" ({self.user_page_index + 1}/{len(self.user_text_pages)})"
                if len(self.user_text_pages) > 1 else ""
            )
            # 画面端から少し離して描画
            self._render_multiline_text(
                self.user_text_pages[self.user_page_index] + page_indicator,
                self.color_text_main,
                30, 30,
                max_width=self.screen_w - 60,
                max_lines=self.USER_TEXT_MAX_LINES,
                bg_color=self.color_user_bg
            )

        # AIテキスト（画面下部、最大3行）
        if self.agent_text_pages and self.agent_page_index < len(self.agent_text_pages):
            line_height = self.font.get_height() + 4
            padding = 15
            rect_h = len(self.agent_text_pages[self.agent_page_index].split('\n')) * line_height + padding * 2
            agent_y = self.screen_h - rect_h - 30
            
            page_indicator = (
                f" ({self.agent_page_index + 1}/{len(self.agent_text_pages)})"
                if len(self.agent_text_pages) > 1 else ""
            )
            self._render_multiline_text(
                self.agent_text_pages[self.agent_page_index] + page_indicator,
                self.color_text_main,
                30, agent_y,
                max_width=self.screen_w - 60,
                max_lines=self.AGENT_TEXT_MAX_LINES,
                bg_color=self.color_agent_bg
            )

        # ────────────────────────────────────────────────────────────
        # 画面更新（60FPS）
        # ────────────────────────────────────────────────────────────
        pygame.display.flip()
        self.clock.tick(60)

    def _split_text_into_pages(self, text, max_width, max_lines):
        """
        テキストを複数ページに分割（堅牢な実装）
        """
        if not text:
            return [""]

        # 1. まず全行を生成
        all_lines = []
        # 改行コードで事前分割されている可能性も考慮
        paragraphs = text.split('\n')
        
        for para in paragraphs:
            current_line = ""
            for char in para:
                test_line = current_line + char
                # 文字幅を計算
                w, h = self.font.size(test_line)
                if w <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        all_lines.append(current_line)
                        current_line = char
                    else:
                        all_lines.append(char)
                        current_line = ""
            if current_line:
                all_lines.append(current_line)

        # 2. 指定された行数ごとにページにまとめる
        pages = []
        for i in range(0, len(all_lines), max_lines):
            chunk = all_lines[i:i + max_lines]
            pages.append("\n".join(chunk))

        return pages if pages else [""]

    def _render_multiline_text(self, text, color, x, y, max_width, max_lines=3, bg_color=None):
        """
        複数行テキストを背景付きで描画

        改行コード（\n）で分割された複数行のテキストを
        指定された位置に、オプションの背景（角丸）付きで描画します。

        Args:
            text (str): 描画するテキスト（改行コード含む）
            color (tuple): RGB色タプル
            x (int): X座標（左端）
            y (int): Y座標（上端）
            max_width (int): 最大幅
            max_lines (int): 最大行数
            bg_color (tuple, optional): 背景色 (R, G, B, A)
        """
        lines = text.split('\n')
        line_height = self.font.get_height() + 4
        
        # 描画対象の行のみ抽出
        display_lines = lines[:max_lines]
        if not display_lines:
            return

        # 各行のサーフェスを作成して最大幅を計算
        line_surfaces = []
        actual_max_w = 0
        for line in display_lines:
            surf = self.font.render(line, True, color)
            line_surfaces.append(surf)
            actual_max_w = max(actual_max_w, surf.get_width())

        # 背景の描画
        padding = 15
        rect_w = actual_max_w + padding * 2
        rect_h = len(line_surfaces) * line_height + padding * 2
        
        if bg_color:
            # 透明度対応のサーフェスを作成
            bg_surface = pygame.Surface((rect_w, rect_h), pygame.SRCALPHA)
            pygame.draw.rect(bg_surface, bg_color, (0, 0, rect_w, rect_h), border_radius=15)
            self.screen.blit(bg_surface, (x, y))

        # 各行を描画
        for i, surf in enumerate(line_surfaces):
            self.screen.blit(surf, (x + padding, y + padding + i * line_height))

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

    def reset_texts(self):
        """
        テキスト表示を完全にリセットする (割り込み用)
        """
        self.user_text = ""
        self.user_text_pages = []
        self.user_page_index = 0
        self.agent_full_text = ""
        self.agent_display_count = 0.0
        self.agent_text_pages = []
        self.agent_page_index = 0

    def clear_user_text(self):
        """
        ユーザーテキストのみリセット
        """
        self.user_text = ""
        self.user_text_pages = []
        self.user_page_index = 0

    def set_user_text(self, text):
        """
        ユーザー発話テキストを設定
        """
        # 新しいユーザー発話が始まったら、前のAIテキストをリセットする（話し終わった後残していたものを消す）
        if self.agent_full_text and self.agent_display_count >= len(self.agent_full_text):
            # AIが話し終わっていたら、新しい会話のためにリセット
            self.agent_full_text = ""
            self.agent_display_count = 0.0
            self.agent_text_pages = []

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
        AI応答テキストを設定 (時間ベースのタイピングエフェクト)
        """
        if self.state == self.STATE_LISTENING:
            return

        if self.agent_full_text != text:
            # 前のテキストが今回のテキストのプレフィックス（ストリーミング中）なら、
            # カウントを維持してスムーズに継続させる
            if not text.startswith(self.agent_full_text):
                self.agent_display_count = 0.0
            
            self.agent_full_text = text
            
            # 発話が終了していれば即座に完了させる
            if self.state == self.STATE_IDLE:
                self.agent_display_count = float(len(text))
                self.agent_text_pages = self._split_text_into_pages(
                    f"Kikai-kun: {text}",
                    self.screen_w - 60,
                    self.AGENT_TEXT_MAX_LINES
                )
                self.agent_page_index = 0

    def quit(self):
        """
        GUIを終了

        Pygameを正常に終了します。
        """
        pygame.quit()
