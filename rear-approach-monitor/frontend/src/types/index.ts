/**
 * 백엔드 Pydantic 모델(backend/app/models.py)과 1:1 대응되는 TypeScript 타입.
 * 필드명/열거값을 반드시 백엔드와 일치시킨다.
 */

export type Module = 'left' | 'right';

export type ObjectType =
  | 'person'
  | 'bicycle'
  | 'car'
  | 'motorcycle'
  | 'bus'
  | 'truck'
  | 'unknown';

export type Movement = 'approaching' | 'receding' | 'stationary';

export type RiskLevel = 'safe' | 'warning' | 'danger';

export type DataSource = 'simulation' | 'device';

export type SystemStatus = 'running' | 'stopped' | 'degraded';

/** 단일 감지 이벤트 (명세 7절 JSON 구조 기반) */
export interface DetectionEvent {
  timestamp: string;
  module: Module;
  detected: boolean;
  object_type: ObjectType;
  confidence: number;
  distance: number | null;
  speed: number | null;
  movement: Movement;
  risk_level: RiskLevel;
  track_id: string | null;
  source: DataSource;
}

/** DB 저장 기록 */
export interface DetectionRecord extends DetectionEvent {
  id: number;
  duration_ms: number | null;
}

/** 실시간 상태 스냅샷 (WebSocket live_state) */
export interface LiveState {
  system_status: SystemStatus;
  source: DataSource;
  left_connected: boolean;
  right_connected: boolean;
  object_count: number;
  detections: DetectionEvent[];
  highest_risk: RiskLevel;
  last_update: string;
  server_time: string;
}

export interface DeviceStatus {
  device_id: string;
  name: string;
  kind: 'central' | 'sensor_module' | 'alert_module' | 'camera' | 'radar';
  connected: boolean;
  battery_percent: number | null;
  last_seen: string | null;
  note: string | null;
}

export interface AppSettings {
  danger_distance_m: number;
  warning_distance_m: number;
  danger_speed_mps: number;
  notifications_enabled: boolean;
  sound_enabled: boolean;
  vibration_enabled: boolean;
  led_enabled: boolean;
  alert_cooldown_sec: number;
  detect_person: boolean;
  detect_bicycle: boolean;
  detect_car: boolean;
  detect_motorcycle: boolean;
  show_camera: boolean;
}

export interface Stats {
  today_detections: number;
  today_danger_alerts: number;
  by_object_type: Record<string, number>;
  by_hour: Record<string, number>;
  left_count: number;
  right_count: number;
}

/** WebSocket 메시지 공통 포맷 */
export interface WsMessage {
  type: 'live_state' | 'alert' | 'device_status' | 'pong' | 'mode_changed';
  data: unknown;
}
