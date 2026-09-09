"""Block/page navigation for the LCD dashboard.

This module is GPIO-agnostic. Future button callbacks only need to call
move_previous(), move_next(), open_selected(), and back().
"""

import re


_SLOT_RE = re.compile(r"^row(\d+)cell(\d+)$")


class DashboardNavigator:
    def __init__(self, pages, logger=None):
        self._pages = pages
        self.logger = logger
        self.current_page_index = self._first_browse_page_index()
        self.selected_key = None
        self.mode = "browse"  # browse | detail
        self._return_state = None
        self._ensure_selection(first=True)

    @property
    def current_page(self):
        return self._pages[self.current_page_index]

    def refresh_pages(self, pages):
        """Replace page config while preserving a valid position where possible."""
        current_name = self.current_page.get("name") if self._pages else None
        self._pages = pages
        if not self._pages:
            self.current_page_index = 0
            self.selected_key = None
            self.mode = "browse"
            self._return_state = None
            return

        if current_name:
            matching = self._page_index_by_name(current_name)
            if matching is not None:
                self.current_page_index = matching
            else:
                self.current_page_index = self._first_browse_page_index()
        self._ensure_selection(first=True)

    def _page_index_by_name(self, name):
        for index, page in enumerate(self._pages):
            if page.get("name") == name:
                return index
        return None

    def _browse_page_indices(self):
        return [
            index for index, page in enumerate(self._pages)
            if page.get("navigation", "browse") == "browse"
        ]

    def _first_browse_page_index(self):
        indices = self._browse_page_indices()
        return indices[0] if indices else 0

    @staticmethod
    def _normalize_slot(raw_slot):
        if isinstance(raw_slot, str):
            return {"module": raw_slot, "colspan": 1, "rowspan": 1, "selectable": True}
        if isinstance(raw_slot, dict):
            slot = dict(raw_slot)
            slot.setdefault("colspan", 1)
            slot.setdefault("rowspan", 1)
            slot.setdefault("selectable", True)
            return slot
        return None

    def selectable_entries(self, page=None):
        """Return selectable block anchors in row-major order.

        A spanning block appears exactly once at its anchor cell, so a 1x2/2x1/2x2
        card gets the same single navigation step as a normal 1x1 card.
        """
        page = page or self.current_page
        layout = page.get("layout", {})
        entries = []

        for key, raw_slot in layout.items():
            match = _SLOT_RE.match(key)
            if not match:
                continue
            slot = self._normalize_slot(raw_slot)
            if not slot or not slot.get("module") or slot.get("selectable") is False:
                continue
            row = int(match.group(1))
            col = int(match.group(2))
            entries.append({
                "key": key,
                "row": row,
                "col": col,
                "slot": slot,
            })

        entries.sort(key=lambda item: (item["row"], item["col"]))
        return entries

    def _ensure_selection(self, first=True):
        if not self._pages:
            self.selected_key = None
            return
        if self.mode != "browse":
            self.selected_key = None
            return

        entries = self.selectable_entries()
        keys = [entry["key"] for entry in entries]
        if self.selected_key in keys:
            return
        self.selected_key = keys[0 if first else -1] if keys else None

    def _adjacent_browse_page(self, direction):
        indices = self._browse_page_indices()
        if not indices:
            return self.current_page_index

        if self.current_page_index not in indices:
            return indices[0 if direction > 0 else -1]

        pos = indices.index(self.current_page_index)
        return indices[(pos + direction) % len(indices)]

    def _move(self, direction):
        if self.mode != "browse":
            return False

        entries = self.selectable_entries()
        if not entries:
            old_page = self.current_page_index
            self.current_page_index = self._adjacent_browse_page(direction)
            self._ensure_selection(first=direction > 0)
            return self.current_page_index != old_page

        keys = [entry["key"] for entry in entries]
        try:
            position = keys.index(self.selected_key)
        except ValueError:
            position = 0 if direction > 0 else len(keys) - 1
            self.selected_key = keys[position]
            return True

        new_position = position + direction
        if 0 <= new_position < len(keys):
            self.selected_key = keys[new_position]
            self._log_selection()
            return True

        # End/start of page: continue with the next/previous browse page.
        self.current_page_index = self._adjacent_browse_page(direction)
        self.selected_key = None
        self._ensure_selection(first=direction > 0)
        self._log_selection(page_changed=True)
        return True

    def move_next(self):
        """Equivalent to the future RIGHT button."""
        return self._move(1)

    def move_previous(self):
        """Equivalent to the future LEFT button."""
        return self._move(-1)

    def selected_entry(self):
        for entry in self.selectable_entries():
            if entry["key"] == self.selected_key:
                return entry
        return None

    def open_selected(self):
        """Open target_page of the selected block. Equivalent to future OK."""
        if self.mode != "browse":
            return False

        entry = self.selected_entry()
        if not entry:
            return False

        target_name = entry["slot"].get("target_page")
        if not target_name:
            if self.logger:
                self.logger.debug("Selected block %s has no target_page", self.selected_key)
            return False

        target_index = self._page_index_by_name(target_name)
        if target_index is None:
            if self.logger:
                self.logger.warning(
                    "target_page '%s' for %s does not exist",
                    target_name,
                    self.selected_key,
                )
            return False

        self._return_state = (self.current_page_index, self.selected_key)
        self.current_page_index = target_index
        self.selected_key = None
        self.mode = "detail"
        if self.logger:
            self.logger.info("Opened detail page '%s'", target_name)
        return True

    def back(self):
        """Return from a detail page to the originating selected block."""
        if self.mode != "detail" or self._return_state is None:
            return False

        self.current_page_index, self.selected_key = self._return_state
        self._return_state = None
        self.mode = "browse"
        self._ensure_selection(first=True)
        if self.logger:
            self.logger.info(
                "Returned to page '%s', block %s",
                self.current_page.get("name", "?"),
                self.selected_key,
            )
        return True

    def _log_selection(self, page_changed=False):
        if not self.logger:
            return
        prefix = "Page/selection changed" if page_changed else "Selection changed"
        self.logger.debug(
            "%s: page=%s block=%s",
            prefix,
            self.current_page.get("name", "?"),
            self.selected_key,
        )
