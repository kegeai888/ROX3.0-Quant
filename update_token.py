import os
import sys
import time
import json
import websocket
import threading

def test_and_update_token(new_token):
    """
    测试新 Token 是否有效，如果有效则更新到 .env 文件
    """
    print(f"正在测试 Token: {new_token[:6]}...{new_token[-4:]}")
    
    # 1. 验证 Token 有效性 (通过 WebSocket 连接测试)
    success = False
    result_msg = ""
    
    def on_open(ws):
        print(">> 连接服务器成功，正在发送订阅请求...")
        # 订阅 700.HK (腾讯) 作为测试
        sub_payload = {
            "cmd_id": 22002,
            "seq_id": 123456,
            "trace": "test_token_update",
            "data": {
                "symbol_list": [
                    {"code": "700.HK", "depth_level": 5},
                ]
            }
        }
        ws.send(json.dumps(sub_payload))

    def on_message(ws, message):
        nonlocal success, result_msg
        data = json.loads(message)
        # print(f"收到消息: {data}")
        
        if 'ret' in data:
            if data['ret'] == 200:
                print(">> Token 验证成功！数据订阅正常。")
                success = True
                ws.close()
            else:
                print(f">> Token 验证失败: {data['msg']}")
                result_msg = data['msg']
                ws.close()
        elif 'cmd_id' in data and data['cmd_id'] == 22002:
             # 收到行情数据，说明成功
             print(">> 收到行情数据，Token 有效。")
             success = True
             ws.close()

    def on_error(ws, error):
        nonlocal result_msg
        print(f">> 连接错误: {error}")
        result_msg = str(error)

    # 启动 WebSocket 测试
    ws_url = f"wss://quote.tradeswitcher.com/quote-stock-b-ws-api?token={new_token}"
    ws = websocket.WebSocketApp(ws_url,
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error)
    
    # 运行 5 秒超时
    wst = threading.Thread(target=ws.run_forever)
    wst.daemon = True
    wst.start()
    
    # 等待结果
    for _ in range(50):
        if success or not wst.is_alive():
            break
        time.sleep(0.1)
        
    if not success:
        print(f"\n[错误] Token 无效或连接失败: {result_msg}")
        return False

    # 2. 更新 .env 文件
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    
    # 读取现有内容
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    else:
        lines = []

    # 更新或添加 Token
    found = False
    new_lines = []
    for line in lines:
        if line.strip().startswith('ALLTICK_TOKEN='):
            new_lines.append(f'ALLTICK_TOKEN={new_token}\n')
            found = True
        else:
            new_lines.append(line)
    
    if not found:
        new_lines.append(f'\nALLTICK_TOKEN={new_token}\n')

    # 写入文件
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
        
    print(f"\n[成功] .env 文件已更新！")
    print("请重启主程序以使新 Token 生效。")
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        token = sys.argv[1]
    else:
        token = input("请输入新的 AllTick Token: ").strip()
    
    if token:
        test_and_update_token(token)
    else:
        print("未输入 Token")
