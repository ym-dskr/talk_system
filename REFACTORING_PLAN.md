# コードリファクタリング計画

## 概要

このドキュメントは、talk_systemプロジェクトのコードベースを整理し、可読性と保守性を向上させるためのリファクタリング計画です。

## 現状分析

### プロジェクト構成

```
talk_system/
├── config.py                    # 設定管理 ✓（日本語docstring済み）
├── wake_word_daemon.py          # ウェイクワード検知デーモン
├── conversation_app.py          # 会話GUIアプリケーション
├── requirements.txt             # 依存関係
├── src/                         # ソースコード
│   ├── audio.py                 # オーディオ入出力 ✓（日本語docstring済み）
│   ├── realtime_client.py       # OpenAI Realtime APIクライアント ✓（日本語docstring済み）
│   ├── wake_word.py             # ウェイクワード検知エンジン ✓（日本語docstring済み）
│   ├── gui.py                   # GUIハンドラー
│   └── animation/               # アニメーション管理
│       ├── __init__.py          # モジュール初期化 ✓
│       ├── animation_controller.py  # アニメーション統合管理 ✓（日本語docstring済み）
│       ├── character_renderer.py    # レイヤー合成 ✓（日本語docstring済み）
│       ├── eye_animator.py          # 瞬きアニメーション ✓（日本語docstring済み）
│       └── mouth_animator.py        # 口パクアニメーション ✓（日本語docstring済み）
├── assets/                      # アセット
│   └── character/               # キャラクター画像レイヤー
│       ├── base/                # ベース（体）
│       ├── eyes/                # 目のバリエーション
│       ├── mouths/              # 口のバリエーション
│       └── effects/             # エフェクト（将来用）
├── model/                       # Picovoiceウェイクワードモデル
│   ├── kikaikun_ja_raspberry-pi_v4_0_0.ppn
│   └── porcupine_params_ja.pv
├── examples/                    # 旧実装（DEPRECATED）
│   └── main.py                  # ❌ 削除予定
└── tools/                       # 開発ツール
    └── extract_layers_fixed.py # レイヤー抽出ツール
```

### システムアーキテクチャ

**2プロセス分離モデル:**

1. **wake_word_daemon.py（バックグラウンドデーモン）**
   - systemdサービスとして常駐
   - ウェイクワード「Kikai-kun」を検知
   - 検知時にconversation_app.pyを起動

2. **conversation_app.py（フォアグラウンドGUIアプリ）**
   - OpenAI Realtime APIと接続
   - リアルタイム音声対話
   - キャラクターアニメーション表示
   - 15秒の無操作で自動終了

**主要コンポーネント:**

- **AudioHandler**: PyAudioベースの音声入出力（48kHz↔24kHz自動リサンプリング）
- **WakeWordEngine**: Picovoice Porcupineによるウェイクワード検知
- **RealtimeClient**: OpenAI Realtime API WebSocketクライアント
- **GUIHandler**: Pygameベースのフルスクリーン表示とテキスト描画
- **AnimationController**: Live2D風のレイヤーベースキャラクターアニメーション

---

## 修正計画

### 1. 不要ファイルの削除

**削除対象:**

- `examples/main.py` - DEPRECATED（旧単一プロセス実装）
- `examples/` ディレクトリ（空になる場合）

**理由:**

- 旧アーキテクチャの実装で、現在は使用されていない
- コードの混乱を避けるため削除

---

### 2. ディレクトリ構造の整理

**変更:**

- `tools/` → `utils/` にリネーム
- `tools/extract_layers_fixed.py` → `utils/extract_layers.py` にリネーム

**理由:**

- "utils"はより一般的な命名規則
- "_fixed"サフィックスは開発時の一時的な命名で、本番には不要

**最終的なディレクトリ構造:**

```
talk_system/
├── config.py
├── wake_word_daemon.py
├── conversation_app.py
├── requirements.txt
├── src/
│   ├── __init__.py              # 新規作成
│   ├── audio.py
│   ├── realtime_client.py
│   ├── wake_word.py
│   ├── gui.py
│   └── animation/
│       ├── __init__.py
│       ├── animation_controller.py
│       ├── character_renderer.py
│       ├── eye_animator.py
│       └── mouth_animator.py
├── assets/
│   └── character/
│       ├── base/
│       ├── eyes/
│       ├── mouths/
│       └── effects/
├── model/
│   ├── kikaikun_ja_raspberry-pi_v4_0_0.ppn
│   └── porcupine_params_ja.pv
└── utils/                       # 旧tools/
    └── extract_layers.py        # 旧extract_layers_fixed.py
```

---

### 3. `src/__init__.py` の作成

**目的:**

- srcディレクトリを適切なPythonパッケージとして構成
- モジュールのエクスポートを明示的に管理

**内容:**

```python
"""
talk_system - Raspberry Pi上で動作するリアルタイム音声対話システム

このパッケージは、Picovoiceウェイクワード検知とOpenAI Realtime APIを組み合わせ、
ウェイクワード「Kikai-kun」で起動する音声対話システムを提供します。
"""

from .audio import AudioHandler
from .realtime_client import RealtimeClient
from .wake_word import WakeWordEngine
from .gui import GUIHandler

__all__ = [
    'AudioHandler',
    'RealtimeClient',
    'WakeWordEngine',
    'GUIHandler',
]
```

---

### 4. `conversation_app.py` の改善

**改善内容:**

- 日本語docstring追加
- クラスとメソッドへの詳細なコメント追加
- 定数の明確化
- 主要な処理フローにコメント追加

**改善ポイント:**

```python
"""
会話GUIアプリケーション

ウェイクワード検知後に起動され、OpenAI Realtime APIを使用した
リアルタイム音声対話を提供します。15秒の無操作で自動終了し、
デーモンがウェイクワード検知モードに戻ります。

主要機能:
- OpenAI Realtime APIとのWebSocket接続
- リアルタイム音声入出力
- Live2D風キャラクターアニメーション
- 発話テキストの画面表示
- 無操作タイムアウト（15秒）
"""
```

---

### 5. `wake_word_daemon.py` の改善

**改善内容:**

- 日本語docstring追加
- 処理フローの詳細なコメント追加
- リサンプリング処理の説明追加
- デバッグ出力の整理

**改善ポイント:**

```python
"""
ウェイクワード検知デーモン

systemdサービスとしてバックグラウンドで常駐し、
マイク入力からウェイクワード「Kikai-kun」を検知します。
検知時にconversation_app.pyを起動し、終了後は再びウェイクワード検知に戻ります。

動作フロー:
1. マイクから音声入力（48kHz → 24kHz → 16kHzとリサンプリング）
2. Picovoice Porcupineでウェイクワード検知
3. 検知時にGUIアプリを起動
4. GUIアプリ終了後、ウェイクワード検知を再開
"""
```

---

### 6. `src/gui.py` の改善

**改善内容:**

- 日本語docstring追加
- 状態定数の説明追加
- ページネーション処理の説明追加
- 日本語フォント処理の説明追加

**改善ポイント:**

```python
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
"""
```

---

### 7. コードの可読性向上

**全ファイル共通の改善:**

1. **定数の明確化**
   - マジックナンバーを定数として定義
   - 定数名に単位を含める（例: `TIMEOUT_SECONDS`）

2. **変数名の改善**
   - より説明的な変数名を使用
   - 略語を避け、意図が明確な命名

3. **コメントの追加**
   - 複雑な処理にはブロックコメント
   - トリッキーな実装には理由を記載

4. **型ヒントの追加（可能な範囲）**
   - 関数の引数と戻り値に型ヒント
   - より明確なインターフェース定義

5. **エラーハンドリングの明確化**
   - 例外処理の意図をコメント
   - ログ出力の一貫性

---

### 8. 割り込み（Barge-in）機能の実装 🆕

**現状の問題:**

現在の実装では、ユーザーの発話検知（`input_audio_buffer.speech_started`）は行われていますが、**実際の割り込み処理が未実装**です：

- ❌ AI音声再生の停止処理がない
- ❌ AI応答生成のキャンセルがない
- ❌ audio_queueのクリア処理がない
- ❌ Realtime APIへの中断指示がない

→ **結果：AIが喋っている最中にユーザーが話し始めても、AIの音声が最後まで再生され続ける**

**正統実装の設計:**

OpenAI Realtime APIとRaspberry Piの構成に最適な割り込み実装を行います。

**実装内容:**

#### 8.1. `src/realtime_client.py` への追加

```python
async def cancel_response(self):
    """
    現在のAI応答を中断する（割り込み処理）

    ユーザー発話開始時に呼び出され、以下の処理を行います：
    1. 進行中の応答生成を停止（response.cancel）
    2. サーバー側の音声バッファをクリア（output_audio_buffer.clear）
    3. 新しいユーザー入力に備える
    """
    await self.send_event({
        "type": "response.cancel"
    })
    await self.send_event({
        "type": "output_audio_buffer.clear"
    })
```

#### 8.2. `src/audio.py` への追加

```python
def stop_playback(self):
    """
    音声再生を即座に停止する

    割り込み時に呼び出され、現在再生中の音声を中断します。
    内部バッファもクリアし、次の再生に備えます。
    """
    if self.output_stream:
        # PyAudioストリームの停止とクリア
        self.output_stream.stop_stream()
        # 短い待機後に再起動（バッファクリアのため）
        time.sleep(0.05)
        self.output_stream.start_stream()
```

#### 8.3. `conversation_app.py` への追加

**修正箇所1: クラス変数の追加**

```python
class ConversationApp:
    def __init__(self):
        # ... 既存の初期化 ...

        # 🆕 割り込み管理用フラグ
        self.response_in_progress = False  # AI応答生成中かどうか
        self.interrupt_active = False      # 割り込み中フラグ（音声受信を無視）
```

**修正箇所2: `on_user_speech_start()` メソッド**

```python
def on_user_speech_start(self):
    """
    ユーザー発話開始時のコールバック

    割り込み処理を実行：
    1. 割り込みフラグを立てる（新しい音声チャンクを拒否）
    2. ローカル音声キューをクリア
    3. 音声再生を停止
    4. Realtime APIに応答キャンセルを送信
    5. GUI状態を更新
    """
    self.last_interaction_time = time.time()

    # 🆕 割り込みフラグを立てる（新しい音声チャンクを拒否）
    self.interrupt_active = True

    # 🆕 割り込み処理：音声キューをクリア
    while not self.audio_queue.empty():
        try:
            self.audio_queue.get_nowait()
        except asyncio.QueueEmpty:
            break

    # 🆕 割り込み処理：音声再生を停止
    self.audio.stop_playback()

    # 🆕 割り込み処理：Realtime APIに中断を通知（常に実行）
    asyncio.create_task(self.client.cancel_response())

    self.response_in_progress = False
    self.is_playing_response = False
    self.gui.set_state(2)  # PROCESSING
```

**修正箇所3: `handle_audio_delta()` メソッドの修正**

```python
def handle_audio_delta(self, audio_bytes):
    """
    AI応答音声受信コールバック

    割り込み中（interrupt_active=True）の場合は、受信した音声を破棄します。
    これにより、APIがキャンセル後も送信してくる音声チャンクを無視できます。
    """
    self.last_interaction_time = time.time()

    # 🆕 割り込み中は音声チャンクを破棄
    if self.interrupt_active:
        return

    self.audio_queue.put_nowait(audio_bytes)
```

**修正箇所4: `on_response_created()` メソッドの追加**

```python
def on_response_created(self):
    """
    AI応答生成開始イベントのハンドラー

    割り込み判定のために、応答生成中フラグを立てます。
    新しい応答が開始されたため、割り込みフラグをリセットします。
    """
    self.response_in_progress = True
    self.interrupt_active = False  # 🆕 新しい応答開始、割り込みフラグをリセット
```

**修正箇所5: `on_response_done()` メソッドの追加**

```python
def on_response_done(self):
    """
    AI応答生成完了イベントのハンドラー

    応答生成中フラグをクリアします。
    """
    self.response_in_progress = False
```

**実装の特徴:**

1. **4段階の割り込み処理**
   - 🆕 **音声受信ガード**: `interrupt_active`フラグで新規チャンクを拒否
   - **キュークリア**: 既にバッファされた音声キューをクリア
   - **再生停止**: 現在再生中の音声を即座に停止
   - **サーバー通知**: `response.cancel`でサーバー側の生成を中断

2. **レースコンディション対策（重要）**
   - 問題: キューをクリアしても、APIが`response.cancel`後も音声デルタを送信し続ける
   - 解決: `interrupt_active`フラグで`handle_audio_delta()`が新規チャンクを破棄
   - 再開: `on_response_created()`で新しい応答時にフラグをリセット
   - **これにより完全な割り込みが実現**

3. **子供向け対話に最適**
   - 即座に音声が止まる（待たせない）
   - サーバー側も完全にリセット
   - 次の発話にすぐ対応できる

4. **Raspberry Pi環境での安定性**
   - PyAudioストリームの再起動で確実にクリア
   - asyncioキューの安全なクリア処理
   - 最小限のオーバーヘッド

**期待される効果:**

- ✅ ユーザーが話し始めたら即座にAI音声が停止（音声キューへの追加をブロック）
- ✅ APIがキャンセル後も送信する音声を確実に破棄
- ✅ 自然な会話の流れ（人間同士の会話に近い）
- ✅ 子供でも直感的に使える
- ✅ システムリソースの無駄がない（不要な生成を停止）

---

## 実装順序

1. **ステップ1**: 修正計画MDファイルの作成 ✓
2. **ステップ2**: 割り込み機能の実装 🆕
   - 2.1. `src/realtime_client.py` に `cancel_response()` メソッド追加
   - 2.2. `src/audio.py` に `stop_playback()` メソッド追加
   - 2.3. `conversation_app.py` に割り込みハンドラー実装
   - 2.4. 動作確認（AI発話中にユーザーが話し始めるテスト）
3. **ステップ3**: 不要ファイルの削除
4. **ステップ4**: ディレクトリのリネーム
5. **ステップ5**: `src/__init__.py` の作成
6. **ステップ6**: `conversation_app.py` の改善（docstring/コメント追加）
7. **ステップ7**: `wake_word_daemon.py` の改善
8. **ステップ8**: `src/gui.py` の改善
9. **ステップ9**: 全体の動作確認

---

## 期待される効果

1. **可読性の向上**
   - 日本語docstringにより、日本語話者が理解しやすい
   - 処理フローがコメントで明確化

2. **保守性の向上**
   - 不要なファイルの削除により、混乱を回避
   - 明確なディレクトリ構造

3. **拡張性の向上**
   - モジュール化された構成
   - 新機能追加時の影響範囲が明確

4. **学習コストの低減**
   - 新しい開発者がコードベースを理解しやすい
   - docstringとコメントが充実

---

## 注意事項

- リファクタリング中も既存機能は維持する
- systemdサービスの設定変更は不要
- .envファイルやmodel/ディレクトリは変更しない
- 動作確認は各ステップ後に実施

---

**作成日**: 2025-12-22
**対象バージョン**: main branch (commit: aad8617)
