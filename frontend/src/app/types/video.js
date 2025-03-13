export const VideoStatus = {
  PENDING: 'pending',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  ERROR: 'error'
};

export const VideoModel = {
  id: '',
  title: '',
  status: VideoStatus.PENDING,
  createdAt: null,
  url: null,
  error: null,
  metadata: null
};