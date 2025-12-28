#!/usr/bin/env python3
"""
OpenAI Realtime APIモデルアクセステスト

使用可能なモデルを確認し、アクセス権をテストします。
"""

import asyncio
import websockets
import json
from config import OPENAI_API_KEY, REALTIME_URL

async def test_model_access(model_name):
    """指定されたモデルへのアクセスをテスト"""
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "realtime=v1"
    }
    url = f"{REALTIME_URL}?model={model_name}"

    print(f"\nTesting model: {model_name}")
    print(f"URL: {url}")

    try:
        async with websockets.connect(url, additional_headers=headers) as ws:
            # session.createdイベントを待つ
            message = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(message)

            if data.get("type") == "session.created":
                print(f"✓ SUCCESS: Model {model_name} is accessible")
                session = data.get("session", {})
                print(f"  Session ID: {session.get('id')}")
                return True
            else:
                print(f"✗ UNEXPECTED: Received {data.get('type')}")
                return False

    except asyncio.TimeoutError:
        print(f"✗ TIMEOUT: Connection timed out")
        return False
    except websockets.exceptions.WebSocketException as e:
        print(f"✗ CONNECTION ERROR: {e}")
        return False
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return False

async def main():
    """複数のモデルをテスト"""
    print("=" * 60)
    print("OpenAI Realtime API Model Access Test")
    print("=" * 60)

    models_to_test = [
        "gpt-4o-realtime-preview-2024-10-01",
        "gpt-4o-mini-realtime-preview-2024-12-17",
        "gpt-realtime-mini-2025-12-15",
        "gpt-realtime-2025-12-15",
        "gpt-4o-realtime-preview",  # エイリアス
        "gpt-4o-mini-realtime-preview",  # エイリアス
    ]

    results = {}
    for model in models_to_test:
        results[model] = await test_model_access(model)
        await asyncio.sleep(1)  # レート制限対策

    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    accessible = [m for m, r in results.items() if r]
    inaccessible = [m for m, r in results.items() if not r]

    if accessible:
        print(f"\n✓ Accessible models ({len(accessible)}):")
        for model in accessible:
            print(f"  - {model}")

    if inaccessible:
        print(f"\n✗ Inaccessible models ({len(inaccessible)}):")
        for model in inaccessible:
            print(f"  - {model}")

    if accessible:
        print(f"\n💡 Recommended: Use '{accessible[0]}'")
    else:
        print("\n⚠️  No models accessible. Please check your API key and account tier.")

if __name__ == "__main__":
    asyncio.run(main())
