import json
import os

from mkdocs.config import config_options
from mkdocs.plugins import BasePlugin
from mkdocs.utils import copy_file, log

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
JS_FILENAME = "audience_toggle.js"
CSS_FILENAME = "audience_toggle.css"
ASSET_PREFIX = "assets/audience_toggle"
CONFIG_SCRIPT_ID = "fcm-config"

DEFAULTS = {
    "storage_key": "fcm-mode",
    "query_param": None,
    "insert_selector": '[data-md-component="palette"]',
    "hide_toc_entries": True,
    "wrapper_class": None,
    "attribute": "data-fcm-hide",
}


class AudienceTogglePlugin(BasePlugin):
    config_scheme = (
        ("modes", config_options.Type(list, default=[])),
        ("storage_key", config_options.Type(str, default=DEFAULTS["storage_key"])),
        ("query_param", config_options.Type(str, default="")),
        ("insert_selector", config_options.Type(str, default=DEFAULTS["insert_selector"])),
        ("hide_toc_entries", config_options.Type(bool, default=True)),
        ("wrapper_class", config_options.Type(list, default=[])),
        ("attribute", config_options.Type(str, default=DEFAULTS["attribute"])),
        ("aria_label", config_options.Type(str, default="Content mode")),
        ("collapse_labels", config_options.Type(bool, default=False)),
        ("show_toast", config_options.Type(bool, default=True)),
    )

    def on_config(self, config):
        modes = self.config.get("modes") or []
        if not modes:
            log.warning(
                "audience_toggle: no 'modes' configured under the plugin's "
                "settings in mkdocs.yml — the toggle will not be inserted."
            )
        normalized = []
        seen_names = set()
        default_name = None
        for i, raw in enumerate(modes):
            if not isinstance(raw, dict) or "name" not in raw:
                raise ValueError(
                    "audience_toggle: each entry under 'modes' must be a "
                    "mapping with at least a 'name' key (got %r)" % (raw,)
                )
            name = str(raw["name"])
            if name in seen_names:
                raise ValueError(
                    "audience_toggle: duplicate mode name %r in 'modes'" % name
                )
            seen_names.add(name)
            entry = {
                "name": name,
                "label": str(raw.get("label", name.title())),
                "icon": raw.get("icon"),
                "description": raw.get("description"),
                "announcement": raw.get("announcement"),
            }
            if raw.get("default"):
                if default_name is not None:
                    raise ValueError(
                        "audience_toggle: more than one mode marked default: true"
                    )
                default_name = name
            normalized.append(entry)

        if normalized and default_name is None:
            default_name = normalized[0]["name"]

        self._runtime_config = {
            "modes": normalized,
            "defaultMode": default_name,
            "storageKey": self.config["storage_key"],
            "queryParam": self.config["query_param"] or None,
            "insertSelector": self.config["insert_selector"],
            "hideTocEntries": self.config["hide_toc_entries"],
            "wrapperClasses": list(self.config["wrapper_class"] or []),
            "attribute": self.config["attribute"],
            "ariaLabel": self.config["aria_label"],
            "collapseLabels": self.config["collapse_labels"],
            "showToast": self.config["show_toast"],
        }

        extra_css = list(config.get("extra_css", []))
        extra_js = list(config.get("extra_javascript", []))
        css_uri = f"{ASSET_PREFIX}/{CSS_FILENAME}"
        js_uri = f"{ASSET_PREFIX}/{JS_FILENAME}"
        if css_uri not in extra_css:
            extra_css.append(css_uri)
        if js_uri not in extra_js:
            extra_js.append(js_uri)
        config["extra_css"] = extra_css
        config["extra_javascript"] = extra_js

        return config

    def on_post_build(self, config):
        for filename in (JS_FILENAME, CSS_FILENAME):
            src_path = os.path.join(STATIC_DIR, filename)
            dest_path = os.path.join(config["site_dir"], ASSET_PREFIX, filename)
            copy_file(src_path, dest_path)

    def on_post_page(self, output, page, config):
        if not getattr(self, "_runtime_config", None) or not self._runtime_config["modes"]:
            return output
        script = (
            f'<script id="{CONFIG_SCRIPT_ID}" type="application/json">'
            f"{json.dumps(self._runtime_config)}"
            f"</script>"
        )
        marker = "</body>"
        if marker in output:
            return output.replace(marker, script + marker, 1)
        return output + script
