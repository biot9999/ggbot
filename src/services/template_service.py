"""Telegram Advertising Bot - Message Template Service"""
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import uuid

from ..config import config
from ..models import MessageTemplate
from ..utils import render_template, setup_logging

logger = setup_logging("template_service")


class TemplateService:
    """Service for managing message templates."""

    def __init__(self):
        self.templates: Dict[str, MessageTemplate] = {}
        self._load_templates()

    def _get_templates_dir(self) -> Path:
        """Get path to templates directory."""
        return config.paths.target_dir.parent / "templates"

    def _get_templates_file(self) -> Path:
        """Get path to templates metadata file."""
        return self._get_templates_dir() / "templates.json"

    def _load_templates(self):
        """Load templates from file."""
        templates_file = self._get_templates_file()
        if templates_file.exists():
            with open(templates_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for template_id, template_data in data.items():
                    self.templates[template_id] = MessageTemplate.from_dict(template_data)
        logger.info(f"Loaded {len(self.templates)} templates")

    def _save_templates(self):
        """Save templates to file."""
        templates_dir = self._get_templates_dir()
        templates_dir.mkdir(parents=True, exist_ok=True)
        
        templates_file = self._get_templates_file()
        data = {
            template_id: template.to_dict()
            for template_id, template in self.templates.items()
        }
        with open(templates_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def create_text_template(
        self,
        name: str,
        text: str,
        buttons: Optional[List[Dict[str, str]]] = None,
    ) -> MessageTemplate:
        """Create a text-only template."""
        template_id = str(uuid.uuid4())[:8]
        template = MessageTemplate(
            id=template_id,
            name=name,
            text=text,
            buttons=buttons,
        )
        self.templates[template_id] = template
        self._save_templates()
        logger.info(f"Created text template: {template_id} ({name})")
        return template

    def create_media_template(
        self,
        name: str,
        media_path: Path,
        media_type: str,
        caption: Optional[str] = None,
        buttons: Optional[List[Dict[str, str]]] = None,
    ) -> MessageTemplate:
        """Create a template with media."""
        template_id = str(uuid.uuid4())[:8]
        
        # Copy media to templates directory
        templates_dir = self._get_templates_dir()
        templates_dir.mkdir(parents=True, exist_ok=True)
        
        media_dir = templates_dir / "media"
        media_dir.mkdir(parents=True, exist_ok=True)
        
        dest_path = media_dir / f"{template_id}_{media_path.name}"
        shutil.copy2(media_path, dest_path)
        
        template = MessageTemplate(
            id=template_id,
            name=name,
            text=caption,
            media_path=str(dest_path),
            media_type=media_type,
            buttons=buttons,
        )
        self.templates[template_id] = template
        self._save_templates()
        logger.info(f"Created media template: {template_id} ({name})")
        return template

    def create_forward_template(
        self,
        name: str,
        channel_username: str,
        message_id: int,
    ) -> MessageTemplate:
        """Create a template for forwarding channel messages."""
        template_id = str(uuid.uuid4())[:8]
        template = MessageTemplate(
            id=template_id,
            name=name,
            forward_from_channel=channel_username,
            forward_message_id=message_id,
        )
        self.templates[template_id] = template
        self._save_templates()
        logger.info(f"Created forward template: {template_id} ({name})")
        return template

    def update_template(
        self,
        template_id: str,
        name: Optional[str] = None,
        text: Optional[str] = None,
        buttons: Optional[List[Dict[str, str]]] = None,
    ) -> Optional[MessageTemplate]:
        """Update an existing template."""
        if template_id not in self.templates:
            return None
        
        template = self.templates[template_id]
        if name is not None:
            template.name = name
        if text is not None:
            template.text = text
        if buttons is not None:
            template.buttons = buttons
        
        self._save_templates()
        logger.info(f"Updated template: {template_id}")
        return template

    def delete_template(self, template_id: str) -> bool:
        """Delete a template."""
        if template_id not in self.templates:
            return False
        
        template = self.templates[template_id]
        
        # Delete media file if exists
        if template.media_path:
            media_path = Path(template.media_path)
            if media_path.exists():
                media_path.unlink()
        
        del self.templates[template_id]
        self._save_templates()
        logger.info(f"Deleted template: {template_id}")
        return True

    def get_template(self, template_id: str) -> Optional[MessageTemplate]:
        """Get a template by ID."""
        return self.templates.get(template_id)

    def get_all_templates(self) -> List[MessageTemplate]:
        """Get all templates."""
        return list(self.templates.values())

    def render_template(
        self,
        template_id: str,
        variables: Dict[str, str],
    ) -> Optional[str]:
        """Render a template's text with variables."""
        template = self.templates.get(template_id)
        if not template or not template.text:
            return None
        
        return render_template(template.text, variables)

    def get_template_preview(self, template_id: str) -> str:
        """Get a preview of a template."""
        template = self.templates.get(template_id)
        if not template:
            return "Template not found"
        
        preview = f"📝 {template.name}\n"
        preview += f"ID: {template.id}\n\n"
        
        if template.text:
            preview += f"Text:\n{template.text[:200]}"
            if len(template.text) > 200:
                preview += "..."
            preview += "\n"
        
        if template.media_path:
            preview += f"\n📎 Media: {template.media_type}\n"
        
        if template.forward_from_channel:
            preview += f"\n📢 Forward from: {template.forward_from_channel}\n"
            preview += f"Message ID: {template.forward_message_id}\n"
        
        if template.buttons:
            preview += f"\n🔘 Buttons: {len(template.buttons)}\n"
            for btn in template.buttons:
                preview += f"  - {btn.get('text', 'Button')}\n"
        
        return preview
