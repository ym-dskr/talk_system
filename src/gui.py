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
- 4: ERROR（エラー状態）- 赤色インジケーター

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
        state (int): 現在の状態（0=Idle, 1=Listening, 2=Processing, 3=Speaking, 4=Error）
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
    STATE_ERROR = 4        # エラー状態（赤色インジケーター）

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

            # キャラクター描画エンジン初期化（設定から表示パラメータを読み込み）
            self.character = CharacterRenderer(
                screen_height=self.screen_h,
                assets_dir=config.CHAR_ASSETS_DIR,
                height_ratio=config.CHARACTER_HEIGHT_RATIO,
                width_ratio=config.CHARACTER_WIDTH_RATIO,
                default_scale=config.CHARACTER_DEFAULT_SCALE
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
        self.clock = pygame.time.Clock()  # 30FPS制御（CPU負荷軽減）

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

        # 文字幅キャッシュ（フォント計測の高速化）
        self.char_width_cache = {}  # {文字: 幅} の辞書

        # レンダリング済みテキストサーフェスキャッシュ（描画の高速化）
        self.rendered_text_cache = {}  # {(text, color): surface} の辞書
        self.max_text_cache_size = 100  # キャッシュサイズ上限

        # ページ分割の差分更新用キャッシュ
        self._last_page_split_count = 0  # 最後にページ分割した文字数
        self._cached_lines = []  # キャッシュされた行リスト

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

            # 2. 文字カウントのみ更新（ページ分割は行わない）
            if self.agent_display_count < text_len:
                self.agent_display_count += actual_typing_speed * delta_ms

                # 最大文字数を超えないように制限
                if self.agent_display_count > text_len:
                    self.agent_display_count = float(text_len)

                # 3. 表示用ページを生成（文字列スライス+軽量ページ分割）
                display_count = int(self.agent_display_count)
                self.agent_text_pages = self._create_partial_display(display_count)
                # タイピング中は常に最新ページを表示
                if self.agent_text_pages:
                    self.agent_page_index = len(self.agent_text_pages) - 1

        # ────────────────────────────────────────────────────────────
        # 背景クリア
        # ────────────────────────────────────────────────────────────
        self.screen.fill((255, 255, 255))  # 白背景

        # ────────────────────────────────────────────────────────────
        # 状態インジケーター（右上の円 + ラベル）
        # ────────────────────────────────────────────────────────────
        indicator_x = self.screen_w - 80
        indicator_y = 60
        indicator_radius = 40

        # 状態ごとの色とラベル設定
        state_config = {
            self.STATE_IDLE: ((128, 128, 128), "IDLE"),          # グレー: 待機中
            self.STATE_LISTENING: ((0, 220, 0), "LISTENING"),    # 明るい緑: 聞いている
            self.STATE_PROCESSING: ((255, 200, 0), "THINKING"),  # オレンジ: 考え中
            self.STATE_SPEAKING: ((0, 120, 255), "SPEAKING"),    # 青: 話している
            self.STATE_ERROR: ((255, 50, 50), "ERROR")           # 赤: エラー
        }

        if self.state in state_config:
            color, label = state_config[self.state]

            # 外側の円（白い縁取り）
            pygame.draw.circle(self.screen, (255, 255, 255), (indicator_x, indicator_y), indicator_radius + 4)
            # 内側の円（状態色）
            pygame.draw.circle(self.screen, color, (indicator_x, indicator_y), indicator_radius)

            # 状態ラベルを円の下に表示
            label_font = pygame.font.Font(None, 24)
            label_surf = label_font.render(label, True, (50, 50, 50))
            label_rect = label_surf.get_rect(center=(indicator_x, indicator_y + indicator_radius + 20))
            self.screen.blit(label_surf, label_rect)

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
        # ただし、タイピング中は無効化（発話終了後のみ）
        # ────────────────────────────────────────────────────────────
        # タイピングが完了しているかチェック
        typing_completed = (
            not self.agent_full_text or
            self.agent_display_count >= len(self.agent_full_text)
        )

        if typing_completed:
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
        # 画面更新（30FPS - CPU負荷軽減）
        # ────────────────────────────────────────────────────────────
        pygame.display.flip()
        self.clock.tick(30)  # 60FPS→30FPSに下げてCPU負荷を軽減

    def _create_partial_display(self, char_count):
        """
        元のテキストから指定文字数分だけを切り出してページ分割（差分更新最適化版）

        Args:
            char_count (int): 表示すべき文字数（プレフィックス「Kikai-kun: 」を除く）

        Returns:
            list: 部分表示用のページリスト

        Note:
            差分更新により、新規追加分のみを処理して高速化
        """
        if not self.agent_full_text or char_count <= 0:
            return []

        # 元のテキストから指定文字数分を切り出し
        display_text = self.agent_full_text[:char_count]

        # プレフィックスを追加
        full_display = f"3FACEロボ: {display_text}"

        # 差分更新: 前回と同じ文字数なら、キャッシュされたページをそのまま返す
        if char_count == self._last_page_split_count and self._cached_lines:
            return self._lines_to_pages(self._cached_lines, self.AGENT_TEXT_MAX_LINES)

        # 新規テキストが追加された場合のみ、差分処理
        max_width = self.screen_w - 60

        # 前回から文字数が減った（リセット）場合は、全体を再計算
        if char_count < self._last_page_split_count:
            self._last_page_split_count = 0
            self._cached_lines = []

        # 前回処理済みのテキスト
        if self._last_page_split_count > 0:
            prefix = "3FACEロボ: "
            prev_text = prefix + self.agent_full_text[:self._last_page_split_count]
        else:
            prev_text = ""

        # 新規追加分のテキスト
        new_text = full_display[len(prev_text):]

        # 差分更新: 新規追加分のみを行分割処理
        if new_text:
            self._cached_lines = self._append_text_to_lines(
                self._cached_lines,
                new_text,
                max_width
            )

        # 文字数を更新
        self._last_page_split_count = char_count

        # ページ分割して返す
        return self._lines_to_pages(self._cached_lines, self.AGENT_TEXT_MAX_LINES)

    def _append_text_to_lines(self, existing_lines, new_text, max_width):
        """
        既存の行リストに新規テキストを追加（差分更新用）

        Args:
            existing_lines (list): 既存の行リスト
            new_text (str): 新規追加テキスト
            max_width (int): 1行の最大幅

        Returns:
            list: 更新された行リスト
        """
        # 既存行のコピーを作成
        lines = existing_lines.copy()

        # 最後の行が未完成の可能性があるため、取り出す
        if lines:
            current_line = lines[-1]
            lines = lines[:-1]
            # 現在行の幅を再計算
            current_width = sum(self.char_width_cache.get(c, 0) for c in current_line)
        else:
            current_line = ""
            current_width = 0

        # 改行コードで分割して処理
        paragraphs = new_text.split('\n')

        for i, para in enumerate(paragraphs):
            for char in para:
                # 文字幅をキャッシュから取得、なければ計算してキャッシュに保存
                if char not in self.char_width_cache:
                    char_w, _ = self.font.size(char)
                    self.char_width_cache[char] = char_w
                else:
                    char_w = self.char_width_cache[char]

                # 追加後の幅を予測
                test_width = current_width + char_w

                if test_width <= max_width:
                    current_line += char
                    current_width = test_width
                else:
                    if current_line:
                        lines.append(current_line)
                        current_line = char
                        current_width = char_w
                    else:
                        # 1文字でも幅を超える場合（通常ありえないが安全のため）
                        lines.append(char)
                        current_line = ""
                        current_width = 0

            # パラグラフの終わりで改行（最後のパラグラフでない場合）
            if i < len(paragraphs) - 1:
                if current_line:
                    lines.append(current_line)
                current_line = ""
                current_width = 0

        # 最後の行を追加（未完成でも保持）
        if current_line:
            lines.append(current_line)

        return lines

    def _lines_to_pages(self, lines, max_lines):
        """
        行リストをページに分割

        Args:
            lines (list): 行のリスト
            max_lines (int): 1ページあたりの最大行数

        Returns:
            list: ページリスト
        """
        if not lines:
            return [""]

        pages = []
        for i in range(0, len(lines), max_lines):
            chunk = lines[i:i + max_lines]
            pages.append("\n".join(chunk))

        return pages if pages else [""]

    def _split_text_into_pages(self, text, max_width, max_lines):
        """
        テキストを複数ページに分割（文字幅キャッシュ最適化版）

        Note: この関数はユーザーテキスト用に使用され、
              AIテキストは _create_partial_display で差分更新されます
        """
        if not text:
            return [""]

        # 1. まず全行を生成
        all_lines = []
        # 改行コードで事前分割されている可能性も考慮
        paragraphs = text.split('\n')

        for para in paragraphs:
            current_line = ""
            current_width = 0

            for char in para:
                # 文字幅をキャッシュから取得、なければ計算してキャッシュに保存
                if char not in self.char_width_cache:
                    char_w, _ = self.font.size(char)
                    self.char_width_cache[char] = char_w
                else:
                    char_w = self.char_width_cache[char]

                # 追加後の幅を予測
                test_width = current_width + char_w

                if test_width <= max_width:
                    current_line += char
                    current_width = test_width
                else:
                    if current_line:
                        all_lines.append(current_line)
                        current_line = char
                        current_width = char_w
                    else:
                        # 1文字でも幅を超える場合（通常ありえないが安全のため）
                        all_lines.append(char)
                        current_line = ""
                        current_width = 0

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
        複数行テキストを背景付きで描画（サーフェスキャッシュ最適化版）

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

        # 各行のサーフェスを作成（キャッシュ使用）して最大幅を計算
        line_surfaces = []
        actual_max_w = 0
        for line in display_lines:
            # キャッシュキーを作成
            cache_key = (line, color)

            # キャッシュから取得、なければレンダリングしてキャッシュに保存
            if cache_key not in self.rendered_text_cache:
                surf = self.font.render(line, True, color)
                # キャッシュサイズ制限: 上限を超えたら古いエントリを削除
                if len(self.rendered_text_cache) >= self.max_text_cache_size:
                    # 先頭のエントリを削除（FIFO方式）
                    first_key = next(iter(self.rendered_text_cache))
                    del self.rendered_text_cache[first_key]
                self.rendered_text_cache[cache_key] = surf
            else:
                surf = self.rendered_text_cache[cache_key]

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
        self.rendered_text_cache.clear()  # レンダリングキャッシュもクリア

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
                # 新規テキストの場合、差分更新キャッシュもリセット
                self._last_page_split_count = 0
                self._cached_lines = []

            self.agent_full_text = text

            # 発話が終了していれば即座に完了させる
            if self.state == self.STATE_IDLE:
                self.agent_display_count = float(len(text))
                # 完全なテキストをページ分割（差分更新を使用）
                self.agent_text_pages = self._create_partial_display(len(text))
                self.agent_page_index = 0
            else:
                # タイピング中なら、現在の文字数に基づいて部分表示を生成
                display_count = int(self.agent_display_count)
                self.agent_text_pages = self._create_partial_display(display_count)
                if self.agent_text_pages:
                    self.agent_page_index = len(self.agent_text_pages) - 1

    def quit(self):
        """
        GUIを終了

        Pygameを正常に終了します。
        """
        pygame.quit()
