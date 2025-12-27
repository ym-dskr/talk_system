# 実機テストチェックリスト

Phase 1 + Phase 2のリファクタリングが完了しました。
以下のチェックリストに従って、Raspberry Pi実機でのテストを実施してください。

## 前提条件

### 1. 環境確認
- [ ] `.env`ファイルが存在し、以下の環境変数が設定されている
  - `OPENAI_API_KEY`
  - `PICOVOICE_ACCESS_KEY`
  - `TAVILY_API_KEY`（オプション）
- [ ] Python仮想環境（`.venv`）がアクティブ化されている
- [ ] 必要なパッケージがインストールされている
  ```bash
  uv pip install pydantic pydantic-settings
  ```

### 2. ハードウェア確認
- [ ] マイクとスピーカーが接続されている
- [ ] オーディオデバイスのインデックスが正しく設定されている（`.env`）
  ```bash
  # オーディオデバイスの確認
  python3 -c "import pyaudio; p = pyaudio.PyAudio(); [print(f'{i}: {p.get_device_info_by_index(i)[\"name\"]}') for i in range(p.get_device_count())]"
  ```

---

## テストケース

### Phase 1.1: 状態管理のテスト

#### テスト1: 正常な状態遷移
- [ ] アプリケーション起動時に`LISTENING`状態になる
- [ ] ユーザー発話時に`PROCESSING`状態に遷移
- [ ] AI応答開始時に`SPEAKING`状態に遷移
- [ ] 応答完了後に`LISTENING`状態に戻る

**確認方法**: ログファイル（`logs/talk_system.log`）で状態遷移を確認
```bash
tail -f logs/talk_system.log | grep "State transition"
```

#### テスト2: 無効な状態遷移の検出
- [ ] 状態遷移エラーがログに記録される（もし発生した場合）

---

### Phase 1.2: ロギングのテスト

#### テスト3: ログファイルの生成
- [ ] `logs/talk_system.log`が自動生成される
- [ ] ログに以下の情報が含まれる
  - タイムスタンプ
  - ログレベル（INFO, DEBUG, ERROR）
  - モジュール名と行番号
  - メッセージ内容

**確認方法**:
```bash
ls -lh logs/
head -20 logs/talk_system.log
```

#### テスト4: ログローテーション
- [ ] 1日経過後、古いログが`talk_system.log.YYYY-MM-DD`にローテーションされる（長期運用時）
- [ ] 7日以上前のログが自動削除される（長期運用時）

---

### Phase 1.3: 例外処理とリカバリのテスト

#### テスト5: オーディオデバイスエラーのハンドリング
- [ ] オーディオデバイスが見つからない場合、エラーログが記録される
- [ ] デバイス一覧がログに出力される（診断情報）
- [ ] アプリケーションが`ERROR`状態になり、クラッシュせず終了する

**再現方法**: `.env`で存在しないデバイスインデックスを指定
```
INPUT_DEVICE_INDEX=999
```

#### テスト6: API接続エラーのリカバリ
- [ ] ネットワーク一時切断時、自動再接続が試行される（最大3回）
- [ ] 再接続成功時、正常に動作を継続する
- [ ] 再接続失敗時、エラーログが記録され、アプリが終了する

**再現方法**: テスト中にネットワークを一時的に切断

#### テスト7: クリーンアップの確認
- [ ] Ctrl+C（KeyboardInterrupt）でアプリを終了した場合でも、クリーンアップが実行される
- [ ] WebSocket接続が正常にクローズされる
- [ ] PyAudioリソースが解放される
- [ ] Porcupineリソースが解放される

**確認方法**: ログで`Cleaning up conversation app...`と`Conversation app exited`を確認

---

### Phase 2.1: 設定管理のテスト

#### テスト8: Pydantic設定の読み込み
- [ ] `.env`から設定が正しく読み込まれる
- [ ] `src/config_models.py`がエラーなくインポートされる
- [ ] 既存コードが動作する（後方互換性の確認）

**確認方法**:
```bash
python3 -c "from src.config_models import AppConfig; config = AppConfig(); print(config.audio.sample_rate)"
# 出力: 24000
```

#### テスト9: フォールバック動作
- [ ] pydanticがインストールされていない環境でも動作する（`config.py`のフォールバック）

**確認方法**: pydanticをアンインストールしてテスト（推奨しない）

---

### Phase 2.2: アーキテクチャドキュメントの確認

#### テスト10: ドキュメントの可読性
- [ ] `docs/ARCHITECTURE.md`が正しく表示される
- [ ] 並行処理モデルの説明が理解できる
- [ ] デバッグガイドが役立つ

---

## 機能テスト（エンドツーエンド）

### テスト11: 基本会話フロー
1. [ ] デーモンを起動: `python3 wake_word_daemon.py`
2. [ ] 「きかいくん」と呼びかけてアプリが起動する
3. [ ] 「今日の天気は？」と質問する
4. [ ] AIが応答する（音声とテキスト）
5. [ ] 無操作で3分後にタイムアウトし、アプリが終了する
6. [ ] デーモンがウェイクワード検知に戻る

### テスト12: 割り込み機能
1. [ ] AIが長い応答を話している最中に「きかいくん」と呼びかける
2. [ ] AI音声が即座に停止する
3. [ ] 新しい質問を受け付ける
4. [ ] 割り込みログが記録される

**確認方法**:
```bash
grep "INTERRUPT" logs/talk_system.log
```

### テスト13: Web検索機能
1. [ ] 「今日のニュースを教えて」と質問する
2. [ ] ログに`Executing web_search for: ...`が表示される
3. [ ] Tavily APIから検索結果が取得される
4. [ ] AIが検索結果を基に回答する

**確認方法**:
```bash
grep "web_search" logs/talk_system.log
```

### テスト14: 終了キーワード
1. [ ] 「バイバイ」「またね」「終了」などのキーワードを発話
2. [ ] 2秒後にアプリが終了する
3. [ ] クリーンアップが実行される

---

## パフォーマンステスト

### テスト15: レイテンシ確認
- [ ] ユーザー発話からAI応答開始までの遅延が許容範囲（2秒以内）
- [ ] 音声の途切れや遅延がない

### テスト16: 長時間稼働
- [ ] 30分以上の連続稼働でメモリリークがない
- [ ] ログファイルサイズが適切に管理されている

---

## トラブルシューティング

### エラー: `ModuleNotFoundError: No module named 'pydantic'`
**解決方法**:
```bash
uv pip install pydantic pydantic-settings
```

### エラー: `OSError: [Errno -9997] Invalid sample rate`
**原因**: オーディオデバイスが指定されたサンプルレートをサポートしていない
**解決方法**: `.env`でデバイスインデックスを正しく設定

### エラー: `RuntimeError: Failed to connect to OpenAI Realtime API`
**原因**: ネットワーク接続エラーまたはAPIキーが無効
**解決方法**:
1. ネットワーク接続を確認
2. `.env`で`OPENAI_API_KEY`が正しく設定されているか確認

### ログに`Invalid state transition`が出る
**原因**: 状態遷移ロジックのバグ
**解決方法**: ログの前後を確認し、どの遷移が無効だったかを特定。必要に応じて修正

---

## テスト完了後

### すべてのテストが合格した場合
- [ ] `TASK_TRACKER.md`のPhase 1とPhase 2を「完了」にマーク
- [ ] 必要に応じてPhase 3（機能拡張）またはPhase 4（プロダクション対応）に進む

### 問題が発覚した場合
- [ ] ログファイル（`logs/talk_system.log`）を確認
- [ ] エラーの詳細を記録
- [ ] 必要に応じて修正を実施
- [ ] 再テスト

---

## 次のステップ

テストが完了したら、以下のオプションから選択してください:

1. **Phase 3へ進む（機能拡張）**:
   - 割り込み処理の改善（フィードバック音、即時停止）
   - パーソナリティ切り替え機能

2. **Phase 4へ進む（プロダクション対応）**:
   - pyproject.tomlの作成（pip installable化）
   - systemdサービス化（自動起動）

3. **実運用開始**:
   - systemdサービスとして登録
   - 自動起動の設定
   - 長期運用の監視

---

## 参考資料

- リファクタリング計画: `REFACTORING_PLAN.md`
- タスク管理: `TASK_TRACKER.md`
- アーキテクチャ: `docs/ARCHITECTURE.md`
- ログファイル: `logs/talk_system.log`
