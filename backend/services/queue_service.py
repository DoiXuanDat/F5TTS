# backend/services/queue_service.py
from celery import Celery
import time
import uuid
from datetime import datetime

# Khởi tạo Celery với Redis làm broker
celery_app = Celery('tts_tasks', broker='redis://localhost:6379/0', backend='redis://localhost:6379/1')

# Theo dõi trạng thái của các tác vụ
task_status = {}

@celery_app.task
def generate_audio_task(text, speaker_id, speed, user_id, task_id=None):
    """Celery task để xử lý tạo audio"""
    if not task_id:
        task_id = str(uuid.uuid4())
    
    # Cập nhật trạng thái: đang xử lý
    task_status[task_id] = {
        'status': 'processing',
        'progress': 0,
        'user_id': user_id,
        'start_time': datetime.now().isoformat(),
        'queue_position': 0  # Không còn trong hàng đợi
    }
    
    try:
        # Mô phỏng công việc tốn thời gian
        # Cập nhật tiến trình theo thời gian thực
        for i in range(10):
            time.sleep(0.5)  # Mô phỏng công việc tốn thời gian
            task_status[task_id]['progress'] = (i + 1) * 10
        
        # Gọi dịch vụ TTS thực tế của bạn ở đây
        # audio_data, sample_rate, relative_path = official_kokoro_tts_service.generate_speech(...)
        
        # Mô phỏng kết quả thành công
        result = {
            'audio_path': f'audio_{task_id}.wav',
            'status': 'completed',
            'duration': 10.5
        }
        
        # Cập nhật trạng thái: hoàn thành
        task_status[task_id] = {
            'status': 'completed',
            'progress': 100,
            'user_id': user_id,
            'result': result,
            'end_time': datetime.now().isoformat()
        }
        
        return result
        
    except Exception as e:
        # Cập nhật trạng thái: lỗi
        task_status[task_id] = {
            'status': 'error',
            'user_id': user_id,
            'error': str(e),
            'end_time': datetime.now().isoformat()
        }
        raise

def get_queue_length():
    """Trả về số lượng công việc đang chờ trong hàng đợi"""
    # Kết nối với Redis để lấy độ dài hàng đợi thực tế
    # Đây là mô phỏng
    processing_tasks = sum(1 for status in task_status.values() if status.get('status') == 'processing')
    return processing_tasks

def get_task_status(task_id):
    """Lấy trạng thái của một tác vụ cụ thể"""
    return task_status.get(task_id, {'status': 'not_found'})

def get_queue_position(task_id):
    """Ước tính vị trí trong hàng đợi của một tác vụ"""
    if task_id not in task_status:
        return -1
    
    # Đếm số tác vụ đang xử lý và đợi trước tác vụ này
    position = 0
    for tid, status in task_status.items():
        if status.get('status') == 'queued' and status.get('start_time', '') < task_status[task_id].get('start_time', ''):
            position += 1
    
    return position