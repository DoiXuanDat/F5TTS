# # backend/websocket_service.py
# from fastapi import WebSocket, WebSocketDisconnect
# import asyncio
# import json
# from services.queue_service import get_task_status, get_queue_position, get_queue_length

# # Quản lý các kết nối WebSocket
# class ConnectionManager:
#     def __init__(self):
#         self.active_connections = {}  # user_id -> WebSocket
#         self.task_connections = {}    # task_id -> user_id

#     async def connect(self, websocket: WebSocket, user_id: str):
#         await websocket.accept()
#         self.active_connections[user_id] = websocket

#     def disconnect(self, user_id: str):
#         if user_id in self.active_connections:
#             del self.active_connections[user_id]

#     def register_task(self, task_id: str, user_id: str):
#         self.task_connections[task_id] = user_id

#     async def send_task_update(self, task_id: str, data: dict):
#         user_id = self.task_connections.get(task_id)
#         if user_id and user_id in self.active_connections:
#             await self.active_connections[user_id].send_json(data)

#     async def broadcast_queue_status(self):
#         """Gửi thông tin về trạng thái hàng đợi cho tất cả người dùng"""
#         message = {
#             "type": "queue_status",
#             "queue_length": get_queue_length(),
#             "active_users": len(self.active_connections)
#         }
#         for connection in self.active_connections.values():
#             await connection.send_json(message)

# manager = ConnectionManager()

# # Tích hợp vào FastAPI
# def setup_websockets(app):
#     @app.websocket("/ws/{user_id}")
#     async def websocket_endpoint(websocket: WebSocket, user_id: str):
#         await manager.connect(websocket, user_id)
#         try:
#             while True:
#                 # Nhận tin nhắn từ client
#                 data = await websocket.receive_text()
#                 try:
#                     message = json.loads(data)
#                     # Xử lý tin nhắn từ client
#                     if message.get("type") == "register_task":
#                         task_id = message.get("task_id")
#                         if task_id:
#                             manager.register_task(task_id, user_id)
#                             # Gửi trạng thái tác vụ hiện tại
#                             status = get_task_status(task_id)
#                             if status:
#                                 # Thêm thông tin vị trí trong hàng đợi
#                                 status["queue_position"] = get_queue_position(task_id)
#                                 await websocket.send_json({
#                                     "type": "task_update",
#                                     "task_id": task_id,
#                                     "data": status
#                                 })
#                 except json.JSONDecodeError:
#                     pass
                
#                 # Gửi cập nhật về trạng thái hàng đợi cho mọi người (mỗi 5 giây)
#                 await asyncio.sleep(5)
#                 await manager.broadcast_queue_status()
                
#         except WebSocketDisconnect:
#             manager.disconnect(user_id)

#     # Tác vụ nền định kỳ gửi cập nhật cho tất cả người dùng
#     @app.on_event("startup")
#     async def start_queue_status_broadcast():
#         asyncio.create_task(periodic_queue_status_broadcast())

#     async def periodic_queue_status_broadcast():
#         while True:
#             await manager.broadcast_queue_status()
#             await asyncio.sleep(10)  # Cập nhật mỗi 10 giây

#     return app