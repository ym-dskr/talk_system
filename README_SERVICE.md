# Kikai-kun Service Setup

このガイドでは、Kikai-kunをsystemdサービスとして設定し、バックグラウンドで常時ウェイクワードを待機させる方法を説明します。

## インストール

1. サービスをインストール:
```bash
cd /home/yutapi5/Programs/talk_system
./install_service.sh
```

2. サービスを起動:
```bash
sudo systemctl start kikai-kun.service
```

3. 起動時に自動起動させる（既にインストールスクリプトで設定済み）:
```bash
sudo systemctl enable kikai-kun.service
```

## サービス管理コマンド

### サービスの状態確認
```bash
sudo systemctl status kikai-kun.service
```

### サービスの起動
```bash
sudo systemctl start kikai-kun.service
```

### サービスの停止
```bash
sudo systemctl stop kikai-kun.service
```

### サービスの再起動
```bash
sudo systemctl restart kikai-kun.service
```

### ログの確認（リアルタイム）
```bash
sudo journalctl -u kikai-kun.service -f
```

### ログの確認（最新100行）
```bash
sudo journalctl -u kikai-kun.service -n 100
```

## アンインストール

サービスを削除する場合:
```bash
cd /home/yutapi5/Programs/talk_system
./uninstall_service.sh
```

## トラブルシューティング

### GUIが表示されない場合

サービスファイルの`DISPLAY`と`XAUTHORITY`環境変数を確認してください：

```bash
# 現在のDISPLAY値を確認
echo $DISPLAY

# 現在のXAUTHORITY値を確認
echo $XAUTHORITY
```

サービスファイル（`kikai-kun.service`）のEnvironment行を現在の値に合わせて修正してください。

### 音声デバイスが見つからない場合

.envファイルで正しいオーディオデバイスが設定されているか確認してください：

```bash
# 利用可能なオーディオデバイスを確認
python3 -c "import pyaudio; p = pyaudio.PyAudio(); [print(f'{i}: {p.get_device_info_by_index(i)[\"name\"]}') for i in range(p.get_device_count())]"
```

### サービスが起動しない場合

1. ログを確認:
```bash
sudo journalctl -u kikai-kun.service -n 50
```

2. 手動で実行してエラーを確認:
```bash
cd /home/yutapi5/Programs/talk_system
python3 main.py
```

3. 依存関係が全てインストールされているか確認:
```bash
pip3 install -r requirements.txt
```

## 注意事項

- サービスは`yutapi5`ユーザーで実行されます
- サービスは10秒間隔で自動再起動するように設定されています（クラッシュ時）
- ログは`journalctl`で確認できます
- GUIアプリケーションなので、X11サーバーが起動している必要があります
