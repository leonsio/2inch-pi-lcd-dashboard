"""Layout and card rendering for TFT2."""

from PIL import Image, ImageDraw, ImageFont


class DashboardRenderer:
    def __init__(self, disp, cfg, card_builders, logger):
        self.disp = disp
        self.cfg = cfg
        self.card_builders = card_builders
        self.logger = logger

        self.width = disp.height
        self.height = disp.width
        self.rows = int(getattr(cfg, "GRID_ROWS", 3))
        self.cols = int(getattr(cfg, "GRID_COLS", 3))
        self.cell_width = self.width / self.cols
        self.cell_height = self.height / self.rows

        font_path = getattr(cfg, "FONT_PATH", "./font/JetBrainsMono-Medium.ttf")
        self.font_title = ImageFont.truetype(font_path, int(getattr(cfg, "FONT_TITLE", 15)))
        self.font_value = ImageFont.truetype(font_path, int(getattr(cfg, "FONT_VALUE", 24)))
        self.font_detail = ImageFont.truetype(font_path, int(getattr(cfg, "FONT_DETAIL", 13)))

    def _status_color(self, status):
        if status == "ok":
            return getattr(self.cfg, "C_OK", "#008000")
        if status == "warn":
            return getattr(self.cfg, "C_WARN", "#D08000")
        if status == "error":
            return getattr(self.cfg, "C_ERROR", "#FF0000")
        return getattr(self.cfg, "C_T1", "#000000")

    @staticmethod
    def _normalize_slot(slot):
        if isinstance(slot, str):
            return {"module": slot, "colspan": 1, "rowspan": 1}
        if isinstance(slot, dict):
            result = dict(slot)
            result.setdefault("colspan", 1)
            result.setdefault("rowspan", 1)
            return result
        return {"module": "", "colspan": 1, "rowspan": 1}

    def _slot_geometry(self, row, col, slot):
        colspan = max(1, min(int(slot.get("colspan", 1)), self.cols - col + 1))
        rowspan = max(1, min(int(slot.get("rowspan", 1)), self.rows - row + 1))
        x0 = (col - 1) * self.cell_width
        y0 = (row - 1) * self.cell_height
        x1 = x0 + self.cell_width * colspan
        y1 = y0 + self.cell_height * rowspan
        return x0, y0, x1, y1

    def _draw_card(self, draw, rect, card):
        x0, y0, x1, y1 = rect
        border = getattr(self.cfg, "C_GRID", "#000000")
        bg = getattr(self.cfg, "C_CELL_BG", "#FFFFFF")
        title_color = getattr(self.cfg, "C_T2", "#777777")
        detail_color = getattr(self.cfg, "C_T2", "#777777")

        draw.rectangle((x0, y0, x1, y1), fill=bg, outline=border, width=2)

        cx = (x0 + x1) / 2
        height = y1 - y0
        title_y = y0 + height * 0.18
        value_y = y0 + height * 0.52
        detail_y = y0 + height * 0.83

        draw.text((cx, title_y), str(card.get("title", "")), fill=title_color,
                  font=self.font_title, anchor="mm")
        draw.text((cx, value_y), str(card.get("value", "")),
                  fill=self._status_color(card.get("status", "normal")),
                  font=self.font_value, anchor="mm")
        detail = str(card.get("detail", ""))
        if detail:
            draw.text((cx, detail_y), detail, fill=detail_color,
                      font=self.font_detail, anchor="mm")

    def render_page(self, page, state):
        background = getattr(self.cfg, "C_SCREEN_BG", "#FFFFFF")
        image = Image.new("RGB", (self.width, self.height), background)
        draw = ImageDraw.Draw(image)

        layout = page.get("layout", {})
        occupied = set()

        for row in range(1, self.rows + 1):
            for col in range(1, self.cols + 1):
                if (row, col) in occupied:
                    continue

                key = f"row{row}cell{col}"
                raw_slot = layout.get(key)
                if raw_slot is None:
                    # Draw empty cell for a consistent grid.
                    self._draw_card(
                        draw,
                        self._slot_geometry(row, col, {"colspan": 1, "rowspan": 1}),
                        {"title": "", "value": "", "detail": "", "status": "normal"},
                    )
                    continue

                slot = self._normalize_slot(raw_slot)
                module_name = str(slot.get("module", "")).lower()
                builder = self.card_builders.get(module_name)
                if builder is None:
                    card = {
                        "title": "CONFIG",
                        "value": "UNKNOWN",
                        "detail": module_name or "empty",
                        "status": "error",
                    }
                    self.logger.warning("Unknown dashboard module '%s' in %s", module_name, key)
                else:
                    try:
                        card = builder(state)
                    except Exception:
                        self.logger.exception("Card builder failed: %s", module_name)
                        card = {
                            "title": module_name.upper(),
                            "value": "ERROR",
                            "detail": "renderer",
                            "status": "error",
                        }

                rect = self._slot_geometry(row, col, slot)
                self._draw_card(draw, rect, card)

                colspan = int(slot.get("colspan", 1))
                rowspan = int(slot.get("rowspan", 1))
                for rr in range(row, min(self.rows, row + rowspan - 1) + 1):
                    for cc in range(col, min(self.cols, col + colspan - 1) + 1):
                        occupied.add((rr, cc))

        self.disp.ShowImage(image)
