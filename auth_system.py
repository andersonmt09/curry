import json
import os
import shutil
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Set

class AuthSystem:
    def __init__(self, admin_id: int, allowed_group: int):
        self.admin_id = admin_id  # Admin principal
        self.allowed_group = allowed_group
        self.authorized_users: Dict[int, str] = {}  # {user_id: nombre}
        self.user_expirations: Dict[int, str | None] = {}  # {user_id: fecha ISO o None}
        self.user_added_by: Dict[int, Dict] = {}
        self.user_last_activity: Dict[int, str] = {}
        self.audit_log: List[Dict] = []
        self.banned_users: Set[int] = set()
        self.admin_users: Set[int] = set()  # Administradores adicionales
        self.active_groups: Dict[int, Dict] = {}
        self.loaded_group_config = False
        
        # Load existing data
        self.load_data()
        self.ensure_default_group()
    
    def load_data(self):
        """Load authorization data from auth_data.json or seed it on first deploy."""
        data_file = 'auth_data.json'
        seed_file = 'auth_data_seed.json'
        data = None
        source = None
        seeded_from_file = False

        try:
            if os.path.exists(data_file):
                print(f"[AUTH] Cargando datos desde {data_file}...")
                with open(data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                source = data_file

                is_empty = (
                    not data.get('authorized_users')
                    and not data.get('admin_users')
                    and not data.get('banned_users')
                    and not data.get('audit_log')
                )
                if is_empty and os.path.exists(seed_file):
                    print(f"[AUTH] {data_file} está vacío. Importando usuarios desde {seed_file}...")
                    with open(seed_file, 'r', encoding='utf-8') as f:
                        seed_data = json.load(f)
                    if seed_data.get('authorized_users') or seed_data.get('admin_users'):
                        data = seed_data
                        source = seed_file
                        seeded_from_file = True
            elif os.path.exists(seed_file):
                print(f"[AUTH] No existe {data_file}. Importando usuarios desde {seed_file}...")
                with open(seed_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                source = seed_file
                seeded_from_file = True

            if data is not None:
                print(f"[AUTH] Datos cargados desde {source}")

                # Migrar datos antiguos si existen
                if 'authorized_users' in data and isinstance(data['authorized_users'], list):
                    # Convertir lista antigua a diccionario
                    self.authorized_users = {int(user_id): f"Usuario_{user_id}" for user_id in data['authorized_users']}
                    self.user_expirations = {}
                    self.user_added_by = {}
                    self.user_last_activity = {}
                    print(f"[AUTH] Migrados usuarios de lista a diccionario: {self.authorized_users}")
                elif 'authorized_users' in data and isinstance(data['authorized_users'], dict):
                    # Asegurar que las claves sean enteros
                    self.authorized_users = {int(k): v for k, v in data['authorized_users'].items()}
                    self.user_expirations = {int(k): v for k, v in data.get('user_expirations', {}).items()}
                    self.user_added_by = {int(k): v for k, v in data.get('user_added_by', {}).items()}
                    self.user_last_activity = {int(k): v for k, v in data.get('user_last_activity', {}).items()}
                    print(f"[AUTH] Usuarios cargados como diccionario: {len(self.authorized_users)} usuarios")
                else:
                    self.authorized_users = {}
                    self.user_expirations = {}
                    self.user_added_by = {}
                    self.user_last_activity = {}
                    print("[AUTH] No se encontraron usuarios autorizados")

                self.banned_users = set(int(uid) for uid in data.get('banned_users', []))
                self.admin_users = set(int(uid) for uid in data.get('admin_users', []))
                self.audit_log = data.get('audit_log', [])
                self.loaded_group_config = 'active_groups' in data
                self.active_groups = {
                    int(k): v for k, v in data.get('active_groups', {}).items()
                    if str(k).lstrip("-").isdigit()
                }
                print(f"[AUTH] Estado final - Usuarios: {len(self.authorized_users)}, Baneados: {len(self.banned_users)}, Admins: {len(self.admin_users)}")

                if seeded_from_file:
                    print(f"[AUTH] Guardando importación inicial en {data_file}...")
                    self.save_data()
                return

            print("[AUTH] No existe auth_data.json ni auth_data_seed.json, iniciando con datos vacíos")
            self.authorized_users = {}
            self.user_expirations = {}
            self.user_added_by = {}
            self.user_last_activity = {}
            self.audit_log = []
            self.banned_users = set()
            self.admin_users = set()
            self.active_groups = {}
        except Exception as e:
            print(f"[AUTH] Error cargando datos: {e}")
            self.authorized_users = {}
            self.user_expirations = {}
            self.user_added_by = {}
            self.user_last_activity = {}
            self.audit_log = []
            self.banned_users = set()
            self.admin_users = set()
            self.active_groups = {}

    def ensure_default_group(self):
        """Keep the original configured group active after older data migrations."""
        try:
            group_id = int(self.allowed_group)
            if not self.loaded_group_config and group_id not in self.active_groups:
                self.active_groups[group_id] = {
                    "title": "Grupo principal",
                    "activated_by": self.admin_id,
                    "activated_by_name": "Sistema",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
        except Exception:
            pass

    def save_data(self):
        """Save authorization data to file"""
        try:
            self.create_backup()
            data = {
                'authorized_users': {str(k): v for k, v in self.authorized_users.items()},  # Convertir claves a string para JSON
                'user_expirations': {str(k): v for k, v in self.user_expirations.items()},
                'user_added_by': {str(k): v for k, v in self.user_added_by.items()},
                'user_last_activity': {str(k): v for k, v in self.user_last_activity.items()},
                'banned_users': list(self.banned_users),
                'admin_users': list(self.admin_users),
                'active_groups': {str(k): v for k, v in self.active_groups.items()},
                'audit_log': self.audit_log[-300:]
            }
            with open('auth_data.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"[AUTH] Datos guardados exitosamente: {len(self.authorized_users)} usuarios, {len(self.admin_users)} admins")
        except Exception as e:
            print(f"[AUTH] Error guardando datos: {e}")

    def create_backup(self):
        """Create a timestamped backup before overwriting auth_data.json."""
        try:
            if not os.path.exists('auth_data.json'):
                return
            os.makedirs('backups', exist_ok=True)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join('backups', f'auth_data_{timestamp}.json')
            if not os.path.exists(backup_path):
                shutil.copy2('auth_data.json', backup_path)
        except Exception as e:
            print(f"[AUTH] Error creando backup: {e}")
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin (principal or additional)"""
        return user_id == self.admin_id or user_id in self.admin_users
    
    def is_main_admin(self, user_id: int) -> bool:
        """Check if user is the main admin"""
        return user_id == self.admin_id

    def log_action(self, action: str, admin_id: int = None, admin_name: str = None, target_id: int = None, details: str = ""):
        """Registra una accion administrativa para auditoria."""
        self.audit_log.append({
            "action": action,
            "admin_id": admin_id,
            "admin_name": admin_name or "Admin",
            "target_id": target_id,
            "details": details,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        self.audit_log = self.audit_log[-300:]
        self.save_data()

    def update_activity(self, user_id: int):
        """Store last activity for tracking/admin checks."""
        user_id = int(user_id)
        now = datetime.now(timezone.utc)
        previous = self.user_last_activity.get(user_id)
        if previous:
            try:
                previous_dt = datetime.fromisoformat(previous)
                if previous_dt.tzinfo is None:
                    previous_dt = previous_dt.replace(tzinfo=timezone.utc)
                if now - previous_dt < timedelta(minutes=5):
                    self.user_last_activity[user_id] = now.isoformat()
                    return
            except Exception:
                pass
        self.user_last_activity[user_id] = now.isoformat()
        self.save_data()
    
    def add_admin(self, user_id: int, added_by: int = None, added_by_name: str = None) -> bool:
        """Add user as admin"""
        if user_id == self.admin_id:
            return False  # Ya es admin principal
        self.admin_users.add(user_id)
        self.log_action("add_admin", added_by, added_by_name, user_id)
        return True
    
    def remove_admin(self, user_id: int, removed_by: int = None, removed_by_name: str = None) -> bool:
        """Remove admin privileges (cannot remove main admin)"""
        if user_id == self.admin_id:
            return False  # No se puede remover admin principal
        if user_id in self.admin_users:
            self.admin_users.remove(user_id)
            self.log_action("remove_admin", removed_by, removed_by_name, user_id)
            return True
        return False
    
    def get_admin_users(self) -> List[int]:
        """Get list of additional admin users"""
        return list(self.admin_users)

    def is_group_active(self, chat_id: int) -> bool:
        """Check if a group is enabled to use the bot."""
        chat_id = int(chat_id)
        return chat_id in self.active_groups or (not self.loaded_group_config and chat_id == int(self.allowed_group))

    def get_group_data(self, chat_id: int) -> Dict:
        """Get saved metadata for an active Telegram group."""
        self.ensure_default_group()
        return self.active_groups.get(int(chat_id), {}).copy()

    def get_group_schedule(self, chat_id: int) -> Dict:
        """Get group schedule metadata."""
        return self.get_group_data(chat_id).get("schedule", {}) or {}

    def set_group_schedule(self, chat_id: int, start_time: str, end_time: str, updated_by: int = None, updated_by_name: str = None) -> bool:
        """Set the daily usage schedule for an active group."""
        chat_id = int(chat_id)
        if not self.is_group_active(chat_id):
            return False
        self.ensure_default_group()
        group = self.active_groups.setdefault(chat_id, {"title": f"Grupo {chat_id}"})
        group["schedule"] = {
            "enabled": True,
            "start": start_time,
            "end": end_time,
            "timezone": "America/Bogota",
            "updated_by": updated_by,
            "updated_by_name": updated_by_name or "Admin",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        self.log_action("set_group_schedule", updated_by, updated_by_name, chat_id, f"{start_time}-{end_time}")
        return True

    def clear_group_schedule(self, chat_id: int, updated_by: int = None, updated_by_name: str = None) -> bool:
        """Remove schedule restriction from an active group."""
        chat_id = int(chat_id)
        if not self.is_group_active(chat_id):
            return False
        self.ensure_default_group()
        self.active_groups.setdefault(chat_id, {"title": f"Grupo {chat_id}"}).pop("schedule", None)
        self.log_action("clear_group_schedule", updated_by, updated_by_name, chat_id)
        return True

    def is_group_schedule_open(self, chat_id: int, now: datetime = None) -> bool:
        """Check if an active group is inside its configured usage schedule."""
        schedule = self.get_group_schedule(chat_id)
        if not schedule or not schedule.get("enabled"):
            return True
        try:
            start_hour, start_minute = [int(part) for part in schedule["start"].split(":", 1)]
            end_hour, end_minute = [int(part) for part in schedule["end"].split(":", 1)]
            bogota_tz = timezone(timedelta(hours=-5))
            current = (now or datetime.now(bogota_tz)).astimezone(bogota_tz)
            current_minutes = current.hour * 60 + current.minute
            start_minutes = start_hour * 60 + start_minute
            end_minutes = end_hour * 60 + end_minute
            if start_minutes == end_minutes:
                return False
            if start_minutes <= end_minutes:
                return start_minutes <= current_minutes < end_minutes
            return current_minutes >= start_minutes or current_minutes < end_minutes
        except Exception:
            return True

    def activate_group(self, chat_id: int, title: str = None, activated_by: int = None, activated_by_name: str = None, invite_link: str = None) -> bool:
        """Enable bot usage inside a Telegram group."""
        chat_id = int(chat_id)
        already_active = chat_id in self.active_groups
        previous = self.active_groups.get(chat_id, {})
        self.active_groups[chat_id] = {
            "title": title or f"Grupo {chat_id}",
            "activated_by": activated_by,
            "activated_by_name": activated_by_name or "Admin",
            "invite_link": invite_link or previous.get("invite_link"),
            "schedule": previous.get("schedule"),
            "created_at": previous.get("created_at") or datetime.now(timezone.utc).isoformat()
        }
        self.log_action("activate_group", activated_by, activated_by_name, chat_id, self.active_groups[chat_id]["title"])
        return not already_active

    def deactivate_group(self, chat_id: int, deactivated_by: int = None, deactivated_by_name: str = None) -> bool:
        """Disable bot usage inside a Telegram group."""
        chat_id = int(chat_id)
        group = self.active_groups.pop(chat_id, None)
        if group:
            self.log_action("deactivate_group", deactivated_by, deactivated_by_name, chat_id, group.get("title", ""))
            return True
        return False

    def get_active_groups(self) -> Dict[int, Dict]:
        """Get active Telegram groups."""
        self.ensure_default_group()
        return self.active_groups.copy()

    def find_group_by_invite_link(self, invite_link: str) -> int | None:
        """Find an active group by its saved Telegram invite link."""
        if not invite_link:
            return None
        normalized = invite_link.strip().rstrip("/")
        for group_id, data in self.active_groups.items():
            saved_link = (data.get("invite_link") or "").strip().rstrip("/")
            if saved_link and saved_link == normalized:
                return int(group_id)
        return None
    
    def is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized"""
        if self.is_user_expired(user_id):
            self.remove_user(user_id)
            return False
        return user_id in self.authorized_users

    def is_user_expired(self, user_id: int) -> bool:
        """Check if an authorized user reached their expiration date."""
        expires_at = self.user_expirations.get(int(user_id))
        if not expires_at:
            return False
        try:
            expiration = datetime.fromisoformat(expires_at)
            if expiration.tzinfo is None:
                expiration = expiration.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) >= expiration.astimezone(timezone.utc)
        except Exception:
            return False
    
    def is_banned(self, user_id: int) -> bool:
        """Check if user is banned"""
        return user_id in self.banned_users

    def can_use_bot(self, user_id: int, chat_id: int, is_private: bool | None = None) -> bool:
        """
        Determina si un usuario puede usar el bot.
        - Primero verifica si está baneado
        - En privado solo usuarios VIP autorizados o administradores pueden usarlo
        - En grupos activos cualquier usuario no baneado puede usarlo gratis
        """
        user_id = int(user_id)
        chat_id = int(chat_id)
        
        # Si está baneado, no puede usar el bot de ninguna manera
        if self.is_banned(user_id):
            return False
            
        if is_private is None:
            try:
                is_private = chat_id > 0
            except Exception:
                is_private = False

        if self.is_admin(user_id):
            return True

        if not is_private:
            if self.is_group_active(chat_id):
                return self.is_group_schedule_open(chat_id)
            return False

        return self.is_authorized(user_id)
    
    def auto_register_user(self, user_id: int, username: str = None, first_name: str = None) -> bool:
        """Auto-registra un usuario con información disponible"""
        if self.is_banned(user_id):
            return False
            
        if not self.is_authorized(user_id):
            # Crear nombre descriptivo basado en información disponible
            if first_name:
                nombre = f"{first_name}_{user_id}"
            elif username:
                nombre = f"@{username}_{user_id}"
            else:
                nombre = f"Usuario_Auto_{user_id}"
            
            self.add_user(user_id, nombre)
            return True
        return False
    
    def add_user(self, user_id: int, nombre: str = None, expires_at: str | None = None, added_by: int = None, added_by_name: str = None) -> bool:
        """Add user to authorized list with optional name"""
        if nombre is None:
            nombre = f"Usuario_{user_id}"
        self.authorized_users[user_id] = nombre
        self.user_expirations[user_id] = expires_at
        self.user_added_by[user_id] = {
            "admin_id": added_by,
            "admin_name": added_by_name or "Admin",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self.save_data()
        self.log_action("add_vip", added_by, added_by_name, user_id, f"{nombre} | vence: {expires_at or 'Permanente'}")
        return True
    
    def remove_user(self, user_id: int, removed_by: int = None, removed_by_name: str = None) -> bool:
        """Remove user from authorized list"""
        if user_id in self.authorized_users:
            nombre = self.authorized_users.get(user_id)
            del self.authorized_users[user_id]
            self.user_expirations.pop(user_id, None)
            self.user_added_by.pop(user_id, None)
            self.user_last_activity.pop(user_id, None)
            self.save_data()
            self.log_action("remove_vip", removed_by, removed_by_name, user_id, nombre or "")
            return True
        return False
    
    def ban_user(self, user_id: int, banned_by: int = None, banned_by_name: str = None) -> bool:
        """Ban a user"""
        self.banned_users.add(user_id)
        self.log_action("ban", banned_by, banned_by_name, user_id)
        return True
    
    def unban_user(self, user_id: int, unbanned_by: int = None, unbanned_by_name: str = None) -> bool:
        """Unban a user"""
        if user_id in self.banned_users:
            self.banned_users.remove(user_id)
            self.log_action("unban", unbanned_by, unbanned_by_name, user_id)
            return True
        return False
    
    def get_authorized_users(self) -> Dict[int, str]:
        """Get dictionary of authorized users with names"""
        return self.authorized_users.copy()

    def get_user_expiration(self, user_id: int) -> str | None:
        """Get the ISO expiration date for an authorized user."""
        return self.user_expirations.get(int(user_id))

    def get_user_added_by(self, user_id: int) -> Dict:
        """Get audit metadata for who added a VIP user."""
        return self.user_added_by.get(int(user_id), {})

    def get_user_last_activity(self, user_id: int) -> str | None:
        """Get ISO last activity for a user."""
        return self.user_last_activity.get(int(user_id))

    def get_audit_log(self) -> List[Dict]:
        """Get audit log copy."""
        return list(self.audit_log)

    def cleanup_expired_users(self) -> List[int]:
        """Remove expired VIP users and return their IDs."""
        expired_users = [uid for uid in list(self.authorized_users) if self.is_user_expired(uid)]
        for uid in expired_users:
            nombre = self.authorized_users.get(uid, "")
            self.authorized_users.pop(uid, None)
            self.user_expirations.pop(uid, None)
            self.user_added_by.pop(uid, None)
            self.audit_log.append({
                "action": "expired_vip",
                "admin_id": None,
                "admin_name": "Sistema",
                "target_id": uid,
                "details": nombre,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            self.audit_log = self.audit_log[-300:]
        if expired_users:
            self.save_data()
        return expired_users
    
    def get_banned_users(self) -> List[int]:
        """Get list of banned users"""
        return list(self.banned_users)
    
    def get_stats(self) -> Dict:
        """Get authorization statistics"""
        return {
            'total_authorized': len(self.authorized_users),
            'total_banned': len(self.banned_users),
            'total_admins': len(self.admin_users) + 1,  # +1 por admin principal
            'allowed_group': self.allowed_group,
            'total_groups': len(self.get_active_groups())
        }
