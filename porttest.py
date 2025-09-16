import websocket

for port in [8765, 8766]:
    try:
        ws = websocket.create_connection(f"ws://localhost:{port}")
        print(f"✅ 接続成功: {port}")
        ws.close()
    except Exception as e:
        print(f"❌ 接続失敗: {port} ({e})")
